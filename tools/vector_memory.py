"""Vector Memory - ChromaDB semantic memory."""
import json
from pathlib import Path
from datetime import datetime


#: Onaylanmis bilgi kartlarinin koleksiyonu. Buraya yalniz
#: `knowledge_card_promoter` yazar (CLAUDE.md 7.1a).
VARSAYILAN_KOLEKSIYON = "jarvis_memories"

#: Turkce anlayan gomme modeli -- bu deponun VARSAYILANI.
#:
#: Chroma belirtilmediginde `all-MiniLM-L6-v2`'ye duser ve o model yalniz
#: INGILIZCE egitilmistir. Olculdu (2026-09-23): dogru belgeyle tek kelime
#: paylasmayan alti Turkce sorguda varsayilan **1/6** aldi -- alti belge
#: arasindan rastgele secmenin beklentisi de 1/6'dir. Bu model **5/6**.
#:
#: Model adi burada duruyor cunku bu bir sohbet modeli degil, indeksin veri
#: bicimini belirleyen bir KODLAYICI: degisirse indeksin tamami yeniden
#: kurulmak zorundadir. CLAUDE.md 7.1'in "model adi koda gomulmez" kurali
#: ModelRegistry'nin yonettigi akil modelleri icindir.
TURKCE_GOMME_MODELI = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

#: Model yuklemesi ~13 sn surer; surec basina bir kez odenir.
_GOMME_ONBELLEGI: dict = {}


class KoleksiyonCakismasi(RuntimeError):
    """Koleksiyonun gomme modeli istenenle uyusmuyor ve veri kaybi riski var."""


def turkce_gomme():
    """Turkce gomme fonksiyonu; surec icinde bir kez kurulur."""
    if "ef" not in _GOMME_ONBELLEGI:
        from chromadb.utils import embedding_functions

        _GOMME_ONBELLEGI["ef"] = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=TURKCE_GOMME_MODELI
        )
    return _GOMME_ONBELLEGI["ef"]


def koleksiyon_ac(client, ad: str, gomme, duyur=None):
    """Koleksiyonu **dogru** gomme modeliyle acar; yanilmayi sessiz birakmaz.

    Iki tuzak var, ikisi de olculdu (2026-09-23) ve ikisi de sessizdir:

    **1. Chroma gomme modelini degistirmeyi reddeder.** Var olan bir
    koleksiyona farkli bir model verilince `ValueError` atar. Koleksiyon
    BOSSA silinip yeniden kurulur -- kaybedilecek sey yoktur. DOLUYSA
    **silinmez**: `KoleksiyonCakismasi` yukselir ve karar insana kalir.
    Bos/dolu ayrimi olmadan bu kod bir veri imha araci olurdu.

    **2. EF verilmeden acilan koleksiyon sessizce varsayilana doner.**
    `get_collection(ad)` -- EF vermeden -- kayitli modeli geri kurmaz,
    `DefaultEmbeddingFunction` kullanir. Sorgu hata vermez, sonuc doner;
    ama soru vektoru belgelerden BASKA bir modelle hesaplanmistir. Iki
    model de 384 boyut urettigi icin boyut hatasi da alinmaz. Sonuc:
    anlamsiz mesafeler, tam guvenle. Bu yuzden acilistan sonra kullanilan
    modelin istenen model oldugu **dogrulanir**.
    """
    bildir = duyur or (lambda m: None)
    ek = {"metadata": {"hnsw:space": "cosine"}}
    if gomme is not None:
        ek["embedding_function"] = gomme

    try:
        col = client.get_or_create_collection(ad, **ek)
    except Exception as exc:
        if "embedding function" not in str(exc).lower():
            raise
        mevcut = client.get_collection(ad)
        try:
            sayi = mevcut.count()
        except Exception:  # noqa: BLE001 - sayilamiyorsa DOLU varsay
            sayi = -1
        if sayi != 0:
            raise KoleksiyonCakismasi(
                f"'{ad}' koleksiyonu baska bir gomme modeliyle kurulmus ve "
                f"{sayi if sayi >= 0 else 'bilinmeyen sayida'} kayit iceriyor. "
                "Silinmedi. Modeli degistirmek indeksin tamamini yeniden "
                "kurmayi gerektirir; bu karar insana aittir."
            ) from exc
        client.delete_collection(ad)
        col = client.get_or_create_collection(ad, **ek)
        bildir(
            f"[hafiza] '{ad}' bos oldugu icin yeni gomme modeliyle yeniden "
            "kuruldu; kayip yok."
        )

    if gomme is not None:
        kullanilan = getattr(col, "_embedding_function", None)
        if kullanilan is not None and kullanilan is not gomme:
            raise KoleksiyonCakismasi(
                f"'{ad}' istenen gomme modeliyle acilmadi "
                f"({type(kullanilan).__name__} kullaniliyor). Sessiz geri "
                "dusme: sorgular hata vermeden anlamsiz sonuc verirdi."
            )
    return col


class VectorMemory:
    def __init__(self, db_path="memory/chroma_db",
                 collection=VARSAYILAN_KOLEKSIYON, gomme=None, duyur=None):
        """
        ``gomme`` verilmezse **Turkce** model kullanilir. Varsayilan
        eskiden Chroma'nin ingilizce modeliydi; bu bir tercih degil,
        gozden kacmis bir varsayilandi -- kurulum uyarmaz, arama calisir,
        sayilar makul gorunur ve sonuclar kuradir.

        Bedeli odenen taraf: model yuklemesi ~13 sn (surec basina bir kez,
        `turkce_gomme()` onbellekler). Bu yuku tasiyan yollar -- bilgi
        karti onaylama, router, jarvis_brain -- canli sohbet dongusunde
        DEGILDIR; `main.py` -> `LocalJarvisAgent` bu depoyu acmaz.
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
        self._gomme = turkce_gomme() if gomme is None else gomme
        self._duyur = duyur
        self.col = self._koleksiyonu_ac()

    def _koleksiyonu_ac(self):
        return koleksiyon_ac(
            self.client, self.collection_name, self._gomme, self._duyur
        )

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
