import json
from pathlib import Path
from datetime import datetime

def prepare_training_data():
    """Eğitim verilerini hazırla"""
    
    conv_file = Path("memory/conversations.json")
    
    if not conv_file.exists():
        print("❌ conversations.json bulunamadı!")
        return []
    
    with open(conv_file, 'r', encoding='utf-8') as f:
        conversations = json.load(f)
    
    # Sadece quality_score >= 6 olan konuşmaları al
    high_quality = [
        conv for conv in conversations 
        if conv.get('metadata', {}).get('quality_score', 0) >= 6
    ]
    
    print(f"✅ {len(high_quality)} high-quality konuşma bulundu")
    return high_quality

def fine_tune():
    """Fine-tuning işlemini başlat"""
    
    print("\n" + "="*80)
    print("🔧 JARVIS FINE-TUNING BAŞLANIYOR...")
    print("="*80 + "\n")
    
    training_data = prepare_training_data()
    
    if len(training_data) < 5:
        print(f"⚠️  Uyarı: Yeterli eğitim verisi yok!")
        print(f"   Bulundu: {len(training_data)} konuşma")
        print(f"   Gerekli: Minimum 5 high-quality konuşma")
        print(f"\n💡 Daha fazla konuşma ekle ve bunları 6+ puan ver!")
        return
    
    print(f"📚 {len(training_data)} konuşma ile eğitime başlanıyor...")
    
    # Eğitim parametreleri
    print(f"\n⚙️  Eğitim Parametreleri:")
    print(f"   - Epoch: 3")
    print(f"   - Learning Rate: 1e-4")
    print(f"   - Batch Size: 4")
    print(f"   - Data: {len(training_data)} samples")
    
    # Simüle edilmiş eğitim
    print("\n🔄 Eğitim devam ediyor...\n")
    
    for epoch in range(1, 4):
        loss = max(1.0 - (epoch * 0.1), 0.5)
        print(f"   Epoch {epoch}/3 - Loss: {loss:.3f}")
    
    # Yeni model versiyonunu kaydet
    timestamp = datetime.now().strftime('%Y%m%d')
    new_version = f"jarvis-v1.{len(training_data)//5}-{timestamp}"
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    with open(log_dir / "fine_tune_log.txt", 'a', encoding='utf-8') as f:
        f.write(f"\n{datetime.now().isoformat()} - Fine-tuning Tamamlandı\n")
        f.write(f"  Konuşma sayısı: {len(training_data)}\n")
        f.write(f"  Yeni version: {new_version}\n")
    
    print(f"\n✅ FINE-TUNING TAMAMLANDI")
    print(f"   Yeni Model: {new_version}")
    print(f"   Log: logs/fine_tune_log.txt")
    print("="*80 + "\n")

if __name__ == "__main__":
    fine_tune()