"""
JARVIS Sistem Kontrolü — PC'yi sesle yönet
"""
import os
import subprocess
import webbrowser
import re
from pathlib import Path


class SystemController:
    
    APPS = {
        "spotify": r"C:\Users\Ahmedov\AppData\Roaming\Spotify\Spotify.exe",
        "chrome": "chrome",
        "google chrome": "chrome",
        "edge": "msedge",
        "firefox": "firefox",
        "notepad": "notepad",
        "not defteri": "notepad",
        "hesap makinesi": "calc",
        "calculator": "calc",
        "vs code": "code",
        "visual studio code": "code",
        "discord": "discord",
        "steam": "steam",
        "whatsapp": "whatsapp",
        "telegram": "telegram",
        "explorer": "explorer",
        "dosya gezgini": "explorer",
    }
    
    WEBSITES = {
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "github": "https://github.com",
        "twitter": "https://twitter.com",
        "x_site": "https://x.com",
        "instagram": "https://instagram.com",
        "linkedin": "https://linkedin.com",
        "gmail": "https://gmail.com",
        "chatgpt": "https://chat.openai.com",
        "claude": "https://claude.ai",
        "spotify": "https://open.spotify.com",
    }
    
    def _find_app(self, name: str):
        """Windows'ta uygulama yolu bul"""
        paths = [
            Path.home() / "AppData/Roaming" / name / f"{name}.exe",
            Path.home() / "AppData/Local" / name / f"{name}.exe",
            Path.home() / "AppData/Local/Programs" / name / f"{name}.exe",
            Path("C:/Program Files") / name / f"{name}.exe",
            Path("C:/Program Files (x86)") / name / f"{name}.exe",
        ]
        for p in paths:
            if p.exists():
                return str(p)
        return None

    def open_app(self, app_name: str) -> str:
        app_name = app_name.lower().strip()
        cmd = self.APPS.get(app_name)
        
        if cmd:
            try:
                if Path(cmd).exists():
                    subprocess.Popen([cmd])
                else:
                    subprocess.Popen(cmd, shell=True)
                return f"{app_name.title()} açıldı efendim."
            except Exception as e:
                return f"Açılamadı efendim: {e}"
        
        # Otomatik bul
        path = self._find_app(app_name.title())
        if path:
            try:
                subprocess.Popen([path])
                return f"{app_name.title()} açıldı efendim."
            except Exception as e:
                return f"Bulundu ama açılamadı: {e}"
        
        return f"{app_name} uygulamasını bulamadım efendim."
    def open_website(self, site_name: str) -> str:
        """Web sitesi aç"""
        site_name = site_name.lower().strip()
        url = self.WEBSITES.get(site_name)
        if url:
            webbrowser.open(url)
            return f"{site_name.title()} açılıyor efendim."
        # Direkt URL verildiyse
        if "." in site_name:
            url = site_name if site_name.startswith("http") else f"https://{site_name}"
            webbrowser.open(url)
            return f"{site_name} açılıyor efendim."
        return f"{site_name} sitesini tanımıyorum efendim."
    
    def volume_up(self) -> str:
        for _ in range(5):
            subprocess.run(["powershell", "-Command",
                "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"],
                capture_output=True)
        return "Ses arttırıldı efendim."
    
    def volume_down(self) -> str:
        for _ in range(5):
            subprocess.run(["powershell", "-Command",
                "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"],
                capture_output=True)
        return "Ses azaltıldı efendim."
    
    def mute(self) -> str:
        subprocess.run(["powershell", "-Command",
            "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
            capture_output=True)
        return "Ses kapatıldı efendim."
    
    def lock_screen(self) -> str:
        subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
        return "Ekran kilitlendi efendim."
    
    def shutdown(self) -> str:
        subprocess.run("shutdown /s /t 30", shell=True)
        return "30 saniye sonra kapanacak efendim. İptal için 'iptal et' deyin."
    
    def cancel_shutdown(self) -> str:
        subprocess.run("shutdown /a", shell=True)
        return "Kapatma iptal edildi efendim."
    
    def find_file(self, filename: str) -> str:
        """Masaüstü ve İndirilenler'de dosya ara"""
        search_dirs = [
            Path.home() / "Desktop",
            Path.home() / "Downloads",
            Path.home() / "Documents",
        ]
        results = []
        for d in search_dirs:
            if d.exists():
                for f in d.rglob(f"*{filename}*"):
                    if f.is_file():
                        results.append(str(f))
                        if len(results) >= 5:
                            break
        if results:
            return f"Bulduğum dosyalar:\n" + "\n".join(results[:5])
        return f"'{filename}' içeren dosya bulamadım efendim."
    
    def open_file(self, filepath: str) -> str:
        """Dosya aç"""
        try:
            os.startfile(filepath)
            return "Dosya açıldı efendim."
        except Exception as e:
            return f"Açılamadı: {e}"
    
    def detect_command(self, text: str):
        """Sesli komuttan ne yapılacağını anla"""
        t = text.lower().strip()
        
        # Uygulama açma
        if any(k in t for k in ["aç", "başlat", "çalıştır"]):
            for app in self.APPS:
                if app in t:
                    return ("app", app)
            for site in self.WEBSITES:
                if site in t:
                    return ("web", site)
        
        # Ses
        if any(k in t for k in ["ses arttır", "ses aç", "sesi aç", "ses yükselt"]):
            return ("vol_up", None)
        if any(k in t for k in ["ses azalt", "ses kıs", "sesi kıs"]):
            return ("vol_down", None)
        if "ses kapat" in t or "sessize al" in t:
            return ("mute", None)
        
        # Ekran
        if "ekran kilit" in t or "kilit" in t:
            return ("lock", None)
        
        # Kapatma
        if "bilgisayarı kapat" in t or "pc kapat" in t:
            return ("shutdown", None)
        if "kapatmayı iptal" in t or "iptal et" in t:
            return ("cancel_shutdown", None)
        
        # Dosya bulma
        if "dosya bul" in t or "dosya ara" in t:
            # "şu dosyayı bul X" → X'i çıkar
            for kelime in ["dosya bul", "dosya ara"]:
                if kelime in t:
                    isim = t.split(kelime)[-1].strip()
                    if isim:
                        return ("find_file", isim)
        
        return None
    
    def execute(self, command_type, arg=None):
        """Komutu çalıştır"""
        if command_type == "app":
            return self.open_app(arg)
        elif command_type == "web":
            return self.open_website(arg)
        elif command_type == "vol_up":
            return self.volume_up()
        elif command_type == "vol_down":
            return self.volume_down()
        elif command_type == "mute":
            return self.mute()
        elif command_type == "lock":
            return self.lock_screen()
        elif command_type == "shutdown":
            return self.shutdown()
        elif command_type == "cancel_shutdown":
            return self.cancel_shutdown()
        elif command_type == "find_file":
            return self.find_file(arg)
        return None