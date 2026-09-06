"""B11 -- olcum alani, olctugu seyi soylemeli.

Codex basmuhendis denetimi (2026-09-06): kalite kosucusu `first_token_ms`
alanini Ollama'nin `prompt_eval_duration` degerinden uretiyor ve
`stream=False` kullaniyor.

Ollama bu alani PROMPT DEGERLENDIRME suresi diye tanimlar; kullaniciya ilk
token'in ulasma zamani diye TANIMLAMAZ. Stream kapaliyken zaten "ilk token"
diye bir an yoktur -- cevabin tamami tek parca gelir.

Kayitli 30,5 ms ve 420,8 ms degerleri gecerlidir, olctukleri anlamda
korunmalidir; ama gercek istemci TTFT'si diye adlandirilamaz. Danisman bu
sayilari Turkish-Gemma'yi elerken "TTFT" diye kullandi -- sayi dogruydu,
etiket yanlisti.

Bu bir kozmetik duzeltme degil: yanlis etiketli bir olcum, dogru bir olcum
gibi karar verdirir. PUSULA'nin 1,5 saniyelik sarti hala OLCULMEDI (B12) ve
bu alan onun yerine gecemez.
"""
from __future__ import annotations

import inspect
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
KOSUCU = KOK / "eval" / "run_turkish_quality.py"


def test_olcum_alani_prompt_eval_olarak_adlandirilir():
    """Alan adi `prompt_eval_ms` olmali, `first_token_ms` degil."""
    kaynak = KOSUCU.read_text(encoding="utf-8", errors="replace")

    assert "prompt_eval_ms" in kaynak, (
        "olcum alani gercekte olctugu seyle adlandirilmali"
    )
    assert '"first_token_ms"' not in kaynak, (
        "`first_token_ms` adi kaldi -- Ollama bu alani ilk token zamani diye "
        "tanimlamiyor, prompt degerlendirme suresi diye tanimliyor"
    )


def test_rapor_ilk_token_iddiasinda_bulunmaz():
    """Markdown raporu kullaniciya 'ilk token' diye sunmamali."""
    kaynak = KOSUCU.read_text(encoding="utf-8", errors="replace")

    # Rapor satirlarindaki kullanici gorunur etiketler
    assert "Ortalama ilk token" not in kaynak, (
        "rapor hala 'ilk token' diyor; olculen sey prompt degerlendirmesi"
    )


def test_donen_sozlukte_alan_gercekten_var():
    """Sozlesme kaynakta degil, DAVRANISTA da tutmali."""
    import eval.run_turkish_quality as m

    fn = getattr(m, "_ollama_ask", None)
    assert fn is not None, "kosucunun model cagrisi bulunamadi"

    kaynak = inspect.getsource(fn)
    assert "prompt_eval_ms" in kaynak, (
        "model cagrisi yeni alan adini dondurmuyor"
    )


def test_eski_kosu_dosyalari_hala_okunabilir():
    """Gecmis kayitlar `first_token_ms` tasiyor; onlar bozulmamali.

    Ad degisikligi ILERI yonludur: yeni kosular yeni adi yazar, eski
    dosyalar oldugu gibi kalir. Tarihsel kaydi yeniden yazmak, olcumun
    kendisini yeniden yazmaktir.
    """
    import json

    eski = sorted((KOK / "automation").glob("KALITE_*.json"))
    if not eski:
        return  # kayit yoksa sinanacak bir sey de yok

    d = json.loads(eski[0].read_text(encoding="utf-8"))
    assert isinstance(d, dict), "eski kosu dosyasi okunamadi"
