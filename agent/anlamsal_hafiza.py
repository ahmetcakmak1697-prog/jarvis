"""agent/anlamsal_hafiza.py — sohbet gecmisinde anlamsal arama (OKUMA yolu).

KART_VEKTOR_HAFIZA ADIM 1-2. Bu modul yalniz **okur** ve bir **indeks**
tutar; kalici hafizaya yazmaz.

Ayrim neden onemli (CLAUDE.md 7.1a):

    `VectorMemory`'nin varsayilan koleksiyonu `jarvis_memories`, ONAYLANMIS
    bilgi kartlarinin gittigi yerdir -- oraya yalniz `knowledge_card_promoter`
    yazar. Bu modul AYRI bir koleksiyon kullanir (`sohbet_indeksi`) ve
    icerigi SQLite sohbet gecmisinden TURETILMISTIR: silinebilir, yeniden
    kurulabilir. Ayni koleksiyon paylasilsaydi `clear_history` indeksi
    silerken onaylanmis kartlari da silerdi -- sessiz ve geri donusu olmayan
    bir veri kaybi.

Gomme modeli neden ayrica veriliyor (olculdu, 2026-09-23):

    Chroma'nin varsayilani `all-MiniLM-L6-v2`, INGILIZCEDIR. Alti Turkce
    sorguluk bir sinavda -- her sorgu dogru belgeyle tek kelime bile
    paylasmayacak sekilde kuruldu -- **1/6** isabet aldi; alti belge
    arasindan rastgele secmenin beklentisi de 1/6'dir. Ayni sinavda
    `paraphrase-multilingual-MiniLM-L12-v2` **5/6** aldi.

    Yani varsayilanla kurulacak bir "anlamsal hafiza" Turkce'de arama
    yapmiyor, kura cekiyor olurdu.

Model yuklemesi **13,4 saniye** surer (olculdu). Bu yuzden arka planda,
bir is parcaciginda isitilir: kullanici ilk sorusunu sorana kadar hazir
olur; hazir degilse o tur icin hafiza **atlanir**, beklenmez. Bos zemin,
gec gelen zeminden iyidir.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

__all__ = [
    "SOHBET_KOLEKSIYONU",
    "VARSAYILAN_N",
    "VARSAYILAN_ESIK",
    "AnlamsalHafiza",
]

#: Sohbet indeksi kendi koleksiyonunda durur; `jarvis_memories`'e dokunmaz.
SOHBET_KOLEKSIYONU = "sohbet_indeksi"

#: Gomme modelinin adi TEK yerde durur: `tools/vector_memory.py`. Burada
#: yeniden yazilsaydi biri degisip digeri kalir, ve uyusmazlik sessiz
#: olurdu -- iki model de 384 boyut uretiyor, yani boyut hatasi da alinmaz.
#: Import tembel: bu modulu import etmek chromadb'yi yuklemez.
def _gomme_modeli() -> str:
    from tools.vector_memory import TURKCE_GOMME_MODELI

    return TURKCE_GOMME_MODELI

#: Kac parca cagrilir. Kucuk tutuldu: prompt'u sismek, hatirlamaktan pahalidir.
VARSAYILAN_N = 4

#: Benzerlik esigi -- SECILDI, olculerek (2026-09-23, 34 parcalik indeks).
#:
#: `MemoryRetrievalPolicy`'nin varsayilani 0,70'tir ve bu yolda
#: KULLANILAMAZ: olculen dogru isabetler 0,418-0,600 bandinda, yani 0,70
#: hepsini elerdi.
#:
#: Sayi iki dagilimdan secildi (`scripts/hafiza_indeksle.py --olc` ve
#: gurultu sinavi):
#:
#:     GURULTU  (karsiligi indekste olmayan 8 soru) -> en yuksek 0,409
#:     ISABET   (karsiligi olan, kelime paylasmayan) -> 0,418 / 0,536 / 0,600
#:
#: Iki dagilimin arasi yalnizca **0,009**. Bu bir esik degil, yazi-turadir:
#: 0,41'de "en yakin eczane nerede" sorusu "Sadece pazipanko'nun stunyu ne
#: ya?" kaydini hafiza diye prompt'a sokuyordu.
#:
#: **0,45** -- ilk secilen 0,50 CANLI TESTTE fazla katı cikti ve duzeltildi.
#:
#: Canli oturumda "Bosta duran devre kartlari hangi mobilyanin altinda
#: duruyordu?" sorusu dogru kaydi **1. sirada 0,469** ile buldu; ikinci
#: sira 0,260'ti, yani pay 0,209 -- acik ara. 0,50 esigi bunu eledi ve
#: JARVIS "bilmiyorum" dedi.
#:
#: Daha genis olcum (39 parcalik gercek indeks, 12 gurultu + 7 isabet):
#:
#:     gurultu ilk-skor TAVANI : 0,411
#:     1. sirasi dogru olanlarin skor TABANI : 0,418
#:
#: Denenen kurallar:
#:
#:     yalniz >= 0,50                       gurultu 0/12 · dogru 4/6
#:     yalniz >= 0,45                       gurultu 0/12 · dogru 5/6
#:     >=0,50 VEYA (>=0,40 ve pay>=0,15)    gurultu 1/12 · dogru 5/6
#:     >=0,50 VEYA (>=0,42 ve pay>=0,18)    gurultu 0/12 · dogru 5/6
#:
#: "Pay" (birinci ile ikinci arasindaki fark) kurali dusunuldu ve
#: ELENDI: tek sayilik esige gore hicbir sey kazandirmiyor, iki
#: parametre getiriyor (CLAUDE.md 2 -- once sadelik). 0,45 olculen
#: gurultu tavaninin 0,039 ustunde, kurtarilmak istenen isabetin
#: (0,469) altinda, ve beraberlikte kalan belirsiz vakanin (0,418,
#: yanlis bir kayitla ESIT skor) ustunde duruyor.
#:
#: Asimetri kasitli: prompt'a giren yanlis bir hatira JARVIS'i kendinden
#: emin bir sekilde yaniltir (PUSULA ihlali); eksik bir hatira yalnizca
#: "bilmiyorum" dedirtir. Kayip taraf ucuz olani.
#:
#: **Bu sayi 19 sondaj ve 39 parcalik bir indeksten geliyor, tek kosu.**
#: Indeks buyudukce yeniden olculmeli; kalibi
#: `scripts/hafiza_indeksle.py --olc`.
VARSAYILAN_ESIK = 0.45


class AnlamsalHafiza:
    """Sohbet indeksinde anlamsal arama; her arizada sessizce bos doner.

    ``fabrika`` yalniz test icindir: cagrildiginda bir `VectorMemory`-benzeri
    nesne dondurur. Uretimde varsayilan fabrika kullanilir ve `chromadb`
    yoksa modul **calismaz ama cokmez** -- sistem Python'unda (testlerin
    kostugu yorumlayici) chromadb kurulu degildir.
    """

    def __init__(
        self,
        db_path: str = "memory/chroma_db",
        n: int = VARSAYILAN_N,
        esik: float = VARSAYILAN_ESIK,
        politika: Any = None,
        duyur: Optional[Callable[[str], None]] = None,
        fabrika: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._db_path = db_path
        self.n = max(1, int(n))
        self.esik = float(esik)
        self._politika = politika
        self._duyur = duyur or (lambda m: None)
        self._fabrika = fabrika or self._varsayilan_fabrika
        self._depo: Any = None
        self._durum = "bekliyor"  # bekliyor | isiniyor | hazir | yok
        self._hata = ""
        self._kilit = threading.Lock()
        self._is: Optional[threading.Thread] = None

    # ── kurulum ──────────────────────────────────────────────────────────

    def _varsayilan_fabrika(self) -> Any:
        """Sohbet indeksini kendi koleksiyonunda acar.

        Gomme modeli artik `VectorMemory`'nin varsayilani (Turkce) ve
        surec basina bir kez yuklenir; burada ayrica kurmak ayni modeli
        iki kez yuklemek olurdu.
        """
        from tools.vector_memory import VectorMemory

        return VectorMemory(
            db_path=self._db_path,
            collection=SOHBET_KOLEKSIYONU,
            duyur=self._duyur,
        )

    def isit(self) -> None:
        """Modeli arka planda yukler. Cagiran **beklemez**."""
        with self._kilit:
            if self._durum != "bekliyor":
                return
            self._durum = "isiniyor"
            self._is = threading.Thread(
                target=self._isit_calis, name="anlamsal-hafiza", daemon=True
            )
            self._is.start()

    def _isit_calis(self) -> None:
        try:
            depo = self._fabrika()
        except Exception as exc:  # noqa: BLE001 - hafiza yoklugu sohbeti durdurmaz
            with self._kilit:
                self._depo, self._durum, self._hata = None, "yok", str(exc)
            self._duyur(f"[hafiza] anlamsal arama kurulamadi: {exc}")
            return
        with self._kilit:
            self._depo, self._durum, self._hata = depo, "hazir", ""

    def bekle(self, saniye: float = 30.0) -> bool:
        """Isinmanin bitmesini bekler. Yalniz betikler ve testler icindir;
        sohbet yolu ASLA beklemez."""
        is_parcacigi = self._is
        if is_parcacigi is not None:
            is_parcacigi.join(saniye)
        return self.hazir()

    def hazir(self) -> bool:
        with self._kilit:
            return self._durum == "hazir" and self._depo is not None

    @property
    def durum(self) -> str:
        with self._kilit:
            return self._durum

    @property
    def hata(self) -> str:
        with self._kilit:
            return self._hata

    def _depoyu_al(self) -> Any:
        with self._kilit:
            return self._depo if self._durum == "hazir" else None

    # ── okuma ────────────────────────────────────────────────────────────

    def ara(self, sorgu: str) -> list[dict]:
        """Sorguya anlamsal olarak yakin gecmis parcalari dondurur.

        Hicbir kosulda istisna sizdirmaz ve hicbir kosulda BEKLEMEZ: hafiza
        bir kolayliktir, sohbetin on kosulu degil.
        """
        metin = (sorgu or "").strip()
        if len(metin) < 3:
            return []

        depo = self._depoyu_al()
        if depo is None:
            return []

        try:
            # `find_similar` esigi Chroma'nin KOSINUS UZAKLIGI cinsindendir
            # (kucuk olan iyi), buradaki `esik` ise BENZERLIK. Donusum tek
            # yerde yapilir; iki farkli olcek iki ayri dosyada tutulsaydi
            # biri digerinin tersine suruklenirdi.
            ham = depo.find_similar(metin, n=self.n, threshold=1.0 - self.esik)
        except Exception as exc:  # noqa: BLE001
            self._duyur(f"[hafiza] arama basarisiz: {exc}")
            return []

        return self._suz(ham, metin)

    def _suz(self, ham: list[dict], sorgu: str) -> list[dict]:
        """Bulunanlari mevcut guvenlik politikasindan gecirir.

        Politika yeniden yazilmadi: `MemoryRetrievalPolicy` repoda zaten var
        ve hassas/onay-bekleyen/suresi-gecmis kayitlari eliyor (CLAUDE.md 9,
        adopt-over-build). Politika calismazsa hicbir sey donmez -- guard
        arizasi kapiyi ACMAZ, KAPATIR (B10 dersi).
        """
        if not ham:
            return []
        try:
            politika = self._politika
            if politika is None:
                from agents.memory_retrieval_policy import MemoryRetrievalPolicy

                politika = MemoryRetrievalPolicy(
                    max_items=self.n, min_similarity=self.esik
                )
                self._politika = politika
            return politika.filter_hits(ham, query=sorgu)
        except Exception as exc:  # noqa: BLE001
            self._duyur(f"[hafiza] politika calistirilamadi, hafiza kullanilmadi: {exc}")
            return []

    def prompt_blogu(self, sorgu: str) -> str:
        """System prompt'a eklenecek blok; bulunan yoksa **bos string**.

        Bos donmek bilincli: `main.py`'deki ayni ilke -- bos zemin, yanlis
        zeminden iyidir. Blok, parcalarin KONUSMA oldugunu ve canli proje
        durumuyla celisirse kaybettigini acikca soyler; yoksa model eski bir
        cumleyi bugunun olgusu gibi tekrar eder (PUSULA ihlali).
        """
        bulunan = self.ara(sorgu)
        if not bulunan:
            return ""

        # Bu metnin ilk hali CANLI TESTTE hafizayi SUSTURDU ve degistirildi.
        #
        # Eski hali "bunlar kanit degildir ... bunlardan yeni olgu TURETME"
        # diyordu. Blok modele ULASIYORDU -- olculdu, prompt'ta oldugu
        # dogrulandi -- ama model onu kullanmayi reddetti ve "bu konusmanin
        # kaydina erisimim yok" dedi. `LOCAL_AGENT_ADDENDUM`'daki "blokta
        # gecmiyorsa cikarim yapma, bilmiyorsun" kuraliyla birlesince metin
        # bir hatirlatma degil, bir YASAK haline gelmisti.
        #
        # Yeni hali once IZNI verir, sonra sinirlari koyar. Korunan uc
        # garanti aynen duruyor: uydurma yok, canli proje durumu ustun,
        # ilgisiz alinti gormezden gelinir.
        satirlar = [
            "## HATIRLADIKLARIN (gercek konusma kaydi)",
            "Bu bolum PROJE DURUMU DEGILDIR; yukaridaki \"blokta gecmiyorsa",
            "bilmiyorsun\" kurali buraya islemez. Asagidakiler Ahmet ile",
            "GERCEKTEN yaptigin konusmalarin kaydidir -- yani bunlari",
            "biliyorsun.",
            "Soru bunlardan biriyle ilgiliyse DOGRUDAN CEVAPLA; \"kaydima",
            "erisimim yok\" DEME, cunku kayit tam burada.",
            "Sinirlar: burada gecmeyen ayrintiyi uydurma; GUNCEL PROJE DURUMU",
            "ile celisirse o kazanir; ilgisizse gormezden gel ve bu bolumden",
            "hic bahsetme.",
        ]
        # Eklenen alinti SAYILIR; baslik satirlarinin sayisina bakilmaz.
        # Eskiden `len(satirlar) > 4` kontrol ediliyordu ve baslik uc satir
        # uzayinca kosul icerik olmadan da dogru oluyordu -- model bos bir
        # "hafizan" basligi gorup ondan bahsediyordu.
        eklenen = 0
        for parca in bulunan:
            tarih = str(parca.get("ts") or "")[:10]
            soru = str(parca.get("user_msg") or "").strip()
            cevap = str(parca.get("jarvis_msg") or "").strip()
            if not soru and not cevap:
                continue
            onek = f"- [{tarih}] " if tarih else "- "
            satirlar.append(f"{onek}Sen: {soru[:160]}")
            if cevap:
                satirlar.append(f"    Ben: {cevap[:220]}")
            eklenen += 1

        return "\n".join(satirlar) if eklenen else ""

    # ── indeks bakimi (kalici hafiza DEGIL) ──────────────────────────────

    def yaz(self, user_msg: str, jarvis_msg: str, meta: Optional[dict] = None) -> str:
        """Indekse bir parca ekler. **Yalniz backfill betigi cagirir.**

        Sohbet yolu bunu cagirmaz: her turu kendiliginden yazmak 7.1a'yi ve
        onay hattini (`answer_crystallizer` -> `knowledge_card_promoter`)
        baypas etmek olurdu.
        """
        depo = self._depoyu_al()
        if depo is None:
            return ""
        try:
            return depo.remember(user_msg, jarvis_msg, meta=meta) or ""
        except Exception as exc:  # noqa: BLE001
            self._duyur(f"[hafiza] indekse yazilamadi: {exc}")
            return ""

    def sayi(self) -> int:
        depo = self._depoyu_al()
        if depo is None:
            return 0
        try:
            return int(depo.stats().get("total", 0))
        except Exception:  # noqa: BLE001
            return 0

    def temizle(self) -> bool:
        """Sohbet indeksini bosaltir. `jarvis_memories`'e DOKUNMAZ.

        `clear_history` bunu cagirir: indeks silinmezse "unut" denen bir
        konusma anlamsal aramayla geri doner -- B04'un ta kendisi, yeni bir
        kapidan.

        Basarisizlik SESSIZ gecmez: `False` doner ve cagiran kullaniciya
        soyler.
        """
        depo = self._depoyu_al()
        if depo is None:
            # Hic kurulmadiysa silinecek bir sey de yok; bu bir basarisizlik
            # degildir. Kurulup da hata verdiyse durum "yok"tur ve asagidaki
            # ayrim onu yakalar.
            return self.durum in ("bekliyor", "isiniyor", "hazir")
        try:
            return bool(depo.reset())
        except Exception as exc:  # noqa: BLE001
            self._duyur(f"[hafiza] indeks silinemedi: {exc}")
            return False
