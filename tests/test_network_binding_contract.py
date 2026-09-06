"""Ag baglama sozlesmesi — bir sunucu tum arayuzlere baglanamaz.

B02 (Codex basmuhendis denetimi, 2026-09-06): `gui.py` `0.0.0.0:5000`
kullaniyordu ve `/chat` kimlik dogrulamasi olmadan `agent.chat()` cagiriyordu.
Yani ev agindaki herkes JARVIS ile konusabilir, notlari okuyabilirdi.

Bu test bir REGRESYON KAPISI degil, bir SOZLESMEDIR: yeni bir arayuz eklenirken
`0.0.0.0` yazmak sessizce gecmesin. "Bu PC'den doner" karari (CLAUDE.md §12,
HA/ESPHome) varsayilan olarak loopback demektir; uzaktan erisim ayri ve acik
bir Ahmet karari olmalidir.

Test kaynagi metin olarak tarar, import etmez: bir sunucu modulunu import
etmek yan etki (ajan kurulumu, .env okuma, soket) tetikleyebilir.
"""
from __future__ import annotations

import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]

#: Tum arayuzlere baglanma isareti. `api_executor.py` bunu bir SSRF
#: kara listesinde *string olarak* aniyor (kendisi baglanmiyor); o yuzden
#: yalniz gercek calistirma cagrilarinin icinde ariyoruz.
_BAGLAMA = re.compile(
    r"""(?:app\.run|uvicorn\.run|run_simple|serve)\s*\([^)]*?["']0\.0\.0\.0["']""",
    re.DOTALL,
)

#: Taranmayacak yerler: sanal ortam, arac ciktisi, tarihsel anlik goruntuler.
_ATLA = (".venv", "graphify-out", "dev_patches", "__pycache__", ".git",
         "node_modules", ".pytest_cache", ".ruff_cache")

#: **ACIK ISTISNA — kapatilmis degil, Ahmet'in karari bekleniyor.**
#:
#: `jarvis_server.py` (4295 satir, FastAPI + WebSocket + CORS + dosya yukleme)
#: `0.0.0.0:8000` kullaniyor ve 35 dosyaya ulasiyor. Tek erisim koku oldugu
#: moduller arasinda `auto_updater`, `self_improver`, `task_executor`,
#: `proactive_agent` var — bu isimler CLAUDE.md §9'un kalici park ettigi
#: cepheye komsu. Bu yuzden danisman ona DOKUNMADI: park edilmis bir cepheye
#: dokunma ihtiyaci dogarsa durulur ve sorulur (§9, DANISMAN MODU).
#:
#: Istisna **bilerek ve tarihli** konuldu ki sessiz bir muafiyet olmasin.
#: Ahmet karar verince bu satir silinir; silinmesi testi kirmiyorsa dosya
#: gercekten duzelmis demektir.
_BEKLEYEN_KARAR = {"jarvis_server.py"}


def _kaynak_dosyalari():
    for yol in KOK.rglob("*.py"):
        if any(p in yol.parts for p in _ATLA):
            continue
        yield yol


def test_hicbir_sunucu_tum_arayuzlere_baglanmaz():
    """`0.0.0.0` ile calisan yeni bir sunucu eklenemez."""
    bulunan = []
    for yol in _kaynak_dosyalari():
        ad = yol.relative_to(KOK).as_posix()
        if yol.name in _BEKLEYEN_KARAR:
            continue
        metin = yol.read_text(encoding="utf-8", errors="replace")
        if _BAGLAMA.search(metin):
            bulunan.append(ad)

    assert not bulunan, (
        "Bu dosyalar tum ag arayuzlerine baglaniyor: "
        f"{sorted(bulunan)}. Varsayilan 127.0.0.1 olmalidir; uzaktan erisim "
        "ayri ve acik bir karardir (B02)."
    )


def test_emekliye_ayrilan_gui_geri_gelmedi():
    """`gui.py` emekli edildi; ayni yuzey yeniden acilmasin.

    Islevleri `jarvis_desktop.py` (v2) tarafindan zaten karsilaniyordu:
    `/` `/api/chat` `/api/sysinfo` `/api/notes` GET+POST, artı `/api/clear`.
    v2 dogru sekilde `127.0.0.1:5001`'e baglaniyor ve `.env` olmadan calisiyor
    (olculdu, 2026-09-06). v1'in `/stats` ucu ise ajan varken **500** veriyordu:
    `JarvisMemory.count()` diye bir metot yok.
    """
    assert not (KOK / "gui.py").exists(), (
        "gui.py emekliye ayrildi (B02). Web arayuzu icin jarvis_desktop.py "
        "kullanilir. Geri getirmek gerekiyorsa bu bir karardir, kaza degil."
    )


def test_istisna_listesi_gercek_dosyalari_gosteriyor():
    """Bekleyen-karar listesi bayatlamasin.

    Dosya silinir ya da duzeltilirse istisna da kalkmali; yoksa liste
    zamanla anlamsiz bir muafiyet torbasina doner.
    """
    for ad in _BEKLEYEN_KARAR:
        yol = KOK / ad
        assert yol.exists(), (
            f"{ad} artik yok ama istisna listesinde duruyor. "
            "Listeden cikar."
        )
        assert _BAGLAMA.search(yol.read_text(encoding="utf-8", errors="replace")), (
            f"{ad} artik 0.0.0.0'a baglanmiyor. Istisnayi kaldir — "
            "sozlesme onu da kapsasin."
        )
