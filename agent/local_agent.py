"""
jarvis/agent/local_agent.py — v5
Doğal sohbet + temiz yanıtlar
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional
from rich.console import Console

from agents.data_classifier import _fold_tr, keyword_present
from agents.model_registry import ModelRegistry
from agents.persona import VOICE_MODE_DIRECTIVE, build_system_prompt

console = Console()

#: Tur siniflandirmasi -> persona seviyesi. Ayni siniflandirma hem modeli hem
#: prompt derinligini secer; iki yerde ayri esik tutulmaz.
_TIER_TO_LEVEL = {"fast": "L1", "mid": "L2", "deep": "L3"}

#: Selamlama ve nezaket deyimleri (fold'lanmis). Iki isi birden yapar:
#: bunlar ARAC TETIKLEMEZ ve `fast` sinifina duser.
#:
#: Neden ayri bir katman: canli testte "Ne haber Jarvis?" web aramasi
#: tetikledi, cunku "haber" TOOL_TRIGGERS icinde. Kelime siniri bunu cozmez --
#: "ne haber" icinde "haber" zaten tam kelime. Ayrim deyimde: "ne haber" bir
#: selamlamadir, "son dakika haberleri" bir arama istegidir.
_SELAMLAR: tuple[str, ...] = (
    "merhaba", "selam", "naber", "ne haber", "ne haberler",
    "gunaydin", "iyi sabahlar", "iyi aksamlar", "iyi geceler", "iyi gunler",
    "nasilsin", "nasilsiniz", "iyi misin", "iyi misiniz", "keyifler nasil",
    "tesekkur", "tesekkurler", "sag ol", "sagol", "eyvallah",
    "gorusuruz", "hosca kal", "kolay gelsin", "hos geldin",
    "tamam", "peki", "anladim", "evet", "hayir", "olur",
)

#: Selamlama sayilmak icin ust sinir. Uzun bir mesaj selamla baslasa bile
#: selamlama degildir: "Merhaba, su konuyu uzun uzun anlat..." gercek bir istek.
_SELAM_MAX_UZUNLUK = 60

#: Veriyi BU MAKINEDEN CIKARAN araclar ve sorguyu tasiyan argumanlarinin adi.
#:
#: B03 (Codex denetimi, 2026-09-06): bu yol `WebResearchPolicy`'den gecmiyordu.
#: `parola=...` iceren bir sorgu arama saglayicisina AYNEN gidiyordu, ve
#: kullanicinin acik "internete cikma" yasagi hicbir yerde okunmuyordu.
#:
#: Kapi `_run_tool`'da, `_detect_tool`'da DEGIL: sinir niyet tahmininde degil
#: yurutme kodunda uygulanir (OWASP LLM01 -- disaridan gelen icerik model
#: talimatina donusebilir, o yuzden prompt seviyesi koruma yetmez).
_EGRESS_ARACLARI: dict[str, str] = {
    "web_search": "query",
    "deep_research": "topic",
}

#: Kullanicinin ACIK "disari cikma" talimati. Kokler yazilir, ekleri
#: `keyword_present` karsilar (CLAUDE.md 6: Turkce sondan eklemelidir ve
#: duz `.lower()` "İ" tuzagina duser).
#:
#: Bu kontrol politikadan ONCE calisir cunku CLAUDE.md 7 boyle emrediyor:
#: "Human override her katmandan ustun: kullanici her an dur/iptal/unut/
#: yerel-kal diyebilir." Politikanin "bu sorgu guncel bilgi gerektiriyor"
#: karari, kullanicinin acik yasagini gecersiz kilamaz.
#:
#: Yanlis pozitif tarafi bilerek secildi: yanlislikla yerel kalirsak cevap
#: zayiflar, yanlislikla disari cikarsak veri sizar. Asimetri lehimize.
_YEREL_KAL_KOKLERI: tuple[str, ...] = (
    "internete cikma", "internete girme", "internete baglanma",
    "webe cikma", "web'e cikma", "aga cikma",
    "disari cikma", "disariya cikma",
    "yerel kal", "lokal kal", "offline kal",
    "arama yapma", "arastirma yapma", "google'lama", "googlelama",
)


def _yerel_kal_istendi(message: str) -> bool:
    """Kullanici aciktan disari cikilmamasini istedi mi?"""
    if not message:
        return False
    fold = _fold_tr(message)
    return any(keyword_present(fold, k) for k in _YEREL_KAL_KOKLERI)


#: ACIK belge isareti. B07 (Codex denetimi, 2026-09-06) oncesinde bu liste
#: "oku, analiz, incele, bak, indir, dosya, yukle" gibi FIILLERI de iceriyordu
#: ve duz alt dize araniyordu. Sonuc: "Bu kodun mantigini analiz et" cumlesi
#: normal sohbeti birakip en yeni PDF'yi acıyordu.
#:
#: Simdi yalnizca BELGE ADI gecerli. Fiiller cikarildi cunku tek baslarina
#: hicbir sey soylemiyorlar: "bir bak" bir dosya istegi degildir.
#:
#: Asimetri bilerek: yanlis negatif ucuz (kullanici "pdf oku" der, calisir),
#: yanlis pozitif pahali (kod sorusu rastgele bir PDF'e sapar).

#: Dosya adi uzantisi -- "rapor.pdf" gibi acik bir hedef de gecerli isarettir.
#: `.md` ve `.txt` A-07'de CIKARILDI: burasi bir kod deposu, "README.md nedir?"
#: ve "requirements.txt nedir?" gunluk kod sorulari -- ikisi de rastgele bir
#: PDF aciyordu.
_BELGE_UZANTISI = re.compile(r"\.(pdf|docx?|epub)\b", re.IGNORECASE)

#: "pdf" tek basina yeter: acik ve tek anlamli bir hedeftir. Kelime siniri
#: KULLANILMAZ -- Turkce sondan eklemelidir ve `keyword_present` bu kadar kisa
#: bir kokte "pdfyi", "pdfleri" gibi cekimleri kesiyordu (A-07). Ozellikle
#: kesme isareti uretmeyen ses dokumleri bu yuzden kaciyordu.
_PDF_KOKU = re.compile(r"\bpdf")

#: Genel belge adlari. Bunlar TEK BASLARINA istek degildir: "belge ne demek?"
#: bir sozluk sorusu, "belgesel" bambaska bir kelime (A-07).
_BELGE_ADLARI: tuple[str, ...] = ("dokuman", "makale", "belge")

#: Fiiller yine tek baslarina hicbir sey tetiklemez -- B07 tam bu yuzden
#: vardi. Yalnizca yukaridaki genel bir belge adini NITELERLER: "belgeyi oku"
#: bir istek, "belge ne demek" degil.
_BELGE_FIILLERI: tuple[str, ...] = (
    "oku", "incele", "analiz", "ozetle", "yukle", "goster", "tara",
)


def _pdf_istegi_mi(message: str) -> bool:
    """Kullanici ACIKCA bir belge istedi mi?

    Uc gecerli isaret var, giderek daha temkinli:
    belge uzantisi > "pdf" koku > genel belge adi + belge fiili.

    `_fold_tr` + `keyword_present` kullanir, duz `.lower()` DEGIL: Turkce'de
    `"İ".lower()` birlesik noktali bir karakter uretir ve "incele" ile
    eslesmez (CLAUDE.md 6). Eski dal duz `.lower()` kullandigi icin buyuk
    harfli girdilerde sessizce farkli davraniyordu.
    """
    if not message:
        return False
    if _BELGE_UZANTISI.search(message):
        return True
    fold = _fold_tr(message)
    if _PDF_KOKU.search(fold):
        return True
    if any(keyword_present(fold, ad) for ad in _BELGE_ADLARI):
        return any(keyword_present(fold, fiil) for fiil in _BELGE_FIILLERI)
    return False


def _is_greeting(message: str) -> bool:
    """Mesaj bir selamlama/nezaket ifadesi mi?

    Uzunluk siniri kasitli: kisa bir tur selamlamadir, uzun bir tur icinde
    selamlama GECER ama kendisi selamlama degildir.
    """
    metin = (message or "").strip()
    if not metin or len(metin) > _SELAM_MAX_UZUNLUK:
        return False
    fold = _fold_tr(metin)
    return any(keyword_present(fold, s) for s in _SELAMLAR)

TOOL_TRIGGERS = {
    "web_search": [
        # "öğren" BİLEREK çıkarıldı: 5 harflik bir fiil kökü ve "öğrenme
        # algoritması", "öğrencilerim" gibi masum cümlelerde eşleşiyordu.
        # Hiçbir sınır kuralı bunu ayıramaz — "öğrenme" morfolojik olarak
        # "hissesinde" ile aynı yapıda (kök + Türkçe ek), ve "hisse" kökünün
        # ek almış hâlinde eşleşmesini İSTİYORUZ. Ayrım kelime listesinde.
        "araştır", "haber", "güncel", "son dakika",
        "search", "latest", "news", "find out", "look up",
        "ne oldu", "durum nedir", "bilgi ver",
    ],
    "deep_research": [
        "derinlemesine araştır", "kapsamlı araştır", "detaylı araştır",
        "hakkında her şey", "tam araştırma",
    ],
    "calculate": [
        "hesapla", "calculate", "sqrt(", "sin(", "cos(", "log(",
        "kaç eder", "kaçtır",
    ],
    "get_datetime": [
        "saat kaç", "tarih nedir", "bugün ne", "hangi gün",
        "şu an saat", "günün tarihi",
    ],
    "get_notes": [
        "notlarım", "notları göster", "notlarımı", "kayıtlarım",
    ],
    "save_note": [
        "not et:", "not al:", "şunu kaydet:", "bunu hatırla:",
        "hatırlat:", "not olarak kaydet",
    ],
}

#: Arama sorgusundan cikarilan KOMUT kaliplari -- aranacak KONU degil (K1).
#:
#: "haber" ve "ne oldu" bu listeden CIKARILDI. Ikisi de kullanicinin
#: aradigi seyin kendisi; komut degil. Olculdu 2026-09-08:
#:
#:     "son haberler nedir"   -> "son ler nedir"
#:     "deprem haberi var mi" -> "deprem i var mi"
#:
#: "haber" koku "haberler"in ORTASINDAN kesiliyor ve arama saglayicisina
#: anlamsiz bir dize gidiyordu. TOOL_TRIGGERS'ta bulunmak bir kelimeyi
#: TETIKLEYICI yapar, kirpilacak yapmaz; iki liste birbirine karismisti.
#:
#: [ACIK KUSUR -- K1b] Kalan kaliplar hala ham `str.replace` ile siliniyor,
#: yani kelime ortasindan kesebiliyorlar ("para araci" -> "paraci").
#: Kelime sinirina gecmek `tests/test_egress_policy_local_path.py`
#: icindeki A-04 sozlesme testinin on kosulunu ortadan kaldiriyor
#: (CLAUDE.md 13.1: bu bir sozlesme degisikligidir, sorulur).
#: Bkz. `automation/IMZASIZ_IS_KUYRUGU.md` K1b.
_WEB_KOMUT_KALIPLARI: tuple[str, ...] = (
    "araştır", "ara ", "güncel bilgi ver", "öğren",
)

# ─── Yerel ajana özgü ek yönergeler ─────────────────────
# Kimlik, sadakat, kişilik, üslup ve uydurma yasağı `agents/persona.py`'den
# gelir (SSOT). Burada YALNIZ bu ajana özgü olan kalır: araç çıktısı kuralları
# ve proje durumu için zemin kuralı.
#
# Proje durumunun KENDİSİ burada yazmaz. Sabit yazılan durum eskir ve model
# eskimiş durumu güvenle tekrar eder — canlı testte tam bu oldu. Olgular
# yalnız `_load_project_context()` üzerinden, canlı dosyalardan gelir.
LOCAL_AGENT_ADDENDUM = """## ARAÇ ÇIKTISI
- Araç adlarını, sistem mesajlarını veya teknik ayrıntıları yanıtta gösterme.
- Araçtan gelen bilgiyi özümse, kendi cümlelerinle anlat.
- Kaynak bağlantısını yalnız gerektiğinde ve kısaca ver.

## PROJE DURUMU
- Proje durumu, commit geçmişi ve canlı sistem hakkında kendiliğinden bilgin
  YOKTUR. Aşağıda "GUNCEL PROJE DURUMU" bloğu verilmişse yalnız oradakini söyle.
- Blok verilmemişse "anlık proje durumuna erişimim yok" de; tahmin yürütme.
- Bir konu blokta geçmiyorsa onun hakkında çıkarım yapma — bilmiyorsun.
- Tarih ve saat için get_datetime aracını kullan; uydurma.

## TÜRKÇE YAZIM
- Yalnız Türkçe konuş. "okay", "voila", "peut-être" gibi yabancı kelimeler yasak.
- Yazım hatası yapma; emin değilsen daha basit kelimeyi seç.
- "Hoş bulduk" konuğun sözüdür, ev sahibinin değil — sen kullanırsan yanlış olur.
"""


def _clean_response(text: str) -> str:
    """Yanıttan teknik/sistem kalıntılarını temizle."""
    noise_patterns = [
        r'\[Araç:.*?\]',
        r'\[Aşağıdaki.*?\]',
        r'\[.*?sonucu\]',
        r'Yukarıdaki bilgilere dayanarak.*?yanıt ver[.\s]*',
        r'kullanıcıya doğal.*?yanıt ver[.\s]*',
        r'\[.*?güncel bilgileri.*?\]',
        r'Polimer endüstrisindeki son gelişmeleri araştır\s*',
    ]
    for p in noise_patterns:
        text = re.sub(p, '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class LocalJarvisAgent:

    def __init__(self):
        self.history: list[dict] = []
        self.turn_count = 0
        self.tool_calls_total = 0
        self.ollama_available = False
        self.available_models: list[str] = []
        self._ollama = None
        self._registry = ModelRegistry()
        # Baglam ve parmak izi birlikte kurulur; sonraki turlarda
        # `_proje_ctx_guncel()` yalniz kaynak degistiyse yeniden okur (B06).
        self._project_ctx = ""
        self._project_ctx_imza = None
        self._proje_ctx_guncel()
        self.memory = self._load_memory()
        self._tools = self._load_tools()
        self._init_ollama()
        # Hafıza sistemi
        from memory.memory_manager import JarvisMemory
        self.memory = JarvisMemory()

    def _load_tools(self) -> dict:
        try:
            # `run_python_code` BILEREK yuklenmiyor. `tools/tools.py:482`
            # icinde `exec()` var ve SkillSpector bunu HIGH isaretledi; ama
            # asil sorun erisilebilirlik degil, ERISILEMEZLIK: `_detect_tool()`
            # yalnizca TOOL_TRIGGERS'ta karsiligi olan araclara yol aciyor,
            # bu arac hicbirine bagli degil. Yani yuklu olmasi deger uretmeden
            # risk tasiyordu. `tools/tools.py` DEGISTIRILMEDI (CLAUDE.md 3).
            from tools.tools import (
                web_search, deep_research, calculate, get_datetime,
                get_notes, save_note, analyze_file,
            )
            tools = {
                "web_search":      web_search,
                "deep_research":   deep_research,
                "calculate":       calculate,
                "get_datetime":    get_datetime,
                "get_notes":       get_notes,
                "save_note":       save_note,
                "analyze_file":    analyze_file,
            }
            console.print(f"[green]✓ Araçlar yüklendi ({len(tools)} araç)[/]")
            return tools
        except Exception as e:
            console.print(f"[yellow]⚠ Araç hatası: {e}[/]")
            return {}

    def _proje_ctx_imzasi(self, root: Path) -> tuple:
        """Proje durumunun kaynaklarindan ucuz bir parmak izi (B06 / A-06).

        Neredeyse yalniz `stat()` yapar -- alt surec yok. Tek istisna `.git`
        isaretcisi, `commondir` ve `HEAD`: uculu de birkac onlarca baytlik
        metin dosyasidir ve nereye bakilacagini soylerler.

        Izlenen kumenin `_load_project_context`'in OKUDUGU kumeyle ayni
        olmasi zorunludur; okunup izlenmeyen bir kaynak sessizce bayatlar.

        Git tarafi A-06'da duzeltildi. Eskiden yalniz `HEAD` izleniyordu ama
        `HEAD` sembolik bir referanstir (`ref: refs/heads/<dal>`): commit
        atildiginda ne icerigi ne mtime'i degisir -- degisen `refs/heads/...`
        dosyasidir. Refler paketlenmisse degisen `packed-refs` olur. Bagli
        bir worktree'de her ikisi de ORTAK dizinde durur, worktree'nin kendi
        gitdir'inde degil.
        """
        import os

        hedefler: list[Path] = [
            root / "roadmap_state.json",
            root / "automation" / "HUMAN_NEEDED.md",
            root / "automation" / "T1_S2_FAIL_LOG.md",
        ]

        git = root / ".git"
        try:
            if git.is_file():
                icerik = git.read_text(encoding="utf-8").strip()
                if icerik.startswith("gitdir:"):
                    ham = Path(icerik.split(":", 1)[1].strip())
                    # Goreli isaretci CALISMA dizinine gore degil, depo
                    # KOKUNE gore cozulur; baska bir worktree'de kirilirdi.
                    git = ham if ham.is_absolute() else root / ham

            ortak = git
            commondir = git / "commondir"
            if commondir.is_file():
                ham = Path(commondir.read_text(encoding="utf-8").strip())
                ortak = ham if ham.is_absolute() else git / ham

            hedefler.append(git / "HEAD")
            hedefler.append(ortak / "packed-refs")

            head = (git / "HEAD").read_text(encoding="utf-8").strip()
            if head.startswith("ref:"):
                ref = head.split(":", 1)[1].strip()
                # Ref ya worktree'ye ozel ya ortak dizindedir; ikisi de
                # izlenir, olmayani zaten (yol, None, None) olarak gecer.
                hedefler.append(git / ref)
                hedefler.append(ortak / ref)
        except Exception:
            pass

        imza: list = []
        for p in hedefler:
            try:
                st = p.stat()
                imza.append((str(p), st.st_mtime_ns, st.st_size))
            except OSError:
                imza.append((str(p), None, None))

        # Dosya degil ama baglami degistiriyor: yukleyici bu bayragi okuyup
        # "Calisma Modu" bolumunu ona gore yaziyor.
        imza.append(
            ("env:JARVIS_PROACTIVE_ENABLED",
             os.getenv("JARVIS_PROACTIVE_ENABLED"), None)
        )
        return tuple(imza)

    def _proje_ctx_guncel(self, root: Path | None = None) -> str:
        """Proje durumunu dondurur; kaynaklar degistiyse YENIDEN okur (B06).

        Eskiden baglam yalniz `__init__`'te bir kez kuruluyordu. Ajan acikken
        commit atilirsa JARVIS eski dunyayi anlatmaya devam ediyordu --
        PUSULA'nin dogrudan ihlali ("repo'nun o anki gercek durumu; uydurma
        degil, canli").

        Tazeleme zamanlayiciyla degil PARMAK IZIYLE yapilir: TTL beklemek
        "canli" degildir, her tur diski taramak da bedava degil.
        """
        kok = Path(root) if root is not None else Path(__file__).parent.parent
        try:
            imza = self._proje_ctx_imzasi(kok)
        except Exception:
            imza = None

        if imza is None or imza != getattr(self, "_project_ctx_imza", None):
            try:
                self._project_ctx = self._load_project_context(kok)
            except Exception:
                # Fail-safe korunur: durum okunamazsa uydurma yerine bos.
                self._project_ctx = ""
            self._project_ctx_imza = imza

        return self._project_ctx or ""

    def _load_project_context(self, root: Path | None = None) -> str:
        """Modele verilecek **canlı** proje durumu bloğunu kurar.

        Olgular burada YAZILMAZ, okunur. Durum daha önce koda sabit
        yazılmıştı ve üç satırı eskimişti (E1-S4 "BEKLIYOR" iken
        `roadmap_state.json`'da DONE); model bu tabloyu her turda görüp
        "tasarım aşamasındayız" diyordu. Kaynak artık `roadmap_state.json` —
        dosya kendini "TEK DOĞRULUK KAYNAGI" ilan ediyor.

        Fail-safe korunur: bir kaynak okunamazsa o bölüm **atlanır**;
        uydurma durum yerine hiç durum yeğdir.

        ``root`` yalnız test içindir; üretimde depo kökü kullanılır.
        """
        root = Path(root) if root is not None else Path(__file__).parent.parent
        lines: list[str] = ["## GUNCEL PROJE DURUMU"]

        # 1. Git log (safe read-only subprocess)
        try:
            import subprocess
            result = subprocess.run(
                ["git", "log", "-5", "--oneline"],
                capture_output=True, text=True, timeout=5,
                cwd=str(root),
            )
            if result.returncode == 0 and result.stdout.strip():
                lines.append("\n### Son Commitler")
                for log_line in result.stdout.strip().splitlines():
                    lines.append(f"  {log_line}")
        except Exception:
            pass

        # 2. Human-needed pending items
        human_path = root / "automation" / "HUMAN_NEEDED.md"
        try:
            human_text = human_path.read_text(encoding="utf-8")
            # Sablon yer tutucusu ("- [ ] [YYYY-MM-DD] [TASK-ID] ...") gercek
            # bir bekleyen is DEGILDIR; modele oyle sunulursa uydurma bir
            # gorev olarak konusur. Dosyadaki ornek satir elenir.
            pending = [
                ln.strip() for ln in human_text.splitlines()
                if ln.strip().startswith("- [ ]")
                and "YYYY-MM-DD" not in ln and "TASK-ID" not in ln
            ]
            if pending:
                lines.append("\n### Insan Onayi Gereken Isler (HUMAN_NEEDED)")
                lines.extend(f"  {p}" for p in pending)
        except Exception:
            pass

        # 3. Yol haritasi durumu — TEK DOGRULUK KAYNAGI: roadmap_state.json.
        #    Sabit metin yok; dosya degisince blok degisir.
        try:
            import json as _json
            veri = _json.loads(
                (root / "roadmap_state.json").read_text(encoding="utf-8")
            )
            adimlar = veri.get("steps") or []
            if adimlar:
                biten = sum(1 for a in adimlar if a.get("status") == "done")
                lines.append("\n### Yol Haritasi Durumu")
                lines.append(f"  Tamamlanan adim: {biten}/{len(adimlar)}")
                for adim in adimlar:
                    if adim.get("status") == "done":
                        continue
                    lines.append(
                        f"  - {adim.get('id')} [{adim.get('status')}] "
                        f"{adim.get('title', '')}"
                    )
                    kanit = adim.get("evidence")
                    if isinstance(kanit, dict):
                        for ad, k in kanit.items():
                            if isinstance(k, dict) and k.get("verdict"):
                                tarih = k.get("date") or k.get("ts") or ""
                                lines.append(
                                    f"      {ad}: {k['verdict']}"
                                    + (f" ({tarih})" if tarih else "")
                                )
        except Exception:
            # Dosya yok/bozuk: durum bolumu ATLANIR. Uydurma durum yerine
            # hic durum yegdir.
            pass

        # 4. Ortamdan CANLI okunan durum (sabit iddia degil).
        import os as _os
        if _os.getenv("JARVIS_PROACTIVE_ENABLED", "0").strip() not in ("1", "true", "True"):
            lines.append("\n### Calisma Modu")
            lines.append("  - Proaktif bildirimler: CANLI DEGIL (JARVIS_PROACTIVE_ENABLED=0)")

        # 4. Optional: T1-S2 fail log summary if present
        fail_log = root / "automation" / "T1_S2_FAIL_LOG.md"
        try:
            fail_text = fail_log.read_text(encoding="utf-8")
            verdict_lines = [
                ln.strip() for ln in fail_text.splitlines()
                if "FAIL" in ln or "Verdict" in ln or "PASS" in ln
            ]
            if verdict_lines:
                lines.append("\n### T1-S2 Son Sonuc")
                lines.extend(f"  {v}" for v in verdict_lines[:3])
        except Exception:
            pass

        lines.append("\n### Onemli Kural")
        lines.append("  Bu blogun disindaki proje durumu, commit veya canli sistem")
        lines.append("  bilgilerini UYDURMA. Bilmiyorsan soyle.")

        return "\n".join(lines)

    def _load_memory(self):
        try:
            from agent.local_agent_memory import LocalMemory
            return LocalMemory()
        except Exception:
            return None

    def _init_ollama(self):
        try:
            import ollama as ol
            self._ollama = ol
            models_resp = ol.list()

            # ✅ FIX: Yeni ve eski Ollama versiyonu uyumlu
            self.available_models = []
            raw_models = getattr(models_resp, 'models', None)
            if raw_models is None:
                raw_models = models_resp.get('models', []) if isinstance(models_resp, dict) else []

            for m in raw_models:
                if isinstance(m, dict):
                    name = m.get('model') or m.get('name', '')
                else:
                    name = getattr(m, 'model', '') or getattr(m, 'name', '')
                if name:
                    self.available_models.append(name)

            if not self.available_models:
                console.print("[yellow]⚠ Model yok![/]")
                return
            self.ollama_available = True
            console.print(
                f"[green]✓ Ollama bağlı[/] | [cyan]{len(self.available_models)} model[/]: "
                f"{', '.join(self.available_models[:3])}"
            )
        except ImportError:
            console.print("[red]✗ pip install ollama[/]")
        except Exception as e:
            console.print(f"[red]✗ Ollama: {e}[/]")

    def _classify(self, message: str) -> str:
        """Turu siniflandirir: fast / mid / deep.

        Ayni karar hem modeli (rol uzerinden) hem persona seviyesini secer;
        boylece "kisa soru" esigi iki yerde ayri ayri tutulmaz.
        """
        # Duz .lower() KULLANILMAZ: "İ".lower() combining dot uretir ve
        # eslesme sessizce kacar (CLAUDE.md 6). Fold her iki tarafa da uygulanir.
        fold = _fold_tr(message)
        deep_kw = ("derinlemesine", "kapsamli", "analiz et", "detayli", "rapor hazirla")
        # Selamin disinda kalan kisa-tur isaretleri.
        fast_kw = ("saat kac", "gorusuruz", "tarih nedir")

        # Uzunluk once bakilir: uzun mesaj selamla baslasa bile kisa tur degil.
        if len(message) > 300 or any(keyword_present(fold, k) for k in deep_kw):
            return "deep"
        if _is_greeting(message) or any(keyword_present(fold, k) for k in fast_kw):
            return "fast"
        return "mid"

    def _model_for_tier(self, tier: str) -> str:
        """Turu aktif profildeki bir role cozer.

        Model adi burada yazili DEGILDIR (CLAUDE.md 7: "Model adi koda
        gomulmez -> ModelRegistry"). Profil degisince kod degismez.
        """
        small = self._registry.local_small()
        main = self._registry.local_main()
        adaylar = {
            "fast": [small, main],
            "mid": [main, small],
            "deep": [self._registry.research_model(), main, small],
        }.get(tier, [main, small])

        for aday in adaylar:
            for kurulu in self.available_models:
                if aday.lower().split(":")[0] in kurulu.lower():
                    return kurulu
        return self.available_models[0] if self.available_models else main

    def _detect_tool(self, message: str) -> Optional[tuple[str, dict]]:
        # Selamlama hicbir arac tetiklemez. Bu kontrol EN BASTA durur:
        # "Ne haber Jarvis?" canli testte web aramasi baslatiyordu.
        if _is_greeting(message):
            return None

        # Duz .lower() yerine fold: "İ" tuzagi (CLAUDE.md 6) ve kisa koklerde
        # kelime siniri, `keyword_present` icinde tek kaynaktan gelir.
        msg = _fold_tr(message)

        def _eslesir(grup: str) -> bool:
            return any(keyword_present(msg, t) for t in TOOL_TRIGGERS[grup])

        if _eslesir("deep_research"):
            return "deep_research", {"topic": message.strip(), "depth": 2}

        if _eslesir("get_datetime"):
            return "get_datetime", {}

        if _eslesir("get_notes"):
            return "get_notes", {"filter_by": "", "show_done": False}

        if _eslesir("save_note"):
            content = message
            for kw in ["not et:", "not al:", "kaydet:", "hatırlat:"]:
                if kw in message.lower():
                    idx = message.lower().index(kw) + len(kw)
                    content = message[idx:].strip()
                    break
            return "save_note", {"content": content, "category": "genel"}

        if _eslesir("calculate"):
            expr = message.replace("hesapla", "").replace("calculate", "").strip()
            return "calculate", {"expression": expr}

        if _eslesir("web_search"):
            query = message
            for kw in _WEB_KOMUT_KALIPLARI:
                query = query.replace(kw, "").strip()
            if len(query) < 3:
                query = message
            return "web_search", {"query": query, "max_results": 5}

        return None

    def _egress_kapisi(self, tool_name: str, args: dict,
                       original_message: str = "") -> Optional[str]:
        """Disari cikan arac icin izin karari. Engel varsa SEBEBI doner.

        Iki katman, bu sirayla:

        1. **Kullanicinin acik yasagi.** Politikadan once gelir; insan
           gecersiz kilmasi her katmandan ustundur (CLAUDE.md 7).
        2. **`WebResearchPolicy`.** Zaten var ve Telegram yolunda
           kullaniliyor; burada yeniden yazilmadi, baglandi (9,
           adopt-over-build). Izin verirse sorgu politikanin
           `sanitized_query`'siyle DEGISTIRILIR -- ham sorgu disari cikmaz.

        Engel sessiz olmaz: bos string yerine sebep doner, cunku
        `_run_tool` hata yolunda "" donduruyor ve kullanici o farki
        goremezdi.
        """
        arg_adi = _EGRESS_ARACLARI[tool_name]
        sorgu = str(args.get(arg_adi) or "")

        if _yerel_kal_istendi(original_message) or _yerel_kal_istendi(sorgu):
            return (
                "Yerel kalmami istediginiz icin disari cikmadim efendim. "
                "Bu soruyu elimdeki bilgiyle yanitlayacagim."
            )

        # Karar ORIJINAL cumle uzerinden verilir, kirpilmis sorgu uzerinden
        # degil. Olculdu (2026-09-06): `_detect_tool` "son haberler nedir"
        # cumlesinden "haber" kelimesini cikarip geriye "son ler nedir"
        # birakiyor; politika bu bozuk metne haklı olarak "guncel bilgi
        # ihtiyaci yok" diyor ve mesru bir sorgu engelleniyordu. Politikanin
        # isi niyeti yargilamak, kirpma artigini degil.
        #
        # [AYRI KUSUR, DUZELTILMEDI] Bozuk sorgu arama saglayicisina o haliyle
        # gidiyor. Bu bir kalite hatasi, guvenlik hatasi degil; B03'un kapsami
        # disinda -- gorulup soylendi, dokunulmadi (CLAUDE.md 3).
        try:
            from agents.web_research_policy import WebResearchPolicy
            karar = WebResearchPolicy().decide(original_message or sorgu)
        except Exception as exc:
            # Guard arizasi disari cikmayi ACMAZ, KAPATIR. Codex B10 tam
            # bunun tersini buldu: router redaction hatasini `except: pass`
            # ile gecip disari cikiyordu.
            return f"Web politikasi calistirilamadi, disari cikmadim: {exc}"

        if not getattr(karar, "allow", False):
            return (
                f"Bu sorguyu disari gondermedim efendim. "
                f"Neden: {getattr(karar, 'reason', 'politika reddetti')}"
            )

        # Karar orijinal cumleye bakti; ama DISARI CIKAN metin `sorgu`.
        # O yuzden `karar.sanitized_query` (orijinalin temizlenmisi) degil,
        # gercekten gidecek olan sorgu temizlenir.
        try:
            nihai = WebResearchPolicy().sanitize(sorgu)
        except Exception:
            # Temizleyici calismadiysa ham sorgu disari CIKMAZ.
            return "Sorgu temizlenemedi, disari cikmadim efendim."

        # A-04: nihai sorgunun VERI SINIFI da denetlenir. Kirpma, orijinalde
        # olmayan hassas bir diziyi URETEBILIYOR -- olculdu 2026-09-06:
        # "paara rola X son haberler" cumlesinden "ara " ve "haber" silinince
        # geriye "parola X son ler" kaliyor ve o haliyle disari cikiyordu.
        #
        # Yalnizca HASSASLIK verdicti okunur. Niyet verdicti bilerek yeniden
        # okunmaz: niyeti yargilamak orijinal cumlenin isidir (yukaridaki
        # not), kirpma artiginin degil.
        try:
            nihai_karar = WebResearchPolicy().decide(nihai)
        except Exception as exc:
            return f"Web politikasi calistirilamadi, disari cikmadim: {exc}"

        if getattr(nihai_karar, "mode", "") == \
                WebResearchPolicy.MODE_SENSITIVE_BLOCKED:
            return (
                "Sorgu kirpildiktan sonra hassas veri iceriyor; disari "
                "gondermedim efendim. Neden: "
                f"{getattr(nihai_karar, 'reason', 'hassas veri')}"
            )

        args[arg_adi] = nihai
        return None

    def _run_tool(self, tool_name: str, args: dict,
                  original_message: str = "") -> str:
        fn = self._tools.get(tool_name)
        if not fn:
            return ""

        # Egress kapisi -- arac CALISMADAN once.
        if tool_name in _EGRESS_ARACLARI:
            engel = self._egress_kapisi(tool_name, args, original_message)
            if engel:
                return engel

        try:
            console.print(f"[dim]🔧 {tool_name}...[/]")
            result = str(fn(**args))
            self.tool_calls_total += 1
            if len(result) > 3500:
                result = result[:3500]
            return result
        except Exception:
            return ""

    def _ask_ollama(self, messages: list[dict], model: str) -> str:
        try:
            response = self._ollama.chat(
                model=model,
                messages=messages,
                stream=False,
                options={
                    "temperature": 0.72,
                    "num_ctx": 4096,
                    "num_predict": 1024,
                    "stop": ["[Araç", "[System", "USER:", "JARVIS:"],
                }
            )
            return response.message.content
        except Exception as e:
            return f"Model hatası: {e}"

    def chat(self, user_message: str) -> str:
        if not self.ollama_available:
            return "⚠️ Ollama bağlı değil."
        # PDF/döküman algılama — yalnız AÇIK belge isteğinde (B07).
        # Eskiden "analiz", "bak", "oku" gibi fiiller de tetikliyordu ve
        # "Bu kodun mantığını analiz et" sorusu rastgele bir PDF açıyordu.
        if _pdf_istegi_mi(user_message):
            from tools.tools import find_and_load_pdf
            from rag.rag_engine import JarvisRAG
            yukle = find_and_load_pdf()
            rag = JarvisRAG()
            # PDF'i RAG'a yükle (kritik!)
            rag.add_documents()
            # Soruyu sor
            cevap = rag.query_with_ollama(user_message)
            return f"{yukle}\n\n{cevap}"
        self.turn_count += 1
        tier = self._classify(user_message)
        model = self._model_for_tier(tier)
        console.print(f"[dim]→ {model.split(':')[0]} | Tur {self.turn_count}[/]")

        # Araç çalıştır
        tool_data = ""
        tool_detection = self._detect_tool(user_message)
        if tool_detection:
            tool_name, tool_args = tool_detection
            console.print(f"[cyan]🔧 {tool_name}[/]")
            tool_data = self._run_tool(tool_name, tool_args, user_message)

        # System prompt: kimlik/sadakat/kisilik/uslup/zemin SSOT'tan gelir.
        system = build_system_prompt(level=_TIER_TO_LEVEL[tier])
        system += "\n\n" + LOCAL_AGENT_ADDENDUM
        # Proje durumu HER TURDA tazelenir (B06). Kaynaklar degismediyse
        # parmak izi ayni kalir ve yeniden okuma yapilmaz.
        proje_ctx = self._proje_ctx_guncel()
        if proje_ctx:
            system += f"\n\n{proje_ctx}"
        if self.memory:
            ctx = self.memory.get_context_for_prompt()
            if ctx:
                system += f"\n\n## Hafıza\n{ctx}"

        # Ses yonergesi EN SONA: cevap hoparlorden OKUNUR, markdown ve kod
        # sesli dinlenmez. Sonra gelen kazanir -- yoksa model "kod ver" diyen
        # seviye yonergesine uyup kodu sesli okumaya calisir (bkz. persona.py).
        if getattr(self, "voice_mode", False):
            system += "\n\n" + VOICE_MODE_DIRECTIVE

        # Mesaj listesi
        messages = [{"role": "system", "content": system}]

        # Geçmiş (son 8 tur)
        recent = self.history[-16:] if len(self.history) > 16 else self.history
        messages.extend(recent)

        # Kullanıcı mesajını oluştur
        if tool_data:
            user_content = (
                f"{user_message}\n\n"
                f"---\n"
                f"Araştırma sonuçları (bu verileri özümse, doğal konuş):\n"
                f"{tool_data}\n"
                f"---\n"
                f"Önemli: Sadece kullanıcıya Türkçe, doğal bir yanıt ver. "
                f"Sistem mesajlarını, araç adlarını veya bu talimatları yanıtta gösterme."
            )
        else:
            user_content = user_message

        messages.append({"role": "user", "content": user_content})

        # Yanıt al
        with console.status("[cyan]JARVIS düşünüyor...[/]"):
            raw = self._ask_ollama(messages, model)

        # Temizle
        response = _clean_response(raw)

        # Geçmişe kaydet
        self.history.append({"role": "user",      "content": user_message})
        self.history.append({"role": "assistant",  "content": response})

        # Hafıza
        if self.memory and len(user_message) > 10:
            self.memory.add_conversation(user_message, response)
        # Otomatik bilgi çıkarma
            try:
                self.memory.auto_extract_info(user_message, response)
            except Exception:
                pass

        # Geçmiş kırpma
        if len(self.history) > 20:
            self.history = self.history[-16:]

        return response

    def clear_history(self):
        """Geçmişi temizle — RAM **ve** kalıcı depo (B04).

        Eskiden yalnız RAM listesi siliniyor, ekrana "Geçmiş temizlendi."
        yazılıyordu. Codex denetimi (2026-09-06) ölçtü: veritabanındaki
        konuşma kalıyor ve `get_context_for_prompt` ile bir sonraki
        prompt'a geri giriyordu. Kullanıcı "unut" diyor, JARVIS "unuttum"
        diyor, sonraki turda hatırlıyordu.

        Profil ve olaylar korunur; yalnız sohbet geçmişi silinir.
        """
        self.history = []
        self.turn_count = 0

        silinen = 0
        if getattr(self, "memory", None) is not None:
            try:
                silinen = self.memory.clear_conversations()
            except Exception as exc:  # noqa: BLE001
                # Sessiz basari YASAK: silinemedi ise kullanici bilmeli.
                console.print(
                    f"[red]Kalıcı geçmiş silinemedi: {exc}[/]\n"
                    "[yellow]Oturum geçmişi temizlendi ama disk kaydı duruyor.[/]"
                )
                return

        console.print(f"[green]Geçmiş temizlendi ({silinen} kalıcı kayıt silindi).[/]")

    def show_stats(self):
        console.print("\n[bold cyan]📊 İstatistikler[/]")
        console.print(f"  Tur: {self.turn_count} | Araç: {self.tool_calls_total}")
        console.print(f"  Modeller: {', '.join(self.available_models[:3])}")
        console.print("  Maliyet: [green]0₺[/]\n")

    def list_models(self):
        for m in self.available_models:
            console.print(f"  • {m}")
