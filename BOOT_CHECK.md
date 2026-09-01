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

## 11. Auto Runner kisa test — PARK EDILMIS (ATLA)

> **DURUM: PARK EDILMIS.** `CLAUDE.md` §9 DEGISMEZ KURALLAR geregi AUTO
> cephesi kapalidir. Bu adim boot check'in **parcasi degildir** — atla.
> Bolum yalnizca tarihsel kayit ve kacak surec temizligi icin duruyor.
> Ayrintili gerekce: `README.md` §10.

~~TERMINALE YAZ:~~ (park edildi — calistirma)

    cd C:\Users\Ahmedov\Desktop\Jarvis\jarvis
    python auto_runner.py

Beklenen (tarihsel):

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
