"""B01 -- `calculate` sandbox kacisi kapali kalmali.

`eval(expression, {"__builtins__": {}}, safe_dict)` bir sandbox DEGILDI.
Bos `__builtins__` yalnizca ADLARI gizler, nesne grafigini degil: her
Python nesnesinden `().__class__.__base__.__subclasses__()` ile tum
siniflara, oradan `catch_warnings.__init__.__globals__['__builtins__']`
ile gercek yerlesiklere donulebiliyor. Danisman kendi makinesinde
`sum([20,22])` -> 42 aldi; ayni zincirden `open` ve `__import__('os')
.system` de erisilebiliyordu.

Testler ARAC SOZLUGUNE BAKMAKLA YETINMEZ: girdi `LocalJarvisAgent`'in
`_detect_tool` -> `_run_tool` zincirinden gecip gercek `calculate`'e
ulasir. Fonksiyonu dogrudan cagiran bir test, ajanin o fonksiyona giden
yolunu kanitlamaz (Codex'in ozel uyarisi).

Kapsam yalniz B01'dir. `run_python_code` (`tools/tools.py:482`) ve API
yolundaki `exec`/`eval` noktalari B09'un konusudur, burada test edilmez.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent

#: Danismanin CALISAN istismari. Eski kodda sayi donduruyordu.
KACIS_IFADESI = (
    "[c for c in ().__class__.__base__.__subclasses__() "
    "if c.__name__=='catch_warnings'][0].__init__"
    ".__globals__['__builtins__']['sum']([20,22])"
)

#: Kacisin her halkasi ayri ayri kapali olmali -- zincirin tamamini tek
#: vakada sinamak, yarim kapatilmis bir duzeltmeyi yesil gosterebilir.
NESNE_GRAFIGI_IFADELERI = [
    "().__class__",
    "().__class__.__base__",
    "().__class__.__base__.__subclasses__()",
    "().__class__.__init__.__globals__",
    "().__init__",
    "__builtins__",
    "abs.__self__",
    "open('LICENSE')",
    "__import__('os').system('echo kacis')",
    "exec('1')",
    "eval('1')",
    "[c for c in (1, 2)]",
    "'abc'.upper()",
    "(lambda: 1)()",
]


@pytest.fixture(scope="module")
def ajan():
    """Gercek LocalJarvisAgent -- Ollama olmadan, ama gercek arac sozlugu ile."""
    from agent.local_agent import LocalJarvisAgent

    a = LocalJarvisAgent.__new__(LocalJarvisAgent)
    a._tools = a._load_tools()
    a.tool_calls_total = 0
    return a


def _hesapla(ajan, ifade: str) -> str:
    """Kullanici cumlesinden gercek `calculate` ciktisina kadar TAM yol."""
    mesaj = f"hesapla {ifade}"
    algi = ajan._detect_tool(mesaj)
    assert algi is not None, f"cumle hicbir araci tetiklemedi: {mesaj!r}"
    ad, kwargs = algi
    assert ad == "calculate", f"beklenen arac calculate, gelen {ad}"
    assert kwargs["expression"] == ifade, "ifade yolda bozuldu"
    return ajan._run_tool(ad, kwargs)


def _hesaplandi_mi(ifade: str, cikti: str) -> bool:
    """Basari bicimi tek: ``"{ifade} = {sonuc}"``. Baska her sey reddir."""
    return cikti.startswith(f"{ifade} = ")


# ─── 1. Kacis reddedilir ────────────────────────────────


def test_catch_warnings_kacisi_reddedilir(ajan):
    """Danismanin dogruladigi istismar artik sayi dondurmuyor."""
    cikti = _hesapla(ajan, KACIS_IFADESI)

    assert not _hesaplandi_mi(KACIS_IFADESI, cikti), (
        f"sandbox kacisi hala calisiyor: {cikti!r}"
    )
    assert "42" not in cikti, f"gadget zinciri sonuc uretti: {cikti!r}"


@pytest.mark.parametrize("ifade", NESNE_GRAFIGI_IFADELERI)
def test_nesne_grafigi_ifadeleri_reddedilir(ajan, ifade):
    """Nitelik erisimi, indeksleme, lambda, uretec ve ad cagrisi kapali."""
    cikti = _hesapla(ajan, ifade)

    assert not _hesaplandi_mi(ifade, cikti), (
        f"izin verilmemesi gereken ifade hesaplandi: {cikti!r}"
    )


# ─── 2. Normal hesaplar bozulmadi ───────────────────────


@pytest.mark.parametrize(
    "ifade,beklenen",
    [
        ("2**10", "1024"),
        ("sqrt(144)", "12.0"),
        ("abs(-5)", "5"),
        ("round(3.14159, 2)", "3.14"),
        ("(2 + 3) * 4 - 6 / 3", "18.0"),
        ("10 % 3", "1"),
        ("7 // 2", "3"),
    ],
)
def test_normal_hesaplar_dogru_sonuc_verir(ajan, ifade, beklenen):
    assert _hesapla(ajan, ifade) == f"{ifade} = {beklenen}"


def test_sin_pi_bolu_dort_dogru_hesaplanir(ajan):
    ifade = "sin(pi/4)*100"
    cikti = _hesapla(ajan, ifade)

    assert _hesaplandi_mi(ifade, cikti), f"normal hesap reddedildi: {cikti!r}"
    assert float(cikti.split(" = ", 1)[1]) == pytest.approx(70.71067811865476)


def test_sifira_bolme_mesaji_korunur(ajan):
    """Var olan davranis: sifira bolme kendi mesajini dondurur."""
    assert _hesapla(ajan, "1/0") == "Hata: Sıfıra bölme"


# ─── 3. Kaynak tuketme de bir saldiridir ────────────────


def test_asiri_us_reddedilir(ajan):
    """`2**5000` bir hesap degil, kaynak istegidir.

    Bu vaka bilerek "hizli ama asiri" secildi: eski kod onu saniyenin
    altinda hesapliyordu, yani kirmizi gorulmesi guvenliydi.
    """
    ifade = "2**5000"
    cikti = _hesapla(ajan, ifade)

    assert not _hesaplandi_mi(ifade, cikti), (
        f"sinirsiz us hesaplandi: {cikti[:120]!r}"
    )


_ALT_SUREC = """
import sys
sys.path.insert(0, sys.argv[1])
from agent.local_agent import LocalJarvisAgent
a = LocalJarvisAgent.__new__(LocalJarvisAgent)
a._tools = a._load_tools()
a.tool_calls_total = 0
ad, kwargs = a._detect_tool("hesapla " + sys.argv[2])
sys.stdout.write("SONUC:" + a._run_tool(ad, kwargs))
"""


def test_ic_ice_us_hesaplanmadan_reddedilir():
    """`9**9**9` ANINDA reddedilmeli -- hesaplanmaya baslanmamali.

    Ayri surec ve sert zaman siniri testin ozudur: eski kod bu ifadeyi
    hesaplamaya girisip dakikalarca CPU ve yuzlerce MB RAM yiyordu. Ayni
    surecte kosmak butun suiti kilitlerdi; sure asimi = test basarisiz.
    """
    ortam = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run(
            [sys.executable, "-c", _ALT_SUREC, str(KOK), "9**9**9"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, env=ortam,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            "calculate('9**9**9') 30 saniyede donmedi: ifade reddedilmeden "
            "hesaplanmaya calisiliyor -- kaynak tuketme yuzeyi acik"
        )

    assert "SONUC:" in p.stdout, f"alt surec cikti uretmedi: {p.stderr[-500:]!r}"
    assert "SONUC:9**9**9 = " not in p.stdout, (
        f"ic ice us hesaplandi: {p.stdout[-200:]!r}"
    )


@pytest.mark.parametrize("expression", [
    "frexp(1)*100",
    "modf(1.5)*100",
    "100*frexp(1)",
    "frexp(1)+modf(1.5)",
    "*".join(["(2**999)"] * 11),
    "1" + "0" * 3100,
    "1e309",
])
def test_non_scalar_or_oversized_arithmetic_is_rejected(ajan, expression):
    # Small tuple probes are safe even against the vulnerable implementation.
    result = _hesapla(ajan, expression)
    assert not _hesaplandi_mi(expression, result)


def test_tuple_rejected_before_multiplication(monkeypatch):
    import ast
    from tools import tools

    reached = []
    def multiply(left, right):
        reached.append((type(left).__name__, right))
        return 0  # Never allocate a giant tuple, including during RED.

    monkeypatch.setitem(tools._BINARY_OPS, ast.Mult, multiply)
    tools.calculate("frexp(1)*1000000000")
    assert reached == [], "non-scalar value reached the arithmetic operator"
