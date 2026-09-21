"""
jarvis/main.py — v3
Yerel Ollama girisi. Dogrudan Claude modu B08 ile emekliye ayrildi.
"""
from __future__ import annotations
import sys
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
    """Load local settings; credentials never select the retired API entry."""
    from dotenv import load_dotenv
    load_dotenv()
    return "local"


def chat_loop(mode: str = "auto"):
    """Ana sohbet döngüsü."""
    if mode == "auto":
        mode = _detect_mode()

    console.print(f"[bold cyan]{BANNER}[/]")

    if mode == "local":
        _run_local_mode()
    else:
        # B08: direct Claude entry retired; supported API executors are separate.
        console.print("[yellow]Eski Claude girisi emekliye ayrildi. python main.py local kullanin.[/yellow]")
        raise SystemExit(2)


def _voice_requested() -> bool:
    """Ses açık mı? Varsayılan AÇIK; JARVIS_VOICE=0 ile kapatılır.

    Edge TTS bir bulut servisi olduğu için AĞIZ ayrıca
    JARVIS_J0_EDGE_TTS_ENABLED=1 ister (CLAUDE.md §7 — veri egress).
    O bayrak yoksa mikrofon çalışır, JARVIS yalnız yazarak cevap verir.
    """
    import os

    return os.getenv("JARVIS_VOICE", "1").strip().lower() not in ("0", "false", "no")


def _build_voice_io(force: bool = False):
    """Ses katmanını kurar. Kurulamazsa klavye moduna düşer — asla çökmez."""
    from voice.voice_loop import build_default_voice_io

    def _klavye(prompt: str) -> str:
        return console.input(prompt)

    def _bildir(mesaj: str) -> None:
        console.print(f"[dim]{mesaj}[/]")

    return build_default_voice_io(
        keyboard=_klavye,
        notify=_bildir,
        enabled=force or _voice_requested(),
    )


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

    from memory.life_graph import LifeGraph, remember_exchange
    life_graph = LifeGraph()

    # Esik 4/5: donanim nobetcisi. Ornek dongu boyunca yasar ki ayni uyari
    # her turda tekrarlanmasin (cooldown durumu ornekte tutulur).
    try:
        from agents.hardware_sentinel import HardwareSentinel
        sentinel = HardwareSentinel()
    except Exception:  # noqa: BLE001 - nobetci yoksa sohbet yine calisir
        sentinel = None

    def _donanimi_kontrol_et():
        """Kritik durumu SORULMADAN bildir. Proaktif koruyucu davranis."""
        if sentinel is None:
            return
        try:
            durum = sentinel.check()
        except Exception:  # noqa: BLE001
            return
        if durum.get("should_notify") and durum.get("alerts"):
            renk = "red" if durum["level"] == "critical" else "yellow"
            console.print()
            for uyari in durum["alerts"]:
                console.print(f"[{renk}]⚠ {uyari['message']}[/]")
            voice_io.say(durum["spoken"])
        elif durum.get("recovered"):
            console.print("[green]✓ Efendim, donanım normale döndü.[/]")

    voice_io = _build_voice_io()

    if voice_io.enabled:
        console.print(
            "[bold green]Jarvis hazır![/] Mikrofon açık — konuşabilirsiniz.\n"
            "[dim]Sustuğunuzda cümle tamamlanır. Ses alınamazsa klavyeye "
            "düşer. Sesi kapatmak: 'ses kapat'[/]\n"
        )
    else:
        console.print(
            "[bold green]Jarvis hazır![/] [yellow]Ses kapalı[/] — yazabilirsiniz.\n"
            "[dim]Sesi açmak için: JARVIS_VOICE=1 ve "
            "JARVIS_J0_EDGE_TTS_ENABLED=1[/]\n"
        )

    while True:
        try:
            # Her turdan ONCE donanimi yokla: Ahmet sormadan uyarilsin.
            _donanimi_kontrol_et()

            user_input = voice_io.prompt("[bold blue]Sen:[/] ").strip()
            if not user_input:
                continue

            lower = user_input.lower()

            if lower in ("çıkış", "exit", "quit", "q"):
                agent.show_stats()
                console.print("\n[dim]Jarvis: Görüşürüz efendim.[/]")
                voice_io.say("Görüşürüz efendim.")
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

            elif lower in ("ses kapat", "sesi kapat", "voice off"):
                voice_io.enabled = False
                console.print("[yellow]Ses kapatıldı — klavye devam ediyor.[/]")
                continue

            elif lower in ("ses aç", "sesi aç", "voice on"):
                voice_io = _build_voice_io(force=True)
                console.print(
                    "[green]Ses açıldı.[/]" if voice_io.enabled
                    else "[red]Ses açılamadı.[/]"
                )
                continue

            # ZEMİN: modele tahmin ettirmek yerine gerçek kaydı ver.
            # Denetimde ölçülen kusur buydu — "Geçen hafta ne konuştuk?"
            # sorusuna olmamış bir konuşma anlatılıyordu. Kayıt yoksa hiçbir
            # şey eklenmez; boş zemin, yanlış zeminden iyidir.
            zemin = life_graph.recall_context()
            mesaj = (
                f"[BİLİNEN GERÇEKLER — yalnız bunlara dayan, "
                f"burada olmayanı uydurma]\n{zemin}\n\n{user_input}"
                if zemin else user_input
            )

            # Ses modunu HER TURDA bildir: 'ses kapat' dendiginde model de
            # bunu ogrenmeli, yoksa sesli konusma kuralini uygulamaya devam
            # eder ya da tersine, sesliyken markdown/kod dokmeye baslar.
            agent.voice_mode = voice_io.enabled

            response = _cevapla(agent, mesaj, voice_io)

            # ÖĞREN: bu turdan çıkan olguları hafızaya işle. Hassas olanlar
            # (sağlık/finans) kalıcı yazılmaz, incelemeye düşer (CLAUDE.md §7).
            try:
                for sonuc in remember_exchange(user_input, life_graph):
                    if sonuc["stored"]:
                        console.print("[dim][hafıza] kaydedildi[/]")
                    elif sonuc["target"] == "review_queue":
                        console.print(
                            "[yellow][hafıza] hassas bilgi — kalıcı "
                            "kaydedilmedi, incelemeye alındı[/]"
                        )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[dim][hafıza] işlenemedi: {exc}[/]")

        except KeyboardInterrupt:
            console.print(f"\n[dim]Çıkmak için 'çıkış' yazın.[/]")
        except Exception as e:
            console.print(f"[red]Hata: {e}[/]")


def _akis_acik() -> bool:
    """JARVIS_STREAM=0 eski tek-parca davranisa dondurur."""
    import os
    return os.environ.get("JARVIS_STREAM", "1").strip().lower() not in (
        "0", "false", "hayir", "kapali")


def _konusma_kuyrugu(voice_io):
    """Cumleleri AYRI bir is parcaciginda seslendirir.

    NEDEN KUYRUK: voice_io.say() sesi calarken BLOKE eder. Akisin
    icinden dogrudan cagirilsaydi her cumlede soket beklerdi; uzun bir
    cevapta bu zaman asimina duser ve kullanici cevabin yarisini
    kaybederdi. Kuyruk sayesinde akis tam hizda bosalir, konusma sirayla
    arkada yurur.
    """
    import queue
    import threading

    kuyruk = queue.Queue()

    def dongu():
        while True:
            cumle = kuyruk.get()
            if cumle is None:
                return
            try:
                voice_io.say(cumle)
            except Exception:  # noqa: BLE001 - ses hatasi sohbeti kesmez
                pass

    is_parcacigi = threading.Thread(target=dongu, daemon=True)
    is_parcacigi.start()
    return kuyruk, is_parcacigi


def _ses_gercekten_calisir(voice_io) -> bool:
    """TTS bu turda GERCEKTEN ses cikaracak mi?

    `voice_io.enabled` mikrofon/ses dongusunu anlatir; sentezleyicinin
    kendisi ayrica reddedebilir (Edge TTS, `JARVIS_J0_EDGE_TTS_ENABLED=1`
    yoksa metni disari cikarmaz -- CLAUDE.md §7 veri egress kapisi).

    NEDEN TUR BASINDA BIR KEZ: `say()` None dondurur ve reddi kendi
    icinde yazar. Akista cumle basina cagrildigi icin ayni uyari akan
    metnin ORTASINA her cumlede bir kez karisiyordu. Bir kez sor, ona
    gore davran.
    """
    if not getattr(voice_io, "enabled", False):
        return False
    hoparlor = getattr(voice_io, "_speaker", None)
    if hoparlor is None:
        return False
    kontrol = getattr(hoparlor, "is_enabled", None)
    if callable(kontrol):
        try:
            return bool(kontrol())
        except Exception:  # noqa: BLE001
            return False
    return True


def _cevapla(agent, mesaj: str, voice_io) -> str:
    """Cevabi akitarak bas, cumle tamamlandikca seslendir.

    Kazanc gorunur degil, DUYULUR: eskiden model 15-25 saniye susuyor,
    sonra hepsi birden geliyordu. Simdi ilk cumle tamamlanir tamamlanmaz
    konusma basliyor.
    """
    if not _akis_acik():
        response = agent.chat(mesaj)
        console.print("\n[bold cyan]Jarvis:[/]")
        console.print(Markdown(response))
        console.print()
        voice_io.say(response)
        return response

    from voice.cumle_tamponu import CumleTamponu

    tampon = CumleTamponu()
    parcalar = []
    konusacak = _ses_gercekten_calisir(voice_io)
    kuyruk, is_parcacigi = _konusma_kuyrugu(voice_io) if konusacak else (None, None)
    console.print("\n[bold cyan]Jarvis:[/] ", end="")
    try:
        for parca in agent.chat_stream(mesaj):
            parcalar.append(parca)
            # markup=False: model ciktisindaki koseli parantezi rich
            # bicimlendirme sanip metni yiyebilir.
            console.print(parca, end="", markup=False, highlight=False)
            for cumle in tampon.besle(parca):
                if kuyruk is not None:
                    kuyruk.put(cumle)
    finally:
        for cumle in tampon.bitir():
            if kuyruk is not None:
                kuyruk.put(cumle)
        console.print("\n")
        if kuyruk is not None:
            kuyruk.put(None)
            # Konusma bitene kadar bekle: sonraki soru istemi JARVIS hala
            # konusurken ekrana dusmesin.
            is_parcacigi.join(timeout=120)
    return "".join(parcalar)


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
            console.print(f"[yellow]Kullanım: python main.py [local|index][/]")
            console.print("[dim]Argumansiz calistirinca yerel Ollama modu secilir.[/]")
    else:
        chat_loop()
