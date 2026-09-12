"""2000 butcesi -- longform disindaki 60 vakanin butcesi olculen durma noktasinin uzerinde.

Olculdu (automation/TERAZI_400_SONDA_2026-09-12.md): 400 butceli 60 vaka
2000 butceyle bir kez kosuldu, iki modelde. 120 cevabin 119'u kendiliginden
durdu; en uzun dogal cevap llama3.1 644, DeepSeek 462 cikis tokeni
(saglayicinin kendi sayaci). 400'de DeepSeek'in uc turkish vakasi duvara
carpip `truncated` sayiliyordu -- terazi cevabi degil kesilmeyi puanliyordu
(automation/TERAZI_ETAP5_2026-09-12.md §5).

Sayi 2000: Ahmet imzasi 2026-09-13 (automation/KART_400_UYGULA_VE_TABAN.md).
Bu dosya ETAP 1'in longform korumasinin (tests/test_longform_butcesi.py)
kisa vakalar icin ikizidir: butceyi sessizce 400'e geri ceken ya da 644'un
altina indiren biri terazinin yine kesilmeyi olcmeye baslamasina yol acar
ve bunu kimse fark etmez.
"""
from __future__ import annotations

#: Sondanin gordugu en uzun kendiliginden duran kisa-vaka cevabi (cikis
#: tokeni): llama3.1 `t1_tr_014`, butce 2000. Butce bunun ALTINA inerse
#: olculen sey yine kesilme olur.
OLCULEN_EN_UZUN_KISA_CEVAP = 644


def test_kisa_vakalarin_butcesi_olculen_durma_noktasinin_uzerinde():
    """Longform disindaki her vaka, sondada gorulen en uzun cevabi tasiyabilmeli."""
    from eval.run_turkish_quality import DEFAULT_NUM_PREDICT, load_cases

    kisa = [c for c in load_cases() if c.get("category") != "longform"]
    assert len(kisa) == 60, len(kisa)

    butceler = {c["id"]: int(c.get("num_predict") or DEFAULT_NUM_PREDICT)
                for c in kisa}
    dar = {i: b for i, b in butceler.items() if b <= OLCULEN_EN_UZUN_KISA_CEVAP}

    assert not dar, (
        f"{len(dar)} vakanin butcesi olculen en uzun kendiliginden duran "
        f"cevabin ({OLCULEN_EN_UZUN_KISA_CEVAP} token) altinda, ornek: "
        f"{sorted(dar.items())[:3]}. Bu butceyle terazi cevabi degil duvara "
        "carpmayi olcer."
    )
