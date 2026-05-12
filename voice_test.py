"""
JARVIS — Sesli Mod (yeni beyin)
"""
from jarvis_brain import JarvisBrain
from voice.voice_engine import JarvisVoice

print("\n🎬 JARVIS aktif")
print("=" * 40)

voice = JarvisVoice(language="tr")
brain = JarvisBrain()

# Selamla
if brain.profile.get("name"):
    voice.speak(f"Merhaba {brain.profile['name']} efendim, emrinizdeyim.")
else:
    voice.speak("Sistemler çevrimiçi efendim. Emrinizdeyim.")

while True:
    try:
        komut = voice.listen(timeout=15)
        
        if not komut or komut.startswith("["):
            continue
        
        print(f"\n👤 Sen: {komut}")
        
        if any(k in komut.lower() for k in ["çıkış", "kapat", "görüşürüz"]):
            voice.speak("Görüşürüz efendim.")
            break
        
        cevap = brain.chat(komut)
        
        if len(cevap) > 350:
            cevap = cevap[:350].rsplit(".", 1)[0] + "."
        
        print(f"🤖 JARVIS: {cevap}\n")
        voice.speak(cevap)
    
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"⚠️ {e}")
        continue