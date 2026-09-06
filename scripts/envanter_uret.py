"""scripts/envanter_uret.py — JARVIS envanterini OLCEREK uretir.

    python scripts/envanter_uret.py            # docs/JARVIS_ENVANTER.md yazar
    python scripts/envanter_uret.py --kontrol   # yazmaz, yalniz ozet basar

**Bu betik hicbir dosyayi tasimaz, silmez, degistirmez.** Tek yazdigi sey
`docs/JARVIS_ENVANTER.md`'nin OTOMATIK bolumudur; isaretcinin ustundeki elle
yazilmis bolume dokunmaz.

Neden var: Ahmet'in sikayeti "ne entegre ne degil kimse bilmiyor" idi.
Cevabi goz karari veremeyiz -- `grep` ile "kullanilmiyor gibi" demek bu
kartin reddettigi seydir. Erisilebilirlik burada **hesaplanir**: giris
noktalarindan baslayip import grafiginde genislik-oncelikli arama yapilir,
her dosya icin "hangi giris noktasindan kac adimda" kaydedilir.

Iki bagimsiz kaynak kullanilir ve **karsilastirilir**:
  1. Bu betigin kendi AST taramasi (belirlenimci, aciklanabilir)
  2. `graphify-out/graph.json` (kartin isaret ettigi kaynak)
Ikisi ayrisirsa fark RAPORLANIR -- sessizce birinin tarafi tutulmaz.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

KOK = Path(__file__).resolve().parents[1]
CIKTI = KOK / "docs" / "JARVIS_ENVANTER.md"
GRAF = KOK / "graphify-out" / "graph.json"

#: Bu isaretcinin ALTI her kosuda yeniden uretilir; USTU elle yazilir ve
#: betik ona dokunmaz. Boylece anlati kaybolmadan tablolar tazelenir.
ISARETCI = "<!-- OTOMATIK-BOLUM: asagisi scripts/envanter_uret.py tarafindan uretilir -->"

# --------------------------------------------------------------------------- #
# Giris noktalari — SINIFLANDIRILMIS, cunku hepsi ayni sey degil
# --------------------------------------------------------------------------- #
#
# A: sistemi calistiran seyler (JARVIS'i baslatan kapilar)
# B: yardimci/arac kapilari (olcum, kurulum, bakim)
# P: PARK EDILMIS (CLAUDE.md §9) -- grafige DAHIL edilir ki neyi besledigi
#    gorunsun, ama "calistirilabilir" diye okunmaz.
#
# Bir modulun `if __name__ == "__main__":` blogu olmasi onu giris noktasi
# YAPMAZ. Repoda 40+ modulde kendini-deneme blogu var; hepsini giris saymak
# neredeyse her seyi CANLI gosterir ve harita degersizlesirdi. O bloklar
# ayri bir baslikta listelenir.
GIRIS_A = [
    "main.py",
    # gui.py 2026-09-06'da emekliye ayrildi (B02): islevleri jarvis_desktop.py
    # tarafindan zaten karsilaniyordu ve o dogru sekilde 127.0.0.1'e baglaniyor.
    # Sozlesme: tests/test_network_binding_contract.py
    "jarvis_desktop.py",
    "jarvis_server.py",
    "jarvis_brain.py",
    "agent/local_agent.py",
    "tools/telegram_agent.py",
]
GIRIS_P = [
    "auto_runner.py",
]
GIRIS_B_DESEN = ("scripts/", "eval/run_", "training/")
GIRIS_B_EK = [
    "setup.py", "setup_password.py", "indir.py",
    "jarvis_snapshot.py", "voice_test.py",
]

TEST_KOK = "tests/"

#: Statik import grafiginin GOREMEDIGI cagri bicimleri.
#: `sys.path` oynatmasi ozellikle onemli: `voice/voice_loop.py` ses hattini
#: `scripts/` altindaki bir module boyle bagliyor ve o bag import agacinda
#: gorunmuyor -- olculdu, uydurulmadi.
DINAMIK = re.compile(r"importlib\.|__import__\(|exec\(|eval\(|globals\(\)\["
                     r"|sys\.path\.(insert|append)")


# --------------------------------------------------------------------------- #
# 1. Dosya listesi ve modul haritasi
# --------------------------------------------------------------------------- #

def izlenen_py() -> List[str]:
    r = subprocess.run(["git", "ls-files", "*.py"], cwd=KOK,
                       capture_output=True, text=True, check=True)
    return sorted(s.strip().replace("\\", "/") for s in r.stdout.splitlines() if s.strip())


def modul_haritasi(dosyalar: List[str]) -> Dict[str, str]:
    """Nokta ile ayrilmis modul adi -> repo yolu."""
    h: Dict[str, str] = {}
    for d in dosyalar:
        p = d[:-3]                      # .py at
        if p.endswith("/__init__"):
            p = p[: -len("/__init__")]
        h[p.replace("/", ".")] = d
    return h


# --------------------------------------------------------------------------- #
# 2. AST import taramasi
# --------------------------------------------------------------------------- #

def _paket(dosya: str) -> str:
    parcalar = dosya.split("/")[:-1]
    return ".".join(parcalar)


def _cozumle(ad: str, harita: Dict[str, str]) -> Set[str]:
    """Modul adini repo dosyalarina cozer; ust paketleri de dahil eder.

    `import a.b.c` calisirken a/__init__.py ve a/b/__init__.py da yurutulur,
    dolayisiyla ucu de erisilmis sayilir.
    """
    bulunan: Set[str] = set()
    parcalar = ad.split(".")
    for i in range(1, len(parcalar) + 1):
        onek = ".".join(parcalar[:i])
        if onek in harita:
            bulunan.add(harita[onek])
    return bulunan


def ast_kenarlari(dosyalar: List[str], harita: Dict[str, str]
                  ) -> Tuple[Dict[str, Set[str]], List[str]]:
    """dosya -> import ettigi repo dosyalari. Ikinci deger: ayrisamayanlar."""
    kenar: Dict[str, Set[str]] = defaultdict(set)
    hatali: List[str] = []
    for d in dosyalar:
        try:
            agac = ast.parse((KOK / d).read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            hatali.append(f"{d}: {exc}")
            continue
        paket = _paket(d)
        for dugum in ast.walk(agac):
            if isinstance(dugum, ast.Import):
                for a in dugum.names:
                    kenar[d] |= _cozumle(a.name, harita)
            elif isinstance(dugum, ast.ImportFrom):
                if dugum.level:                     # goreli import
                    ust = paket.split(".")
                    taban = ".".join(ust[: len(ust) - (dugum.level - 1)]) if dugum.level > 1 else paket
                    tam = f"{taban}.{dugum.module}" if dugum.module else taban
                else:
                    tam = dugum.module or ""
                if not tam:
                    continue
                kenar[d] |= _cozumle(tam, harita)
                for a in dugum.names:               # from paket import altmodul
                    kenar[d] |= _cozumle(f"{tam}.{a.name}", harita)
        kenar[d].discard(d)
    return kenar, hatali


# --------------------------------------------------------------------------- #
# 3. Graphify kenarlari (bagimsiz ikinci kaynak)
# --------------------------------------------------------------------------- #

#: Yalniz KOD iliskileri. `references`, `cites`, `rationale_for`,
#: `conceptually_related_to` gibi anlamsal kenarlar erisilebilirlik kaniti
#: DEGILDIR -- belge duzeyinde benzerlik gosterirler.
KOD_ILISKILERI = {"imports", "imports_from", "calls", "indirect_call",
                  "inherits", "method", "uses"}


def graphify_kenarlari() -> Tuple[Dict[str, Set[str]], Optional[str]]:
    if not GRAF.exists():
        return {}, "graphify-out/graph.json yok"
    g = json.loads(GRAF.read_text(encoding="utf-8"))
    dugum = {x["id"]: x for x in g.get("nodes", [])}
    kenar: Dict[str, Set[str]] = defaultdict(set)
    for bag in g.get("links", []):
        if bag.get("relation") not in KOD_ILISKILERI or bag.get("_origin") != "ast":
            continue
        k = dugum.get(bag.get("source"), {}).get("source_file") or bag.get("source_file")
        h = dugum.get(bag.get("target"), {}).get("source_file")
        if not k or not h or not k.endswith(".py") or not h.endswith(".py"):
            continue
        k, h = k.replace("\\", "/"), h.replace("\\", "/")
        if k != h:
            kenar[k].add(h)
    return kenar, None


# --------------------------------------------------------------------------- #
# 4. Erisilebilirlik
# --------------------------------------------------------------------------- #

def bfs(kenar: Dict[str, Set[str]], kokler: List[str]) -> Dict[str, Tuple[int, str]]:
    """dosya -> (en kisa adim, hangi giris noktasindan)."""
    sonuc: Dict[str, Tuple[int, str]] = {}
    for kok in kokler:
        kuyruk = deque([(kok, 0)])
        gorulen = {kok}
        while kuyruk:
            d, adim = kuyruk.popleft()
            eski = sonuc.get(d)
            if eski is None or adim < eski[0]:
                sonuc[d] = (adim, kok)
            for h in sorted(kenar.get(d, ())):
                if h not in gorulen:
                    gorulen.add(h)
                    kuyruk.append((h, adim + 1))
    return sonuc


# --------------------------------------------------------------------------- #
# 5. Ek taramalar
# --------------------------------------------------------------------------- #

def kendi_main_blogu(dosyalar: List[str]) -> List[str]:
    bulunan = []
    for d in dosyalar:
        try:
            m = (KOK / d).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if '__name__ == "__main__"' in m or "__name__ == '__main__'" in m:
            bulunan.append(d)
    return bulunan


def dinamik_izler(dosyalar: List[str]) -> Dict[str, List[str]]:
    """Erisilebilirligi HESAPLANAMAYAN cagri bicimleri."""
    bulunan: Dict[str, List[str]] = {}
    for d in dosyalar:
        satirlar = []
        try:
            metin = (KOK / d).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, s in enumerate(metin.splitlines(), 1):
            if DINAMIK.search(s) and not s.lstrip().startswith("#"):
                satirlar.append(f"L{i}: {s.strip()[:88]}")
        if satirlar:
            bulunan[d] = satirlar
    return bulunan


def ornek_yapilandirmalar() -> List[Tuple[str, str, bool]]:
    r = subprocess.run(["git", "ls-files"], cwd=KOK, capture_output=True,
                       text=True, check=True)
    cikti = []
    for f in r.stdout.splitlines():
        f = f.strip().replace("\\", "/")
        if ".example" in f:
            gercek = f.replace(".example", "")
            cikti.append((f, gercek, (KOK / gercek).exists()))
    return sorted(cikti)


def belgede_gecen_olmayan_py() -> Dict[str, List[str]]:
    """Belgelerde adi gecen ama diskte OLMAYAN .py dosyalari."""
    r = subprocess.run(["git", "ls-files", "*.md"], cwd=KOK,
                       capture_output=True, text=True, check=True)
    desen = re.compile(r"[`(\s/]([A-Za-z0-9_./-]+\.py)\b")
    eksik: Dict[str, List[str]] = defaultdict(list)
    for md in r.stdout.splitlines():
        md = md.strip().replace("\\", "/")
        try:
            metin = (KOK / md).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in set(desen.findall(metin)):
            yol = m.lstrip("./")
            if "*" in yol or yol.startswith("<"):
                continue
            if not (KOK / yol).exists() and not list(KOK.glob(f"**/{Path(yol).name}")):
                eksik[yol].append(md)
    return {k: sorted(set(v)) for k, v in sorted(eksik.items())}


# --------------------------------------------------------------------------- #
# 6. Siniflandirma
# --------------------------------------------------------------------------- #

def siniflandir(dosyalar: List[str], kenar: Dict[str, Set[str]],
                ornekler: List[Tuple[str, str, bool]]) -> Dict[str, dict]:
    giris_a = [d for d in GIRIS_A if d in dosyalar]
    giris_p = [d for d in GIRIS_P if d in dosyalar]
    giris_b = sorted({d for d in dosyalar
                      if d.startswith(GIRIS_B_DESEN) or d in GIRIS_B_EK}
                     - set(giris_a) - set(giris_p))
    testler = [d for d in dosyalar if d.startswith(TEST_KOK)]

    a_ulasan = bfs(kenar, giris_a)
    p_ulasan = bfs(kenar, giris_p)
    b_ulasan = bfs(kenar, giris_b)
    t_ulasan = bfs(kenar, testler)

    # Gercek yapilandirmasi olmayan .example bekleyenler
    bekleyen = {g for _, g, var in ornekler if not var}

    sonuc: Dict[str, dict] = {}
    for d in dosyalar:
        kayit = {"a": a_ulasan.get(d), "b": b_ulasan.get(d),
                 "p": p_ulasan.get(d), "t": t_ulasan.get(d)}
        if d in giris_a:
            kayit["sinif"], kayit["kanit"] = "CANLI", "giris noktasi (A)"
        elif d in giris_p:
            kayit["sinif"], kayit["kanit"] = "CANLI", "giris noktasi (PARK EDILMIS)"
        elif d in giris_b:
            kayit["sinif"], kayit["kanit"] = "CANLI", "giris noktasi (B: arac)"
        elif kayit["a"]:
            kayit["sinif"] = "CANLI"
            kayit["kanit"] = f"{kayit['a'][1]} -> {kayit['a'][0]} adim"
        elif kayit["b"]:
            kayit["sinif"] = "CANLI"
            kayit["kanit"] = f"{kayit['b'][1]} -> {kayit['b'][0]} adim (arac hatti)"
        elif kayit["p"]:
            kayit["sinif"] = "CANLI"
            kayit["kanit"] = f"{kayit['p'][1]} -> {kayit['p'][0]} adim (PARK EDILMIS hat)"
        elif d in testler:
            kayit["sinif"], kayit["kanit"] = "YALNIZ-TEST", "test dosyasinin kendisi"
        elif kayit["t"]:
            kayit["sinif"] = "YALNIZ-TEST"
            kayit["kanit"] = f"yalniz testlerden: {kayit['t'][1]} -> {kayit['t'][0]} adim"
        else:
            kayit["sinif"], kayit["kanit"] = "YETIM", "hicbir giristen ve testten erisilemiyor"
        sonuc[d] = kayit

    # ORNEK/SABLON: gercek yapilandirmasi olmayan dosyayi acikca isteyen modul
    for d in dosyalar:
        try:
            metin = (KOK / d).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for gereken in bekleyen:
            if gereken and Path(gereken).name in metin:
                sonuc[d]["ornek_bekliyor"] = gereken
                break
    return sonuc


# --------------------------------------------------------------------------- #
# 7. Belge uretimi
# --------------------------------------------------------------------------- #

def _tablo(basliklar, satirlar) -> List[str]:
    return (["| " + " | ".join(basliklar) + " |",
             "|" + "|".join(["---"] * len(basliklar)) + "|"]
            + ["| " + " | ".join(str(h) for h in s) + " |" for s in satirlar])


def uret() -> str:
    dosyalar = izlenen_py()
    harita = modul_haritasi(dosyalar)
    kenar, sozdizim_hatasi = ast_kenarlari(dosyalar, harita)
    g_kenar, g_hata = graphify_kenarlari()
    ornekler = ornek_yapilandirmalar()
    sinif = siniflandir(dosyalar, kenar, ornekler)

    # Iki kaynagin ayrismasi
    ast_ciftler = {(k, h) for k, hs in kenar.items() for h in hs}
    g_ciftler = {(k, h) for k, hs in g_kenar.items() for h in hs
                 if k in harita.values() or k in dosyalar}
    yalniz_ast = ast_ciftler - g_ciftler
    yalniz_g = g_ciftler - ast_ciftler

    sayim = defaultdict(int)
    for k in sinif.values():
        sayim[k["sinif"]] += 1

    L: List[str] = [ISARETCI, ""]
    L += ["*Uretim: `python scripts/envanter_uret.py`. Bu bolum elle "
          "duzenlenmez; isaretcinin ustu elle yazilir.*", ""]

    # --- Ozet ---
    L += ["## A. Sayilar", "",
          f"Izlenen `.py`: **{len(dosyalar)}** "
          f"(test: {sum(1 for d in dosyalar if d.startswith(TEST_KOK))}, "
          f"test disi: {sum(1 for d in dosyalar if not d.startswith(TEST_KOK))})", ""]
    L += _tablo(["Sinif", "Adet"],
                [[s, sayim.get(s, 0)] for s in ("CANLI", "YALNIZ-TEST", "YETIM")])
    L += ["", "Test disi dosyalarin sinif dagilimi:", ""]
    td = defaultdict(int)
    for d, k in sinif.items():
        if not d.startswith(TEST_KOK):
            td[k["sinif"]] += 1
    L += _tablo(["Sinif", "Adet"], [[s, td.get(s, 0)] for s in ("CANLI", "YALNIZ-TEST", "YETIM")])
    L += [""]

    # --- Giris noktalari ---
    giris_a = [d for d in GIRIS_A if d in dosyalar]
    giris_p = [d for d in GIRIS_P if d in dosyalar]
    giris_b = sorted({d for d in dosyalar
                      if d.startswith(GIRIS_B_DESEN) or d in GIRIS_B_EK}
                     - set(giris_a) - set(giris_p))
    L += ["## B. Giris noktalari", "",
          "**A — sistemi calistiranlar.** JARVIS'i baslatan kapilar.", ""]
    L += _tablo(["Dosya", "Buradan erisilen dosya sayisi"],
                [[f"`{d}`", len(bfs(kenar, [d])) - 1] for d in giris_a])
    L += ["", "**PARK EDILMIS (CLAUDE.md §9 — CALISTIRMA).** Grafige neyi "
          "besledigi gorunsun diye dahil edildi.", ""]
    L += _tablo(["Dosya", "Buradan erisilen dosya sayisi"],
                [[f"`{d}`", len(bfs(kenar, [d])) - 1] for d in giris_p])
    L += ["", f"**B — arac kapilari** ({len(giris_b)} dosya): olcum, kurulum, "
          "bakim. Bunlardan erisilen bir modul CANLI'dir ama ses hattinda "
          "olmayabilir; kanit sutunu hangisinden geldigini soyler.", ""]

    # --- Tam siniflandirma ---
    L += ["## C. Her `.py` dosyasinin sinifi", "",
          "`kanit` sutunu erisilebilirligin NASIL hesaplandigini soyler: "
          "hangi giris noktasindan kac adim.", ""]
    for dizin in sorted({d.split("/")[0] if "/" in d else "(kok)" for d in dosyalar}):
        alt = [d for d in dosyalar
               if (d.split("/")[0] if "/" in d else "(kok)") == dizin]
        if dizin == "tests":
            L += [f"### `{dizin}/` — {len(alt)} dosya", "",
                  "Hepsi **YALNIZ-TEST**: test kosucusundan baska cagirani yok. "
                  "Bu bir kusur degil, tanim. Tek tek listelenmedi.", ""]
            continue
        L += [f"### `{dizin}` — {len(alt)} dosya", ""]
        L += _tablo(["Dosya", "Sinif", "Kanit", "Not"],
                    [[f"`{d}`", sinif[d]["sinif"], sinif[d]["kanit"],
                      (f"`{sinif[d]['ornek_bekliyor']}` bekliyor"
                       if sinif[d].get("ornek_bekliyor") else "")]
                     for d in sorted(alt)])
        L += [""]

    # --- Yetimler ---
    yetim = sorted(d for d, k in sinif.items() if k["sinif"] == "YETIM")
    L += ["## D. Cop adaylari — LISTE, SILME DEGIL", "",
          "CLAUDE.md §3: *\"onceden var olan dead code'a dokunma "
          "(gor, soyle, silme).\"* Bu bolum bir karar listesidir; "
          "bu kart hicbirini silmedi.", ""]
    if yetim:
        satir = []
        for d in yetim:
            p = KOK / d
            boyut = p.stat().st_size if p.exists() else 0
            try:
                tarih = subprocess.run(
                    ["git", "log", "-1", "--format=%ad", "--date=short", "--", d],
                    cwd=KOK, capture_output=True, text=True, check=False).stdout.strip()
            except Exception:  # noqa: BLE001
                tarih = "?"
            satir.append([f"`{d}`", f"{boyut:,} B", tarih or "?"])
        L += _tablo(["Dosya", "Boyut", "Son commit"], satir)
    else:
        L += ["Yetim dosya bulunamadi."]
    L += [""]

    # --- Olculemeyenler ---
    L += ["## E. Erisilebilirligi HESAPLANAMAYAN yerler", "",
          "Dinamik cagri (`importlib`, `__import__`, `exec`, `getattr`) statik "
          "grafikte gorunmez. Asagidaki dosyalar bu bicimleri kullaniyor; "
          "onlardan cikan baglar **eksik olabilir**. Bir modul yalniz dinamik "
          "yoldan cagriliyorsa YETIM gorunur ama olmayabilir.", ""]
    din = dinamik_izler([d for d in dosyalar if not d.startswith(TEST_KOK)])
    for d, satirlar in sorted(din.items()):
        L += [f"- `{d}`"]
        L += [f"  - `{s}`" for s in satirlar[:6]]
        if len(satirlar) > 6:
            L += [f"  - … ({len(satirlar) - 6} satir daha)"]
    L += [""]

    # --- Ornek/sablon ---
    L += ["## F. ORNEK/SABLON — gercek yapilandirma bekleyenler", ""]
    L += _tablo(["Sablon", "Beklenen gercek dosya", "Var mi"],
                [[f"`{s}`", f"`{g}`", "EVET" if var else "**YOK**"]
                 for s, g, var in ornekler])
    L += ["", "Bu dosyalarin ICERIGI okunmadi (CLAUDE.md §9). Yalniz "
          "varliklari kontrol edildi.", ""]

    # --- Belge var kod yok ---
    L += ["## G. BELGE-VAR-KOD-YOK", "",
          "Belgelerde adi gecen ama diskte bulunmayan `.py` dosyalari.", ""]
    eksik = belgede_gecen_olmayan_py()
    if eksik:
        L += _tablo(["Anilan dosya", "Nerede aniliyor"],
                    [[f"`{k}`", ", ".join(f"`{x}`" for x in v[:3])
                      + (f" (+{len(v) - 3})" if len(v) > 3 else "")]
                     for k, v in eksik.items()])
    else:
        L += ["Bulunamadi."]
    L += [""]

    # --- Kendi main bloklari ---
    kendi = [d for d in kendi_main_blogu(dosyalar) if not d.startswith(TEST_KOK)]
    kendi = [d for d in kendi if d not in giris_a + giris_b + giris_p]
    L += ["## H. Kendi `__main__` blogu olan ama giris noktasi SAYILMAYAN moduller",
          "",
          f"{len(kendi)} modul kendini-deneme blogu tasiyor. Bunlari giris "
          "noktasi saymak neredeyse her seyi CANLI gosterirdi; ayri tutuldular. "
          "Bir modul bu listedeyse **elle** calistirilabilir demektir.", ""]
    L += ["- " + ", ".join(f"`{d}`" for d in sorted(kendi))] if kendi else ["Yok."]
    L += [""]

    # --- Iki kaynagin karsilastirmasi ---
    L += ["## I. Olcumun kendisi ne kadar guvenilir", "",
          "Erisilebilirlik iki bagimsiz kaynaktan hesaplandi ve karsilastirildi.", ""]
    L += _tablo(["Kaynak", "Dosya-duzeyi kenar"],
                [["Bu betigin AST taramasi", len(ast_ciftler)],
                 ["graphify `graph.json` (yalniz `ast` kokenli kod iliskileri)",
                  len(g_ciftler)],
                 ["Yalniz AST'de var", len(yalniz_ast)],
                 ["Yalniz graphify'da var", len(yalniz_g)]])
    L += ["", "Siniflandirma **AST taramasindan** hesaplandi: import iliskisi "
          "belirlenimci ve satir satir dogrulanabilir. graphify grafigi ikinci "
          "kaynak olarak tutuldu; `calls`/`method` gibi cagri kenarlari import "
          "grafiginin gormedigi baglari da tasidigi icin sayisi farklidir.", ""]
    if yalniz_g:
        ornek = sorted(yalniz_g)[:10]
        L += ["Yalniz graphify'da gorunen kenarlardan ornekler "
              "(cagri kenarlari — import olmadan da olusabilir):", ""]
        L += [f"- `{a}` -> `{b}`" for a, b in ornek]
        L += [""]
    if sozdizim_hatasi:
        L += ["**Ayristirilamayan dosyalar (sozdizimi):**", ""]
        L += [f"- `{s}`" for s in sozdizim_hatasi]
        L += [""]
    if g_hata:
        L += [f"**graphify uyarisi:** {g_hata}", ""]

    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="JARVIS envanteri uretir")
    ap.add_argument("--kontrol", action="store_true",
                    help="dosyaya yazma, yalniz ozet bas")
    a = ap.parse_args()

    govde = uret()
    if a.kontrol:
        print(govde[:2000])
        return 0

    if CIKTI.exists():
        eski = CIKTI.read_text(encoding="utf-8")
        bas = eski.split(ISARETCI)[0] if ISARETCI in eski else eski + "\n"
    else:
        bas = "# JARVIS Envanteri\n\n*(elle yazilan bolum henuz bos)*\n\n"
    CIKTI.write_text(bas + govde, encoding="utf-8")
    print(f"yazildi: {CIKTI.relative_to(KOK)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
