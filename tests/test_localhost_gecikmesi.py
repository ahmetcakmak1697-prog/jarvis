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

* Test yalniz `_HEDEFLER`'deki dort dosyaya bakar (kartin "EVET" dedigi
  yollar). `ollama` Python paketini kullanan yollar -- agent/local_agent.py'nin
  sohbet cagrisi `import ollama` ile paketin varsayilan istemcisine gider --
  zaten 127.0.0.1'e baglaniyor; onlara dokunulmadi.
  ISTISNA (olculdu, duzeltilmedi): ayni `chat()`'in acik PDF/belge istegi
  dali (agent/local_agent.py:939-947, `_pdf_istegi_mi`) cevabi
  rag/rag_engine.py:138'den alir; o satir `requests.post` ile localhost'a
  gider. Yani ses yolu yalniz bu dalda ~2 s oder.
* Park edilmis dort dosya KAPSAM DISIDIR ve bu bir EKSIKLIK DEGILDIR:
  agents/daily_digest.py, agents/orchestrator.py, agents/proactive_agent.py,
  agents/self_improver.py hala localhost kullaniyor. CLAUDE.md §9 park
  edilmis cepheleri hicbir gerekceyle yeniden acmayi yasakliyor; kusur
  "gor, soyle, silme" ilkesiyle listelendi, duzeltilmedi. Onlari buraya
  eklemek o cepheleri acmak demektir -- Ahmet'in karari olmadan genisletme.
* Kartin tablosunda OLMAYAN ve bu kartta duzeltilmeyen yerler de var
  (2026-09-13, `git grep localhost:11434`): jarvis_brain.py (5 yer),
  rag/rag_engine.py (agent/local_agent.py bu modulu import ediyor),
  setup.py, training/conversation_summarizer.py,
  training/quality_evaluator.py. Bunlar ayri bir karar; bu test onlari
  kapsamaz.
"""
from __future__ import annotations

from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]

#: KART_LOCALHOST_2SN §1'in "EVET" dedigi izlenen uretim yollari.
_HEDEFLER = (
    "config/runtime_profiles.json",
    "agents/model_registry.py",
    "agents/ollama_executor.py",
    "eval/run_turkish_quality.py",
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
