"""
jarvis/main.py — v3
Claude (API) veya Lokal (Ollama) modunu destekler.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.markdown import Markdown

console = Console()

BANNER = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""

def _detect_mode() -> str:
    """
    Çalışma modunu otomatik belirle:
    - USE_LOCAL_MODEL=true  → lokal (Ollama)
    - ANTHROPIC_API_KEY var → claude (API)
    - Hiçbiri               → lokal (fallback)
    """
    from dotenv import load_dotenv
    load_dotenv()

    if os.getenv("USE_LOCAL_MODEL", "false").lower() == "true":
        return "local"
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return "claude"
    return "local"


def chat_loop(mode: str = "auto"):
    """Ana sohbet döngüsü."""
    if mode == "auto":
        mode = _detect_mode()

    console.print(f"[bold cyan]{BANNER}[/]")

    if mode == "local":
        _run_local_mode()
    else:
        _run_claude_mode()


def _run_local_mode():
    """Tamamen lokal Ollama modu — 0 maliyet."""
    console.print("[bold green]⚡ LOKAL MOD[/] — Ollama | 0 Token maliyeti\n")
    console.print("[dim]Komutlar: çıkış | temizle | modeller | istatistik[/]\n")

    from agent.local_agent import LocalJarvisAgent
    agent = LocalJarvisAgent()

    if not agent.ollama_available:
        console.print("\n[red]❌ Ollama bağlanamadı![/red]")
        console.print("[yellow]1. Ollama kurulu mu? → 1_windows_hazirlik.bat[/yellow]")
        console.print("[yellow]2. Model var mı? → 2_model_indir.bat[/yellow]")
        console.print("[yellow]3. 'ollama serve' çalışıyor mu?[/yellow]")
        return

    console.print("[bold green]Jarvis hazır![/] Konuşabilirsiniz.\n")

    while True:
        try:
            user_input = console.input("[bold blue]Sen:[/] ").strip()
            if not user_input:
                continue

            lower = user_input.lower()

            if lower in ("çıkış", "exit", "quit", "q"):
                agent.show_stats()
                console.print("\n[dim]Jarvis: Görüşürüz efendim.[/]")
                break

            elif lower in ("temizle", "clear", "reset"):
                agent.clear_history()
                continue

            elif lower in ("istatistik", "stats"):
                agent.show_stats()
                continue

            elif lower in ("modeller", "models"):
                agent.list_models()
                continue

            elif lower in ("yardım", "help"):
                _show_help(mode="local")
                continue

            response = agent.chat(user_input)
            console.print(f"\n[bold cyan]Jarvis:[/]")
            console.print(Markdown(response))
            console.print()

        except KeyboardInterrupt:
            console.print(f"\n[dim]Çıkmak için 'çıkış' yazın.[/]")
        except Exception as e:
            console.print(f"[red]Hata: {e}[/]")


def _run_claude_mode():
    """Claude API modu."""
    try:
        from config import validate, JARVIS_NAME, PROJECT_PATH
    except ImportError:
        console.print("[red]Config yüklenemedi. config.py mevcut mu?[/]")
        return

    errors = validate()
    if errors:
        for e in errors:
            console.print(f"[red]❌ {e}[/]")
        console.print("\n[yellow]💡 Lokal modda çalışmak için .env'e USE_LOCAL_MODEL=true ekleyin[/]")
        raise SystemExit(1)

    console.print("[bold magenta]☁ CLAUDE MODU[/] — Anthropic API\n")
    console.print("[dim]Komutlar: çıkış | geçmişi temizle | index | istatistik | yardım[/]\n")
    console.print(f"[bold green]{JARVIS_NAME} hazır[/] | Proje: [cyan]{PROJECT_PATH}[/]\n")
    console.print("[dim]💡 Model otomatik seçiliyor: Haiku→Sonnet→Opus (token tasarrufu)[/]\n")

    from agent.jarvis_agent import JarvisAgent
    agent = JarvisAgent()

    while True:
        try:
            user_input = console.input("[bold blue]Sen:[/] ").strip()
            if not user_input:
                continue

            lower = user_input.lower()

            if lower in ("çıkış", "exit", "quit", "q"):
                agent.show_stats()
                console.print(f"\n[dim]{JARVIS_NAME}: Görüşürüz efendim.[/]")
                break
            elif lower in ("geçmişi temizle", "clear", "reset"):
                agent.clear_history()
                continue
            elif lower in ("istatistik", "stats", "token"):
                agent.show_stats()
                continue
            elif lower in ("index", "indeksle"):
                _run_indexer()
                continue
            elif lower in ("yardım", "help"):
                _show_help(mode="claude")
                continue

            response = agent.chat(user_input)
            console.print(f"\n[bold cyan]{JARVIS_NAME}:[/]")
            console.print(Markdown(response))
            console.print()

        except KeyboardInterrupt:
            console.print(f"\n[dim]Çıkmak için 'çıkış' yazın.[/]")
        except Exception as e:
            console.print(f"[red]Hata: {e}[/]")


def _run_indexer():
    try:
        from rag.indexer import RAGIndexer
        from config import PROJECT_PATH
        console.print(f"[cyan]İndeksleniyor: {PROJECT_PATH}[/]")
        idx = RAGIndexer()
        stats = idx.index_project(PROJECT_PATH)
        console.print(f"[green]✓ İndekslendi: {stats.get('total_chunks', 0)} chunk[/]")
    except Exception as e:
        console.print(f"[red]İndeksleme hatası: {e}[/]")


def _show_help(mode: str = "local"):
    if mode == "local":
        console.print("""
[bold cyan]JARVIS Komutları (Lokal Mod):[/]
  çıkış      → Programdan çık
  temizle    → Konuşma geçmişini temizle
  modeller   → Yüklü AI modellerini listele
  istatistik → Kullanım istatistikleri
  yardım     → Bu menü
        """)
    else:
        console.print("""
[bold cyan]JARVIS Komutları (Claude Modu):[/]
  çıkış          → Programdan çık
  geçmişi temizle → Konuşma geçmişini temizle
  index          → Proje dosyalarını indeksle
  istatistik     → Token kullanım istatistikleri
  yardım         → Bu menü
        """)


# ─── Entry point ─────────────────────────────────────────
if __name__ == "__main__":
    # Argüman kontrolü
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "local":
            chat_loop(mode="local")
        elif arg == "claude":
            chat_loop(mode="claude")
        elif arg == "index":
            _run_indexer()
        else:
            console.print(f"[yellow]Kullanım: python main.py [local|claude|index][/]")
            console.print("[dim]Argümansız çalıştırınca .env'e göre otomatik mod seçilir.[/]")
    else:
        chat_loop()
