import os
import pandas as pd
import PyPDF2

class DocumentAnalyst:
    def read_file(self, file_path):
        if not os.path.exists(file_path):
            return "Hata: Dosya bulunamadı efendim."
        
        ext = os.path.splitext(file_path)[1].lower()
        
        # 1. PDF Okuma
        if ext == ".pdf":
            text = ""
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages[:10]: # İlk 10 sayfa (Hız için)
                    text += page.extract_text()
            return f"--- PDF İÇERİĞİ ---\n{text[:2000]}"

        # 2. Excel veya CSV Analizi
        elif ext in [".xlsx", ".xls", ".csv"]:
            df = pd.read_csv(file_path) if ext == ".csv" else pd.read_excel(file_path)
            summary = f"Dosya Özeti: {len(df)} satır, {len(df.columns)} sütun bulundu.\n"
            summary += f"Sütun Başlıkları: {list(df.columns)}\n"
            summary += f"İlk 5 Satır:\n{df.head().to_string()}"
            return summary

        # 3. Metin Dosyaları
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                return f"--- DOSYA İÇERİĞİ ---\n{f.read()[:2000]}"