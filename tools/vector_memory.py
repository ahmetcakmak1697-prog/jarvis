"""Vector Memory - ChromaDB semantic memory."""
import json
from pathlib import Path
from datetime import datetime


#: Onaylanmis bilgi kartlarinin koleksiyonu. Buraya yalniz
#: `knowledge_card_promoter` yazar (CLAUDE.md 7.1a).
VARSAYILAN_KOLEKSIYON = "jarvis_memories"


class VectorMemory:
    def __init__(self, db_path="memory/chroma_db",
                 collection=VARSAYILAN_KOLEKSIYON, gomme=None):
        """
        ``collection`` ve ``gomme`` varsayilanlari DEGISMEDI: mevcut
        cagiranlarin (promoter, router, telegram) davranisi aynen korunur.
        Yeni yollar acikca secer -- `agent/anlamsal_hafiza.py` sohbet
        indeksini ayri bir koleksiyonda ve Turkce anlayan bir gomme
        fonksiyonuyla tutar. Varsayilani degistirmek, 13 saniyelik model
        yuklemesini bu yolu istemeyen herkese odetirdi.
        """
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError("pip install chromadb")
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=db_path, settings=Settings(anonymized_telemetry=False))
        self.collection_name = collection
        self._gomme = gomme
        self.col = self._koleksiyonu_ac()

    def _koleksiyonu_ac(self):
        ek = {"metadata": {"hnsw:space": "cosine"}}
        if self._gomme is not None:
            ek["embedding_function"] = self._gomme
        return self.client.get_or_create_collection(self.collection_name, **ek)

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

            docs = r.get("documents", [[]])[0] or []
            metas = r.get("metadatas", [[]])[0] or []
            distances = r.get("distances", [[]])[0] or []
            ids = r.get("ids", [[]])[0] or []

            out = []
            for idx, doc in enumerate(docs):
                m = metas[idx] if idx < len(metas) and isinstance(metas[idx], dict) else {}
                d = distances[idx] if idx < len(distances) else None
                doc_id = ids[idx] if idx < len(ids) else ""

                try:
                    distance = float(d) if d is not None else None
                except Exception:
                    distance = None

                # Existing threshold is Chroma cosine distance based: lower is better.
                if distance is not None and distance >= threshold:
                    continue

                similarity = None
                if distance is not None:
                    similarity = max(0.0, min(1.0, 1.0 - distance))

                out.append({
                    "id": doc_id,
                    "user_msg": m.get("user_msg", ""),
                    "jarvis_msg": m.get("jarvis_msg", ""),
                    "ts": m.get("ts", ""),
                    "distance": distance,
                    "similarity": similarity,
                    "metadata": m,
                    "document": doc,
                })
            return out
        except Exception:
            return []

# Mevcut VectorMemory sınıfının içine ekle:

    def save_info(self, content, metadata=None):
        """Brain'in 'save_info' çağrısını 'remember' metoduna bağlar."""
        # Senin 'remember' metodun user ve jarvis mesajı bekliyor. 
        # Bunu genel bir kayıt sistemine uyarlıyoruz.
        return self.remember("Sistem Kaydı", content, meta=metadata)

    def search_memory(self, query):
        """Brain'in 'search_memory' çağrısını 'find_similar' metoduna bağlar."""
        results = self.find_similar(query, n=1)
        if results:
            # En yakın sonucu Jarvis'in anlayacağı formatta döndürür
            res = results[0]
            return f"--- Hatırlanan Bilgi ---\nKullanıcı: {res['user_msg']}\nJarvis: {res['jarvis_msg']}"
        return None
    
    def stats(self):
        try:
            return {"total": self.col.count()}
        except:
            return {"total": 0}

    def reset(self):
        """Bu ornegin koleksiyonunu bosaltir -- SABIT bir ad degil.

        Eskiden ad iki yerde "jarvis_memories" olarak yaziliydi; ayri bir
        koleksiyon acan bir cagiran `reset()` cagirdiginda KENDI indeksini
        degil, onaylanmis bilgi kartlarini silerdi.
        """
        try:
            self.client.delete_collection(self.collection_name)
            self.col = self._koleksiyonu_ac()
            return True
        except Exception:
            return False
