"""memory/entity_extractor.py — konuşmadan varlık ve olgu çıkarma.

Eşik 3'ün ilk yarısı. Ahmet konuşurken ailesinden, işinden, sporundan,
sağlığından, borsadan ya da hobilerinden bahsettiğinde bunu yapılandırılmış
bir olguya çevirir.

**Neden LLM değil, kural tabanlı?** CLAUDE.md §7: "Deterministik routing =
güvenlik özelliği." Bir modele "bu cümleden olgu çıkar" demek, kalıcı hafızaya
ne yazılacağını modelin kaprisine bırakmak olurdu — aynı cümle iki kez farklı
sonuç üretebilir ve halüsinasyon doğrudan hafızaya sızar. Denetimde ölçüldü:
qwen2.5:7b, prompt'taki örnek cümleyi gerçek bir anı gibi aktarıyordu. Kural
tabanlı çıkarım test edilebilir, ücretsiz ve tekrarlanabilir.

**Türkçe (CLAUDE.md §6):** eşleştirme ASCII-fold üzerinden yapılır;
`"İ".lower()` combining-dot tuzağına düşülmez. Fold yardımcısı
`agents.data_classifier` içinde zaten var, yeniden yazılmadı.

**İki eksenli güvenlik (§7):** her olgu bir `sensitive` bayrağı taşır. Sağlık
ve finans hassastır — çağıran taraf bunları otomatik kalıcı hafızaya yazmaz,
onay kuyruğuna gönderir.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from agents.data_classifier import _fold_tr

__all__ = ["ExtractedFact", "extract", "SENSITIVE_CATEGORIES"]

#: Otomatik kalıcı hafızaya yazılmayan, onay kuyruğuna giden sınıflar.
SENSITIVE_CATEGORIES = frozenset({"health", "finance"})

#: Soru cümlesi işaretleri — soru bir olgu değildir, kaydedilmez.
_SORU_ISARETLERI = (
    "?", " mi", " mı", " mu", " mü", "ne zaman", "kim ", "nedir",
    "hangi", "kac ", "nerede", "nasil",
)

#: Olumsuzluk — "Eşim yok" bir olgu olarak kaydedilmez.
_OLUMSUZ = (" yok", " degil", " yokmus", "hic ")


@dataclass
class ExtractedFact:
    """Konuşmadan çıkarılmış tek bir olgu.

    `raw_text` her zaman doldurulur: bir olgunun hangi cümleden geldiği
    izlenebilir olmalı, yoksa hafıza denetlenemez.
    """

    category: str                      # family | work | sport | health | finance | hobby
    relation: str                      # es | ogul | kiz | anne | baba | self
    value: str                         # çıkarılan değer (isim, tarih, kurum...)
    raw_text: str                      # olgunun geldiği ham cümle
    attribute: Optional[str] = None    # ad | dogum_gunu | ... (yoksa None)
    sensitive: bool = False
    confidence: float = 0.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Akrabalık sözlüğü — fold'lanmış anahtar -> kanonik ilişki
# --------------------------------------------------------------------------- #

_AKRABALIK = {
    "esim": "es", "esimin": "es",
    "karim": "es", "karimin": "es",
    "kocam": "es", "kocamin": "es",
    "oglum": "ogul", "oglumun": "ogul",
    "kizim": "kiz", "kizimin": "kiz",
    "annem": "anne", "annemin": "anne",
    "babam": "baba", "babamin": "baba",
    "kardesim": "kardes", "kardesimin": "kardes",
}

# "esimin adi Dilara" / "kizimin adi Zeynep"
_AD_KALIBI = re.compile(
    r"(?P<akraba>\w+)\s+ad[iı]\s+(?P<ad>[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ]*)"
)
# "esim Dilara ile ..." — akrabalık hemen ardından ozel isim
_YANYANA_KALIBI = re.compile(
    r"(?P<akraba>\w+)\s+(?P<ad>[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ]*)"
)
# "esimin dogum gunu 3 Mart"
_DOGUM_KALIBI = re.compile(
    r"(?P<akraba>\w+)\s+do[gğ]um\s+g[uü]n[uü]\s+(?P<tarih>[\w\s]+?)(?:[.,;]|$)"
)

_AYLAR = (
    "ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz",
    "agustos", "eylul", "ekim", "kasim", "aralik",
)

# kategori -> (fold'lanmis anahtar kelimeler, hassas mi)
_KATEGORI_SINYALLERI = {
    "work": (("eshot", "isyer", "calisiyorum", "tekniker", "vardiya",
              "mesai", "is yerim"), False),
    "sport": (("kosuyorum", "kosu", "spor", "antrenman", "yuzuyorum",
               "bisiklet", "salon"), False),
    "health": (("alerji", "alerjim", "doktor", "ilac", "tansiyon",
                "hastalik", "ameliyat", "reçete", "recete"), True),
    "finance": (("borsa", "hisse", "portfoy", "yatirim", "temettu",
                 "fon", "kripto"), True),
    "hobby": (("hobi", "hobim", "arduino", "gitar", "kitap okuyorum",
               "fotograf", "model"), False),
}


def _soru_mu(fold: str) -> bool:
    return any(isaret in fold for isaret in _SORU_ISARETLERI)


def _olumsuz_mu(fold: str) -> bool:
    return any(isaret in fold for isaret in _OLUMSUZ)


def _akraba_coz(kelime: str) -> Optional[str]:
    return _AKRABALIK.get(_fold_tr(kelime))


def _aile_olgulari(metin: str) -> List[ExtractedFact]:
    olgular: List[ExtractedFact] = []
    gorulen: set = set()

    for eslesme in _DOGUM_KALIBI.finditer(metin):
        iliski = _akraba_coz(eslesme.group("akraba"))
        if not iliski:
            continue
        tarih = eslesme.group("tarih").strip()
        if not tarih or not any(ay in _fold_tr(tarih) for ay in _AYLAR):
            continue
        anahtar = (iliski, "dogum_gunu")
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        olgular.append(ExtractedFact(
            category="family", relation=iliski, attribute="dogum_gunu",
            value=tarih, raw_text=metin, confidence=0.9, tags=["aile", "tarih"],
        ))

    for kalip, guven in ((_AD_KALIBI, 0.95), (_YANYANA_KALIBI, 0.75)):
        for eslesme in kalip.finditer(metin):
            iliski = _akraba_coz(eslesme.group("akraba"))
            if not iliski:
                continue
            anahtar = (iliski, "ad")
            if anahtar in gorulen:
                continue
            ad = eslesme.group("ad").strip()
            if not ad or _fold_tr(ad) in _AKRABALIK:
                continue
            gorulen.add(anahtar)
            olgular.append(ExtractedFact(
                category="family", relation=iliski, attribute="ad",
                value=ad, raw_text=metin, confidence=guven, tags=["aile", "isim"],
            ))

    return olgular


#: Kısa kökler substring olarak aranmaz. CLAUDE.md §6: "kısa köklerde
#: false-positive'e dikkat." Ölçülen gerçek vaka: "fon" kökü
#: "Python fonksiyonu yaz" cümlesinde eşleşip onu finans olgusu sandı.
_KISA_KOK_SINIRI = 5


def _kelime_var(fold: str, anahtar: str) -> bool:
    """Anahtar kelime metinde geçiyor mu?

    Uzun kökler substring aranır (Türkçe sondan eklemeli: "alerji" →
    "alerjim"). Kısa kökler ise TAM KELIME aranır, yoksa başka kelimelerin
    içine gizlenirler.
    """
    if len(anahtar) < _KISA_KOK_SINIRI:
        return re.search(rf"\b{re.escape(anahtar)}\b", fold) is not None
    return anahtar in fold


def _kategori_olgulari(metin: str, fold: str) -> List[ExtractedFact]:
    olgular: List[ExtractedFact] = []
    for kategori, (anahtarlar, hassas) in _KATEGORI_SINYALLERI.items():
        vurus = next((a for a in anahtarlar if _kelime_var(fold, a)), None)
        if vurus is None:
            continue
        olgular.append(ExtractedFact(
            category=kategori,
            relation="self",
            attribute=None,
            value=_deger_sec(metin, anahtarlar, vurus),
            raw_text=metin,
            sensitive=hassas,
            confidence=0.7,
            tags=[kategori],
        ))
    return olgular


_OZEL_ISIM = re.compile(r"\b[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ]{2,}\b")


def _deger_sec(metin: str, anahtarlar, vurus: str) -> str:
    """Kategoriyi temsil eden en bilgilendirici parçayı seçer.

    Özel isim varsa (ESHOT, Arduino, THYAO) onu tercih eder; yoksa tetikleyen
    kelimenin kendisine düşer. Uydurma yapmaz — her iki durumda da değer
    cümlenin içinden gelir.

    Tetikleyicinin kendisi tercih edilmez: "Hobim Arduino ile uğraşmak"
    cümlesinde değer "Hobim" değil "Arduino" olmalı. Ama tetikleyici aynı
    zamanda aranan varlıksa ("ESHOT'ta çalışıyorum") o zaman değer odur —
    bu durumda metindeki **özgün yazımıyla** döner, fold'lanmış hâliyle değil.
    """
    del anahtarlar  # imza uyumu; karar yalnız tetikleyiciye bakar

    adaylar = [a for a in _OZEL_ISIM.findall(metin)
               if _fold_tr(a) not in _AKRABALIK]

    for aday in adaylar:
        if _fold_tr(aday) != vurus:
            return aday

    # Tek aday tetikleyicinin kendisiyse: özgün yazımı koru (ESHOT, THYAO).
    for aday in adaylar:
        if _fold_tr(aday) == vurus:
            return aday

    return vurus


def extract(text: Optional[str]) -> List[ExtractedFact]:
    """Bir konuşma turundan olguları çıkarır.

    Soru cümleleri ve olumsuz ifadeler olgu sayılmaz: "Eşimin doğum günü ne
    zaman?" bir sorudur, "Eşim yok" bir olumsuzlamadır — ikisi de hafızaya
    yazılacak bir bilgi değildir.
    """
    if not text or not str(text).strip():
        return []

    metin = str(text).strip()
    fold = _fold_tr(metin)

    if _soru_mu(fold) or _olumsuz_mu(fold):
        return []

    olgular = _aile_olgulari(metin)
    olgular.extend(_kategori_olgulari(metin, fold))
    return olgular
