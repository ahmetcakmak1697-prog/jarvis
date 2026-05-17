from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parent.parent


IGNORED_DIRS = {
    ".git",
    ".vscode",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "node_modules",
    "models",
    "model",
    "cache",
    ".cache",
    "logs",
    "outputs",
    "output",
    "tmp",
    "temp",
    "dist",
    "build",
    "jarvis_snapshot_export",
    "memory",
    "jarvis_data",
    "uploads",
    "data",
    "chroma_db",
    "rag_cache",
}


IGNORED_FILES = {
    ".env",
    ".env.example",
    ".env.local",
    ".env.production",
    "jarvis_snapshot_full_safe.zip",
    "snapshot.txt",
    "snapshot_20260512.txt",
    "research_cache.json",
    "conversations.json",
    "search_credits.json",
    "user_profile.json",
    "jarvis_memory.db",
}


IGNORED_EXTS = {
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".bin",
    ".gguf",
    ".safetensors",
    ".pt",
    ".pth",
    ".onnx",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".mp3",
    ".wav",
    ".flac",
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
}


ALLOWED_EXTS = {
    ".py",
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".bat",
    ".ps1",
    ".sh",
}


def safe_path(path: str) -> Path:
    """
    Kullanıcının verdiği yolu proje klasörü içinde güvenli hale getirir.
    """
    p = Path(path)

    if not p.is_absolute():
        p = PROJECT_ROOT / p

    try:
        p = p.resolve()
    except Exception:
        return PROJECT_ROOT

    return p


def should_ignore(file: Path) -> bool:
    """
    Dosya arama/listeleme sırasında gereksiz veya hassas dosyaları dışarıda bırakır.
    """
    try:
        rel = file.relative_to(PROJECT_ROOT)
        parts = rel.parts
    except Exception:
        parts = file.parts

    if any(part in IGNORED_DIRS for part in parts):
        return True

    if file.name in IGNORED_FILES:
        return True

    if file.suffix.lower() in IGNORED_EXTS:
        return True

    if file.suffix.lower() not in ALLOWED_EXTS:
        return True

    return False


def read_file(path: str, max_chars: int = 12000) -> str:
    """
    Dosya içeriğini okur.
    """
    p = safe_path(path)

    if not p.exists():
        return f"Dosya bulunamadı: {path}"

    if not p.is_file():
        return f"Bu bir dosya değil: {path}"

    if should_ignore(p):
        return f"Bu dosya güvenlik/temizlik filtresi nedeniyle okunmadı: {path}"

    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Dosya okunamadı: {e}"

    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[NOT: Dosya çok uzun olduğu için kesildi.]"

    return text


def count_text_in_file(path: str, text: str) -> str:
    """
    Bir dosyada belirli metnin kaç kez geçtiğini sayar.
    """
    p = safe_path(path)

    if not p.exists():
        return f"Dosya bulunamadı: {path}"

    if not p.is_file():
        return f"Bu bir dosya değil: {path}"

    if should_ignore(p):
        return f"Bu dosya güvenlik/temizlik filtresi nedeniyle okunmadı: {path}"

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Dosya okunamadı: {e}"

    count = content.count(text)

    return f"{p.name} dosyasında '{text}' ifadesi {count} kez geçiyor."


def count_regex_in_file(path: str, pattern: str) -> str:
    """
    Regex ile sayım yapar.
    Kod kelimeleri için daha doğru sonuç verir.
    Örnek pattern: \\belif\\b
    """
    p = safe_path(path)

    if not p.exists():
        return f"Dosya bulunamadı: {path}"

    if not p.is_file():
        return f"Bu bir dosya değil: {path}"

    if should_ignore(p):
        return f"Bu dosya güvenlik/temizlik filtresi nedeniyle okunmadı: {path}"

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Dosya okunamadı: {e}"

    try:
        matches = re.findall(pattern, content)
    except Exception as e:
        return f"Regex hatası: {e}"

    return f"{p.name} dosyasında pattern '{pattern}' toplam {len(matches)} kez bulundu."


def search_text_in_project(text: str, folder: str = ".", max_results: int = 50) -> str:
    """
    Proje içinde metin arar.
    """
    root = safe_path(folder)

    if not root.exists():
        return f"Klasör bulunamadı: {folder}"

    results = []

    for file in root.rglob("*"):
        if len(results) >= max_results:
            break

        if not file.is_file():
            continue

        if should_ignore(file):
            continue

        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if text in content:
            try:
                rel = file.relative_to(PROJECT_ROOT)
            except Exception:
                rel = file

            line_numbers = []

            for i, line in enumerate(content.splitlines(), start=1):
                if text in line:
                    line_numbers.append(str(i))

                    if len(line_numbers) >= 5:
                        break

            results.append(f"{rel} | satırlar: {', '.join(line_numbers)}")

    if not results:
        return f"Proje içinde '{text}' bulunamadı."

    return "Bulunan yerler:\n" + "\n".join(results)


def list_project_files(folder: str = ".", max_files: int = 200) -> str:
    """
    Proje dosyalarını güvenli ve temiz şekilde listeler.
    Gizli dosyaları, cache/veri/model/log dosyalarını göstermez.
    """
    root = safe_path(folder)

    if not root.exists():
        return f"Klasör bulunamadı: {folder}"

    files = []

    for file in root.rglob("*"):
        if len(files) >= max_files:
            break

        if not file.is_file():
            continue

        if should_ignore(file):
            continue

        try:
            rel = file.relative_to(PROJECT_ROOT)
        except Exception:
            rel = file

        files.append(str(rel))

    if not files:
        return "Dosya bulunamadı."

    return "\n".join(files)