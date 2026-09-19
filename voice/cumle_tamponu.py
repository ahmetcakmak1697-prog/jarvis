"""Akan metni TTS'e verilebilir cumlelere bolen tampon.

NEDEN VAR: model cevabi akitinca (KART: ADIM 3) kullanici 15-25 saniye
bos ekrana bakmak yerine ilk cumleyi bir saniye icinde DUYAR. Ama TTS'e
yarim cumle verilemez -- ses cumlenin ortasinda kesilir. Bu sinif akan
parcalari biriktirir ve yalniz TAM cumleleri disari verir.

NEDEN NAIF NOKTA ARAMASI YETMEZ (Turkce, ve bu projenin kendi ciktilari):

    "Oda 25.5 derece."       25.5'teki nokta cumle sonu DEGIL
    "Toplam 1621.27 kWh"     panelin her enerji degeri boyle
    "Saat 21.30'da geldim."  ayni tuzak
    "Dr. Ahmet aradi."       kisaltma noktasi cumle sonu DEGIL
    "Efendim... Buyurun."    uc nokta TEK sinirdir, uc tane degil

Yanlis bolme TTS'i cumle ortasinda konusturur; hic bolmemek akisi
oldurup tek parca bekletir. Ikisi de kullanicinin duydugu seyi bozar.
"""
from __future__ import annotations

__all__ = ["CumleTamponu"]

# Cumle bitirebilen isaretler. Virgul ve noktali virgul BILEREK yok:
# TTS'i her virgulde durdurmak konusmayi parcali ve robotik yapiyor.
_SON_ISARETLER = ".!?…"

# Noktasi cumle sonu OLMAYAN kisaltmalar. Genis tutuldu: fazla korumanin
# bedeli TTS'in bir cumle gec baslamasi, eksik korumanin bedeli cumlenin
# ortasinda konusmak. Ikincisi daha kotu.
_KISALTMALAR = frozenset({
    "vs", "vb", "bkz", "dr", "prof", "doc", "av", "sn", "orn", "yy",
    "tel", "cad", "sok", "mah", "no", "md", "hz", "sf", "cev", "ed",
    "alb", "gen", "yrd", "uzm", "mus", "ltd", "sti", "ac",
})

# Noktalama hic gelmezse TTS asla baslamaz. Bu sinir asilinca son
# bosluktan zorla bolunur -- guvenlik valfi, normal yol degil.
_ZORLA_BOL = 240

_TR_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _fold(s: str) -> str:
    """Turkce guvenli kucuk harf. Duz .lower() 'I' harfinde kacirir."""
    return s.translate(_TR_FOLD).lower()


class CumleTamponu:
    """Parca parca beslenir, tam cumleler dondurur.

    >>> t = CumleTamponu()
    >>> t.besle("Merhaba efen")
    []
    >>> t.besle("dim. Nasilsin?")
    ['Merhaba efendim.', 'Nasilsin?']
    >>> t.bitir()
    []
    """

    def __init__(self, zorla_bol: int = _ZORLA_BOL) -> None:
        self._tampon = ""
        self._zorla_bol = zorla_bol

    def besle(self, parca: str) -> list[str]:
        """Yeni parcayi ekle, tamamlanan cumleleri dondur."""
        if not parca:
            return []
        self._tampon += parca
        return self._cikar()

    def bitir(self) -> list[str]:
        """Akis bitti: yarim kalani da ver. Idempotent."""
        kalan = self._tampon.strip()
        self._tampon = ""
        return [kalan] if kalan else []

    # ------------------------------------------------------------------ #

    def _cikar(self) -> list[str]:
        cumleler: list[str] = []
        while True:
            kes = self._sinir(self._tampon)
            if kes is None:
                break
            ham = self._tampon[:kes].strip()
            self._tampon = self._tampon[kes:].lstrip()
            if ham:
                cumleler.append(ham)
        # guvenlik valfi: noktalamasiz uzun konusma
        while len(self._tampon) > self._zorla_bol:
            kes = self._tampon.rfind(" ", 0, self._zorla_bol)
            if kes <= 0:
                break
            ham = self._tampon[:kes].strip()
            self._tampon = self._tampon[kes:].lstrip()
            if ham:
                cumleler.append(ham)
        return cumleler

    def _sinir(self, s: str) -> int | None:
        """Tam cumle sonunun bitis indeksi; yoksa None."""
        n = len(s)
        i = 0
        while i < n:
            if s[i] not in _SON_ISARETLER:
                i += 1
                continue
            # "..." tek sinirdir: isaret dizisinin tamamini yut
            j = i
            while j < n and s[j] in _SON_ISARETLER:
                j += 1
            # Sinirdan sonra bosluk ya da metin sonu gerekir.
            # "25.5" burada elenir: noktadan sonra rakam var.
            if j < n and not s[j].isspace():
                i = j
                continue
            if self._yanlis_alarm(s, i, j, n):
                i = j
                continue
            return j
        return None

    def _yanlis_alarm(self, s: str, i: int, j: int, n: int) -> bool:
        # Kisaltma: noktadan onceki harf obegi bilinen bir kisaltma mi
        if s[i] == "." and j - i == 1:
            k = i
            while k > 0 and s[k - 1].isalpha():
                k -= 1
            kok = s[k:i]
            if kok and _fold(kok) in _KISALTMALAR:
                return True
        # Akisin TAM ucunda, rakamdan hemen sonra gelen nokta: ondalik
        # olabilir ve devami henuz gelmemistir ("Oda 25." -> "Oda 25.5").
        # Beklemenin bedeli bir parca gecikme; yanilmanin bedeli sayiyi
        # ikiye bolup yanlis okumak.
        if j >= n and i > 0 and s[i - 1].isdigit():
            return True
        return False
