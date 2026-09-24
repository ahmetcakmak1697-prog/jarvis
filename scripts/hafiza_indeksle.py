# -*- coding: utf-8 -*-
"""scripts/hafiza_indeksle.py — SQLite sohbet gecmisini anlamsal indekse alir.

KART_VEKTOR_HAFIZA ADIM 2. Bu betik **kalici hafizaya yazmaz**: urettigi sey
`memory/jarvis_memory.db` uzerine kurulan, silinip yeniden kurulabilen bir
arama yapisidir (CLAUDE.md 7.1a kapsami disindadir). Onaylanmis bilgi
kartlarinin koleksiyonuna (`jarvis_memories`) dokunmaz.

    python scripts/hafiza_indeksle.py          # indeksi kur/guncelle
    python scripts/hafiza_indeksle.py --olc    # esigi olcmek icin sinav kos
    python scripts/hafiza_indeksle.py --sil    # indeksi bosalt

**Idempotent**: her kayit iceriginden turetilen sabit bir kimlik alir ve
`upsert` ile yazilir. Iki kez calistirmak kopya uretmez -- olculur, iddia
edilmez (asagida "onceki/sonraki" sayilari basilir).

**Tekrarlar birlestirilir.** Olculdu (2026-09-23): 183 kaydin yalniz 34'u
essiz; "nerede kaldik" 59, "Bir metrede kac santimetre vardir?" 33, teknik
borc sorusu 33 kez tekrar ediyor. Bunlar sohbet degil, kalite takiminin
kosulari. Ayni cumleyi 59 kez indekslemek, aramanin ilk dort sonucunu ayni
seye ayirmak demekti.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import NamedTuple

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

# Windows konsolu CP1254'tur ve "✓" ile Turkce karakterleri basamaz.
# Yardimci repoda zaten var; yeniden yazilmadi (CLAUDE.md 9).
# Cagri `__main__` bloguna tasindi: import ANINDA stdout'u yeniden
# yapilandirmak, bu modulu import eden testin ciktisini da degistiriyordu.
from _utf8io import configure_utf8_stdio  # noqa: E402

VERITABANI = KOK / "memory" / "jarvis_memory.db"

#: Cevap yerine ariza metni tasiyan kayitlar indekslenmez: onlari
#: hatirlamak, hatirlamamaktan kotudur.
_ARIZA_DESENI = re.compile(
    r"^\s*(⚠️|Model hatası|Model hatasi|Ollama bağlı değil|Hata:)", re.IGNORECASE
)

#: Cok kisa alisverisler ("tamam", "peki") arama degeri tasimaz.
_ASGARI_UZUNLUK = 12


def _anahtar(metin: str) -> str:
    """Tekrar tespiti icin sadelestirilmis anahtar."""
    return re.sub(r"\s+", " ", (metin or "").strip().lower())


def _kimlik(soru: str, cevap: str) -> str:
    """Icerikten turetilen SABIT kimlik -- idempotentligin tek kaynagi."""
    ham = f"{_anahtar(soru)}\x00{_anahtar(cevap)}".encode("utf-8")
    return "sohbet_" + hashlib.sha1(ham).hexdigest()[:20]


class UzlastirmaPlani(NamedTuple):
    eklenecek: set[str]
    degismeyen: set[str]
    silinecek: set[str]
    durma: str | None


def uzlastir_plani(gecerli: set[str], mevcut: set[str]) -> UzlastirmaPlani:
    """Indeksi SQLite ile uzlastirma karari -- saf fonksiyon, I/O yok.

    Upsert yalniz EKLER. Bir konusma SQLite'tan silindiginde indeks kaydi
    yerinde kalir ve arama onu geri getirir; indeks zamanla SQLite'in ust
    kumesine doner. Ayni sey DUZENLENEN kayit icin de gecerli: kimlik
    icerikten turedigi icin metin degisince yeni kimlik olusur ve eskisi
    oksuz kalir.

    **Iki emniyet, ikisi de silmeyi engeller:**

    1. ``gecerli`` bos ise hicbir sey silinmez. "Orada olmayani sil" emri,
       SQLite okunamadigi ya da bos dondugu anda "indeksin tamamini sil"
       demektir. `tools/vector_memory.py:koleksiyon_ac`'taki asimetrinin
       aynisi: bos oldugunu KANITLAYAMIYORSAK dokunulmaz.

    2. Silinecek oran indeksin yarisini ASIYORSA durulur. Normal kullanimda
       bir seferde bu kadar kayit dusmez; dusuyorsa okuma tarafinda bir sey
       bozulmustur. Gercekten kastediliyorsa yol zaten var: `--sil` ile
       bosalt, sonra yeniden kur. Yeni bir "zorla" bayragi ACILMADI --
       var olan bir yol dururken ikincisini eklemek, yanlislikla silmenin
       yolunu cogaltmak olurdu.
    """
    eklenecek = gecerli - mevcut
    degismeyen = gecerli & mevcut
    fazlalik = mevcut - gecerli

    if not gecerli:
        return UzlastirmaPlani(
            eklenecek, degismeyen, set(),
            "gecerli kimlik kumesi BOS -- indekse dokunulmadi. SQLite "
            "okunamamis ya da bos olabilir.",
        )

    if mevcut and len(fazlalik) * 2 > len(mevcut):
        return UzlastirmaPlani(
            eklenecek, degismeyen, set(),
            f"indeksin yarisindan fazlasi ({len(fazlalik)}/{len(mevcut)}) "
            "silinecekti -- durdum. Gercekten kastediyorsan: "
            "`--sil` ile bosalt, sonra yeniden kur.",
        )

    return UzlastirmaPlani(eklenecek, degismeyen, fazlalik, None)


def kayitlari_oku(db: Path | None = None, sessiz: bool = False) -> list[dict]:
    """Essiz sohbet parcalarini dondurur (en yenisi kazanir).

    ``db`` varsayilani None, `VERITABANI` DEGIL. Fark onemli: Python
    varsayilan argumani TANIM aninda baglar, yani imza
    ``db: Path = VERITABANI`` yazildiginda modul degiskenini sonradan
    degistirmek hicbir ise yaramaz ve fonksiyon her zaman uretim
    veritabanini okur. Bir dogrulama betigi tam bu yuzden gecici kopyayi
    isaret ettigini saniyordu ama gercek veriyi okuyordu.
    """
    db = Path(db) if db is not None else VERITABANI

    def yaz(m):
        if not sessiz:
            print(m)

    if not db.exists():
        yaz(f"[!] Veritabani yok: {db}")
        return []

    conn = sqlite3.connect(db)
    try:
        satirlar = conn.execute(
            "SELECT id, timestamp, user_message, jarvis_response "
            "FROM conversations ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    essiz: dict[str, dict] = {}
    atlanan_ariza = atlanan_kisa = 0
    for _id, ts, soru, cevap in satirlar:
        soru, cevap = (soru or "").strip(), (cevap or "").strip()
        if not soru or not cevap:
            atlanan_kisa += 1
            continue
        if _ARIZA_DESENI.match(cevap):
            atlanan_ariza += 1
            continue
        if len(soru) + len(cevap) < _ASGARI_UZUNLUK:
            atlanan_kisa += 1
            continue
        # Ayni soru daha once gectiyse EN YENI cevap kalir: eski cevap
        # muhtemelen daha kotu bir modelden geldi.
        essiz[_anahtar(soru)] = {
            "ts": ts or "",
            "soru": soru,
            "cevap": cevap,
        }

    yaz(f"    toplam satir      : {len(satirlar)}")
    yaz(f"    ariza metni atlandi: {atlanan_ariza}")
    yaz(f"    kisa/bos atlandi  : {atlanan_kisa}")
    yaz(f"    essiz parca       : {len(essiz)}")
    return list(essiz.values())


def parcalari_hazirla(kayitlar: list[dict]) -> dict[str, tuple[str, dict]]:
    """Kayitlari kimlik -> (belge, ustveri) eslemesine cevirir.

    Tek yerde kurulur: eskiden bu mantik `indeksle` ve `indeksle_sessiz`
    icinde IKI KEZ yaziliydi ve ikisi birbirinden surukleniyordu.
    """
    hazir: dict[str, tuple[str, dict]] = {}
    for p in kayitlar:
        kimlik = _kimlik(p["soru"], p["cevap"])
        belge = f"USER: {p['soru']}\nJARVIS: {p['cevap']}"
        hazir[kimlik] = (belge, {
            "ts": p["ts"],
            "user_msg": p["soru"][:200],
            "jarvis_msg": p["cevap"][:300],
            # Politikanin okudugu alanlar. Metin SQLite'a yazilirken
            # `RedactionGuard`'dan gecti (memory_manager._temizle), yani
            # burada yeniden maskelemek ikinci kez ayni isi yapmak olurdu.
            "memory_type": "sohbet_indeksi",
            "storage_target": "vector",
            "sensitivity": "normal",
            "memory_action": "index",
        })
    return hazir


def mevcut_kimlikler(depo) -> set[str]:
    """Indekste duran kimlikler. `include=[]` yalniz kimlik getirir."""
    try:
        return set(depo.col.get(include=[]).get("ids") or [])
    except Exception as exc:  # noqa: BLE001
        print(f"[!] Indeks kimlikleri okunamadi: {exc}")
        return set()


def _hafiza():
    from agent.anlamsal_hafiza import AnlamsalHafiza

    h = AnlamsalHafiza(duyur=lambda m: print(f"    {m}"))
    t0 = time.perf_counter()
    print("[*] Turkce gomme modeli yukleniyor (ilk acilista ~13 sn)...")
    h.isit()
    if not h.bekle(180):
        print(f"[!] Hafiza kurulamadi: {h.durum} {h.hata}")
        return None
    print(f"[✓] Hazir ({round((time.perf_counter() - t0) * 1000)} ms)")
    return h


def _uygula(depo, hazir: dict, plan: UzlastirmaPlani, sessiz: bool = False) -> None:
    """Plani indekse uygular: once yaz, sonra fazlaligi sil."""
    def yaz(m):
        if not sessiz:
            print(m)

    yazilacak = sorted(plan.eklenecek | plan.degismeyen)
    if yazilacak:
        depo.col.upsert(
            ids=yazilacak,
            documents=[hazir[k][0] for k in yazilacak],
            metadatas=[hazir[k][1] for k in yazilacak],
        )

    if plan.durma:
        yaz(f"[!] {plan.durma}")
    elif plan.silinecek:
        depo.col.delete(ids=sorted(plan.silinecek))


def indeksle(sessiz: bool = False, hafiza=None) -> int:
    """Indeksi SQLite ile UZLASTIRIR: ekler, gunceller ve fazlaligi siler.

    ``hafiza`` verilmezse uretim deposu acilir. Parametre testler icindir
    ve bir ihtiyactan dogdu: eskiden bu fonksiyon HER ZAMAN varsayilan
    Chroma yolunu aciyordu, yani gecici bir kopya uzerinde dogrulanamazdi.
    Bir dogrulama betigi tam bu yuzden sessizce yanlis depoyu olctu --
    hedefi secilemeyen kod, sinanamayan koddur.
    """
    def yaz(m):
        if not sessiz:
            print(m)

    yaz("[*] SQLite sohbet gecmisi okunuyor...")
    kayitlar = kayitlari_oku(sessiz=sessiz)
    if not kayitlar:
        # Bos okuma indeksi SILDIRMEZ -- `uzlastir_plani` de ayni kurali
        # tutuyor, burada erken cikis onu bir kez daha uyguluyor.
        yaz("[!] Indekslenecek kayit yok; indekse DOKUNULMADI.")
        return 0

    h = hafiza if hafiza is not None else _hafiza()
    if h is None:
        return 1

    depo = h._depoyu_al()
    hazir = parcalari_hazirla(kayitlar)
    mevcut = mevcut_kimlikler(depo)
    plan = uzlastir_plani(set(hazir), mevcut)

    yaz(f"[*] Indekste {len(mevcut)} parca var.")
    t0 = time.perf_counter()
    _uygula(depo, hazir, plan, sessiz=sessiz)
    sure = (time.perf_counter() - t0) * 1000

    # Sayi basilmazsa uzlastirmanin calistigi IDDIA edilemez.
    yaz(f"[✓] eklenen {len(plan.eklenecek)} · "
        f"degismeyen {len(plan.degismeyen)} · "
        f"silinen {len(plan.silinecek)}  ({round(sure)} ms)")
    yaz(f"    indeks: {len(mevcut)} -> {depo.stats().get('total', 0)}")
    return 0


def sil() -> int:
    h = _hafiza()
    if h is None:
        return 1
    print("[✓] Indeks bosaltildi." if h.temizle() else "[!] Bosaltilamadi.")
    return 0


#: Esik sinavi. Her sorgu, beklenen kaydin KELIMELERINI paylasmaz; paylassa
#: duz metin aramasi da bulurdu ve olculen sey anlamsal kazanc olmazdi.
_SINAV: tuple[tuple[str, str], ...] = (
    ("kod kalitesi zamanla neden bozulur", "teknik borc"),
    ("uzunluk birimleri arasinda ne iliski var", "santimetre"),
    ("projede su an hangi noktadayiz", "nerede kaldik"),
)


def olc() -> int:
    """Esigi SECMEK icin gercek korpus uzerinde benzerlik dagilimi basar."""
    h = _hafiza()
    if h is None:
        return 1

    depo = h._depoyu_al()
    print(f"[*] Indekste {depo.stats().get('total', 0)} parca var.\n")

    # Idempotentlik kaniti: ayni yazma iki kez yapilinca sayi degismemeli.
    print("[*] Idempotentlik kontrolu...")
    once = depo.stats().get("total", 0)
    indeksle(sessiz=True)
    sonra = depo.stats().get("total", 0)
    print(f"    ikinci yazim sonrasi: {once} -> {sonra} "
          f"{'(KOPYA YOK)' if once == sonra else '(KOPYA URETTI!)'}\n")

    print("[*] Esik sinavi -- dogru kayit kacinci sirada ve hangi benzerlikte?")
    for sorgu, beklenen in _SINAV:
        t0 = time.perf_counter()
        ham = depo.find_similar(sorgu, n=5, threshold=1.0)
        sure = (time.perf_counter() - t0) * 1000
        print(f"\n  SORGU: {sorgu!r}   ({round(sure)} ms)")
        print(f"  beklenen icerik: {beklenen!r}")
        for sira, v in enumerate(ham, 1):
            benz = v.get("similarity")
            isaret = "->" if beklenen.lower() in str(v.get("user_msg", "")).lower() else "  "
            print(f"   {isaret} {sira}. benzerlik={benz:.3f}  "
                  f"{str(v.get('user_msg'))[:58]}")
    print("\n[i] Esik, DOGRU kayitlarin altinda / YANLIS kayitlarin ustunde "
          "kalacak sekilde secilir.")
    return 0


if __name__ == "__main__":
    configure_utf8_stdio()
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"--olc": olc, "--sil": sil}.get(arg, indeksle)())
