cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis

Compress-Archive -Path .\README.md, .\BOOT_CHECK.md -DestinationPath .\jarvis_checkpoint_B1_6_before_docs_update.zip -Force
Test-Path .\jarvis_checkpoint_B1_6_before_docs_update.zip

$readme = @'
# JARVIS v5 - Operation Overmind

JARVIS v5; lokal calisan, web paneli olan, hafiza kullanan ve proaktif durum servisi bulunan kisisel AI asistan projesidir.

Bu sistem B1 hattindan sonra daha stabil hale getirildi:

- Guvenli login ve session sistemi
- WebSocket auth korumasi
- ProactiveCore merkezi durum servisi
- Gercek sistem durumu: CPU, RAM, disk, GPU, VRAM, sicaklik
- Gercek guvenlik durumu: hatali girisler, aktif session, bloklu IP
- Gercek task snapshot: bekleyen, calisan, tamamlanan, hatali gorevler
- Dashboard kartlari ProactiveCore verisine baglandi
- Auto Runner onarildi
- Smoke test paketi eklendi

---

## 1. Yeni terminal acinca ilk komut

Her yeni PowerShell veya VS Code Terminal acildiginda once proje klasorune girilir.

TERMINALE YAZ:

    cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis

---

## 2. Server baslatma

JARVIS web panelini acmak icin server baslatilir.

TERMINALE YAZ:

    python jarvis_server.py

Beklenen cikti:

    JARVIS v5 - OPERATION OVERMIND
    PC: http://localhost:8000
    WiFi: http://192.168.1.4:8000

---

## 3. Paneli acma

Server calisirken panel tarayicidan acilir.

TARAYICIYA YAZ:

    http://localhost:8000

Ayni WiFi agindaki baska cihazdan acmak icin:

    http://192.168.1.4:8000

Not: Login icin dogrudan /login adresine gitme. Ana panel adresini ac, sifreyi panelden gir.

---

## 4. Health kontrolu

Server gercekten ayakta mi diye kontrol etmek icin /healthz endpointi kullanilir.

TERMINALE YAZ:

    Invoke-RestMethod -Uri http://127.0.0.1:8000/healthz

Beklenen cikti:

    ok      : True
    service : jarvis
    server  : online
    auth    : enabled
    version : v5

---

## 5. Smoke test

Sistemin temel parcalari bozulmus mu diye smoke test calistirilir.

TERMINALE YAZ:

    python .\tests\run_smoke_suite.py

Beklenen sonuc:

    A5 smoke OK
    Efendim, temel sistem butunlugu dogrulandi.

---

## 6. Proactive status

Proactive status, JARVIS panelinin merkezi durum verisidir.

Bu veri su bloklari icerir:

    briefing
    weather
    music
    security
    system
    suggestion
    tasks

Once panele giris yap:

TARAYICIYA YAZ:

    http://localhost:8000

Sonra proactive status ac:

TARAYICIYA YAZ:

    http://localhost:8000/api/proactive-status

Not: Bu URL PowerShell'e duz yazilmaz. Tarayiciya yazilir.

---

## 7. Sistem durumu testi

CPU, RAM, disk, GPU, VRAM ve sicaklik verisi bu testle okunur.

TERMINALE YAZ:

    python -c "from tools.system_intelligence import get_system_status, get_health_score; import json; s=get_system_status(); h=get_health_score(s); print(json.dumps({'system':s,'health':h}, ensure_ascii=False, indent=2))"

Beklenen alanlar:

    cpu_percent
    ram
    disk
    gpu
    health

---

## 8. Guvenlik durumu testi

Login denemeleri, aktif session ve bloklu IP bilgileri bu testle okunur.

TERMINALE YAZ:

    python .\tools\security_snapshot.py

Beklenen alanlar:

    level
    shield
    failed_login_24h
    failed_login_total
    blocked_ips
    active_sessions
    line

---

## 9. Task durumu testi

Gorev kuyrugu ve gecmis gorevler bu testle okunur.

TERMINALE YAZ:

    python .\tools\task_snapshot.py

Beklenen alanlar:

    pending
    running
    completed
    failed
    recent
    line

---

## 10. Auto Runner

Auto Runner, JARVIS'in arka planda uzun sureli calismasi icin kullanilir.

TERMINALE YAZ:

    cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis
    python auto_runner.py

Beklenen cikti:

    JARVIS Auto Runner baslatildi.
    Server zaten calisiyor. Yeni instance baslatilmadi.
    Auto Runner aktif. Durdurmak icin Ctrl+C.

Kapatmak icin terminale tikla ve Ctrl+C yap.

Kapanmazsa auto_runner processini bul:

    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*auto_runner.py*" } | Select-Object ProcessId, CommandLine

PID ile kapat:

    taskkill /PID PID_NUMARASI /F

---

## 11. Port kontrolu

Port 8000 dolu mu diye bakilir.

TERMINALE YAZ:

    netstat -ano | findstr :8000

Eger LISTENING gorunuyorsa server calisiyordur.

Kapatmak icin:

    taskkill /PID PID_NUMARASI /F

---

## 12. Sik yapilan hata: URL'yi terminale yazmak

Yanlis:

    http://localhost:8000/api/proactive-status

Bu PowerShell komutu degildir.

Dogru kullanim:

TARAYICIYA YAZ:

    http://localhost:8000/api/proactive-status

veya health kontrolu icin:

TERMINALE YAZ:

    Invoke-RestMethod -Uri http://127.0.0.1:8000/healthz

---

## 13. Git ve checkpoint akisi

Her kritik degisiklikten sonra smoke test calistir:

    python .\tests\run_smoke_suite.py

Sonra git durumunu kontrol et:

    git status --short

Degisen dosyalari ekle:

    git add DOSYA_ADI

Commit al:

    git commit -m "Aciklayici commit mesaji"

Checkpoint al:

    Compress-Archive -Path .\agents, .\tools, .\tests, .\jarvis_server.py, .\jarvis_brain.py -DestinationPath .\jarvis_checkpoint_ornek.zip -Force
    Test-Path .\jarvis_checkpoint_ornek.zip

True donerse checkpoint alinmistir.

---

## 14. B1 durum ozeti

    B1.1   ProactiveCore state builder                    OK
    B1.2   /api/proactive-status endpoint                 OK
    B1.3   Dashboard kartlarini ProactiveCore'a baglama    OK
    B1.4.1 Gercek system status                           OK
    B1.4.2 Gercek security snapshot                       OK
    B1.4.3 Gercek task snapshot                           OK
    B1.4.4 Auto Runner repair                             OK
    B1.5   Patch dosyalarini dev_patches altina arsivleme OK
    B1.6   README / BOOT_CHECK dokumantasyonu             OK

---

## 15. Onemli notlar

    .env dosyasi git'e alinmaz.
    memory/ klasoru runtime verisidir.
    logs/ klasoru runtime log verisidir.
    .venv/ klasoru git'e alinmaz.
    checkpoint zip dosyalari git'e alinmaz.
    dev_patches/ eski patch scriptlerinin arsividir.

Yeni terminal acinca ilk komut:

    cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis
'@

$boot = @'
# JARVIS v5 - Boot Check

Bu dosya JARVIS'i acmadan once veya sorun oldugunda uygulanacak hizli kontrol listesidir.

---

## 1. Proje klasorune gir

TERMINALE YAZ:

    cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis

---

## 2. Port 8000 bos mu?

TERMINALE YAZ:

    netstat -ano | findstr :8000

Cikti yoksa port bostur.

LISTENING varsa PID numarasini kapat:

    taskkill /PID PID_NUMARASI /F

---

## 3. Server baslat

TERMINALE YAZ:

    python jarvis_server.py

Beklenen:

    JARVIS v5 - OPERATION OVERMIND
    PC: http://localhost:8000
    WiFi: http://192.168.1.4:8000

---

## 4. Health kontrolu

Yeni terminal ac.

TERMINALE YAZ:

    cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis
    Invoke-RestMethod -Uri http://127.0.0.1:8000/healthz

Beklenen:

    ok      : True
    service : jarvis
    server  : online
    auth    : enabled
    version : v5

---

## 5. Login kontrolu

TARAYICIYA YAZ:

    http://localhost:8000

Sifre gir. Panel aciliyorsa login calisiyor.

Sifreyi yenilemek icin:

    python setup_password.py

---

## 6. Proactive status kontrolu

Once panelden login ol.

TARAYICIYA YAZ:

    http://localhost:8000

Sonra:

    http://localhost:8000/api/proactive-status

JSON icinde su alanlar gorulmeli:

    briefing
    security
    system
    suggestion
    tasks

---

## 7. Sistem snapshot kontrolu

TERMINALE YAZ:

    python -c "from tools.system_intelligence import get_system_status, get_health_score; import json; s=get_system_status(); h=get_health_score(s); print(json.dumps({'system':s,'health':h}, ensure_ascii=False, indent=2))"

Beklenen alanlar:

    cpu_percent
    ram
    disk
    gpu
    health

---

## 8. Security snapshot kontrolu

TERMINALE YAZ:

    python .\tools\security_snapshot.py

Beklenen alanlar:

    level
    shield
    failed_login_24h
    failed_login_total
    blocked_ips
    active_sessions
    line

---

## 9. Task snapshot kontrolu

TERMINALE YAZ:

    python .\tools\task_snapshot.py

Beklenen alanlar:

    pending
    running
    completed
    failed
    recent
    line

---

## 10. Smoke suite

TERMINALE YAZ:

    python .\tests\run_smoke_suite.py

Beklenen:

    A5 smoke OK
    Efendim, temel sistem butunlugu dogrulandi.

---

## 11. Auto Runner kisa test

TERMINALE YAZ:

    cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis
    python auto_runner.py

Beklenen:

    JARVIS Auto Runner baslatildi.
    Server zaten calisiyor. Yeni instance baslatilmadi.
    Auto Runner aktif. Durdurmak icin Ctrl+C.

Kapatmak icin terminale tikla ve Ctrl+C yap.

Kapanmazsa process bul:

    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*auto_runner.py*" } | Select-Object ProcessId, CommandLine

PID ile kapat:

    taskkill /PID PID_NUMARASI /F

---

## 12. Sik hatalar

URL'yi PowerShell'e duz yazma.

Yanlis:

    http://localhost:8000/api/proactive-status

Dogru:

    Invoke-RestMethod -Uri http://localhost:8000/healthz

veya tarayiciya yaz:

    http://localhost:8000/api/proactive-status

---

## 13. Port dolu hatasi

Hata:

    [Errno 10048] address already in use

Cozum:

    netstat -ano | findstr :8000
    taskkill /PID PID_NUMARASI /F

---

## 14. Oturum gerekli hatasi

Hata:

    {"ok": false, "error": "Oturum gerekli."}

Cozum:

    Once http://localhost:8000 uzerinden login ol.
    Sonra API endpointini tarayicida ac.

---

## 15. B1 sonrasi saglam durum

    B1.1   ProactiveCore state builder                  OK
    B1.2   Proactive status API                         OK
    B1.3   Dashboard binding                            OK
    B1.4.1 Real system status                           OK
    B1.4.2 Real security snapshot                       OK
    B1.4.3 Real task snapshot                           OK
    B1.4.4 Auto Runner repair                           OK
    B1.5   Patch archive cleanup                        OK

Ana test:

    python .\tests\run_smoke_suite.py
'@

Set-Content -Encoding UTF8 .\README.md $readme
Set-Content -Encoding UTF8 .\BOOT_CHECK.md $boot

Write-Host "README.md ve BOOT_CHECK.md temiz yazildi."
Get-Content .\README.md -TotalCount 20
Get-Content .\BOOT_CHECK.md -TotalCount 20