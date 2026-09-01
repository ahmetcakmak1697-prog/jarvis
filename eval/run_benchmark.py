import json
from pathlib import Path
from datetime import datetime

def run_benchmark():
    """Benchmark testini çalıştır"""
    
    benchmark_file = Path("eval/benchmark_v1.txt")
    
    if not benchmark_file.exists():
        print("❌ benchmark_v1.txt bulunamadı!")
        return
    
    print("\n" + "="*80)
    print("🧪 JARVIS BENCHMARK TEST BAŞLANIYOR...")
    print("="*80 + "\n")
    
    # Test soruları (ilk 5)
    test_questions = [
        "1. B4C'nin Ehull değeri kaç meV/atom?",
        "2. Grafen'in band gap'i kaç eV?",
        "3. Ti3SiC2'nin yoğunluğu yaklaşık kaç g/cm³?",
        "4. c-BN'nin sertliği B4C'ye kıyasla ne kadar sert?",
        "5. Grafen+B4C hibrit'in Ehull'ü kaç meV olur?",
    ]
    
    scores = []
    
    for q in test_questions:
        print(f"\n{q}")
        try:
            score = int(input("Cevap doğrumu? (1-10): "))
            if 1 <= score <= 10:
                scores.append(score)
        except:
            print("Geçersiz giriş")
            pass
    
    # Sonuçları göster
    if scores:
        avg_score = sum(scores) / len(scores)
        accuracy = int(avg_score / 10 * 100)
        
        print("\n" + "="*80)
        print(f"✅ TEST TAMAMLANDI")
        print(f"Test sayısı: {len(scores)}")
        print(f"Ortalama Puan: {avg_score:.1f}/10")
        print(f"Doğruluk: {accuracy}%")
        print("="*80 + "\n")
        
        # Sonuçları dosyaya kaydet
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Benchmark Tarihi: {datetime.now()}\n")
            f.write(f"Test sayısı: {len(scores)}\n")
            f.write(f"Ortalama Puan: {avg_score:.1f}/10\n")
            f.write(f"Doğruluk: {accuracy}%\n\n")
            f.write(f"Detaylı Puanlar: {scores}\n")
        
        print(f"📊 Sonuçlar kaydedildi: logs/benchmark_*.txt")

if __name__ == "__main__":
    run_benchmark()