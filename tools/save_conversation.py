import json
import sys
from pathlib import Path
from datetime import datetime

def get_input(prompt):
    """Python input() yerine güvenli input al"""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    return sys.stdin.readline().strip()

def save_conversation():
    """Konuşma kaydet - ERROR HANDLING ile"""
    
    conv_file = Path("memory/conversations.json")
    
    try:
        # JSON yükle
        if conv_file.exists():
            with open(conv_file, 'r', encoding='utf-8') as f:
                conversations = json.load(f)
        else:
            conversations = []
        
        print("\n" + "="*80)
        print("📝 JARVIS KONUŞMA KAYIT")
        print("="*80 + "\n")
        
        # 1. Soru
        user_text = get_input("🔹 Soru (User input): ")
        if not user_text:
            print("❌ Soru boş olamaz!")
            return
        
        # 2. Cevap
        print("\n(JARVIS cevabını yapıştır - Ctrl+V)\n")
        assistant_text = get_input("🔹 JARVIS cevabı: ")
        if not assistant_text:
            print("❌ Cevap boş olamaz!")
            return
        
        # 3. Puan
        while True:
            score_text = get_input("\n🔹 Puan (1-10): ")
            try:
                score = int(score_text)
                if 1 <= score <= 10:
                    break
                print("   ❌ 1-10 arasında yazmalısın!")
            except ValueError:
                print("   ❌ Sayı giriniz!")
        
        # 4. Kategori
        category = get_input("\n🔹 Kategori (materials_basics): ").strip() or "materials_basics"
        
        # 5. Feedback
        feedback = get_input("\n🔹 Feedback (boş bırakabilirsin): ").strip()
        
        # Yeni konuşma
        new_conv = {
            "id": f"conv_{len(conversations)+1:03d}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat() + "Z",
            "conversation": {
                "user": user_text,
                "assistant": assistant_text
            },
            "metadata": {
                "quality_score": score,
                "category": category,
                "language": "turkish",
                "feedback": feedback
            }
        }
        
        conversations.append(new_conv)
        
        # JSON'a yaz
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
        
        # Sonuç
        print("\n" + "="*80)
        print(f"✅ Konuşma #{len(conversations)} kaydedildi!")
        print(f"   Soru: {user_text[:60]}")
        print(f"   Puan: {score}/10")
        print(f"   Toplam konuşma: {len(conversations)}/20")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        print("Lütfen tekrar dene!")

if __name__ == "__main__":
    save_conversation()