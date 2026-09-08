"""K2 -- mutation gate KOSMAYAN bir test komutuna "mukemmel" diyemez.

`tests/test_mutation_gate.py::test_weak_tests_leave_survivor` yanip
sonuyordu: tam suitte `assert 1.0 < 0.8` ile dustu, tek basina 5/5
gecti, sonraki kosuda yesil geldi. Skorun 1.0 olmasi "her mutant oldu"
demek -- zayif test verildigi halde.

Kok neden OLCULDU (2026-09-08), tahmin edilmedi. `scripts/mutation_gate.py`
alt-surecin cikis kodunu tek bir esikle okuyordu:

    if cp.returncode != 0:
        killed += 1        # "testler bug'i yakaladi"

Sifirdan farkli HER cikis kodu "yakalandi" sayiliyor. Oysa pytest:

    0 = testler kosuldu, gecti          -> mutant HAYATTA
    1 = testler kosuldu, basarisiz      -> mutant OLDURULDU
    2 = kesinti      3 = ic hata
    4 = kullanim hatasi                 5 = hic test toplanmadi
        ^-- bunlarin hicbiri mutantin yakalandigini KANITLAMAZ

Olculen sonuc: test komutu hic calismadiginda kapi **skor 1.0** veriyor.

    "pytest <olmayan dosya>" (exit 5) -> skor=1.0  survivors=0
    "bu_komut_yok"                    -> skor=1.0  survivors=0
    "sys.exit(2)"                     -> skor=1.0  survivors=0

Yani anti-test-gaming kapisi, test komutu tamamen bozukken "testlerin
kusursuz" diyor. Bu `FAILURES.md`'deki "YESIL ile OLCULDU ayni sey
degildir" ailesinin ta kendisi: bir BASARISIZLIK sinyali, tespitin
KANITI olarak okunuyor.

Yanip sonmenin nasil dogdugu da buradan anlasiliyor: alt-surecteki
pytest cevresel bir sebeple kosamadiginda butun mutantlar "olduruldu"
sayiliyor ve skor 1.0'a firliyor.
"""
from __future__ import annotations

import sys
import textwrap

import pytest

from mutation_gate import run_gate

SRC = textwrap.dedent("""
    def grade(score):
        passed = score >= 50 and score <= 100
        return passed
""")

ZAYIF_TEST = textwrap.dedent("""
    import os, sys
    sys.path.insert(0, os.path.dirname(__file__))
    from srcmod import grade
    def test_mid():
        assert grade(75) is True
""")


def _kaynak(tmp_path) -> str:
    (tmp_path / "srcmod.py").write_text(SRC, encoding="utf-8")
    return str(tmp_path / "srcmod.py")


def _pytest_cmd(tmp_path, dosya: str) -> str:
    return f'"{sys.executable}" -m pytest "{tmp_path / dosya}" -q'


# ─── 1. Kosmayan komut skor uretmez ─────────────────────


@pytest.mark.parametrize("kod", [2, 3, 4, 5])
def test_kosmayan_test_komutu_mukemmel_skor_uretmez(tmp_path, kod):
    """Olculmeyen bir sey "olduruldu" sayilamaz -- sessizce 1.0 donmez."""
    from mutation_gate import MutationGateError

    src = _kaynak(tmp_path)
    komut = f'"{sys.executable}" -c "import sys; sys.exit({kod})"'

    with pytest.raises(MutationGateError) as hata:
        run_gate(src, komut, threshold=0.8, max_mutants=0, timeout=30)

    assert str(kod) in str(hata.value), (
        f"hata mesaji cikis kodunu soylemiyor: {hata.value}"
    )


def test_pytest_hic_test_toplayamazsa_skor_uretilmez(tmp_path):
    """Gercek pytest ile: olmayan dosya -> exit 4, skor yok."""
    from mutation_gate import MutationGateError

    src = _kaynak(tmp_path)

    with pytest.raises(MutationGateError):
        run_gate(src, _pytest_cmd(tmp_path, "boyle_bir_dosya_yok.py"),
                 threshold=0.8, max_mutants=0, timeout=60)


def test_bozuk_komutta_kaynak_yine_geri_yuklenir(tmp_path):
    """Istisna atilsa bile mutasyona ugrayan dosya orijinaline doner."""
    from mutation_gate import MutationGateError

    src = _kaynak(tmp_path)
    once = open(src, encoding="utf-8").read()

    with pytest.raises(MutationGateError):
        run_gate(src, f'"{sys.executable}" -c "import sys; sys.exit(4)"',
                 threshold=0.8, max_mutants=0, timeout=30)

    assert open(src, encoding="utf-8").read() == once, (
        "istisna yolunda kaynak mutasyonlu kaldi"
    )


def test_BILINEN_SINIR_bulunamayan_komut_ayirt_edilemiyor(tmp_path):
    """ACIK BORC: Windows kabugu "komut yok" icin de 1 donduruyor.

    Olculdu 2026-09-08: `cmd /c bu_komut_yok` -> exit 1, stderr'de
    "is not recognized as an internal or external command". Cikis kodu
    "testler kosuldu ve basarisiz" ile AYNI, yani bu vaka yalniz koda
    bakarak ayrilamiyor.

    Test bu siniri GORUNUR tutmak icin var: bulunamayan komut hala
    "olduruldu" sayiliyor ve skor 1.0 cikiyor. Duzeltilmesi stderr
    ayristirmayi ya da `shell=False`'a gecmeyi gerektirir; ikisi de
    `run_gate`'in sozlesmesini degistirir.
    """
    src = _kaynak(tmp_path)

    score, survivors, ran = run_gate(
        src, '"bu_komut_kesinlikle_yok_12345"',
        threshold=0.8, max_mutants=0, timeout=30,
    )

    assert (score, survivors) == (1.0, []), (
        "bilinen sinir kapanmis -- testin docstring'i ve FAILURES.md "
        "kaydi guncellenmeli"
    )
    assert ran >= 3


# ─── 2. Asiri duzeltme kontrolu ─────────────────────────


def test_gercek_basarisizlik_hala_olduruldu_sayilir(tmp_path):
    """exit 1 = testler KOSULDU ve basarisiz -- tek gecerli "yakalandi"."""
    src = _kaynak(tmp_path)
    (tmp_path / "test_srcmod.py").write_text(ZAYIF_TEST, encoding="utf-8")

    score, survivors, ran = run_gate(
        src, _pytest_cmd(tmp_path, "test_srcmod.py"),
        threshold=0.8, max_mutants=0, timeout=60,
    )

    assert ran >= 3
    assert 0.0 < score < 1.0, (
        f"zayif test hem oldurup hem kacirmali; skor {score}"
    )
    assert survivors, "zayif test hicbir mutanti kacirmadi -- supheli"
