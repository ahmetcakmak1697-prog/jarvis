import pytesseract
from PIL import Image
import os

class VisionAnalyst:
    def __init__(self):
        # Tesseract yolunu belirtmemiz gerekebilir (Windows için gerekliyse)
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass

    def analyze_image(self, image_path):
        if not os.path.exists(image_path):
            return "Hata: Görsel dosyası bulunamadı efendim."
        
        try:
            # 1. Resimdeki yazıları sömür (OCR)
            img = Image.open(image_path)
            extracted_text = pytesseract.image_to_string(img, lang='tur+eng')
            
            # 2. Sonucu raporla
            if not extracted_text.strip():
                return "Görseli inceledim ama içerisinde okunabilir bir metin bulamadım."
            
            return f"--- GÖRSEL ANALİZ RAPORU ---\nİçerik:\n{extracted_text}"
        except Exception as e:
            return f"Görsel analiz hatası: {str(e)}"