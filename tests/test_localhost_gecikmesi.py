"""localhost her istekte ~2 saniye yakiyor -- izlenen uretim yollari 127.0.0.1 yazar.

Olculdu (2026-09-12/13, bu makine; automation/TERAZI_400_SONDA_2026-09-12.md
§1c ve automation/KART_LOCALHOST_2SN.md §0):

    getaddrinfo("localhost") sirasi : ['::1', '127.0.0.1']
    urllib -> http://localhost:11434 : ~2,05 s / istek
    urllib -> http://127.0.0.1:11434 : ~0,001-0,016 s / istek

Ollama IPv6'yi (::1) dinlemiyor; baglanti once orada zaman asimina ugrayip
IPv4'e dusuyor. Kalite kosucusunda bu, Ollama yolundaki her vakanin
`total_s`'ini ~2 s sisirdi ve `raw_tps * total_s` turetmesini 1,36-4,02 kat
buyuttu -- "llama 400 butceyle 502 token" yanlis alarmi buradan cikti.

KAPSAM BILEREK DARDIR -- genisletmeden once oku:

* Test yalniz `_HEDEFLER`'deki on dosyaya bakar (iki kartin "EVET" dedigi
  yollar: KART_LOCALHOST_2SN ve KART_LOCALHOST_KALANLAR). `ollama` Python
  paketini kullanan yollar -- agent/local_agent.py'nin sohbet cagrisi
  `import ollama` ile paketin varsayilan istemcisine gider -- zaten
  127.0.0.1'e baglaniyor; onlara dokunulmadi.
  PDF DALI DUZELTILDI (KART_LOCALHOST_KALANLAR, 2026-09-14; commit'i bulmak
  icin: `git log -S "127.0.0.1:11434" -- rag/rag_engine.py`). Ayni `chat()`'in
  acik PDF/belge istegi dali (agent/local_agent.py:939-947, `_pdf_istegi_mi`)
  cevabi rag/rag_engine.py'den alir; `requests.post` artik 127.0.0.1'e
  gider. `requests` da ayni bedeli oduyordu (olculdu: localhost ~2,05 s,
  127.0.0.1 ~0,015 s / istek).
* Park edilmis dort dosya KAPSAM DISIDIR ve bu bir EKSIKLIK DEGILDIR:
  agents/daily_digest.py, agents/orchestrator.py, agents/proactive_agent.py,
  agents/self_improver.py hala localhost kullaniyor. CLAUDE.md §9 park
  edilmis cepheleri hicbir gerekceyle yeniden acmayi yasakliyor; kusur
  "gor, soyle, silme" ilkesiyle listelendi, duzeltilmedi. Onlari buraya
  eklemek o cepheleri acmak demektir -- Ahmet'in karari olmadan genisletme.
* 2026-09-14 itibariyla (`git grep localhost:11434`) kalan yerler YALNIZ
  sunlardir ve hepsi bilerek disarida: yukaridaki park edilmis dort dosya,
  ve tests/test_api_executor.py'deki test verisi (`https://localhost:11434/v1`
  -- sahte URL, gercek cagri yok; OpenAI-uyumlu ucun localhost'u
  REDDETTIGINI sinar). Bu dosyanin kendi metni de `localhost:11434` gecirir;
  o da kapsamda degildir.
"""
from __future__ import annotations

from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]

#: KART_LOCALHOST_2SN §1 ve KART_LOCALHOST_KALANLAR §1'in "EVET" dedigi yollar.
_HEDEFLER = (
    # KART_LOCALHOST_2SN (5ebf4aa)
    "config/runtime_profiles.json",
    "agents/model_registry.py",
    "agents/ollama_executor.py",
    "eval/run_turkish_quality.py",
    # KART_LOCALHOST_KALANLAR -- PDF dali oncelikli: canli ses yolu
    "rag/rag_engine.py",
    "jarvis_brain.py",
    "training/conversation_summarizer.py",
    "training/quality_evaluator.py",
    "tests/jarvis_system_audit.py",
    "setup.py",
)


@pytest.mark.parametrize("goreli", _HEDEFLER)
def test_izlenen_uretim_yolu_localhost_kullanmaz(goreli):
    """Bu makinede localhost ::1'e cozuluyor ve her istek ~2 s bekliyor."""
    metin = (KOK / goreli).read_text(encoding="utf-8")
    kalanlar = [f"  {no}: {satir.strip()}"
                for no, satir in enumerate(metin.splitlines(), 1)
                if "localhost:11434" in satir]

    assert not kalanlar, (
        f"{goreli} hala localhost:11434 kullaniyor -- her istek ~2 s bekler "
        "(once ::1 deneniyor). 127.0.0.1 yaz:\n" + "\n".join(kalanlar)
    )
