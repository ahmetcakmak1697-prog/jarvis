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

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

# Windows konsolu CP1254'tur ve "✓" ile Turkce karakterleri basamaz.
# Yardimci repoda zaten var; yeniden yazilmadi (CLAUDE.md 9).
from _utf8io import configure_utf8_stdio  # noqa: E402

configure_utf8_stdio()

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


def kayitlari_oku(db: Path = VERITABANI) -> list[dict]:
    """Essiz sohbet parcalarini dondurur (en yenisi kazanir)."""
    if not db.exists():
        print(f"[!] Veritabani yok: {db}")
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

    print(f"    toplam satir      : {len(satirlar)}")
    print(f"    ariza metni atlandi: {atlanan_ariza}")
    print(f"    kisa/bos atlandi  : {atlanan_kisa}")
    print(f"    essiz parca       : {len(essiz)}")
    return list(essiz.values())


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


def indeksle() -> int:
    print("[*] SQLite sohbet gecmisi okunuyor...")
    parcalar = kayitlari_oku()
    if not parcalar:
        print("[!] Indekslenecek kayit yok.")
        return 0

    h = _hafiza()
    if h is None:
        return 1

    depo = h._depoyu_al()
    onceki = depo.stats().get("total", 0)
    print(f"[*] Indeksteki mevcut kayit: {onceki}")

    belgeler, kimlikler, ustveri = [], [], []
    for p in parcalar:
        kimlikler.append(_kimlik(p["soru"], p["cevap"]))
        belgeler.append(f"USER: {p['soru']}\nJARVIS: {p['cevap']}")
        ustveri.append({
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

    t0 = time.perf_counter()
    depo.col.upsert(documents=belgeler, ids=kimlikler, metadatas=ustveri)
    sure = (time.perf_counter() - t0) * 1000

    sonraki = depo.stats().get("total", 0)
    print(f"[✓] {len(belgeler)} parca yazildi ({round(sure)} ms)")
    print(f"    indeks: {onceki} -> {sonraki}")
    if onceki and sonraki != onceki + max(0, len(belgeler) - onceki):
        pass  # bilgi amacli; asil idempotentlik kanitini --olc basiyor
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
    indeksle_sessiz(depo)
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


def indeksle_sessiz(depo) -> None:
    parcalar = []
    conn = sqlite3.connect(VERITABANI)
    try:
        satirlar = conn.execute(
            "SELECT timestamp, user_message, jarvis_response FROM conversations"
        ).fetchall()
    finally:
        conn.close()
    essiz: dict[str, tuple] = {}
    for ts, soru, cevap in satirlar:
        soru, cevap = (soru or "").strip(), (cevap or "").strip()
        if not soru or not cevap or _ARIZA_DESENI.match(cevap):
            continue
        if len(soru) + len(cevap) < _ASGARI_UZUNLUK:
            continue
        essiz[_anahtar(soru)] = (ts or "", soru, cevap)
    for ts, soru, cevap in essiz.values():
        parcalar.append((_kimlik(soru, cevap), f"USER: {soru}\nJARVIS: {cevap}", {
            "ts": ts, "user_msg": soru[:200], "jarvis_msg": cevap[:300],
            "memory_type": "sohbet_indeksi", "storage_target": "vector",
            "sensitivity": "normal", "memory_action": "index",
        }))
    if parcalar:
        depo.col.upsert(
            ids=[p[0] for p in parcalar],
            documents=[p[1] for p in parcalar],
            metadatas=[p[2] for p in parcalar],
        )


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"--olc": olc, "--sil": sil}.get(arg, indeksle)())
