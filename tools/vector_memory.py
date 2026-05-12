"""Vector Memory - ChromaDB semantic memory."""
import json
from pathlib import Path
from datetime import datetime


class VectorMemory:
    def __init__(self, db_path="memory/chroma_db"):
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError("pip install chromadb")
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=db_path, settings=Settings(anonymized_telemetry=False))
        self.col = self.client.get_or_create_collection(
            "jarvis_memories", metadata={"hnsw:space": "cosine"})

    def remember(self, user_msg, jarvis_msg, meta=None):
        if not user_msg or not jarvis_msg:
            return ""
        doc_id = f"c_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        text = f"USER: {user_msg}\nJARVIS: {jarvis_msg}"
        m = (meta or {}).copy()
        m["ts"] = datetime.now().isoformat()
        m["user_msg"] = user_msg[:200]
        m["jarvis_msg"] = jarvis_msg[:300]
        try:
            self.col.add(documents=[text], ids=[doc_id], metadatas=[m])
            return doc_id
        except Exception as e:
            print(f"VM err: {e}")
            return ""

    def find_similar(self, query, n=3, threshold=0.7):
        if not query or self.col.count() == 0:
            return []
        try:
            r = self.col.query(query_texts=[query],
                               n_results=min(n, self.col.count()))
            if not r.get('documents') or not r['documents'][0]:
                return []
            out = []
            for doc, m, d in zip(r['documents'][0], r['metadatas'][0], r['distances'][0]):
                if d < threshold:
                    out.append({"user_msg": m.get("user_msg", ""),
                                "jarvis_msg": m.get("jarvis_msg", ""),
                                "ts": m.get("ts", ""), "distance": d})
            return out
        except:
            return []

    def stats(self):
        try:
            return {"total": self.col.count()}
        except:
            return {"total": 0}

    def reset(self):
        try:
            self.client.delete_collection("jarvis_memories")
            self.col = self.client.get_or_create_collection(
                "jarvis_memories", metadata={"hnsw:space": "cosine"})
            return True
        except:
            return False
