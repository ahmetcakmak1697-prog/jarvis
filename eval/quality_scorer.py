"""eval/quality_scorer.py — Türkçe kalite regresyonu için deterministik puanlama.

**Bu modül saftır.** Model çalıştırmaz, ağa çıkmaz, donanıma dokunmaz. Girdi
bir vaka tanımı + bir cevap metni; çıktı ölçülebilir sinyaller. Böylece
puanlama mantığı Ollama olmadan test edilebilir — `voice/stt.py`'de donanımı
mantıktan ayırdığımız ayrımın aynısı.

**Neyi ölçer, neyi ölçmez.** Ölçtüğü: kodlama bütünlüğü, yabancı kelime
sızıntısı, persona işaretleri, zemin davranışı (kayıt yokken itiraf), uzunluk.
Ölçmediği: **Türkçe akıcılık.** Akıcılık öznel; onu Ahmet'in kulağı
değerlendirir (FAZ-T1 deseni: deterministik kapı yalnız regresyonu tutar).

Bir ölçüt yalnızca vaka onu **beyan ettiyse** puanlanır. Beyan edilmemiş
ölçüt için `None` döner — uydurulmuş bir puan, puan yokluğundan kötüdür.

Bozuk-kodlama dedektörü `agents/data_classifier`'dan gelir; burada ikinci bir
kopyası tutulmaz (adopt-over-build).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from agents.data_classifier import (
    _fold_tr,
    corrupted_fragments,
    keyword_present,
)
from agents.persona import LEVELS, build_system_prompt

__all__ = [
    "TURKISH_TOKENIZER_PENALTY",
    "VRAM_CEILING_MB",
    "LEAK_NGRAM_WORDS",
    "REPETITION_NGRAM_WORDS",
    "REPETITION_MIN_HITS",
    "REPETITION_REPORT_MIN_HITS",
    "FOREIGN_RUN_WORDS",
    "TRUNCATION_MIN_CHARS",
    "score_answer",
    "turkish_equivalent_tps",
    "exceeds_vram_ceiling",
    "corrupted_fragments",
]

#: HARDWARE_AND_LOCAL_LLM_RESEARCH.md §4: Türkçe, İngilizce'ye göre kelime
#: başına ~1,9 kat token harcıyor. Ham tok/s bu yüzden yanıltıcıdır.
TURKISH_TOKENIZER_PENALTY = 1.9

#: Aynı belgenin §3'ü: 8 GB kartta pratik tavan ~6 GB model dosyası. Tepe
#: VRAM bunu aşan model katman katman RAM'e taşar (ölçüldü: mistral-nemo
#: 6880 MB → 25,8 tok/s; sığanlar ~78 tok/s).
VRAM_CEILING_MB = 6144

#: Türkçe cevapta bulunmaması gereken yabancı işaretçiler. Kısa olanlar
#: kelime sınırıyla aranır (CLAUDE.md §6: kısa kökte yanlış pozitif).
_FOREIGN = (
    "okay", "voila", "peut-etre", "peut-être",
    "sure,", "of course", "here's", "here is", "let's", "however,",
    "i'm ", "i am ", " the ", " and ", " you ", " your ", " with ",
    "that's", "certainly", "absolutely",
)

#: Yapay zekâ kalıpları — persona bunları açıkça yasaklıyor.
_BOILERPLATE = (
    "yardimci olabilirim", "yardimci olmaktan", "nasil yardimci",
    "size nasil", "memnuniyet duyarim", "mutluluk duyarim",
    "elbette, hemen", "tabii ki, hemen", "buradayim",
)

#: "Kaydım yok" ailesi — KÖK olarak tutulur, çekim olarak değil.
#:
#: Bu liste iki kez ölçümle düzeldi. Önce llama3.1 "erişemiyorum" dedi ve ilk
#: sürüm kaçırdı; sonra aynı model "erişe**medim**" dedi ve ikinci sürüm de
#: kaçırdı. Türkçe sondan eklemeli: tam çekim listelemek sonu gelmeyen bir iş.
#: Kök yazılır, `keyword_present` ekleri kendisi karşılar (CLAUDE.md §6).
#: Yanlış negatif burada pahalıdır: dürüst bir cevabı "uydurma" saymak,
#: modeli haksız yere suçlar ve ölçümü çürütür.
_NO_RECORD_ROOTS = (
    "erise",            # erişemedim / erişemiyorum / erişemem
    "erisim yok", "erisimim yok",
    "kaydim yok", "kayit yok", "kaydi yok", "kayit bulunmuyor",
    "kaydina sahip", "kayda sahip",
    "bilmiyorum", "bilgim yok", "bilgiye sahip",
    "sahip degilim", "bulunmuyor", "mevcut degil",
    "hatirlam",         # hatırlamıyorum / hatırlamam
    "veri yok", "elimde bir kayit", "elimde kayit",
)


# --------------------------------------------------------------------------- #
# Uc evrensel dedektor — 2026-09-01 kosusunun ELLE okunmasindan cikti
# --------------------------------------------------------------------------- #
#
# O kosu "63/64 gecti" dedi; 64 cevabin tamami elle okununca makinenin
# goremedigi uc kusur ailesi bulundu (`automation/KART_kalite_dedektorleri.md`).
# Ucu de `encoding_ok` gibi EVRENSEL: vaka beyan etmese de uygulanir, cunku
# hicbir vaka "sistem prompt'unu geri okuma" ya da "cumleyi yarida kesme"
# iznini beyan etmez.

#: Kelime ayirici. Kesme isareti korunur ("Ahmet'in" tek kelimedir); markdown
#: isaretleri (**, ##, -) dogal olarak dusar, boylece bicimi degistirilmis
#: ama kelimesi kelimesine ayni olan bir alinti yine yakalanir.
_WORD = re.compile(r"[0-9a-z']+")

#: Sizinti esigi: persona'nin TALIMAT bloklarindan bu uzunlukta bir dizi
#: cevapta aynen geciyorsa sizinti. Kart 6 oneriyordu; canli 64 cevapta
#: OLCULDU ve 6 yalnizca 2 vakayi yakaliyor (kartin isaret ettigi 6'dan).
#: 3'te 6 vaka yakalaniyor, yanlis pozitif yok. Aradaki degerler (4, 5)
#: "Reaktif degil, proaktifsin." gibi kisa ama kelimesi kelimesine alintilari
#: kaciriyor. Kartin kendi talimati: "esigi olcerek sec".
LEAK_NGRAM_WORDS = 3

#: Tekrar esigi: bu uzunlukta bir dizi, ayni cevapta bu kadar kez.
#: Kart bilerek muhafazakar (gozlenen dejenerasyonlar 4x idi). Olculdu:
#: 3 -> 3 vaka duser, 2 -> 8 vaka duser ve bu kosuda yanlis pozitif yok.
REPETITION_NGRAM_WORDS = 8
REPETITION_MIN_HITS = 3

#: RAPORLANAN ikinci esik -- puanlanmaz (`has_efendim` ile ayni sinif).
#:
#: A13, 2026-09-04, Ahmet: puanlanan esik 3'te KALIR. Gerekce: 2x'in
#: "yanlis pozitif yok" olcumu TEK modelin 64 cevabi uzerinde yapildi.
#: Bu takimin varlik sebebi modelleri kiyaslamak; llama3.1'de temiz olan
#: esik baska modelde, paralel kurulmus bir listede tokezleyebilir --
#: dedektor liste ISARETINI atip ICERIGINI biraktigi icin (ki bu dogru
#: karardir, gozlenen dejenerasyonlarin dordu de madde iclerindeydi).
#: Asimetri `_NO_RECORD_ROOTS`'un notuyla ayni: iyi bir cevabi haksiz yere
#: dusurmek olcumun kendisini curutur.
#:
#: Sayi yine de kaybolmasin diye yazilir: ikinci bir model olculdugunde
#: "esik 2 olsaydi ne olurdu" sorusuna takimi yeniden kosturmadan cevap
#: verilebilsin.
REPETITION_REPORT_MIN_HITS = 2

#: Yabanci dil sizintisi PUANLANIRKEN aranan sey tek kelime degil, ardisik
#: bir Ingilizce dizisi. Gerekce olculdu (3 kosu, 192 cevap): `_FOREIGN`
#: listesi oldugu gibi puanlansaydi 5 eslesmenin 3'u yanlis pozitif olurdu --
#: AC/DC albüm adlari ("The Razors Edge"), Python anahtar kelimesi
#: (`with open(...)`), Turkce ek almis ozel isim ("Rock and roll'un").
#: Karti "listeyi daralt" diyordu; olculdu, daraltmak yetmiyor: yanlis
#: pozitifleri ureten " and " ayni zamanda TEK gercek vakayi da yakalayan
#: isaretci. Ayrim kelimede degil UZUNLUKTA: gercek sizinti 7+ kelimelik bir
#: cumle, yanlis pozitifler en fazla 3 kelimelik ozel isim.
#:
#: Esik 4-7 araliginda ayni sonucu veriyor (2 vaka, 0 yanlis pozitif); 6
#: bilerek ortadan secildi. Raporlanan `foreign_hits` degismedi -- tek
#: kelime hala GORULUR, yalnizca puanlanmaz.
FOREIGN_RUN_WORDS = 6

#: Turkce'ye ozgu harfler: bir kelimede varsa o kelime Ingilizce dizisini keser.
_TR_LETTERS = frozenset("çğıöşü")

_TOKEN_SPLIT = re.compile(r"([^\w']+)")

#: Kesilme yalniz bu uzunlugun uzerinde aranir. Kisa ve uslupca bitirilmis
#: cevaplar ("Evet", "Merhaba Efendim") noktalama olmadan da mesrudur.
TRUNCATION_MIN_CHARS = 200

#: Bitmis bir cumlenin son isareti. Kapanmis kod citi ayrica kabul edilir.
_TERMINATORS = (".", "!", "?", ":", ")", "]", '"', "”", "…")

#: Persona'nin talimat metnindeki TIRNAKLI parcalar. Olculdu (2026-09-05):
#: talimat bolumunde 13 tirnakli parca var ve **hicbiri talimat degil** --
#: ya yasak kalip ornegi ("Size yardimci olmaktan mutluluk duyarim"), ya
#: modelin SOYLEMESI istenen cumle ("bu konusmanin kaydina erisimim yok",
#: "bilmiyorum"), ya uslup ornegi. Ucu de modelin uretmesi beklenen ya da
#: yasaklanan METINDIR; geri okundu diye sizinti sayilamaz.
#:
#: Bedeli olculmustu: qwen'in 6 "sizintisinin" 4'u tek bir yasak kalipti ve
#: ayni kusur `ai_boilerplate` sutununda ikinci kez sayiliyordu. Daha
#: sinsisi: persona modele "bu konusmanin kaydina erisimim yok de" diyor --
#: model dogru davranip bunu deseydi sizinti yiyecekti, hem de tam zemin
#: kategorisinde. Kimlik onsozunun disarida birakilmasiyla ayni mantik.
_QUOTED_EXAMPLE = re.compile(r'"[^"\n]*"')

#: Satir basi liste isareti. Yalniz ISARET atilir, madde ICERIGI atilmaz:
#: gozlenen dejenerasyonlarin dordu de numarali madde iclerinde yasiyor
#: (t2_longform_001'de ayni 15 kelimelik dizi dort ayri maddede). Madde
#: icerigini hariç tutmak dedektoru olculen ana kusura kor ederdi.
_LIST_MARKER = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+")


def _words(text: str) -> List[str]:
    return _WORD.findall(_fold_tr(text))


def _ngrams(kelimeler: List[str], n: int) -> List[str]:
    return [" ".join(kelimeler[i:i + n]) for i in range(len(kelimeler) - n + 1)]


def _instruction_ngrams() -> frozenset:
    """Persona'nin TALIMAT bloklarindan n-gram kumesi — SSOT'tan turetilir.

    Metin kopyalanmaz: `build_system_prompt()` ne uretiyorsa o olculur, yani
    persona degistiginde dedektor kendiliginden degisir.

    Iki sey DISARIDA birakilir, ikisi de olcumle:

    1. **Basliksiz kimlik onsozu.** Ahmet hakkinda OLGU tasiyor (ESHOT,
       polimer, İSG) ve "hafizanda benim hakkimda ne var?" sorusuna dogru
       cevap bu olgulari KULLANMAKTIR. Onsozu dahil etmek t1_tone_012'yi --
       dogru davranan bir cevabi -- kaldiriyordu.
    2. **Tirnakli ornekler** (`_QUOTED_EXAMPLE` notuna bak). Talimat degil,
       ornektirler; modelin uretmesi beklenen ya da yasaklanan metindir.

    Geriye kalan sey talimat cumlesidir ve hicbir kosulda geri okunmamali.
    """
    parcalar: set = set()
    for seviye in (None, *LEVELS):
        for ses in (False, True):
            prompt = build_system_prompt(level=seviye, voice_mode=ses)
            bas = prompt.find("## ")
            talimat = prompt[bas:] if bas >= 0 else prompt
            # Silmek degil AYIRICI ile degistirmek: silinseydi tirnagin iki
            # yanindaki kelimeler birlesip persona'da HIC gecmeyen bir dizi
            # uretirdi ve dedektor olmayan bir cumleyi arardi.
            talimat = _QUOTED_EXAMPLE.sub("\n", talimat)
            parcalar |= set(_ngrams(_words(talimat), LEAK_NGRAM_WORDS))
    return frozenset(parcalar)


_LEAK_NGRAMS = _instruction_ngrams()


def _prompt_leak_hits(text: str) -> List[str]:
    """Cevapta persona talimatindan aynen gecen diziler (en fazla 3 ornek)."""
    ortak = _LEAK_NGRAMS.intersection(_ngrams(_words(text), LEAK_NGRAM_WORDS))
    # Tamami degil ilk uc ornek yazilir: t1_mix_003 gibi persona'yi butunuyle
    # dokmus bir cevapta 82 dizi eslesiyor ve rapor okunmaz hale geliyor.
    return sorted(ortak)[:3]


def _prose_only(text: str) -> str:
    """Kod bloklarini atar, liste ISARETLERINI temizler (icerigi birakir)."""
    satirlar: List[str] = []
    kod_icinde = False
    for satir in text.splitlines():
        if satir.lstrip().startswith("```"):
            kod_icinde = not kod_icinde
            continue
        if kod_icinde:
            continue
        satirlar.append(_LIST_MARKER.sub("", satir))
    return "\n".join(satirlar)


def _top_repeat(text: str) -> tuple[Optional[str], int]:
    """En sik gecen dizi ve kac kez gectigi. Metin cok kisaysa ``(None, 0)``.

    Iki esik ayni sayimdan turer: biri puanlanir, biri yalniz raporlanir.
    """
    sayac = Counter(_ngrams(_words(_prose_only(text)), REPETITION_NGRAM_WORDS))
    if not sayac:
        return None, 0
    ifade, adet = sayac.most_common(1)[0]
    return ifade, adet


def _is_truncated(text: str) -> bool:
    """Cevap cumle ortasinda mi bitiyor?"""
    if len(text) <= TRUNCATION_MIN_CHARS:
        return False
    # Sondaki markdown vurgusu bitis isaretini gizleyebilir: "...onemlidir.**"
    kirpik = text.rstrip().rstrip("*_ \t")
    if kirpik.endswith("```") and kirpik.count("```") % 2 == 0:
        return False
    return not kirpik.endswith(_TERMINATORS)


def turkish_equivalent_tps(raw_tps: float) -> float:
    """Ham tok/s → Türkçe-eşdeğer tok/s."""
    return (raw_tps or 0) / TURKISH_TOKENIZER_PENALTY


def exceeds_vram_ceiling(peak_mb: Optional[float]) -> Optional[bool]:
    """Tepe VRAM belgelenmiş pratik tavanı aşıyor mu? Ölçüm yoksa None."""
    if peak_mb is None:
        return None
    return float(peak_mb) > VRAM_CEILING_MB


def _foreign_hits(fold: str) -> List[str]:
    bulunan = []
    for kelime in _FOREIGN:
        if len(kelime.strip()) < 5 and " " not in kelime.strip():
            if re.search(rf"\b{re.escape(kelime.strip())}\b", fold):
                bulunan.append(kelime)
        elif kelime in fold:
            bulunan.append(kelime)
    return bulunan


def _non_turkish_runs(text: str) -> List[List[str]]:
    """Ardisik "Turkce gorunmeyen" kelime dizileri.

    Diziyi KESEN sey: Turkce'ye ozgu harf, kesme isareti (Turkce ek almis
    ozel isim: "roll'un"), rakam, noktalama ve satir sonu.
    """
    diziler: List[List[str]] = []
    simdiki: List[str] = []
    for parca in _TOKEN_SPLIT.split(text):
        if not parca.strip():
            if "\n" in parca and simdiki:
                diziler.append(simdiki)
                simdiki = []
            continue
        katlanmis = _fold_tr(parca)
        keser = ("'" in parca
                 or any(c in _TR_LETTERS for c in parca.lower())
                 or not katlanmis.isalpha())
        if keser:
            if simdiki:
                diziler.append(simdiki)
            simdiki = []
        else:
            simdiki.append(katlanmis)
    if simdiki:
        diziler.append(simdiki)
    return diziler


def _is_english_prompt(prompt: Optional[str]) -> bool:
    """Soru Ingilizce mi? Persona: "Ahmet İngilizce yazarsa İngilizce yanıt
    verirsin." Oyleyse Ingilizce cevap kusur degil, KURALA UYMAKTIR.

    Vaka setindeki tek ornek `t1_mix_001` ("hey can you check the system
    status?"). Bu koruma olmasa persona'sina uyan model dusurulurdu.
    """
    if not prompt:
        return False
    metin = str(prompt)
    if any(c in _TR_LETTERS for c in metin.lower()):
        return False
    return bool(_foreign_hits(" " + _fold_tr(metin) + " "))


def _foreign_run(text: str) -> Optional[str]:
    """Turkce metne yapistirilmis Ingilizce CUMLE; yoksa None."""
    for dizi in _non_turkish_runs(_prose_only(text)):
        if (len(dizi) >= FOREIGN_RUN_WORDS
                and _foreign_hits(" " + " ".join(dizi) + " ")):
            return " ".join(dizi)
    return None


def score_answer(answer: Optional[str], case: Dict[str, Any]) -> Dict[str, Any]:
    """Tek bir cevabı puanlar.

    Dönen sözlükteki her ölçüt üç durumdan biridir: ``True`` (geçti),
    ``False`` (kaldı), ``None`` (vaka bunu beyan etmedi, puanlanmadı).
    """
    metin = (answer or "").strip()
    fold = _fold_tr(metin)
    basarisiz: List[str] = []

    if not metin:
        return {
            # Boş metnin kodlaması bozuk DEĞİLDİR; hiç kodlaması yoktur.
            # Eskiden burada `False` yazıyordu ve rapor bunu "Bozuk kodlama"
            # diye özetliyordu (2026-09-09'da 15 ağ kopması UTF-8 hatası
            # sanıldı). Düşme sebebi `empty` olarak zaten doğru yazılıyor.
            "answer_chars": 0, "encoding_broken": [], "encoding_ok": True,
            "foreign_hits": [], "foreign_ok": True, "foreign_run": None,
            "has_efendim": False, "ai_boilerplate": False,
            "persona_ok": None, "admits_no_record": False, "grounding_ok": None,
            "contains_ok": None, "length_ok": None,
            "prompt_leak": False, "prompt_leak_hits": [],
            "repetition_ok": True, "repeated_phrase": None,
            "repeated_phrase_2x": None, "truncated": False,
            "passed": False, "failed_checks": ["empty"],
        }

    bozuk = corrupted_fragments(metin)
    encoding_ok = not bozuk
    if not encoding_ok:
        basarisiz.append("encoding")

    yabanci = _foreign_hits(fold)
    kalip = any(b in fold for b in _BOILERPLATE)
    efendim = "efendim" in fold

    # Persona kalibi ADIYLA yasakliyor; bu, kodlama bozuklugu kadar nesnel
    # bir kusurdur. 192 cevapta olculdu, yanlis pozitif yok.
    if kalip:
        basarisiz.append("boilerplate")

    # Ingilizce CUMLE sizintisi. Soru Ingilizce ise puanlanmaz: persona
    # "Ahmet İngilizce yazarsa İngilizce yanıt verirsin" diyor.
    yabanci_dizi = (None if _is_english_prompt(case.get("prompt"))
                    else _foreign_run(metin))
    if yabanci_dizi:
        basarisiz.append("foreign")

    # Uc evrensel dedektor: vaka beyan etmese de uygulanir.
    sizinti = _prompt_leak_hits(metin)
    if sizinti:
        basarisiz.append("prompt_leak")

    en_sik, tekrar_adedi = _top_repeat(metin)
    tekrar = en_sik if tekrar_adedi >= REPETITION_MIN_HITS else None
    if tekrar:
        basarisiz.append("repetition")
    # Raporlanan esik `basarisiz`'a GIRMEZ: olculur, yazilir, puanlanmaz.
    tekrar_2x = en_sik if tekrar_adedi >= REPETITION_REPORT_MIN_HITS else None

    kesik = _is_truncated(metin)
    if kesik:
        basarisiz.append("truncated")

    persona_ok: Optional[bool] = None
    if case.get("expect_efendim") is not None:
        persona_ok = (efendim is bool(case["expect_efendim"]))
        if not persona_ok:
            basarisiz.append("persona")

    # Kok eslesmesi paylasilan yardimciyla: Turkce ekleri o karsiliyor.
    itiraf = any(keyword_present(fold, k) for k in _NO_RECORD_ROOTS)
    grounding_ok: Optional[bool] = None
    if case.get("must_admit_no_record") is not None:
        beklenen = bool(case["must_admit_no_record"])
        grounding_ok = (itiraf is beklenen) if beklenen else True
        if not grounding_ok:
            basarisiz.append("grounding")

    contains_ok: Optional[bool] = None
    gruplar = case.get("must_contain_any")
    if gruplar:
        contains_ok = all(
            any(_fold_tr(sec) in fold for sec in grup) for grup in gruplar
        )
        if not contains_ok:
            basarisiz.append("contains")

    length_ok: Optional[bool] = None
    if case.get("min_chars") is not None:
        length_ok = len(metin) >= int(case["min_chars"])
        if not length_ok:
            basarisiz.append("length")

    return {
        "answer_chars": len(metin),
        "encoding_broken": bozuk,
        "encoding_ok": encoding_ok,
        "foreign_hits": yabanci,
        "foreign_ok": yabanci_dizi is None,
        "foreign_run": yabanci_dizi,
        "has_efendim": efendim,
        "ai_boilerplate": kalip,
        "persona_ok": persona_ok,
        "admits_no_record": itiraf,
        "grounding_ok": grounding_ok,
        "contains_ok": contains_ok,
        "length_ok": length_ok,
        "prompt_leak": bool(sizinti),
        "prompt_leak_hits": sizinti,
        "repetition_ok": tekrar is None,
        "repeated_phrase": tekrar,
        "repeated_phrase_2x": tekrar_2x,
        "truncated": kesik,
        "passed": not basarisiz,
        "failed_checks": basarisiz,
    }
