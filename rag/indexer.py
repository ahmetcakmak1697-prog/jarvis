"""
jarvis/rag/indexer.py
─────────────────────────────────────────────────────────
ADIM 3 — Kod Tabanı İndeksleme (RAG)

Projenin tüm dosyalarını tarar, parçalara böler,
vektör veritabanına (ChromaDB) kaydeder.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterator

import chromadb
from chromadb.utils import embedding_functions
from config import (
    PROJECT_PATH, RAG_DB_PATH,
    EMBED_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
)

# ─── Taranmayacak dosya/klasörler ───────────────────────
SKIP_DIRS  = {".git", "node_modules", "__pycache__", ".venv", "venv",
              "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache"}
SKIP_EXTS  = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin",
              ".jpg", ".png", ".gif", ".ico", ".svg", ".woff", ".ttf",
              ".zip", ".tar", ".gz", ".lock", ".log"}
TEXT_EXTS  = {".py", ".js", ".ts", ".tsx", ".jsx", ".vue", ".html", ".css",
              ".scss", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
              ".md", ".txt", ".rst", ".sh", ".bash", ".env.example",
              ".dockerfile", "Makefile", ".sql", ".go", ".rs", ".rb", ".java"}


def _file_id(path: Path) -> str:
    """Dosya yolundan deterministik ID üret."""
    return hashlib.md5(str(path).encode()).hexdigest()


def _iter_files(root: Path) -> Iterator[Path]:
    """Projedeki tüm metin dosyalarını tarar."""
    for dirpath, dirnames, filenames in os.walk(root):
        # Atlanan klasörleri in-place çıkar (os.walk optimizasyonu)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() in TEXT_EXTS or fpath.name in {"Makefile", "Dockerfile"}:
                if fpath.suffix.lower() not in SKIP_EXTS:
                    yield fpath


def _chunk_text(text: str, path: Path) -> list[dict]:
    """Metni örtüşen parçalara böler."""
    lines  = text.splitlines()
    chunks = []
    buf, buf_start = [], 0

    for i, line in enumerate(lines):
        buf.append(line)
        joined = "\n".join(buf)
        if len(joined) >= CHUNK_SIZE:
            chunks.append({
                "text": joined,
                "file": str(path),
                "start_line": buf_start,
                "end_line": i,
            })
            # Overlap: son N karakter ile devam et
            overlap_lines = []
            overlap_size  = 0
            for l in reversed(buf):
                if overlap_size + len(l) > CHUNK_OVERLAP:
                    break
                overlap_lines.insert(0, l)
                overlap_size += len(l)
            buf       = overlap_lines
            buf_start = i - len(overlap_lines) + 1

    if buf:
        chunks.append({
            "text": "\n".join(buf),
            "file": str(path),
            "start_line": buf_start,
            "end_line": len(lines) - 1,
        })
    return chunks


# ────────────────────────────────────────────────────────
#  Ana sınıf
# ────────────────────────────────────────────────────────
class RAGIndexer:
    """
    Kullanım:
        idx = RAGIndexer()
        stats = idx.index_project()   # ilk kurulum
        idx.update_file(Path("main.py"))  # dosya değişince
    """
    def __init__(self):
        RAG_DB_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(RAG_DB_PATH))
        self.ef     = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        self.col    = self.client.get_or_create_collection(
            name="codebase",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )

    # ─── İndeksleme ─────────────────────────────────────
    def index_project(self, root: Path | None = None) -> dict:
        """Tüm projeyi tarayıp ChromaDB'e kaydeder."""
        root = root or PROJECT_PATH
        print(f"[RAG] Proje taranıyor: {root}")

        files_done, chunks_added = 0, 0
        for fpath in _iter_files(root):
            n = self._index_file(fpath)
            chunks_added += n
            files_done   += 1
            if files_done % 20 == 0:
                print(f"  → {files_done} dosya işlendi, {chunks_added} chunk eklendi")

        print(f"[RAG] Tamamlandı: {files_done} dosya, {chunks_added} chunk")
        return {"files": files_done, "chunks": chunks_added}

    def _index_file(self, path: Path) -> int:
        """Tek dosyayı indeksler. Değişmemişse atlar."""
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            return 0
        if not text.strip():
            return 0

        chunks = _chunk_text(text, path)
        if not chunks:
            return 0

        ids   = [f"{_file_id(path)}_c{i}" for i in range(len(chunks))]
        texts = [c["text"] for c in chunks]
        metas = [{
            "file":       c["file"],
            "start_line": c["start_line"],
            "end_line":   c["end_line"],
            "language":   path.suffix.lstrip("."),
        } for c in chunks]

        # Var olanları sil, yenilerini ekle (upsert emülasyonu)
        existing = self.col.get(ids=ids)["ids"]
        if existing:
            self.col.delete(ids=existing)
        self.col.add(ids=ids, documents=texts, metadatas=metas)
        return len(chunks)

    def update_file(self, path: Path) -> int:
        """Tek dosyayı günceller (kaydet olayında çağır)."""
        # Eski chunkları temizle
        file_str = str(path)
        results  = self.col.get(where={"file": file_str})
        if results["ids"]:
            self.col.delete(ids=results["ids"])
        return self._index_file(path)

    # ─── Arama ──────────────────────────────────────────
    def search(self, query: str, n: int = 5) -> list[dict]:
        """Semantik arama. En alakalı code chunkları döndürür."""
        res = self.col.query(
            query_texts=[query],
            n_results=min(n, self.col.count()),
            include=["documents", "metadatas", "distances"],
        )
        results = []
        for doc, meta, dist in zip(
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0],
        ):
            results.append({
                "text":       doc,
                "file":       meta["file"],
                "start_line": meta["start_line"],
                "end_line":   meta["end_line"],
                "language":   meta.get("language", ""),
                "score":      round(1 - dist, 4),   # benzerlik skoru
            })
        return results

    def format_context(self, query: str, n: int = 5) -> str:
        """Arama sonuçlarını Claude için formatlanmış metin döndürür."""
        results = self.search(query, n=n)
        if not results:
            return ""
        parts = ["## Proje Kodu — İlgili Parçalar\n"]
        for r in results:
            rel_file = Path(r["file"]).relative_to(PROJECT_PATH)
            parts.append(
                f"### `{rel_file}` (satır {r['start_line']}–{r['end_line']}, "
                f"benzerlik: {r['score']})\n"
                f"```{r['language']}\n{r['text']}\n```\n"
            )
        return "\n".join(parts)

    @property
    def count(self) -> int:
        return self.col.count()
