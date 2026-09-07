"""
jarvis/tools/tools.py — v2 (KAPSAMLI GÜNCELLEME)
─────────────────────────────────────────────────────────
YENİ ARAÇLAR:
  🌐 web_search        — DuckDuckGo ile internet araması
  🌐 fetch_webpage     — Sayfadan içerik çekme
  🔬 deep_research     — Çok adımlı derin araştırma
  📁 analyze_file      — PDF / Excel / CSV / TXT analizi
  🐍 run_python_code   — Güvenli Python çalıştırma
  🧮 calculate         — Matematiksel hesap
  📅 get_datetime      — Tarih/saat bilgisi
  📝 save_note         — Not / görev kaydet
  📋 get_notes         — Notları listele / ara
  🗑️  delete_note       — Not sil
"""
from __future__ import annotations

import ast
import io
import json
import math
import operator
import os
import subprocess
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from config import PROJECT_PATH, AUTO_RUN_COMMANDS
from rich.console import Console
from rich.prompt import Confirm

console = Console()

# ─── Notlar için kalıcı depo ────────────────────────────
NOTES_FILE = Path(__file__).parent.parent / "data" / "notes.json"


def _load_notes() -> list[dict]:
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if NOTES_FILE.exists():
        return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    return []


def _save_notes(notes: list[dict]):
    NOTES_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── Yardımcı ───────────────────────────────────────────
def _run(cmd: str, cwd: Path = PROJECT_PATH, timeout: int = 30) -> dict:
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace"
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Zaman aşımı ({timeout}s)", "returncode": -1, "success": False}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "success": False}


def _confirm_command(cmd: str) -> bool:
    if AUTO_RUN_COMMANDS:
        return True
    return Confirm.ask(f"[yellow]Komut çalıştırılsın mı?[/] [cyan]{cmd}[/]")


# ════════════════════════════════════════════════════════
#  MEVCUT ARAÇLAR (iyileştirildi)
# ════════════════════════════════════════════════════════

def run_terminal_command(command: str) -> str:
    """Terminal komutu çalıştırır."""
    if not _confirm_command(command):
        return "Kullanıcı komutu iptal etti."
    result = _run(command)
    if result["success"]:
        return result["stdout"] or "(Komut başarıyla çalıştı, çıktı yok)"
    return f"HATA (kod {result['returncode']}):\n{result['stderr']}"


def read_file(file_path: str) -> str:
    """Dosya içeriğini okur."""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_PATH / path
    try:
        content = path.read_text(errors="ignore", encoding="utf-8")
        if len(content) > 10_000:
            return content[:10_000] + f"\n\n... (kesildi, toplam {len(content):,} karakter)"
        return content
    except FileNotFoundError:
        return f"Dosya bulunamadı: {path}"
    except Exception as e:
        return f"Hata: {e}"


def write_file(file_path: str, content: str) -> str:
    """Dosyaya içerik yazar."""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_PATH / path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"✓ Dosya yazıldı: {path} ({len(content):,} karakter)"
    except Exception as e:
        return f"Hata: {e}"


def list_directory(dir_path: str = ".") -> str:
    """Klasör içeriğini listeler."""
    path = Path(dir_path)
    if not path.is_absolute():
        path = PROJECT_PATH / path
    try:
        items = []
        for item in sorted(path.iterdir()):
            if item.name.startswith("."):
                continue
            icon = "📁" if item.is_dir() else "📄"
            size = f" ({item.stat().st_size:,} B)" if item.is_file() else ""
            items.append(f"{icon} {item.name}{size}")
        return "\n".join(items) if items else "(boş klasör)"
    except Exception as e:
        return f"Hata: {e}"


def search_in_files(query: str, file_pattern: str = "*.py") -> str:
    """Proje dosyalarında metin arar."""
    result = _run(f'grep -r --include="{file_pattern}" -n "{query}" .', cwd=PROJECT_PATH)
    if result["stdout"]:
        lines = result["stdout"].splitlines()[:50]
        return "\n".join(lines)
    return f"'{query}' için sonuç bulunamadı ({file_pattern})"


def git_status() -> str:
    status = _run("git status --short")
    log = _run("git log --oneline -10")
    branch = _run("git branch --show-current")
    return (
        f"Branch: {branch['stdout']}\n\n"
        f"Değişiklikler:\n{status['stdout'] or '(temiz)'}\n\n"
        f"Son 10 commit:\n{log['stdout']}"
    )


def git_diff(file_path: str = "") -> str:
    cmd = f"git diff {file_path}" if file_path else "git diff"
    result = _run(cmd)
    if not result["stdout"]:
        return "Bekleyen değişiklik yok."
    return "\n".join(result["stdout"].splitlines()[:100])


def get_project_structure(max_depth: int = 3) -> str:
    result = _run(
        f"find . -maxdepth {max_depth} -not -path '*/.*' "
        "-not -path '*/node_modules/*' -not -path '*/__pycache__/*' "
        "| sort | head -80"
    )
    return result["stdout"] or "Yapı alınamadı."


# ════════════════════════════════════════════════════════
#  YENİ ARAÇ 1: WEB ARAMA
# ════════════════════════════════════════════════════════

def web_search(query: str, max_results: int = 5) -> str:
    """
    DuckDuckGo ile internet araması yapar.
    duckduckgo_search paketi gerekli: pip install duckduckgo-search
    """
    try:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"**{r.get('title', 'Başlıksız')}**\n"
                    f"URL: {r.get('href', '')}\n"
                    f"Özet: {r.get('body', '')[:300]}\n"
                )
        if not results:
            return f"'{query}' için sonuç bulunamadı."
        return f"## '{query}' Arama Sonuçları\n\n" + "\n---\n".join(results)
    except ImportError:
        return "❌ duckduckgo-search kurulu değil. Terminalde çalıştır:\npip install duckduckgo-search"
    except Exception as e:
        return f"Arama hatası: {e}"


# ════════════════════════════════════════════════════════
#  YENİ ARAÇ 2: SAYFA İÇERİĞİ ÇEKME
# ════════════════════════════════════════════════════════

def fetch_webpage(url: str, max_chars: int = 5000) -> str:
    """
    Bir web sayfasının metin içeriğini çeker.
    requests + beautifulsoup4 gerekli.
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Gereksiz elementleri kaldır
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if len(l.strip()) > 20]
        clean = "\n".join(lines)

        if len(clean) > max_chars:
            clean = clean[:max_chars] + f"\n\n... (kesildi, toplam {len(clean):,} karakter)"

        return f"## {url}\n\n{clean}"

    except ImportError:
        return "❌ Gerekli paketler eksik. Çalıştır:\npip install requests beautifulsoup4"
    except Exception as e:
        return f"Sayfa çekme hatası: {e}"


# ════════════════════════════════════════════════════════
#  YENİ ARAÇ 3: DERİN ARAŞTIRMA
# ════════════════════════════════════════════════════════

def deep_research(topic: str, depth: int = 3) -> str:
    """
    Bir konu hakkında çok adımlı derin araştırma yapar:
    1. Arama yap
    2. En iyi sonuçları getir
    3. Özet oluştur
    depth=1 hızlı, depth=3 kapsamlı
    """
    try:
        from duckduckgo_search import DDGS
        import requests
        from bs4 import BeautifulSoup

        output = [f"# '{topic}' Hakkında Derin Araştırma\n"]

        # Farklı açılardan ara
        search_queries = [topic]
        if depth >= 2:
            search_queries.append(f"{topic} nasıl çalışır")
            search_queries.append(f"{topic} avantajları dezavantajları")
        if depth >= 3:
            search_queries.append(f"{topic} son gelişmeler 2024 2025")
            search_queries.append(f"{topic} uzman görüşleri")

        all_results = []
        seen_urls = set()

        with DDGS() as ddgs:
            for q in search_queries[:depth + 1]:
                for r in ddgs.text(q, max_results=3):
                    url = r.get("href", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)

        output.append(f"**{len(all_results)} kaynak bulundu**\n")

        # İlk 3 kaynağın içeriğini çek
        detailed_sources = []
        headers = {"User-Agent": "Mozilla/5.0"}

        for r in all_results[:3]:
            url = r.get("href", "")
            title = r.get("title", "")
            snippet = r.get("body", "")

            try:
                resp = requests.get(url, headers=headers, timeout=8, verify=False)
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                text = soup.get_text(separator=" ", strip=True)
                text = " ".join(text.split())[:2000]
                detailed_sources.append(f"### {title}\nURL: {url}\n{text}\n")
            except Exception:
                detailed_sources.append(f"### {title}\nURL: {url}\nÖzet: {snippet}\n")

        output.extend(detailed_sources)

        # Kalan sonuçları özet olarak ekle
        if len(all_results) > 3:
            output.append("\n## Diğer Kaynaklar\n")
            for r in all_results[3:]:
                output.append(f"- [{r.get('title','')}]({r.get('href','')})\n  {r.get('body','')[:150]}\n")

        return "\n".join(output)

    except ImportError:
        return "❌ duckduckgo-search ve requests gerekli:\npip install duckduckgo-search requests beautifulsoup4"
    except Exception as e:
        return f"Araştırma hatası: {e}\n{traceback.format_exc()}"


# ════════════════════════════════════════════════════════
#  YENİ ARAÇ 4: DOSYA ANALİZİ (PDF / EXCEL / CSV)
# ════════════════════════════════════════════════════════

def analyze_file(file_path: str, analysis_type: str = "auto") -> str:
    """
    Dosya analizi yapar.
    Desteklenen formatlar: PDF, Excel (.xlsx/.xls), CSV, TXT, JSON, Python

    analysis_type: "auto" | "summary" | "full" | "stats"
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_PATH / path

    if not path.exists():
        return f"Dosya bulunamadı: {path}"

    ext = path.suffix.lower()
    size_kb = path.stat().st_size / 1024

    header = f"## Dosya Analizi: {path.name}\n"
    header += f"Boyut: {size_kb:.1f} KB | Format: {ext}\n\n"

    # ── PDF ──────────────────────────────────────────────
    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            num_pages = len(reader.pages)
            text_parts = []
            for i, page in enumerate(reader.pages[:10]):  # İlk 10 sayfa
                text_parts.append(f"[Sayfa {i+1}]\n{page.extract_text()}")
            full_text = "\n\n".join(text_parts)
            if len(full_text) > 8000:
                full_text = full_text[:8000] + f"\n...(kesildi, {num_pages} sayfa)"
            return header + f"Sayfa sayısı: {num_pages}\n\n{full_text}"
        except ImportError:
            return header + "❌ pypdf kurulu değil:\npip install pypdf"
        except Exception as e:
            return header + f"PDF okuma hatası: {e}"

    # ── EXCEL ─────────────────────────────────────────────
    elif ext in (".xlsx", ".xls", ".xlsm"):
        try:
            import pandas as pd
            xl = pd.ExcelFile(str(path))
            result = [header, f"Sayfa sayısı: {len(xl.sheet_names)}\n"]
            for sheet_name in xl.sheet_names[:5]:
                df = pd.read_excel(str(path), sheet_name=sheet_name)
                result.append(f"### Sayfa: '{sheet_name}'")
                result.append(f"Satır: {len(df):,} | Sütun: {len(df.columns)}")
                result.append(f"Sütunlar: {', '.join(str(c) for c in df.columns)}\n")
                if analysis_type in ("stats", "full"):
                    result.append("**İstatistikler:**")
                    result.append(df.describe().to_string())
                result.append("\n**İlk 5 satır:**")
                result.append(df.head().to_string())
                result.append("")
            return "\n".join(result)
        except ImportError:
            return header + "❌ pandas/openpyxl kurulu değil:\npip install pandas openpyxl"
        except Exception as e:
            return header + f"Excel okuma hatası: {e}"

    # ── CSV ──────────────────────────────────────────────
    elif ext == ".csv":
        try:
            import pandas as pd
            df = pd.read_csv(str(path), encoding="utf-8", errors="replace")
            result = [
                header,
                f"Satır: {len(df):,} | Sütun: {len(df.columns)}",
                f"Sütunlar: {', '.join(str(c) for c in df.columns)}\n",
            ]
            if analysis_type in ("stats", "full", "auto"):
                result.append("**Özet İstatistikler:**")
                result.append(df.describe(include="all").to_string())
                result.append("\n**Eksik Değerler:**")
                missing = df.isnull().sum()
                result.append(missing[missing > 0].to_string() or "Eksik değer yok")
            result.append("\n**İlk 10 satır:**")
            result.append(df.head(10).to_string())
            return "\n".join(result)
        except ImportError:
            return header + "❌ pandas kurulu değil:\npip install pandas"
        except Exception as e:
            return header + f"CSV okuma hatası: {e}"

    # ── JSON ─────────────────────────────────────────────
    elif ext == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            text = json.dumps(data, ensure_ascii=False, indent=2)
            if len(text) > 5000:
                text = text[:5000] + "\n...(kesildi)"
            return header + text
        except Exception as e:
            return header + f"JSON okuma hatası: {e}"

    # ── METİN / KOD ──────────────────────────────────────
    else:
        return header + read_file(file_path)


# ════════════════════════════════════════════════════════
#  YENİ ARAÇ 5: GÜVENLİ PYTHON ÇALIŞTIRMA
# ════════════════════════════════════════════════════════

def run_python_code(code: str, timeout: int = 15) -> str:
    """
    Python kodunu güvenli izole ortamda çalıştırır.
    Veri analizi, hesaplama, grafik için idealdir.
    """
    # Tehlikeli import'ları engelle
    dangerous = ["import os", "import sys", "import subprocess",
                 "import shutil", "__import__", "eval(", "exec(", "open("]
    for d in dangerous:
        if d in code:
            return f"❌ Güvenlik: '{d}' kullanımı engellenmiştir."

    try:
        # Stdout'u yakala
        import io
        from contextlib import redirect_stdout, redirect_stderr

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Güvenli namespace
        safe_globals = {
            "__builtins__": {
                "print": print, "len": len, "range": range,
                "str": str, "int": int, "float": float, "list": list,
                "dict": dict, "tuple": tuple, "set": set, "bool": bool,
                "sum": sum, "min": min, "max": max, "abs": abs,
                "round": round, "sorted": sorted, "enumerate": enumerate,
                "zip": zip, "map": map, "filter": filter,
            },
            "math": math,
        }

        # pandas ve numpy izin ver
        try:
            import pandas as pd
            import numpy as np
            safe_globals["pd"] = pd
            safe_globals["np"] = np
        except ImportError:
            pass

        output_lines = []

        # print'i yakala
        import builtins
        original_print = builtins.print

        def capturing_print(*args, **kwargs):
            output_lines.append(" ".join(str(a) for a in args))

        builtins.print = capturing_print
        try:
            exec(code, safe_globals)
        finally:
            builtins.print = original_print

        if output_lines:
            return "```\n" + "\n".join(output_lines) + "\n```"
        return "(Kod çalıştı, çıktı yok)"

    except Exception as e:
        return f"❌ Hata: {type(e).__name__}: {e}\n{traceback.format_exc()[:500]}"


# ════════════════════════════════════════════════════════
#  YENİ ARAÇ 6: HESAP MAKİNESİ
# ════════════════════════════════════════════════════════

#: `eval` bir sandbox'a kapatılamaz. `{"__builtins__": {}}` yalnız ADLARI
#: gizler, nesne grafiğini değil: `().__class__.__base__.__subclasses__()`
#: zincirinden `catch_warnings.__init__.__globals__` üzerinden gerçek
#: yerleşiklere dönülüyordu (B01 — çalışan istismarla doğrulandı, `sum` da
#: `open` da `os.system` de erişilebiliyordu). Kara liste denemeleri tarihsel
#: olarak hep delindi; bu yüzden ifade artık `eval` EDİLMEZ, AST'si beyaz
#: listeyle yorumlanır. `_eval_node` içinde ele alınmayan her düğüm türü —
#: nitelik erişimi, indeksleme, lambda, üreteç, dize — reddedilir.
_MATH_CONSTANTS = {
    k: v for k, v in ((k, getattr(math, k)) for k in dir(math))
    if not k.startswith("_") and not callable(v)
}
_ALLOWED_FUNCS = {
    k: v for k, v in ((k, getattr(math, k)) for k in dir(math))
    if not k.startswith("_") and callable(v)
}
_ALLOWED_FUNCS["abs"] = abs
_ALLOWED_FUNCS["round"] = round

_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

#: Kaynak tüketme de bir saldırıdır: `9**9**9` reddedilmeden hesaplanırsa
#: süreç dakikalarca CPU ve yüzlerce MB RAM yer. Tek çağrıyla dev tam sayı
#: üreten math işlevleri de aynı nedenle sınırlanır.
_MAX_EXPONENT = 1000
_MAX_RESULT_BITS = 10_000
_ARG_LIMITS = {"factorial": 1000, "comb": 1000, "perm": 1000}


def _guarded_pow(base, exponent):
    if abs(exponent) > _MAX_EXPONENT:
        raise ValueError(f"üs çok büyük (en fazla {_MAX_EXPONENT})")
    if isinstance(base, int) and isinstance(exponent, int) and exponent > 0:
        if base.bit_length() * exponent > _MAX_RESULT_BITS:
            raise ValueError("sonuç çok büyük")
    return base ** exponent


def _checked_number(value):
    # A-03: every AST result must be a bounded scalar before its parent runs.
    if type(value) not in (int, float):
        raise ValueError("only scalar numbers are allowed")
    if isinstance(value, int) and value.bit_length() > _MAX_RESULT_BITS:
        raise ValueError("numeric result is too large")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("numeric result must be finite")
    return value


def _eval_node(node):
    """Tek bir AST düğümünü yorumlar; beyaz listede olmayan her şeyi reddeder."""
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"yalnız sayı kullanılabilir: {node.value!r}")
        return _checked_number(node.value)

    if isinstance(node, ast.Name):
        if node.id in _MATH_CONSTANTS:
            return _checked_number(_MATH_CONSTANTS[node.id])
        raise ValueError(f"bilinmeyen ad: {node.id}")

    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"izin verilmeyen işleç: {type(node.op).__name__}")
        return _checked_number(op(_eval_node(node.operand)))

    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            return _checked_number(_guarded_pow(_eval_node(node.left), _eval_node(node.right)))
        op = _BINARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"izin verilmeyen işleç: {type(node.op).__name__}")
        return _checked_number(op(_eval_node(node.left), _eval_node(node.right)))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("yalnız izinli işlev adları çağrılabilir")
        fn = _ALLOWED_FUNCS.get(node.func.id)
        if fn is None:
            raise ValueError(f"izin verilmeyen işlev: {node.func.id}")
        if node.keywords:
            raise ValueError("anahtar sözcüklü argüman desteklenmiyor")
        args = [_eval_node(a) for a in node.args]
        limit = _ARG_LIMITS.get(node.func.id)
        if limit is not None and any(a > limit for a in args):
            raise ValueError(f"{node.func.id} argümanı çok büyük (en fazla {limit})")
        return _checked_number(fn(*args))

    raise ValueError(f"izin verilmeyen ifade: {type(node).__name__}")


def calculate(expression: str) -> str:
    """
    Matematiksel ifadeyi hesaplar.
    Örnek: "sin(pi/4) * 100", "2**10", "sqrt(144)"
    """
    try:
        result = _eval_node(ast.parse(expression, mode="eval").body)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Hata: Sıfıra bölme"
    except Exception as e:
        return f"Hesaplama hatası: {e}"


# ════════════════════════════════════════════════════════
#  YENİ ARAÇ 7: TARİH / SAAT
# ════════════════════════════════════════════════════════

def get_datetime(timezone: str = "Europe/Istanbul") -> str:
    """Şu anki tarih ve saati döndürür."""
    try:
        from datetime import datetime
        import zoneinfo
        tz = zoneinfo.ZoneInfo(timezone)
        now = datetime.now(tz)
        return (
            f"📅 {now.strftime('%A, %d %B %Y')}\n"
            f"🕐 {now.strftime('%H:%M:%S')} ({timezone})\n"
            f"📆 Yılın {now.timetuple().tm_yday}. günü | Hafta {now.isocalendar()[1]}"
        )
    except Exception:
        from datetime import datetime
        now = datetime.now()
        return f"{now.strftime('%d.%m.%Y %H:%M:%S')}"


# ════════════════════════════════════════════════════════
#  YENİ ARAÇ 8: NOT SİSTEMİ (Görev / Hatırlatıcı)
# ════════════════════════════════════════════════════════

def save_note(content: str, category: str = "genel", tags: str = "") -> str:
    """
    Not / görev / hatırlatıcı kaydeder.
    category: genel | görev | fikir | araştırma | kişisel
    tags: virgülle ayrılmış etiketler
    """
    notes = _load_notes()
    note = {
        "id": int(time.time() * 1000),
        "content": content,
        "category": category,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "created_at": datetime.now().isoformat(),
        "done": False,
    }
    notes.append(note)
    _save_notes(notes)
    return f"✅ Not kaydedildi (ID: {note['id']})\nKategori: {category} | Etiketler: {tags or 'yok'}"


def get_notes(filter_by: str = "", category: str = "", show_done: bool = False) -> str:
    """
    Notları listeler veya arar.
    filter_by: içerik araması
    category: kategori filtresi
    show_done: tamamlananları da göster
    """
    notes = _load_notes()

    if not notes:
        return "📋 Henüz not yok. save_note ile not ekleyebilirsin."

    # Filtrele
    filtered = notes
    if not show_done:
        filtered = [n for n in filtered if not n.get("done")]
    if category:
        filtered = [n for n in filtered if n.get("category", "").lower() == category.lower()]
    if filter_by:
        q = filter_by.lower()
        filtered = [n for n in filtered if q in n.get("content", "").lower()
                    or any(q in t.lower() for t in n.get("tags", []))]

    if not filtered:
        return f"'{filter_by or category}' için not bulunamadı."

    lines = [f"## 📋 Notlar ({len(filtered)} adet)\n"]
    for n in sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True):
        status = "✅" if n.get("done") else "⬜"
        date = n.get("created_at", "")[:10]
        tags = " ".join(f"#{t}" for t in n.get("tags", []))
        lines.append(
            f"{status} [{n.get('category', 'genel')}] {date} (ID:{n['id']})\n"
            f"   {n.get('content', '')}\n"
            f"   {tags}"
        )
    return "\n".join(lines)


def complete_note(note_id: int) -> str:
    """Notu tamamlandı olarak işaretle."""
    notes = _load_notes()
    for n in notes:
        if n.get("id") == note_id:
            n["done"] = True
            n["completed_at"] = datetime.now().isoformat()
            _save_notes(notes)
            return f"✅ Not tamamlandı: {n.get('content', '')[:80]}"
    return f"Not bulunamadı: ID={note_id}"


def delete_note(note_id: int) -> str:
    """Notu siler."""
    notes = _load_notes()
    before = len(notes)
    notes = [n for n in notes if n.get("id") != note_id]
    if len(notes) < before:
        _save_notes(notes)
        return f"🗑️ Not silindi (ID: {note_id})"
    return f"Not bulunamadı: ID={note_id}"


# ════════════════════════════════════════════════════════
#  Claude tool_use ŞEMA TANIMLARI
# ════════════════════════════════════════════════════════
TOOL_DEFINITIONS = [
    # ── Mevcut araçlar ──────────────────────────────────
    {
        "name": "run_terminal_command",
        "description": "Terminal/shell komutu çalıştırır. Pip kurulumu, test, build vb. için.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Shell komutu"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Dosya içeriğini okur (kod, metin, config).",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
    },
    {
        "name": "write_file",
        "description": "Dosyaya içerik yazar. Yoksa oluşturur, varsa günceller.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "Klasör içeriğini listeler.",
        "input_schema": {
            "type": "object",
            "properties": {"dir_path": {"type": "string", "default": "."}},
        },
    },
    {
        "name": "search_in_files",
        "description": "Proje dosyalarında metin arar (grep).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "file_pattern": {"type": "string", "default": "*.py"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "git_status",
        "description": "Git repo durumu: değişiklikler, branch, son commitler.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "git_diff",
        "description": "Bekleyen git değişikliklerini gösterir.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string", "default": ""}},
        },
    },
    {
        "name": "get_project_structure",
        "description": "Projenin klasör ve dosya yapısını gösterir.",
        "input_schema": {
            "type": "object",
            "properties": {"max_depth": {"type": "integer", "default": 3}},
        },
    },
    # ── YENİ araçlar ────────────────────────────────────
    {
        "name": "web_search",
        "description": "İnternette DuckDuckGo ile arama yapar. Güncel bilgi, haberler, teknik konular için kullan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Arama sorgusu"},
                "max_results": {"type": "integer", "default": 5, "description": "Sonuç sayısı (1-10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_webpage",
        "description": "Bir URL'den web sayfası içeriğini çeker ve metin olarak döndürür.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Tam URL (https://...)"},
                "max_chars": {"type": "integer", "default": 5000},
            },
            "required": ["url"],
        },
    },
    {
        "name": "deep_research",
        "description": "Bir konu hakkında çok adımlı derin araştırma yapar. Birden fazla kaynak bulur ve içerik çeker. Kapsamlı araştırma için kullan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Araştırılacak konu"},
                "depth": {"type": "integer", "default": 2, "description": "Derinlik: 1=hızlı, 2=orta, 3=kapsamlı"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "analyze_file",
        "description": "PDF, Excel, CSV, JSON dosyalarını okur ve analiz eder. Veri setleri, raporlar ve dökümanlar için kullan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Dosya yolu"},
                "analysis_type": {
                    "type": "string",
                    "enum": ["auto", "summary", "full", "stats"],
                    "default": "auto",
                    "description": "auto=akıllı seçim, summary=özet, full=tam, stats=istatistik",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "run_python_code",
        "description": "Python kodu çalıştırır. Hesaplama, veri analizi, pandas işlemleri için kullan. numpy ve pandas hazır.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Çalıştırılacak Python kodu"},
                "timeout": {"type": "integer", "default": 15},
            },
            "required": ["code"],
        },
    },
    {
        "name": "calculate",
        "description": "Matematiksel ifadeyi hesaplar. sin, cos, sqrt, log, pi vb. destekler.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Matematik ifadesi, örn: 'sqrt(144) + sin(pi/4)'"},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_datetime",
        "description": "Şu anki tarih ve saati döndürür.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "default": "Europe/Istanbul"},
            },
        },
    },
    {
        "name": "save_note",
        "description": "Not, görev veya fikir kaydeder. Kalıcı olarak saklanır.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Not içeriği"},
                "category": {
                    "type": "string",
                    "enum": ["genel", "görev", "fikir", "araştırma", "kişisel"],
                    "default": "genel",
                },
                "tags": {"type": "string", "default": "", "description": "Virgülle ayrılmış etiketler"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "get_notes",
        "description": "Kaydedilen notları listeler veya arar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter_by": {"type": "string", "default": "", "description": "İçerik araması"},
                "category": {"type": "string", "default": "", "description": "Kategori filtresi"},
                "show_done": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "complete_note",
        "description": "Görevi/notu tamamlandı olarak işaretler.",
        "input_schema": {
            "type": "object",
            "properties": {"note_id": {"type": "integer"}},
            "required": ["note_id"],
        },
    },
    {
        "name": "delete_note",
        "description": "Notu kalıcı olarak siler.",
        "input_schema": {
            "type": "object",
            "properties": {"note_id": {"type": "integer"}},
            "required": ["note_id"],
        },
    },
]

# ─── Araç kaydı ──────────────────────────────────────────
TOOL_REGISTRY: dict[str, Any] = {
    "run_terminal_command": run_terminal_command,
    "read_file":            read_file,
    "write_file":           write_file,
    "list_directory":       list_directory,
    "search_in_files":      search_in_files,
    "git_status":           git_status,
    "git_diff":             git_diff,
    "get_project_structure": get_project_structure,
    # Yeni araçlar
    "web_search":           web_search,
    "fetch_webpage":        fetch_webpage,
    "deep_research":        deep_research,
    "analyze_file":         analyze_file,
    "run_python_code":      run_python_code,
    "calculate":            calculate,
    "get_datetime":         get_datetime,
    "save_note":            save_note,
    "get_notes":            get_notes,
    "complete_note":        complete_note,
    "delete_note":          delete_note,
}


def execute_tool(name: str, inputs: dict) -> str:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return f"Bilinmeyen araç: {name}"
    try:
        return str(fn(**inputs))
    except Exception as e:
        return f"Araç hatası ({name}): {e}"
import os
import glob
import shutil
from pathlib import Path

def find_and_load_pdf(query: str = None) -> str:
    """
    Masaüstü, İndirilenler ve mevcut klasörde PDF ara.
    Bulduğunu data/documents/ klasörüne kopyala, RAG'a yükle.
    """
    # Aranacak klasörler
    search_dirs = [
        Path.home() / "Desktop",
        Path.home() / "Downloads", 
        Path.home() / "Masaüstü",
        Path.home() / "İndirilenler",
        Path.cwd(),
    ]
    
    found_pdfs = []
    for d in search_dirs:
        if d.exists():
            found_pdfs.extend(d.glob("*.pdf"))
    
    if not found_pdfs:
        return "Masaüstü veya İndirilenler klasöründe PDF bulunamadı."
    
    # En son değiştirilen PDF'i al
    latest_pdf = max(found_pdfs, key=lambda p: p.stat().st_mtime)
    
    # data/documents/ klasörüne kopyala
    dest_dir = Path("data/documents")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / latest_pdf.name
    shutil.copy2(latest_pdf, dest)
    
    # RAG'a yükle
    try:
        from rag.rag_engine import JarvisRAG
        rag = JarvisRAG()
        rag.add_documents([str(dest)])
        return f"✅ '{latest_pdf.name}' yüklendi ve RAG'a eklendi. Şimdi sorabilirsin."
    except Exception as e:
        return f"PDF kopyalandı ama RAG'a eklenemedi: {e}"
    import os
import shutil
from pathlib import Path

def find_and_load_pdf(query: str = None) -> str:
    """
    Masaüstü ve İndirilenler klasöründe en son PDF'i bul.
    data/documents/ klasörüne kopyala.
    """
    search_dirs = [
        Path.home() / "Desktop",
        Path.home() / "Downloads",
        Path.home() / "Masaüstü",
        Path.home() / "İndirilenler",
        Path.cwd(),
    ]
    
    found_pdfs = []
    for d in search_dirs:
        if d.exists():
            found_pdfs.extend(d.glob("*.pdf"))
    
    if not found_pdfs:
        return "❌ Masaüstü veya İndirilenler'de PDF bulunamadı."
    
    # En son değiştirilen PDF'i al
    latest_pdf = max(found_pdfs, key=lambda p: p.stat().st_mtime)
    
    # data/documents/ klasörüne kopyala
    dest_dir = Path("data/documents")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / latest_pdf.name
    
    try:
        shutil.copy2(latest_pdf, dest)
        print(f"📄 {latest_pdf.name} kopyalandı → {dest}")
        return f"✅ '{latest_pdf.name}' yüklendi ve analiz ediliyor..."
    except Exception as e:
        return f"❌ Kopyalama hatası: {e}"