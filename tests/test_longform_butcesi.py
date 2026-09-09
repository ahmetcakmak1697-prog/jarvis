"""ETAP 1 -- longform butcesi olcumle secildi mi, tahminle mi?

Olculmus durum (2026-09-09, `KART_DEEPSEEK_10_KUSUR.md`): dort longform
vakasinin dordu de `num_predict=1200`'de `done_reason="length"` ile
kesiliyordu. Yani terazi modelin cevabini degil, **duvara carpmasini**
puanliyordu.

2026-09-10'da sonda kosuldu: butce 4000'e cikarilinca dordu de
`done_reason="stop"` ile bitti. En uzun cevap **2977 cikis tokeni**
(`automation/TERAZI_ETAP1_2026-09-10.md` 1).

Bu dosya iki seyi korur:

1. **Butce olculen durma noktasinin uzerinde kalir.** Biri butceyi
   sessizce 1200'e geri cekerse ya da 2977'nin altina indirirse, terazi
   yine kesilmeyi olcmeye baslar ve bunu kimse fark etmez.
2. **`passing_threshold` bir TABAN KAYDIDIR, hedef degil** (A14). `">=N"`
   sozdizimi yasak; ve blok hangi butceyle olculdugunu SOYLEMELI, yoksa
   iki farkli tanimla olculmus sayilar yan yana konur.
"""
from __future__ import annotations

import json
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
VAKALAR = KOK / "eval" / "turkish_quality_cases.json"

#: Sondanin gordugu en uzun kendiliginden duran cevap (cikis tokeni).
#: Butce bunun ALTINA inerse olculen sey yine kesilme olur.
OLCULEN_DURMA_TOKENI = 2977


def _veri() -> dict:
    return json.loads(VAKALAR.read_text(encoding="utf-8"))


def test_longform_butcesi_olculen_durma_noktasinin_uzerinde():
    """Butce, modelin kendi durdugu en uzun cevabi tasiyabilmeli."""
    lf = [c for c in _veri()["cases"] if c.get("category") == "longform"]

    assert lf, "longform vakasi yok"
    for vaka in lf:
        butce = vaka.get("num_predict")
        assert butce is not None, f"{vaka['id']} butce beyan etmiyor"
        assert butce > OLCULEN_DURMA_TOKENI, (
            f"{vaka['id']} butcesi {butce}; olculen en uzun kendiliginden "
            f"duran cevap {OLCULEN_DURMA_TOKENI} token. Bu butceyle terazi "
            "modelin cevabini degil duvara carpmasini olcer."
        )


def test_taban_kaydi_hangi_butceyle_olculdugunu_soyler():
    """Iki farkli tanimla olculmus sayi, tanimi yazilmadan yan yana konamaz."""
    esik = _veri()["passing_threshold"]

    assert "olcum_tanimi" in esik, (
        "taban kaydi hangi butceyle olculdugunu soylemiyor; 49/64 ile yeni "
        "sayi ayni blokta yasayamaz"
    )
    tanim = esik["olcum_tanimi"]
    assert "longform_num_predict" in tanim, tanim


def test_taban_kaydinda_hedef_sozdizimi_yok():
    """A14: bu blok olculmus tabani yazar, tutturulacak hedefi degil."""
    esik = _veri()["passing_threshold"]

    for anahtar, deger in esik.items():
        if not isinstance(deger, str):
            continue
        assert ">=" not in deger, (
            f"`{anahtar}` hedef sozdizimi tasiyor: {deger!r}. A14: hedef "
            "yazmak 'sayiyi tutturmaya oynama' baskisini geri getirir."
        )


def test_eski_taban_silinmedi():
    """Eski sayi, hangi tanimla olculdugu ile birlikte KALIR."""
    esik = _veri()["passing_threshold"]
    metin = json.dumps(esik, ensure_ascii=False)

    assert "49/64" in metin, (
        "eski taban silinmis; tarihsel sayi yeniden yazilamaz, yalnizca "
        "tanimiyla birlikte etiketlenir"
    )


def test_longform_disindaki_vakalarin_butcesi_degismedi():
    """Degisen tek sey longform butcesi olmali (kart siniri)."""
    diger = [c for c in _veri()["cases"] if c.get("category") != "longform"]

    beyan_eden = [c for c in diger if c.get("num_predict") is not None]
    assert all(c["num_predict"] == 400 for c in beyan_eden), (
        "longform disinda bir vakanin butcesi oynamis: "
        f"{[(c['id'], c['num_predict']) for c in beyan_eden if c['num_predict'] != 400]}"
    )
