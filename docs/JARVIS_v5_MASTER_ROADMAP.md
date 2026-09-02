JARVIS v5 — Mimari Anayasa ve Master Yol Haritası
Üç-zekâ sentezi · Sürüm 1.3 · Haziran 2026

Bu belge bir hayal listesi değil, bir inşaat planıdır. Her satırı, çalışan kod + test + commit disipliniyle doğrulanabilir hedeflere bağlıdır. Vizyon büyük; ama büyük vizyon ancak küçük, kanıtlı adımlarla ayakta kalır.


v1.2 Patch Notes (neler değişti)
Bu sürüm, v1.0'ın GPT + donanım/saha mimarı (Gemini) çapraz-kontrolünden ve web-doğrulamalı teknik araştırmadan geçmiş halidir. Eklenenler:

Reality Check — "✅" işaretleri git/test ile audit edilebilir kabul edilir (§3.0).
Bağımlılık İtirafı — "asla fişi çekilemez" → daha mühendisçe, savunulabilir ifade (§1.1).
Koşullu gizlilik — "verini hiçbir yere göndermez" → dış servis varsa politika+maskeleme+onay (§1.1).
D-serisi yasal sınır — yalnızca açık, login'siz, robots.txt-uyumlu kaynaklar (§5/D).
Memory Audit Log — her semantik kayıt için zorunlu meta-veri (§6, C1 kabul kriteri).
C1.6 Sentezleyici — episodik veri ham değil, sentezlenip kalıcılaşır (telemetri mantığı) (§6).
C2 alt-fazlara bölündü — C2.1–C2.5 (§5/C).
F2 async — Telegram callback zaman aşımı düzeltmesi (§5/F).
H-serisi Fail-Safe — donanım watchdog / ölü adam anahtarı (§5/H).

Web-doğrulamalı teknik dayanaklar §11'de.

v1.3 Temizlik Notları
Bu sürüm, v1.2'nin repo dokümanı olarak daha okunabilir ve denetlenebilir hale getirilmiş sürümüdür:

- Bozulan markdown tabloları düzeltildi.
- C1.6 konsolidasyon dili yumuşatıldı: tekil TTL anı yerine oturum/gün/episode bazlı konsolidasyon.
- E serisi ayrımı netleştirildi: ürünleştirme C'den sonra; izole STT/TTS/wake-word laboratuvar testleri serbest.
- H serisi "kusursuz" ifadesi mühendislik diliyle değiştirildi: stabil, testli, rollback mekanizmalı.
- §11 kaynak/referans listesi denetlenebilir başlıklar halinde netleştirildi.

0. Bu Belge Nasıl Okunmalı
Üç farklı yapay zekânın (mimari disiplin, genişlemeci vizyon, dengeleyici sentez) çapraz-kontrolünden süzülmüş ortak akıldır. Çelişen yerlerde en muhafazakâr, en test edilebilir yol seçilmiştir. Bu projenin bugünkü olgunluğu — çoğu hobi projesinin asla ulaşamadığı — tam olarak bu disiplin sayesinde mümkün oldu.

1. Kuzey Yıldızı: JARVIS Neden Farklı
1.1 Gerçek hendek (the moat)
Piyasada AutoGPT, OpenClaw, Manus, CrewAI türü ajan sistemleri var. Ortak zayıflıkları: bulut bağımlı, API bağımlı, abonelik bağımlı, kapatılabilir. Şirket fişi çekerse kullanıcının elinde hiçbir şey kalmaz.
JARVIS'in farkı: Egemen, yerel, sana ait bir zekâ.

RTX 3070'inin içinde yaşar — kimsenin sunucusunda değil.
Aylık abonelik istemez.
Seni tanır: ESHOT mesaini, Vulcan S servis tarihini, ÜPEM projeni.

Bağımlılık İtirafı (v1.2 — dürüst ifade). Eski sürümdeki "asla fişi çekilemez" cümlesi fazla iddialıydı. Doğrusu:

"Bulut sağlayıcı tarafından kapatılamaz. Donanım ve OS ayakta kaldığı sürece, temel yerel işlevleri internet olmadan da çalışır."

Çünkü sistem yine şunlara bağımlıdır: Windows ortamı, disk sağlığı, model dosyaları, Python bağımlılıkları. Dış servisler (Telegram, Tailscale, web araştırması, hava durumu) ise çekirdek değil, uzantıdır — koptuklarında çekirdek yaşar, sadece o özellik durur.
Koşullu gizlilik (v1.2). "Verini hiçbir yere göndermez" koşulsuz değildir. Doğrusu:

"Varsayılan olarak yerel çalışır. Dış servise (web araştırması, bulut model, Telegram) veri gidecekse; politika kontrolü, maskeleme ve kullanıcı onayı katmanından geçer."

Bu, kategori farkıdır — "daha iyi chatbot" değil. Bulut asistanları seni tanıyamaz; milyonlarca kullanıcıdan birisin. JARVIS yalnızca seni tanır çünkü yalnızca senin.
1.2 Film JARVIS'inin gerçek DNA'sı
Film JARVIS'ini JARVIS yapan şey GPT-seviyesi zekâ değil — Tony'yi tanımasıydı.

Sessiz yetkinlik. Heyecan yapmaz; iş zaten yapılmıştır.
Önce sonuç, sonra gerekçe. Teknik detayı istenmedikçe saklar.
Endişeli sadakat. Gerektiğinde uyarır, patronluk taslamaz.
Haklıyken itiraz. Son kararı sahibine bırakır.

Bu DNA, "içeride mühendislik, dışarıda JARVIS" mimarisinin ta kendisidir.

2. Mimari Anayasa — 10 Değişmez İlke

Overwrite yok, patch var. Byte-safe, idempotent, anchor-tabanlı, fail-loud, .bak, py_compile.
Tek faz, tek hedef. Faz büyürse alt-faza bölünür.
Test önce, özellik sonra. Eval/smoke geçmeden commit yok.
İçeride mühendislik, dışarıda JARVIS. Ham state korunur; kullanıcıya doğal dil.
Model adı kodda yazılmaz. ModelRegistry üzerinden (M0).
Donanım kararı benchmark ile verilir. placeholder gerçek modele geçmez.
Yeni ağır framework eklenmez. Kendi çekirdeği + gerektiği kadar bağımlılık.
Human-in-the-Loop. Sonuç doğuran hiçbir işlem onaysız yapılmaz.
Proaktiflik seyrek, önemli, yüksek eşiklidir. Sık uyarı = mute = ölü özellik.
Gizlilik tasarımdan gelir. Coarse konum, hassas veri proaktif kullanılmaz, veri yerel.


3. Dürüst Envanter — Şu An Neredeyiz
3.0 Reality Check (v1.2)

Aşağıdaki tablodaki tüm "✅" işaretleri git log + test dosyaları + çalışan endpoint ile doğrulanabilir (audit edilebilir) kabul edilir. Doğrulanamayan bir satır varsa "✅" değil "✅/doğrulanacak" işareti taşımalıdır. Anayasanın güvenilirliği bu kurala bağlıdır.

3.1 Tamamlanan katmanlar

| Seri | Ne | Durum |
|---|---|---|
| A | Güvenlik temeli, smoke suite, WS auth | ✅ |
| B1 / B2 / B2.7 | ProactiveCore, task sistemi (allowlist), Tailscale + Telegram | ✅ |
| P0 | M0 runtime profiles, engineering standards, backup | ✅ |
| D1 | Web policy, source scoring, candidate queue, audit | ✅ |
| D2.1–D2.4 | Telegram `/web`, policy eval (20/20), lifecycle, cache + rate limit (18/18) | ✅ |
| N1 | Persona few-shot prompt | ✅ |
| E1.1–E1.5C | Profil, proaktif briefing, koşullu uyarı, motosiklet/hava riski, canlı hava, `/brief` + `/brief_live`, JARVIS tonu, saat bağlamı | ✅ |
| C3 | Raporlama state, structured output guard, redaction, internal trace | ✅ |
| C4 | Internal trace logger | ✅ |
| H1.5 | Organ contract (JarvisOrgan adapter sözleşmesi) | ✅ |
| H1.6 | Repo hygiene guard | ✅ |
| M0 | World model foundation (home/rooms/people/devices/modes) | ✅ |
| M0.2 | Inventory model (tools/electronics/materials/safety) | ✅ |
| M0.3 | World–inventory linker (room_id join) | ✅ |
| M0.4 | Project workspace model (projects.json + ProjectWorkspaceStore) | ✅ |
3.2 Olgunluk — iki ölçek

Çalışan MVP açısından: ~%65–70.
"Dream JARVIS" (çok-modlu, sürekli öğrenen) açısından: ~%35–40.

3.3 Dürüst rakip kıyası
Genel ajan yeteneği ekseninde bulut araçları bugün daha olgun (~8/10); JARVIS ~6.5/10. Ama egemen, kişisel, offline-yetenekli asistan ekseninde — projenin asıl ekseni — rakipler bu kategoriye girmiyor bile. Hedef mimari tamamlandığında JARVIS bu eksende ~9.5/10 olur ve muadili olmayan ürüne dönüşür.

4. Merkezî Tez: Sürekli Kişisel Model

JARVIS'i film JARVIS'ine yaklaştıracak şey ses, avatar veya donanım değil — seni sürekli tanıyan, biriken bir kişisel modeldir.

Bugünkü engel "bilgi toplayamamak" değil; toplanan bilgiyi uzun vadeli anlamlandıramamak. Bu çözülmeden ses eklenirse felaket olur: sesli komut veri girişini 10x hızlandırır, ama hafıza politikası yoksa bağlam penceresi çöple dolar ve JARVIS aptallaşır. Sıralama tartışmasız: önce beyin (C serisi), sonra kaslar.

5. Katmanlı Yol Haritası
C — Hafıza & Öz-Bilgi        [SIRADAKİ · kritik yol]
D — Araştırma Derinliği (OSINT)
E — Ses & Doğal Etkileşim
F — Ajans (Human-in-the-Loop otonomi)
G — Model Zekâsı & Donanım
H — Fiziksel Dünya            [EN SON]
C — Hafıza & Öz-Bilgi (beyin)
Mevcut ChromaDB/RAG üstüne karar/politika katmanı. Yeni kütüphane yok.

C1 — Hafıza Politikası

C1.1 Episodik/Semantik ayrım + sınıflandırıcı (kural+LLM hibrit, salt-LLM değil — §11)
C1.2 Onay katmanı (kalıcı yazımdan önce onay; candidate queue genişletilir)
C1.3 Çöp toplayıcı (TTL dolan episodik veriyi otonom sil)
C1.4 Geri-getirme politikası (çok-sinyalli: semantik + anahtar-kelime + varlık eşleme, §11)
C1.5 Eval suite (BEAM kategorileri: tercih/talimat takibi, bilgi çıkarımı, bilgi güncelleme, çok-oturum, özetleme, zamansal akıl yürütme, olay sıralama, çekimserlik, çelişki çözümü — §11)
C1.6 Sentezleyici (v1.3 — telemetri mantığı): Episodik veri ham haliyle kalıcı hafızaya yazılmaz. Bunun yerine oturum kapanışı, gün sonu veya belirli episode sayısı sonrası konsolidasyon yapılır; JARVIS geçici verilerden kısa ve denetlenebilir sentezler çıkarır, yalnızca onaylanabilir sentez adaylarını kalıcı hafızaya taşır. (Örn: "Ahmet 2 Haziran'da fırtına nedeniyle motosiklet yerine alternatif ulaşım kullandı.") — ChromaDB şişmesini ve RAM darboğazını önler. Uyarı: naif özetleme bilgi kaybettirebilir; bu yüzden sentez dedup'lu, kaynaklı ve dikkatli olmalı (§11).


C2 — Proje Zekâsı (v1.2 — alt-fazlara bölündü)

C2.1 Proje kayıt şeması
C2.2 Aktif / bloke / bekliyor durumları
C2.3 "Sonraki adım" çıkarımı
C2.4 Proje özet endpoint'i
C2.5 Telegram /project veya /roadmap komutu


C3 — Raporlama & Sentez

Günlük/haftalık digest, "bu hafta ne öğrendim", akşam özeti (önce sorar)



D — Araştırma Derinliği (meşru OSINT)
D2 cache/rate-limit üstüne çok-kaynaklı derin araştırma.

D3 akademik makaleler, patentler, GitHub, StackOverflow, teknik forumlar, haber, resmi siteler
D4 çapraz doğrulama, kaynak güven skoru, atıf zorunluluğu
D5 araştırma→hafıza hattı (bulgular candidate olur, onayla semantiğe geçer)


D-serisi yasal sınır (v1.2): Login gerektiren, erişim izni olmayan, robots.txt/policy ihlali içeren veya güvenlik-atlatma gerektiren kaynaklar kapsam dışıdır. Yalnızca açık, izinli, login'siz kaynaklar.

E — Ses & Doğal Etkileşim (ürünleştirme C'den sonra)

Not: E serisinin ürünleştirilmesi C serisi tamamlanmadan başlamaz. Ancak STT/TTS/wake-word gibi izole laboratuvar testleri, ana dala bağlanmadan ve hafıza/context akışını kirletmeden yapılabilir.

E2 ses girişi (wake word "JARVIS" + STT)
E3 ses çıkışı (TTS + barge-in)
E4 sese özel briefing formatı (kısa, konuşma dili)

F — Ajans (Human-in-the-Loop otonomi)
Gemini'nin proaktif ajan vizyonu — doğru yapılmış hali. Otonom push değil; yüksek eşik + onay.

F1 — Arka plan gözcüsü (daemon): Saatte bir sessizce kontrol. Sadece state üretir. (Not: consolidation daemon'u (C1.6) da bu döngüye binebilir — §11.)
F2 — Telegram onay mekanizması (v1.2 — async zorunlu): Yalnızca gerçekten kritik olayda (fırtına, donanım çöküşü, olağandışı ağ) onay mesajı atar: [Onayla] / [Yoksay].

Zaman aşımı düzeltmesi (web-doğrulandı, §11): Telegram, butona basılınca answerCallbackQuery çağrılana kadar progress bar gösterir; 8GB VRAM'de ağır task çalışırken yanıt gecikirse kullanıcıda 5-15 sn takılı spinner / "hata" görünür. Çözüm: buton basılınca Python anında answerCallbackQuery ile "Görev alındı" döner, ağır işi mevcut task_queue.json + worker üzerinden arka planda (async) başlatır.


F3 — Güvenli aksiyon yürütme: Onaylanırsa mevcut task allowlist üzerinden çalışır. Allowlist dışına çıkmaz. Async kuyruk zorunlu.


F serisinin eşiği kasıtlı çok yüksektir. "CPU %80" push'a değmez; "disk %95, çökmek üzere" değer.

G — Model Zekâsı & Donanım

G1 model benchmark (Qwen vs mistral-nemo, Türkçe kalite)
G2 fine-tuning (Unsloth + QLoRA, veri birikince; 3070'de 3B)
G3 dual3090 geçişi (NVLink 48GB, 70B-Q4, vLLM) — benchmark sonrası

H — Fiziksel Dünya (EN SON — beyin oturmadan kas takılmaz)
C ve E stabil, testli ve rollback mekanizmalı çalışmadan kesinlikle girilmez. Yazılım hatası log'a düşer; yanlış röle komutu kışın kombiyi kapatır.

M5StickC Plus2 → varlık algılama (should_interrupt besler)
ESP32 röle → TOGGLE_RELAY task (allowlist, onaylı, async)
RTL-SDR / Flipper → güvenlik sinyali girdisi


Fiziksel Fail-Safe kuralı (v1.2 — web-doğrulandı, §11): Fiziksel dünyaya dokunan her donanım kendi Donanım Watchdog'unu barındırır. JARVIS'ten N dakika "hayattayım" sinyali (heartbeat) gelmezse, ESP32 kendi rölelerini otonom olarak güvenli duruma çeker. ESP32'nin donanımsal TWDT/IWDT'si bunu destekler; pattern: 60 sn heartbeat + 5 dk sinyal yoksa güvenli duruma geç. Bu, klasik "ölü adam anahtarı" fail-safe ilkesidir.


6. C1 Detay Planı (sıradaki faz)
Mevcut yapı taşları: tools/vector_memory.py, rag/rag_engine.py, rag/indexer.py, agents/memory_candidate_queue.py, agents/memory_scorer.py, agents/memory_policy.py. C1 bunları yeniden yazmaz — politika zırhıyla bağlar.
İki katmanlı hafıza modeli

| Katman | İçerik | Ömür | Depo |
|---|---|---|---|
| Episodik | "bugün hava", "şu an CPU", oturum bağlamı | TTL (örn. 6 saat) | geçici JSON |
| Semantik | Vulcan S servis tarihi, ÜPEM projesi, kararlar | kalıcı | ChromaDB |
Akış

Yeni bilgi → kural+LLM hibrit sınıflandırıcı: episodik mi, semantik mi, çöp mü?
Semantik adayı → onay katmanı (candidate queue genişletilir)
"Bunu hatırla" denirse → doğrudan yazılabilir
Episodik → oturum/gün/episode bazlı C1.6 konsolidasyonuna girer → yalnızca kaynaklı ve onaylanabilir sentez adayı kalıcılaşır
Çöp toplayıcı → TTL dolan ham episodik veriyi siler
Geri-getirme → çok-sinyalli (semantik+keyword+varlık), yalnızca alakalı bağlam çekilir

C1 kabul kriterleri

 Episodik veri TTL sonunda otomatik silinir
 Semantik yazım onaysız gerçekleşmez (C1.2)
 Hassas veri (tam adres, şifre) asla otomatik semantik olmaz
 Memory Audit Log (v1.2): her semantik kayıt zorunlu meta-veriyle tutulur:
[source, reason, confidence, approved_by, created_at, delete_id]
Neyi neden hatırladığımızı, hangi mesajdan çıkardığımızı, kimin onayladığını ve nasıl sileceğimizi bilmek zorundayız.
 Ham episodik veri kalıcıya yazılmaz; oturum/gün/episode bazlı sentez adayı üretilir (C1.6)
 Bağlam penceresi alakasız geçmişle şişmez (C1.4)
 test_c1_memory_policy.py yeşil; mevcut smoke suite hâlâ geçer (regression)


7. Kalıcı Standartlar
M0 runtime profile · eval/acceptance her faz · backup/DR (.env hariç) · byte-safe patch · schema_version her veri dosyasında · test izolasyonu (temp root) · T1 Türkçe kalite hattı · checkpoint + commit her fazda.

8. Risk Kaydı

| Risk | Etki | Önlem |
|---|---|---|
| Aşırı proaktiflik | Mute, ölü özellik | Yüksek eşik (İlke 9) |
| Framework şişmesi | Kontrol kaybı | Yeni framework yok (İlke 7) |
| Hafızasız sese geçiş | Context çöpü | C serisi ürünleşmeden E serisi ürünleştirilmez |
| Erken fiziksel dünya | Gerçek dünya hasarı | H en son + watchdog + rollback |
| Naif konsolidasyon | Bilgi kaybı, yanlış kalıcı hafıza | C1.6 dedup'lu, kaynaklı ve onaylanabilir sentez |
| Salt-LLM hafıza çıkarımı | Maliyet, olasılıksal hata, biriken hata | Kural+LLM hibrit (§11) |
| Telegram callback timeout | Takılı spinner, kötü UX | F2 async (§11) |
| Donanım fazla iddialı | Boşa para | Benchmark zorunlu (İlke 6) |
| Hassas veri sızıntısı | Gizlilik ihlali | Coarse konum, maskeleme, audit log |
| Context window taşması | Yavaş, kalitesiz cevap | C1.4 çok-sinyalli geri-getirme |
| Tek geliştirici yorgunluğu | Proje durması | Küçük fazlar, her commit değerli |

9. İlerleme Metrikleri
Hafıza isabeti (C1.5/BEAM) · unutma isabeti · sıfır-sızıntı (%100 hedef) · proaktif hassasiyet (mute oranı düşük) · bağlam verimliliği (token sayısı) · offline yetenek yüzdesi · regression sağlığı (her commit smoke yeşil).

10. Sıradaki Somut Adım

E1.5C commit'ini kilitle, working tree temiz.
Bu belgeyi (v1.3) commit'le: Reality Check doğrulaması sonrası `docs/JARVIS_v5_MASTER_ROADMAP.md`.
C1 keşfi: tools/vector_memory.py + rag/rag_engine.py (veya indexer.py) gerçek hallerini incele. C1 bunların üstüne politika; ne olduklarını bilmeden tasarım çıkmaz.
C1.1 ile başla: kural+LLM hibrit episodik/semantik sınıflandırıcı. Küçük, test edilebilir, byte-safe.
Her alt-faz: keşif → tasarım → byte-safe patch → test → checkpoint → commit.


11. Web-Doğrulamalı Teknik Dayanaklar ve Referanslar (v1.3)

Bu bölümdeki kaynaklar, roadmap kararlarını gerekçelendirmek için tutulur. Uygulama sırasında nihai karar yine repo testleri, benchmark ve güvenlik ilkeleriyle verilir.

### 11.1 Telegram callback / async onay akışı

- Referans: Telegram Bot API — `CallbackQuery` ve `answerCallbackQuery`
- Referans: python-telegram-bot dokümantasyonu — `CallbackQuery.answer()`
- Mimari sonuç: Butona basılır basılmaz hızlı cevap verilir; ağır iş mevcut `task_queue.json` + worker üzerinden arka planda yürütülür.

### 11.2 Hafıza konsolidasyonu / uzun dönem hafıza

- Referans: Mem0 — production-ready long-term memory architecture
- Referans: Letta / MemGPT — agent memory and state management
- Referans: LoCoMo / BEAM türü uzun dönem hafıza benchmark yaklaşımları
- Mimari sonuç: Ham geçmiş kalıcı hafızaya boca edilmez. Kural+LLM hibrit sınıflandırma, audit log, dedup ve oturum/gün/episode bazlı konsolidasyon kullanılır.

### 11.3 ESP32 watchdog / ölü adam anahtarı

- Referans: Espressif ESP-IDF — Task Watchdog Timer (TWDT), Interrupt Watchdog Timer (IWDT)
- Mimari sonuç: Fiziksel dünyaya dokunan her cihaz heartbeat + güvenli duruma dönüş mantığı taşır. JARVIS susarsa cihaz güvenli moda geçer.

### 11.4 Denetim notu

Bu referans listesi kaynak başlıklarını sabitler. Linkler ve kesin sayısal iddialar, ilgili faza girildiğinde tekrar web-doğrulanır ve faz dokümanına işlenir. Roadmap içinde doğrulanmamış sayısal iddia kalıcı karar sayılmaz.

Kapanış
JARVIS artık "basit bot" değil. Test edilebilir geliştirme disiplini, güvenli temel, kontrollü web araştırması, kişisel profil, proaktif state, canlı hava + motosiklet riski ve saat bağlamlı JARVIS tonu olan çalışan bir kişisel asistan çekirdeği.
Önündeki en kritik eşik ses değil, donanım değil, avatar değil. Hafıza. C serisi oturduğunda, JARVIS "güzel bir dashboard" olmaktan çıkıp "Ahmet'in dijital ikinci beyni" seviyesine geçer.

İçeride mühendislik. Dışarıda JARVIS. Yerel, egemen, sana ait.

— Üç zekânın sentezi: vizyon (Gemini) + denge (GPT) + disiplin (Claude), web-doğrulamalı.