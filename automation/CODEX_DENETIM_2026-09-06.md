**JARVIS — Başmühendis teknik denetimi**

**Ahmet ve Claude için • 6 Eylül 2026 • Kaynak kod, güvenlik, hafıza ve ürün hedefi**

**Karar:** Mevcut sistem geliştirmeye değer bir temel taşıyor; fakat güvenli ve tutarlı bir kişisel asistan olduğunu henüz söyleyemeyiz. En önemli engel, aynı repoda bulunan güvenlik ve hafıza bileşenlerinin günlük kullanılan giriş yollarında aynı şekilde uygulanmaması. Yeni bulut veya cihaz yetkilerinden önce aşağıdaki erişilebilir kusurlar ele alınmalı. Bu bir düzeltme onayı veya yeni yol haritası değildir.

İnceleme dalı `auto/opencode-deepseek`. Başlangıç HEAD `1dbaf71`, son karşılaştırılan HEAD `211edf5`. İnceleme sırasında başka bir oturum anayasayı işaretçiye dönüştüren commit'i yaptı ve envanter dosyaları oluşturdu. İki commit arasında burada denetlenen uygulama/test dosyalarında fark bulunmadı. Başka oturumun dosyaları değiştirilmedi. Bu rapor repo dışında, ayrı çıktı olarak üretildi.

**Kanıtın gücü**

“Doğrulandı” ifadesi kaynak kodu ve belirtilen sahte bağımlılıklı deneyi anlatır. İnternete açık bir saldırı, gerçek kullanıcı verisi sızıntısı veya bilgisayarın ele geçirilmesi gösterilmedi. Model, mikrofon, hoparlör ve ev cihazları canlı çalıştırılmadı. Testlerde dotenv yüklemesini devre dışı bırakan `PYTHON_DOTENV_DISABLED=1` kullanıldı; gerçek gizli dosyalar incelenmedi.

| Kontrol | Bu incelemedeki sonuç | Anlamı |
|---|---|---|
| `pytest tests -q` | 1706 geçti, 2 toplama uyarısı; 57,07 saniye | Mevcut otomatik sözleşmeler geçiyor |
| Test dosyaları ters alfabetik sıra | 1706 geçti, aynı 2 uyarı; 61,42 saniye | Mevcut süitte sıra kaynaklı başarısızlık görülmedi |
| `ruff check .` | 293 bulgu, çıkış kodu 1 | Lint temiz değil; kayıtlı borçla aynı |
| Son eşzamanlı değişikliklerden sonra Ruff | 293 bulgu | Bu ölçümde sayı değişmedi |
| Yeni güvenlik/davranış deneyleri | Aşağıdaki somut kusurlar doğrulandı | Testlerin geçmesi bu davranışların güvenli olduğunu kanıtlamıyor |

İki uyarı, `test_e1_3_proactive_alerts.py` ve `test_e1_5B_2_system_health_threshold.py` içindeki kuruculu `TestCore` sınıflarının pytest tarafından test sınıfı olarak toplanmamasıyla ilgili. Tek başına bunları test kaybı diye yorumlamıyorum.

**Gerçekte hangi yol çalışıyor?**

| Giriş | Kodda izlenen yol | Kritik ayrım |
|---|---|---|
| `main.py local` | VoiceIO → LocalJarvisAgent → doğrudan araçlar / Ollama / erken PDF dalı | AssistantExecutor kapılarından geçmiyor |
| `gui.py` ve masaüstü arayüzü | Flask → LocalJarvisAgent | Yerel ajanın araç yüzeyini HTTP üzerinden erişilebilir yapıyor |
| `main.py claude` | JarvisAgent → Anthropic ve TOOL_DEFINITIONS | Ayrı uygulama; şu anda MemoryManager import'u bozuk |
| Telegram'ın soru bileşimi | AssistantExecutor → LocalFirstRouter → ExecutionPolicy | Diğer yollarda eksik kalan politika bileşenleri burada bulunuyor |

Kanıt: [yerel giriş](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/main.py:89), [API girişi](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/main.py:250), [Telegram bileşimi](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tools/telegram_agent.py:1356), [yerel yolun kaskada uğramadığını zaten belgeleyen test](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tests/test_local_agent_wiring.py:1). Telegram'ın çalıştığını veya yeniden açılması gerektiğini iddia etmiyorum. Bu tablo çağrı ilişkisini gösterir.

**B01 — Yüksek: hesap makinesi matematik sınırını aşabiliyor**

[calculate](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tools/tools.py:498) kullanıcı ifadesini `eval` ile değerlendiriyor. `__builtins__={}` güvenlik yalıtımı sağlamıyor. Nesne niteliklerinden Python'un yükleyicisine ulaşan zararsız bir ifade, yerleşik `sum([20,22])` işlevini çağırıp **42** döndürdü. Gerçek dosya veya süreç erişimi denenmedi.

Bu araç yerel ajana yükleniyor ve `hesapla/calculate` tetikleyicisinden doğrudan çağrılıyor: [araç seçimi](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:364). Önceden `run_python_code` aracının yerel sözlükten çıkarılmış olması bu ikinci yolu kapatmıyor. Aynı HTTP arayüzüne erişebilen biri için B02 ile birleşen etkisi çok daha yüksek.

**En küçük düzeltme yönü:** yalnız desteklenen sayısal ifadelerin, açıkça izinli matematik çağrılarının ve sınırlı işlem büyüklüğünün değerlendirilmesi. Repo içindeki mevcut güvenli hesaplayıcı seçenekleri önce incelenmeli; yeni bağımlılık kararı bu raporda verilmedi. **Kabul testi:** normal hesaplar doğru; nitelik erişimi, nesne dolaşımı, comprehension ve izin dışı çağrılar etkisiz biçimde reddediliyor. [Python eval açıklaması](https://docs.python.org/3/library/functions.html#eval).

**B02 — Koşullu kritik: web arayüzü kimlik doğrulamasız, tüm ağ arayüzlerine bağlanıyor**

[gui.py /chat](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/gui.py:364) kimlik doğrulamadan `agent.chat(message)` çağırıyor; [sunucu başlatma](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/gui.py:427) `0.0.0.0:5000` kullanıyor. Flask test istemcisinde, hiçbir kimlik bilgisi olmadan yapılan istek **200** aldı ve sahte ajan çalıştı. Not okuma/yazma uçlarında da uygulama içi yetki denetimi görünmüyor.

**Koşul:** bu arayüz başlatılmış olmalı ve saldırgan ağ üzerinden erişebilmeli. Firewall, yönlendirici ve gerçek dış erişim doğrulanmadı; port sorgusu açık bir 5000 dinleyicisi göstermedi, fakat bundan genel bir “ağ güvenli” sonucu çıkarılamaz. Masaüstü uygulamasının 5001 portu ise kaynakta `127.0.0.1` kullanıyor; iki arayüzü karıştırmamak gerekir.

**Düzeltme yönü:** yalnız bu PC hedefi için varsayılan erişim yüzeyini daraltmak; uzaktan kullanım ayrıca onaylanırsa açık kimlik/yetki sınırı kurmak. **Kabul testi:** yetkisiz istek araç çağırmıyor; istemci/sunucu gerçek başlatma ayarları da denetleniyor. Yalnız test istemcisinin geçmesi ağ bağlama ayarını doğrulamaz.

**B03 — Yüksek: “yerel kal” ve hassas veri politikası yerel web aracına uygulanmıyor**

[yerel araç algılama](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:364) içinde “Internete cikma, son haberler nedir?” girdisi **web_search** seçti. İkinci sentetik girdide `parola=FAKE_MARKER` arama sorgusunda aynen kaldı. [web_search](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tools/tools.py:179) aldığı sorguyu doğrudan arama sağlayıcısına iletiyor.

Deney yalnız araç seçimini ve argümanı yakaladı; gerçek sorgu gönderilmedi. Kaynak kodunda bu iki nokta arasında WebResearchPolicy, RedactionGuard veya kullanıcıya ait yerel-kal durumu yok. Dolayısıyla “Ollama kullanıyoruz” ifadesi tek başına dışarı veri çıkmadığı anlamına gelmiyor.

**Düzeltme yönü:** egress öncesi mevcut politika bileşenlerini bu yola uygulamak; açık kullanıcı yasağını anahtar kelime eşleşmesinden önce işletmek. **Kabul testi:** yerel-kal isteğinde sahte ağ çağrısı sayısı sıfır; hassas sorguda da sıfır; izinli genel sorgu beklenen temiz içerikle çalışıyor.

**B04 — Yüksek: hassas hafıza politikası sohbet veritabanında delinmiş; temizleme kalıcı geçmişi geri getirebiliyor**

[sohbet sonu kayıt](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:520) 10 karakterden uzun mesajı ve model cevabını [JarvisMemory.add_conversation](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/memory/memory_manager.py:72) üzerinden sınıflandırmadan SQLite'a yazıyor. Buna karşılık [LifeGraph hassas olgu davranışı](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/memory/life_graph.py:116) hassas olguyu saklamadığını bildiriyor. Bu ikinci koruma, ilk depodaki ham konuşmayı engellemiyor.

Yalnız RAM içinde tutulan SQLite deneyinde sentetik özel işaret içeren konuşma kaydedildi. `clear_history()` sonrası RAM geçmişi **0** oldu, veritabanında **1** konuşma kaldı ve işaret [get_context_for_prompt](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/memory/memory_manager.py:136) ile yeniden prompt'a girdi. [clear_history](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:535) yalnız RAM listesini ve sayaçları sıfırlıyor.

Ayrı bir doğruluk sorunu: LifeGraph `target="review_queue"` döndürüyor, fakat [main.py'deki çağıran](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/main.py:211) yalnız “incelemeye alındı” yazıyor. Bu yolda gerçek bir kuyruğa ekleme yok; “kuyruğa gönderildi” ile “gönderilmesi gerekiyor” birbirine karışmış.

**Düzeltme yönü:** kalıcı konuşma, doğrulanmış olgu ve onay bekleyen adayı açık saklama kurallarıyla ayırmak; temizle/unut davranışını kullanıcıya doğru ifade etmek ve bütün ilgili depolarda uygulamak. **Kabul testi:** sentetik hassas değer yasaklı kalıcı depoya girmiyor; unutma sonrası yeni tur ve yeni ajan oturumunda geri çağrılmıyor; kuyruğa alındı mesajı ancak kuyruk kaydı gerçekten oluşunca veriliyor. Onay kuyruğunun kendi saklama/gizlilik kuralı ayrıca açık olmalı.

**B05 — Yüksek, TTS açıkken: ses çıkışı veri sınıfını denetlemiyor**

[VoiceIO.say](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/voice/voice_loop.py:125) metni biçimsel temizleyip [EdgeTTSAdapter.speak](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/scripts/j0_tts_adapters.py:442) işlevine veriyor. Adaptör yalnız açma bayrağı ve boş metni kontrol ediyor; içerik sınıfını bilmiyor. Bayrak açık, sentezleyici sahte iken `parola=FAKE_AUDIT_MARKER` metni aynen sentezleyiciye ulaştı.

Varsayılan kapalı olması olumlu bir koruma; genel açma izni ise her hassas içeriğin dışarı gönderilmesine izin vermekle aynı şey değil. Edge TTS çevrimiçi bir servistir. [Projenin kendi açıklaması](https://github.com/rany2/edge-tts).

**Düzeltme yönü:** mevcut sınıflandırma ve kullanıcı egress tercihini TTS öncesinde de uygulamak; izin verilmeyen içeriği ekranda tutmak. **Kabul testi:** genel metin seslendirilir; hassas/yerel-kal bağlamında sahte bulut sentez çağrısı sıfırdır. Piper cephesini yeniden açmak bu düzeltmenin önkoşulu değildir.

**B06 — Yüksek: “güncel proje durumu” oturum içinde bayatlıyor**

[kurucu](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:140) proje bağlamını bir kez oluşturuyor; [chat içinde kullanım](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:473) aynı metni tekrar kullanıyor. Deneyde yeni bağlam üreticisi “STATE_AFTER” döndürecek şekilde hazırlandı; bir sohbet turunda üretici **0 kez** çağrıldı ve modele “STATE_BEFORE” gönderildi.

Üstelik [bağlam yükleyici](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:175) git log, HUMAN_NEEDED, roadmap ve tarihsel bir T1 sonucunu okuyor; çalışma sırası, AHMET_ONAYI_BEKLEYENLER, git status ve BLACKBOX bu bileşimde yok. Bu PC'deki ilk git komutunda sahiplik uyuşmazlığı da gözlendi. Yükleyicinin git hatasını sessiz atlaması durumu daha eksik gösterebilir; global git güven ayarı değiştirilmedi.

**Düzeltme yönü:** durum sorusunda talep anında doğrulanmış, kaynak zamanı belli bir görünüm üretmek. Her tur tüm belgeleri prompt'a doldurmak gerekmez. BLACKBOX'ın son kaydı tarihsel Piper cephesine ait olduğundan, sırf “son satır” diye aktif iş kabul edilmemeli. **Kabul testi:** ajan açıkken kaynak değişince sonraki durum yanıtı değişiyor; git okunamazsa eksiklik belirtiliyor; park edilmiş iş sıradaki görev diye sunulmuyor.

**B07 — Yüksek: genel bir analiz cümlesi izinsiz PDF seçme ve ayrı model yoluna sapıyor**

[erken PDF dalı](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:443) “pdf, dosya, makale, oku, analiz, incele, bak, indir” alt dizilerinden birini görünce normal sohbeti bırakıyor. “Bu kodun mantigini analiz et” deneyi, sahte bağımlılıklarda **en yeni PDF'yi bul → RAG kur → belgeleri indeksle → RAG sorgula** sırasını çalıştırdı. Normal ajan çağrısı **0** oldu.

[etkin find_and_load_pdf tanımı](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tools/tools.py:918) belirtilmiş dosyayı çözmek yerine Desktop/Downloads ve çalışma dizinindeki en yeni PDF'yi seçiyor. [JarvisRAG](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/rag/rag_engine.py:17) kendi sabit `mistral-nemo:latest` varsayılanını kullanıyor; normal ModelRegistry, persona, ses yönergesi ve sohbet geçmişi bu dalda atlanıyor. Her girişte `add_documents()` bütün hedefleri tekrar ekleyebilir; bu yolda içerik kimliğiyle tekilleştirme görünmüyor.

**Düzeltme yönü:** genel analiz isteğini dosya işlemi saymamak; yalnız açık dosya isteğinde belirtilen hedefi kullanmak ve ortak model/politika yolunu korumak. **Kabul testi:** dosyasız analiz PDF aramaz; belirtilen A dosyası varken daha yeni B dosyası seçilmez; aynı belge tekrar yüklendiğinde parça sayısı gereksiz büyümez.

**B08 — Yüksek işlev hatası: API modu tanımlı olmayan bir hafıza sınıfını içe aktarıyor**

[API ajanı import'u](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/jarvis_agent.py:32) `MemoryManager` istiyor; [hafıza modülü](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/memory/memory_manager.py:14) yalnız `JarvisMemory` tanımlıyor. Gerçek import satırı tek başına, hiçbir API/config yüklemeden yürütüldüğünde **ImportError** verdi.

Bu nedenle “API bağlı, sadece frontier kapısı açılacak” ifadesi bütün girişler için doğru değil. Ana mod seçicisi de yerel zorlaması yoksa API anahtarı varlığında Claude yolunu seçiyor: [mod seçimi](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/main.py:25). Gerçek anahtar varlığı araştırılmadı.

**Düzeltme yönü:** bu eski giriş yolunun desteklenip desteklenmeyeceğini mevcut karara göre netleştirmek; desteklenecekse hafıza arayüz sözleşmesini birlikte doğrulamak. Sadece sınıf adını değiştirmek yeterli olduğu varsayılmamalı. **Kabul testi:** config ve sağlayıcı sahteyken ana API girişinin import/kurulum/tek tur yolu çalışıyor.

**B09 — API yolu açılmadan giderilmeli: TLS, dosya ve shell sınırları**

[API istemcisi](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/jarvis_agent.py:84) `httpx.Client(verify=False)` kullanıyor. HTTPX bunun sertifika doğrulamasını tamamen kaldırdığını açıkça belgeliyor. [HTTPX SSL](https://www.python-httpx.org/advanced/ssl/). Web içerik indirmede de [fetch_webpage](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tools/tools.py:219) ve araştırma dalında doğrulama kapalı.

[read_file / write_file](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tools/tools.py:91) mutlak yolları ve proje dışına çıkan göreli yolları sınırlamıyor. Sahte Path ile proje dışı hedef, herhangi bir onay olmadan yazma işlevine ulaştı. [git_diff](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tools/tools.py:158) argümanı shell komutuna birleştiriyor; sahte çalıştırıcı `git diff main.py & echo AUDIT_MARKER` komut metnini aldı. Gerçek shell çalıştırılmadı. [_run](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/tools/tools.py:52) `shell=True` kullanıyor; terminal aracındaki onay bu dolaylı yolu korumuyor. `run_python_code` API araç listesinde de mevcut ve aynı süreçte `exec` kullanıyor.

**Sınır:** B08 nedeniyle API ajanındaki bu yüzeyin bugün başarıyla çalıştığı gösterilmedi. Import düzeltilirken bu riskler etkinleşebilir; “şu anda API üzerinden ele geçirilebilir” hükmü verilmemeli.

**Kabul testi:** sertifika hatası reddedilir; mutlak/proje dışı yollar, junction/symlink kaçışları ve gizli dosyalar engellenir; shell ayraçları komut olamaz; kalıcı yazma açık yetki sınırına bağlıdır. Harici içeriğin model talimatına dönüşebilmesi nedeniyle sınır prompt'ta değil yürütme kodunda uygulanmalı. [OWASP prompt injection rehberi](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

**B10 — Orta/yüksek: dış çağrı bütçesi yerel cevapları da kesebiliyor**

[router bütçe denetimi](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agents/local_first_router.py:109) cache/hafıza cevabı bulamadığında, çalıştırıcının yerel mi bulut mu olacağı belirlenmeden `external_call` bütçesi tüketiyor. [ExecutionPolicy](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agents/execution_policy.py:40) varsayılanında aynı karar Ollama'ya gidiyor.

Bir çağrılık sahte ledger deneyinde ilk kararın gerçek hedefi **local** oldu; ikinci yerel soru **external_blocked** aldı. Bulut kullanılmadan dış çağrı bütçesi yerel sohbeti kapatabiliyor. Bu bulgu AssistantExecutor yoluna ait; main.py yerel dalının mevcut davranışı diye sunulmamalı.

Ayrıca [CostLedger](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agents/cost_ledger.py:25) para veya token değil çağrı sayıyor. “50 çağrı” bir aylık dolar tavanı değildir. Router redaction hatasını da `except: pass` ile geçiriyor; hata enjekte edildiğinde `ask_external` döndü. Bu son deney aşağıdaki API gizlilik denetimlerinin de aşıldığını kanıtlamaz.

**Düzeltme yönü:** bütçeyi gerçek egress noktasında tüketmek; bütçe yokken yerel yanıt yolunu açık tutmak; guard arızasında dışarı çıkışı kapatmak. **Kabul testi:** yerel çağrı bütçeyi tüketmez; dış çağrı bir kez tüketir; bütçe tükenmesi yerel yanıtı engellemez; guard arızasında dış çağrı sıfırdır.

**B11 — Ölçüm açığı: kalite takımı günlük ajanı ölçmüyor; TTFT etiketi yanlış**

[kalite koşucusu](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/eval/run_turkish_quality.py:345) doğrudan `/api/generate` çağırıyor: temperature **0,2**, genellikle **400** çıktı token'ı ve 4 uzun vaka için **1200**. [günlük yerel ajan](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:423) ise `chat`, temperature **0,72**, **1024** çıktı token'ı, ek yönergeler, proje bağlamı, geçmiş ve araçlarla çalışıyor. Dolayısıyla 49/64 sonucu, bu günlük bileşimin başarı oranı değildir. Model kıyası için değeri var; uçtan uca güvence olarak kullanılamaz.

Koşucu `first_token_ms` alanını `prompt_eval_duration` değerinden üretiyor ve `stream=False` kullanıyor. Ollama bu alanı prompt değerlendirme süresi diye tanımlar; kullanıcıya ilk token ulaşma zamanı diye tanımlamaz. [Ollama Generate API](https://docs.ollama.com/api/generate). Kayıtlı 30,5 ms ve 420,8 ms değerleri ölçüldükleri anlamda korunmalı; gerçek istemci TTFT diye adlandırılmamalı.

[yerel model kıyas raporu](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/automation/MODEL_KIYASI_TURKCE_2026-09-05.md:1) llama/Gemma/Turkcell için 49/54/46 puanı kaydediyor; bunlar bu incelemede yeniden koşturulmadı. Gemma'nın 7076 MB tepe kullanımı, projenin 6144 MB çalışma bütçesini aşar; tek başına 8 GB fiziksel belleğe sığmadığını veya CPU offload oluştuğunu kanıtlamaz.

**Kabul testi:** model kıyası korunur, gerçek ajan bileşimi için ayrı senaryo ölçümü eklenir; gerçek TTFT ilk içerik parçası alınırken ölçülür; bilinmeyen ölçüme 0 veya farklı süre türü yazılmaz. Prompt/üretim ayarları raporda izlenir.

**B12 — Ürün hedefi açığı: ses hattı tüm yanıtı ve tüm sentezi bekliyor**

[Ollama çağrısı](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/agent/local_agent.py:423) streaming kapalı. [ana döngü](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/main.py:201) önce `agent.chat` tamamlanmasını bekliyor, sonra seslendiriyor. [Edge sentezi](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/scripts/j0_tts_adapters.py:480) MP3 dosyasının oluşmasını bekliyor; oynatıcı da ses bitene kadar blokluyor. Bu sırada ana döngü yeni mikrofon girdisi almıyor. Doğal “dur” ile konuşmayı kesme burada kurulmuş değil.

Böyle bir boruda hızlı token üretimi tek başına 1,5 saniye hedefini garanti etmez. Soğuk/sıcak başlangıç, konuşma sonu algılama, STT, model, sentez ve ilk duyulan ses ayrı ölçülmeli. Bu incelemede gerçek uçtan uca gecikme ölçülmedi.

**Düzeltme yönü:** önce gerçek zaman çizelgesini ölçmek; PUSULA durum sorusunu mümkün olduğunca doğrulanmış veriden kısa üretmek; gerekli olduğunda ilk cümle üzerinden ses akışı ve kullanıcı kesmesi kurmak. **Kabul testi:** ses bitişi → ilk duyulan ses için açık başlangıç/bitiş tanımıyla p50/p95 raporu; ayrı iptal senaryosu. 1,5 saniyenin hangi istatistik için kabul sınırı olduğu Ahmet'in ürün kararıdır.

**Daha küçük ama gerçek bakım açıkları**

- [otomatik isim çıkarımı](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/memory/memory_manager.py:175) “ben ” sonrasındaki ilk kelimeyi isim sayabiliyor; “ben bugün…” gibi bir ifade yanlış profil oluşturabilir. Kullanıcı alıntısı ile kendisine ait doğrulanmış olgu ayrılmıyor.
- [geçici ses dosyası](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/scripts/j0_tts_adapters.py:480) için bu akışta silme/finally adımı görünmüyor. İşletim sisteminin temizlemesine kadar sesli içerik diskte kalabilir; kalıcılık süresi ölçülmedi.
- [GUI istatistikleri](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/gui.py:382) `agent.memory.count()` çağırıyor; JarvisMemory'de bu metot yok. Ana arayüzden bağımsız bir bileşen testi bunu yakalamalı.
- Proje durumu belgeleri kısmen eski: roadmap üst `updated` alanı 2026-06-18, 14 üst adımdan 13'ü done; çalışma sırası belgesi hâlâ karar bekleyen başlıklar taşıyor. Bunlar bütün alt kararların güncel olmadığı sonucunu tek başına vermez; ancak yanıt üretirken tarih ve kapsam ayırımı gerektirir.

**JARVIS hedefine göre önerilen karar sırası**

Bu sıra mevcut çalışma planını otomatik değiştirmez. Somut güvenlik kanıtları nedeniyle Ahmet'e önerilen öncelik değişikliğidir. Her kart ayrı onay ve kapanış gerektirir.

| Öncelik | Dar iş paketi | Başarı kanıtı |
|---|---|---|
| 1 | B01 hesaplayıcı sınırı; GUI kullanılıyorsa B02 erişim sınırı ayrı kart | Kısıt dışı ifade/istek hiçbir yetkili işlem yapamıyor |
| 2 | B03 ve B05: kullanıcı yerel-kal tercihi ve içerik politikası bütün egress yollarında | Web ve TTS dahil yasaklı çağrı sayısı sıfır |
| 3 | B04: gerçek saklama, unutma ve onay kuyruğu davranışı | Sonraki tur ve yeniden başlatmada silinen içerik geri gelmiyor |
| 4 | B06 ve B07: doğru iş seçimi ve canlı repo bağlamı | Gerçekçi 10–20 kullanıcı senaryosu doğru yola gidiyor |
| 5 | B11 ve B12: günlük ajan kalitesi ve ilk ses ölçümü | Model testi ile ürün testi ayrılmış; gecikme gerçekten ölçülmüş |
| 6 | B08–B10: API giriş sözleşmesi ve bütçe/egress kusurları | Fake sağlayıcılı tüm giriş testleri; gerçek bulut ayrıca insan onaylı |
| 7 | Mevcut sıraya göre onaylı frontier ve daha sonra HA/ESPHome yüzeyleri | Ortak davranış ve güvenlik sözleşmeleri her yeni yüzeyde geçiyor |

Claude için ilk dar kart önerim **“Yerel calculate aracında matematik dışı Python değerlendirmesini kapat”**. Test kapsamı araç sözlüğüne bakmakla bitmemeli; LocalJarvisAgent'tan gerçek hesaplayıcıya kadar gelen girdi sınanmalı. Kaynak değişmeden önce hatayı üreten test, sonra küçük patch, tam süit iki sıra ve lint borcu kontrolü gerekir. Bütün sistemi yeniden yazmayı önermiyorum.

Filmdeki hissi sağlayacak özellikler: doğru bağlamı hatırlama, kısa ve isabetli Türkçe, konuşurken durdurabilme, kaynaklı proje bilgisi ve bir işlemi gerçekten yaptıysa bunu doğru bildirme. Aynı yanlış davranışı beş odaya taşımak bu hedefi yaklaştırmaz. Bellek düzeltme/silme, oturum izolasyonu, dosyanın hangi kaynaktan geldiğinin taşınması ve eylem sonucunun doğrulanması; yeni kişilik prompt'larından daha doğrudan ürün değeri sağlar. Bunlar bu raporda özellik uygulaması olarak başlatılmadı.

**Mevcut kararları koruyan iki stratejik not**

Home Assistant'ı bu PC'de çalıştırma kararı korunabilir. Ancak “Windows uygulaması” ifadesi kurulumu yeterince tarif etmiyor: resmî Windows kılavuzu HAOS için sanal makine yolunu belgeliyor. Ağ, USB geçişi, kaynak ayırma ve yeniden başlama davranışı donanım entegrasyonu kartında açık olmalı. Yeni bir sunucu veya yeni ürün önermiyorum. [Home Assistant Windows kurulumu](https://www.home-assistant.io/installation/windows/).

Yedekleme riski çalışma sırası belgesinde açıkça kayıtlı: ilk push büyük geçmiş nesneleri nedeniyle reddedilmiş ve eski bundle'a dayanılıyor. Bu PC dışında doğrulanmış güncel bir kurtarma kopyasının varlığı bu incelemede kontrol edilmedi. “Kesin yedek yok” diyemem; bir kurtarma denemesiyle doğrulanmış yedek kanıtı gereklidir. Geçmiş yeniden yazımı veya push yapılmadı. [mevcut karar ve yedek engeli](C:/Users/Ahmedov/Desktop/Jarvis/jarvis-agent-auto/docs/strategy/CALISMA_SIRASI_KARARI.md:1).

**Yöntem, kaynaklar ve sınırlar**

Önce Graphify mevcut grafiği sorgulandı; sorgular ana giriş, LocalJarvisAgent, JarvisMemory, EdgeTTSAdapter, hesaplayıcı, router, redaction ve bütçe bağlantılarını daralttı. Grafikteki bağlantılar canlı kaynak dosyalarından tekrar doğrulandı. Wiki indeks dosyası bulunmadı. `update_plan` aracı bu oturumda mevcut değildi; kapsam → kaynak keşfi → karşı deney → sentez → çıktı doğrulama sırası izlendi. Alt ajanlar kullanım sınırı nedeniyle sonuç üretemedi; rapordaki inceleme ve deneyleri ana ajan yaptı.

Dış araştırma yalnız burada kullanılan teknik iddialar için Python, HTTPX, Ollama, OWASP, Edge TTS projesi ve Home Assistant'ın kendi belgeleriyle sınırlandı. Erişim tarihi 6 Eylül 2026; dokümanlar yaşayan kaynaklardır. Yeni model/repo keşfi, fiyat tavsiyesi, CVE veri tabanı taraması veya bütün bağımlılıkların güvenlik denetimi yapılmadı.

Mevcut model kıyas raporları tarihsel yerel kanıttır; içlerindeki bütün donanım ve üçüncü taraf benchmark iddiaları bağımsız yeniden doğrulanmadı. 49/64'ten genel zekâ yüzdesi veya “JARVIS yüzde kaç bitti” sayısı üretilemez. Gerçek ağ sızma testi, oturum kimliği sınaması, HA cihaz kontrolü, güç kesintisi/geri yükleme deneyi ve mikrofon performans ölçümü bu denetimin dışında kaldı.

Araştırma; başlıca çağrı yolları kaynakla açıklanınca, yüksek etkili iddialar zararsız deney veya doğrudan kod kanıtıyla desteklenince ve kalan belirsizlikler açıkça sınırlanınca durduruldu. Kod düzeltilmedi, uygulama yayımlanmadı, commit/push yapılmadı. Bulgular açık durumdadır.
