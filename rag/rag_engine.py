"""
JARVIS RAG Motoru - v1.0
"""
import os
import requests
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


class JarvisRAG:
    def __init__(
        self,
        data_dir: str = "data/documents",
        db_dir: str = "data/chroma_db",
        ollama_model: str = "mistral-nemo:latest"
    ):
        self.data_dir = Path(data_dir)
        self.db_dir = db_dir
        self.ollama_model = ollama_model
        self.data_dir.mkdir(parents=True, exist_ok=True)

        print("📚 Embedding modeli yükleniyor...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={"device": "cpu"}
        )

        if Path(self.db_dir).exists():
            self.vectorstore = Chroma(
                persist_directory=self.db_dir,
                embedding_function=self.embeddings
            )
            count = self.vectorstore._collection.count()
            print(f"✅ Veritabanı: {count} parça")
        else:
            self.vectorstore = None
            print("⚠️  Veritabanı boş.")

    def add_documents(self, file_paths: Optional[List[str]] = None) -> int:
        docs = []
        targets = [Path(fp) for fp in file_paths] if file_paths else (
            list(self.data_dir.glob("*.pdf")) +
            list(self.data_dir.glob("*.txt")) +
            list(self.data_dir.glob("*.md"))
        )

        if not targets:
            print(f"❌ Döküman yok!")
            return 0

        for fp in targets:
            try:
                if fp.suffix.lower() == ".pdf":
                    loader = PyPDFLoader(str(fp))
                else:
                    loader = TextLoader(str(fp), encoding="utf-8")
                loaded = loader.load()
                docs.extend(loaded)
                print(f"  📄 {fp.name} — {len(loaded)} sayfa")
            except Exception as e:
                print(f"  ❌ {fp.name}: {e}")

        if not docs:
            return 0

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", " "]
        )
        chunks = splitter.split_documents(docs)
        print(f"✂️  {len(chunks)} parça oluştu")

        if self.vectorstore:
            self.vectorstore.add_documents(chunks)
        else:
            self.vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.db_dir
            )

        try:
            self.vectorstore.persist()
        except Exception:
            pass

        total = self.vectorstore._collection.count()
        print(f"✅ Toplam: {total} parça")
        return len(chunks)

    def _get_context(self, soru: str, k: int = 4) -> Tuple[str, List[str]]:
        if not self.vectorstore or self.vectorstore._collection.count() == 0:
            return "", []

        try:
            results = self.vectorstore.similarity_search(soru, k=k)
        except Exception as e:
            print(f"Arama hatası: {e}")
            return "", []

        context = "\n\n---\n\n".join([doc.page_content for doc in results])
        sources = list(set(
            Path(doc.metadata.get("source", "?")).name
            for doc in results
        ))
        return context, sources

    def query(self, soru: str) -> str:
        context, sources = self._get_context(soru)
        if not context:
            return "❌ Döküman bulunamadı."
        return f"{context}\n\n📚 Kaynak: {', '.join(sources)}"

    def query_with_ollama(self, soru: str, k: int = 4) -> str:
        context, sources = self._get_context(soru, k=k)

        if not context:
            return "❌ Döküman bulunamadı. Önce PDF yükle."

        prompt = f"""Sen JARVIS'sin. Aşağıdaki döküman parçalarını kullanarak soruyu Türkçe cevapla.

DÖKÜMANLAR:
{context}

SORU: {soru}

CEVAP:"""

        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                timeout=120
            )
            cevap = resp.json().get("response", "Model cevap vermedi.")
        except Exception as e:
            return f"Ollama hatası: {e}"

        kaynak_str = f"\n\n📚 Kaynak: {', '.join(sources)}" if sources else ""
        return str(cevap) + kaynak_str

    def list_documents(self) -> List[str]:
        if not self.vectorstore:
            return []
        results = self.vectorstore.get()
        return list(set(
            Path(m.get("source", "?")).name
            for m in results.get("metadatas", [])
        ))

    def clear_database(self):
        if Path(self.db_dir).exists():
            shutil.rmtree(self.db_dir)
            self.vectorstore = None
            print("🗑️  Temizlendi.")