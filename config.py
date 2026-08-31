"""
jarvis/config.py
Tüm sistem ayarlarını tek yerden yönetir.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Persona SSOT (saf modul, yan etkisiz -- bkz. agents/persona.py)
from agents.persona import build_system_prompt as _build_system_prompt

# .env dosyasını yükle
load_dotenv()
os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
# ─── Temel ──────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
JARVIS_NAME: str       = os.getenv("JARVIS_NAME", "Jarvis")
JARVIS_LANGUAGE: str   = os.getenv("JARVIS_LANGUAGE", "tr")
JARVIS_MODEL: str      = os.getenv("JARVIS_MODEL", "claude-opus-4-5-20251101")

# ─── Proje ──────────────────────────────────────────────
PROJECT_PATH: Path = Path(os.getenv("PROJECT_PATH", ".")).resolve()

# ─── Bellek ─────────────────────────────────────────────
MEMORY_PROVIDER: str = os.getenv("MEMORY_PROVIDER", "local")
QDRANT_URL: str      = os.getenv("QDRANT_URL", "http://localhost:6333")
MEMORY_DB_PATH: Path = Path(__file__).parent / "data" / "memory"

# ─── RAG ────────────────────────────────────────────────
RAG_DB_PATH: Path    = Path(__file__).parent / "data" / "rag"
EMBED_MODEL: str     = "all-MiniLM-L6-v2"   # Hızlı, lokal
CHUNK_SIZE: int      = 500    # Token başına karakter
CHUNK_OVERLAP: int   = 50
MAX_RAG_RESULTS: int = 5

# ─── Ajan ───────────────────────────────────────────────
MAX_AGENT_ITERATIONS: int = int(os.getenv("MAX_AGENT_ITERATIONS", "100"))
AUTO_RUN_COMMANDS: bool   = os.getenv("AUTO_RUN_COMMANDS", "false").lower() == "true"

# ─── Ses ────────────────────────────────────────────────
VOICE_ENABLED: bool  = os.getenv("VOICE_ENABLED", "false").lower() == "true"
WHISPER_MODEL: str   = os.getenv("WHISPER_MODEL", "base")
TTS_VOICE: str       = os.getenv("TTS_VOICE", "tr-TR-AhmetNeural")
SAMPLE_RATE: int     = 16000
SILENCE_THRESHOLD: float = 0.01
SILENCE_DURATION: float  = 1.5   # saniye

# ─── System Prompt ──────────────────────────────────────
# Persona SSOT: metin agents/persona.py icinde tanimlidir. Burada yeniden
# yazilmaz -- daha once repoda birbirinden habersiz UC ayri persona vardi.
# Sozlesme kilidi: tests/test_persona_ssot.py
SYSTEM_PROMPT_TR: str = _build_system_prompt(name=JARVIS_NAME)

SYSTEM_PROMPT_EN = f"""You are {JARVIS_NAME} — a highly capable AI assistant similar to Jarvis from Iron Man.

## PERSONALITY
- Intelligent, analytical, and proactive
- Concise and precise — no unnecessary filler
- Address the user formally or by name
- Point out errors gently but stay solution-focused
- Respond in English (switch to Turkish if user writes Turkish)

## CAPABILITIES
- File system: read, write, search
- Terminal: run commands (requires confirmation)
- Git: repo status, commit history, diff
- Web: search and fetch content
- Project memory: remember previous conversations
- Codebase knowledge: familiar with all project files

## BEHAVIOR RULES
- Always ask before running a command
- Never expose sensitive files (.env, passwords)
- Say "I don't know" rather than making things up
- Highlight the most important info in every response
"""

SYSTEM_PROMPT = SYSTEM_PROMPT_TR if JARVIS_LANGUAGE == "tr" else SYSTEM_PROMPT_EN


def validate():
    """Başlangıçta kritik ayarları kontrol eder."""
    errors = []
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY.startswith("sk-ant-xxx"):
        errors.append("ANTHROPIC_API_KEY .env dosyasında ayarlanmamış!")
    if not PROJECT_PATH.exists():
        errors.append(f"PROJECT_PATH bulunamadı: {PROJECT_PATH}")
    return errors
