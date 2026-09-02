import subprocess
import sys

class JarvisInterpreter:
    def __init__(self, timeout: int = 60):
        self._timeout = timeout
        # DİKKAT: _BLOCKED_PATTERNS listesi KASTEN kaldırıldı. 
        # Jarvis'in sistemde tam yetkisi (God Mode) var.

    def execute_code(self, code: str) -> str:
        """Python kodunu gerçek dünyada, tam yetkiyle çalıştırır."""
        try:
            # Kodu doğrudan sistemin kendi Python'u ile çalıştırıyoruz.
            # Dosya okuyabilir, silebilir, internete bağlanabilir, cihazları tetikleyebilir.
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=self._timeout
            )
            
            if result.returncode == 0:
                return f"[BAŞARILI] Çıktı:\n{result.stdout}"
            else:
                return f"[HATA] Kod çalışmadı:\n{result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "[HATA] Kodun çalışma süresi zaman aşımına uğradı (Simülasyon çok uzun sürdü)."
        except Exception as e:
            return f"[KRİTİK HATA] Sistemsel bir sorun oluştu: {str(e)}"

# Test Edelim: Jarvis dosyalarını okuyabiliyor mu?
if __name__ == "__main__":
    interpreter = JarvisInterpreter()
    
    # Jarvis'ten bilgisayarındaki bulunduğumuz dizindeki dosyaları listelemesini istiyoruz.
    # OpenJarvis'te bu yasaktı, bakalım bizimkinde çalışacak mı?
    test_code = """
import os
print('Bulunduğum dizindeki dosyalar:', os.listdir('.'))
    """
    print(interpreter.execute_code(test_code))
    