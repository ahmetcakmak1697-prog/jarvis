import os
import json
import sqlite3
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _exists(path: str) -> bool:
    return (PROJECT_ROOT / path).exists()


def _json_count(path: str) -> int:
    p = PROJECT_ROOT / path
    if not p.exists():
        return 0

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            return len(data)
    except Exception:
        return 0

    return 0


def _db_chat_count() -> int:
    db_path = PROJECT_ROOT / "memory" / "jarvis_memory.db"

    if not db_path.exists():
        return 0

    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM chats")
        count = cur.fetchone()[0]
        con.close()
        return count
    except Exception:
        return 0


def _search_credit_status() -> str:
    p = PROJECT_ROOT / "memory" / "search_credits.json"

    if not p.exists():
        return "Kredi dosyası yok"

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        remaining = data.get("remaining", "?")
        reset_date = data.get("reset_date", "?")
        return f"{remaining}/1000 | yenilenme: {reset_date}"
    except Exception:
        return "Kredi dosyası okunamadı"


def run_diagnostics() -> str:
    """
    Jarvis çekirdek sağlık kontrolü.
    """
    checks = []

    checks.append(("jarvis_brain.py", _exists("jarvis_brain.py")))
    checks.append(("tools/file_tools.py", _exists("tools/file_tools.py")))
    checks.append(("tools/web_research.py", _exists("tools/web_research.py")))
    checks.append(("test_jarvis_tools.py", _exists("test_jarvis_tools.py")))
    checks.append(("memory klasörü", _exists("memory")))

    tavily_active = bool(os.getenv("TAVILY_API_KEY"))
    tavily_status = "aktif" if tavily_active else "pasif"

    profile_count = _json_count("memory/user_profile.json")
    conversation_count = _json_count("memory/conversations.json")
    chat_count = _db_chat_count()
    credit_status = _search_credit_status()

    lines = []
    lines.append("JARVIS SAĞLIK KONTROLÜ")
    lines.append("=" * 40)

    lines.append("\nÇekirdek dosyalar:")
    for name, ok in checks:
        icon = "OK" if ok else "EKSİK"
        lines.append(f"- {name}: {icon}")

    lines.append("\nWeb araştırma:")
    lines.append(f"- Tavily: {tavily_status}")
    lines.append(f"- Arama kredisi: {credit_status}")

    lines.append("\nHafıza:")
    lines.append(f"- Profil kayıt sayısı: {profile_count}")
    lines.append(f"- Conversation kayıt sayısı: {conversation_count}")
    lines.append(f"- SQLite chat kayıt sayısı: {chat_count}")

    lines.append("\nDurum:")
    if all(ok for _, ok in checks):
        lines.append("Genel durum: İYİ")
    else:
        lines.append("Genel durum: DİKKAT GEREKİYOR")

    return "\n".join(lines)
def run_self_tests() -> str:
    """
    Jarvis çekirdek fonksiyonlarını hızlı test eder.
    Ağır web araması yapmaz; sadece temel modüllerin çalışabilirliğini kontrol eder.
    """
    results = []

    def ok(name):
        results.append((name, True, ""))

    def fail(name, err):
        results.append((name, False, str(err)[:160]))

    # 1. Dosya araçları
    try:
        from tools.file_tools import list_project_files, search_text_in_project, count_regex_in_file

        files = list_project_files()
        if "jarvis_brain.py" in files:
            ok("Dosya listeleme")
        else:
            fail("Dosya listeleme", "jarvis_brain.py listede bulunamadı")

        search = search_text_in_project("research_and_learn")
        if "web_research.py" in search or "jarvis_brain.py" in search:
            ok("Proje içinde arama")
        else:
            fail("Proje içinde arama", "research_and_learn bulunamadı")

        count = count_regex_in_file("jarvis_brain.py", r"\bdef\b")
        if "toplam" in count:
            ok("Kod sayma")
        else:
            fail("Kod sayma", count)

    except Exception as e:
        fail("Dosya araçları", e)

    # 2. WebResearcher temel durum
    try:
        from tools.web_research import WebResearcher

        w = WebResearcher()
        if w:
            ok("WebResearcher başlatma")
        else:
            fail("WebResearcher başlatma", "nesne oluşmadı")

        if w.tavily:
            ok("Tavily aktif")
        else:
            fail("Tavily aktif", "TAVILY_API_KEY yok veya tavily paketi pasif")

    except Exception as e:
        fail("WebResearcher", e)

    # 3. Diagnostics
    try:
        diag = run_diagnostics()
        if "JARVIS SAĞLIK KONTROLÜ" in diag:
            ok("Diagnostics")
        else:
            fail("Diagnostics", "beklenen başlık yok")
    except Exception as e:
        fail("Diagnostics", e)

    # Rapor
    lines = []
    lines.append("JARVIS SELF-TEST")
    lines.append("=" * 40)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, err in results:
        icon = "OK" if success else "HATA"
        if success:
            lines.append(f"- {name}: {icon}")
        else:
            lines.append(f"- {name}: {icon} | {err}")

    lines.append("")
    lines.append(f"Sonuç: {passed}/{total} test başarılı")

    if passed == total:
        lines.append("Genel durum: İYİ")
    else:
        lines.append("Genel durum: DİKKAT GEREKİYOR")

    return "\n".join(lines)