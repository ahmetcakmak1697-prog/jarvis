import sqlite3
from pathlib import Path

# OpenJarvis'ten alınan ve Domain Isolation ile güçlendirilmiş SQL Şeması
_CREATE_TRACES = """\
CREATE TABLE IF NOT EXISTS traces (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id              TEXT    NOT NULL UNIQUE,
    context_domain        TEXT    NOT NULL DEFAULT 'genel',  -- BİZİM EKLEDİĞİMİZ SÜTUN (kurumsal, kisisel, kodlama)
    query                 TEXT    NOT NULL DEFAULT '',
    model_used            TEXT    NOT NULL DEFAULT 'llama3.1-local', -- %95 Local / %5 API takibi için
    result                TEXT    NOT NULL DEFAULT '',
    total_tokens          INTEGER NOT NULL DEFAULT 0,
    metadata              TEXT    NOT NULL DEFAULT '{}',
    messages              TEXT    NOT NULL DEFAULT '[]',
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class JarvisMemoryStore:
    def __init__(self, db_path: str = "jarvis_memory.db") -> None:
        # Veritabanını senin memory klasöründe oluşturur
        self._db_path = Path(__file__).parent / db_path
        
        # OpenJarvis'in WAL Mode taktiği (Hızı ve aynı anda işlemi artırır)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TRACES)
        self._conn.commit()
        print(f"[*] Jarvis Hafıza Merkezi Aktif: {self._db_path}")

    def log_interaction(self, trace_id, domain, query, model, result, tokens=0):
        # Jarvis'in yaşadıklarını hafızaya kazıdığı fonksiyon
        query_sql = """
            INSERT INTO traces (trace_id, context_domain, query, model_used, result, total_tokens)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self._conn.execute(query_sql, (trace_id, domain, query, model, result, tokens))
        self._conn.commit()

# Test etmek için alt kısım
if __name__ == "__main__":
    memory = JarvisMemoryStore()
    memory.log_interaction("test_001", "sistem", "Hafıza testi başlatıldı.", "llama3.1-local", "Başarılı", 15)
    print("[+] Test verisi hafızaya yazıldı. Jarvis artık unutmuyor.")