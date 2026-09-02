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
from typing import Any, Dict, List, Optional

from agents.data_classifier import (
    _fold_tr,
    corrupted_fragments,
    keyword_present,
)

__all__ = [
    "TURKISH_TOKENIZER_PENALTY",
    "VRAM_CEILING_MB",
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
            "answer_chars": 0, "encoding_broken": [], "encoding_ok": False,
            "foreign_hits": [], "has_efendim": False, "ai_boilerplate": False,
            "persona_ok": None, "admits_no_record": False, "grounding_ok": None,
            "contains_ok": None, "length_ok": None,
            "passed": False, "failed_checks": ["empty"],
        }

    bozuk = corrupted_fragments(metin)
    encoding_ok = not bozuk
    if not encoding_ok:
        basarisiz.append("encoding")

    yabanci = _foreign_hits(fold)
    kalip = any(b in fold for b in _BOILERPLATE)
    efendim = "efendim" in fold

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
        "has_efendim": efendim,
        "ai_boilerplate": kalip,
        "persona_ok": persona_ok,
        "admits_no_record": itiraf,
        "grounding_ok": grounding_ok,
        "contains_ok": contains_ok,
        "length_ok": length_ok,
        "passed": not basarisiz,
        "failed_checks": basarisiz,
    }
