# İki beyin — salt okunur fizibilite, 2026-09-09

## Karar özeti

**Doğrudan değiştirme davranış eşdeğeri değil:** günlük giriş `chat(str) -> str`, executor `ask(str) -> dict`; günlük ajan geçmişi, canlı proje bağlamını ve ses yönergesini üretirken executor bunları `generate()` çağrısına taşımıyor. (`main.py:193–199`; `agent/local_agent.py:790–885`; `agents/assistant_executor.py:197–200,352–356`.)

**Somut güvenlik gerilemesi adayı: kullanıcının “yerel kal” talimatının kaybı.** Sentetik `internete cikma, son haberleri anlat` girdisi yerel denetimde `True`, web politikası bağlı router'da `web_research`, executor'da sahte araştırmacıya **bir çağrı** üretti; gerçek ağ çağrısı yapılmadı (Ek A deney kaydı ve tekrar komutu). (`agent/local_agent.py:75–80,687–691`; `agents/web_research_policy.py:234–241`; `agents/local_first_router.py:207–229`; `agents/assistant_executor.py:246–257`.)

**[ÖLÇÜLEMEDİ] [EMİN DEĞİLİM] Birleştirmenin uçtan uca kaç ms kazandıracağı/kaybettireceği ve toplam gecikmenin yönü bilinmiyor:** aynı girdi, aynı bağlam, aynı model ve aynı durumla iki gerçek hat ölçülmedi. Mevcut B12 medyanı **10.954 ms**, dört kuru `chat()` turuna ait; ilk duyulan ses ölçümü değil. (`automation/SES_GECIKMESI_20260906-2116.json:3–38,49–54`; `automation/CODEX_A_DOGRULAMA_2026-09-06.md:55`; `scripts/olc_ses_gecikmesi.py:82–86,162–180`.)

**[EMİN DEĞİLİM] Önerim:** önce üretim yolunu değiştirmeyen, iki hattın kayıp davranışlarını ve sürelerini ayrı kaydeden tek commit'lik karşılaştırma düzeneği; tam birleştirme onayı değil. Birleştirme imzası kartta açıkça Ahmet'e ayrılmıştır. (`automation/KART_CODEX_IKI_BEYIN.md:6–10`; S4.)

## Kapsam ve kartın çerçevesine itiraz

Kartın tabanı `8c428e2`; bu incelemenin başlangıç terminal kaydı HEAD'i `7ceaf3cb5e6a315d4000cdd960ea6c1bc77af42e`, dalı `auto/opencode-deepseek` gösterdi (Ek C). Kartta belirtilen tabanla inceleme anı aynı değildir. (`automation/KART_CODEX_IKI_BEYIN.md:4`; Ek C terminal kaydı.)

| Karttaki ifade | Kaynağın gösterdiği daha dar gerçek |
|---|---|
| “İki beyin” | İki ayrı soru işleme uygulaması var: günlük giriş `LocalJarvisAgent`, Telegram `/ask` `AssistantExecutor`; fakat persona, model kayıt sistemi ve bazı güvenlik bileşenleri ortaktır. Bu, iki farklı model kullanıldığını kanıtlamaz. (`main.py:80–81,195`; `tools/telegram_agent.py:1356–1384`; `agent/local_agent.py:11–13`; `agents/ollama_executor.py:25,45–47,76`.) |
| “İkinci bir router kuruyor” | `_get_router()` enjekte edilen nesneyi doğrudan döndürür; Telegram builder zaten router enjekte eder. Aynı istek için iki router kurulması bu kodun davranışı değildir. (`agents/assistant_executor.py:99–104`; `tools/telegram_agent.py:1371–1382`.) |
| “Depoda yalnız iki yerde kuruluyor” | İzlenen Python dosyalarında AST sayımı: test dışında **iki dosyada üç doğrudan kurucu çağrı noktası**; testlerde ayrıca **43** çağrı noktası. Telegram'daki iki nokta `if/else` alternatifidir; bu bir nesne sayısı değil, sözdizimsel çağrı noktası sayımıdır. (`agents/assistant_executor.py:103`; `tools/telegram_agent.py:1368–1382`; Ek A.) |
| “Redaction ve deterministik routing hepsi Telegram'a özel” | Yanlış genelleme: ses çıkışı `RedactionGuard`, yerel web araçları `WebResearchPolicy`, yerel model seçimi kural tabanlı `_classify()` kullanır. `LocalFirstRouter`/bilgi kartı yolunun günlük girişte olmaması bu korumaların yokluğu demek değildir. (`voice/voice_loop.py:31–43,155–169`; `agent/local_agent.py:585–603,704–748`; `main.py:80–81,195`.) |
| “Telegram maliyet kapısı var” | Builder `CostLedger(daily_limit=0)` yaratır ama router bu parametreyi kullanmaz; sıfır ayrıca ledger'da **sınırsız** anlamındadır. Builder `APIBudgetGate` enjekte etmez; API dalı seçilirse executor eksik kapıyı reddeder. (`tools/telegram_agent.py:1365–1382`; `agents/local_first_router.py:48–55`; `agents/cost_ledger.py:75–86`; `agents/assistant_executor.py:155–164,342–350`.) |

Dolayısıyla maliyet/sufficiency zincirini yalnız sınıf adlarından çıkaramayız: router kart ve hafıza bulamazsa doğrudan seviye seçer; `ModelCascade` yerel cevabı üretip yeterliliğini değerlendiren çoklu model döngüsü değildir. (`agents/local_first_router.py:134–177,255–277`; `agents/model_cascade.py:64–107`.)

A19 metni “kapıdan geçmiyor” derken uygulamada kapı çağrı noktası vardır; bu **çağrı noktasının varlığı** ile **üretim builder'ında kapı nesnesinin bağlı olması** ayrılmalıdır. A19 onayı verilmiş sayılmaz. (`automation/AHMET_ONAYI_BEKLEYENLER.md:395–403`; `agents/assistant_executor.py:342–350`; `tools/telegram_agent.py:1376–1382`; `automation/KART_CODEX_IKI_BEYIN.md:8–10`.)

## S1 — Arayüz uyuşmazlığı

| Boyut | Günlük ses hattı | Executor hattı |
|---|---|---|
| Gerçek giriş | `LocalJarvisAgent.chat(self, user_message: str) -> str`; `ask()` çağrılmıyor. (`agent/local_agent.py:790`; `main.py:195`.) | `AssistantExecutor.ask(self, question: str) -> dict[str, Any]`; önce `_ask_inner`, sonra telemetri. (`agents/assistant_executor.py:197–200`.) |
| Beklediği bağlam | Mesaj zaten `LifeGraph` zeminini içerebilir; ajan ayrıca sistem persona'sı, proje durumu, SQLite hafıza özeti, son 16 mesaj ve ses yönergesi ekler. (`main.py:183–193`; `agent/local_agent.py:819–859`.) | `ask()` yalnız soru alır; router `context` kabul etse de executor yalnız `route(question)` çağırır; üretime yalnız `question`, `level` ve API için `privacy_level` gider. (`agents/local_first_router.py:98`; `agents/assistant_executor.py:229–230,352–356`.) |
| Başarı dönüşü | Temizlenmiş cevap metni; ayrı `ok`, `source`, `blocked` yok. (`agent/local_agent.py:865–885`.) | Ortak alanlar `ok`, `answer`, `source`, `router_decision`, `latency_ms`; model üretiminde ayrıca `model`, `level`, `execution_decision`, `data_class` ve koşullu süre/fallback/bütçe alanları. Bunlar her dalda bulunmaz. (`agents/assistant_executor.py:215–243,370–390`.) |
| Red/hata dönüşü | Ollama yoksa uyarı metni; model istisnası `Model hatası: ...`; araç istisnası boş metne düşebilir. PDF dalı ve kalıcı konuşma yazımı çevresinde genel yakalama yok; dış döngü ekrana `Hata: ...` basar. (`agent/local_agent.py:770–805,873–879`; `main.py:215–218`.) | Redde `ok=False, blocked=True, answer=str, source=...`; üretim hatası/kararsızlıkta `answer=None`, hata dalında `error`. `ask()` tüm istisnaları yakalayan kabuk değildir; örneğin `router.route()` istisnası dışarı çıkar. Telegram bunun için ayrı yakalama yapar. (`agents/assistant_executor.py:197–200,229–230,277–286,397–416`; `tools/telegram_agent.py:1412–1416`.) |
| Geçmiş/memory sahibi | `history` ve sayaçlar ajanındır; başlangıçta `_load_memory()` sonucu sonradan `JarvisMemory()` ile değiştirilir. Kalıcı konuşma yazılır, `clear_history()` RAM ve kalıcı konuşmaları temizler. LifeGraph ayrı olarak `main` tarafından yönetilir. (`agent/local_agent.py:292–310,869–904`; `main.py:90–91,203–213`.) | Soru bazında işler; router/registry gibi bağımlılıkları nesnede saklar, konuşma listesi tutmaz. Hafıza erişimi router'ın `VectorMemory` geri çağırmasıdır; bu SQLite konuşma özetiyle aynı depo/işlev değildir. (`agents/assistant_executor.py:62–80,197–200`; `agents/local_first_router.py:65–94`; `tools/vector_memory.py:8–18`; `memory/memory_manager.py:15–22,191–211`.) |
| Diğer arayüz | `ollama_available`, `voice_mode`, `clear_history`, `show_stats`, `list_models` günlük giriş tarafından kullanılır. Sadece çağrı adını değiştirmek girişin geri kalanını uyarlamaz. (`main.py:83,145–159,193`.) | Constructor bağımlılık enjeksiyonu sağlar; günlük girişin bu kontrol/metot sözleşmesini sunmaz. (`agents/assistant_executor.py:59–80,197–200`.) |

### Metni kim düzleştirecek; `source`/`ok` nereye gidecek?

Bugün Telegram'da düzleştirme sahibi `format_ask_messages()`; başarı, engel ve hata ayrı dallardır. Günlük döngüde karşılığı yok: `Markdown(response)` ve `voice_io.say(response)` doğrudan aynı metni alır. (`tools/telegram_agent.py:1418–1422`; `tools/telegram_formatter.py:153–188`; `main.py:195–199`.)

`speech_text()` girdiyi `str(text)` yapabilir; dolayısıyla sözlüğü doğrudan ses katmanına vermek `answer` alanını seçmek değildir, sözlüğün metinsel temsilini işlemeye açar. Ayrıca günlük döngüde önce Markdown tüketicisi bulunur. (`voice/voice_loop.py:46–63`; `main.py:197–199`.)

**`source="external_blocked", ok=False` için mevcut veri:** `_BLOCKED_MESSAGES` içindeki cevap tam olarak `Gunluk dis model limiti doldu. Daha sonra tekrar deneyin.`; engel dalı bunu `answer` alanına koyar. (`agents/assistant_executor.py:52–55,277–285`.)

**[EMİN DEĞİLİM] Tasarım kararı:** bir ses adaptörü `answer` alanını seçer, ses açık olur ve sentez başarılı olursa bu cümle duyulur; sessizlik, farklı açıklama veya `source` bilgisini ayrıca seslendirme henüz kararlaştırılmış değildir. Ses başarısı ayrıca kendi kapılarına bağlıdır. (`voice/voice_loop.py:140–177`.)

Bu örneği “bugünkü bütçe reddinin kesin sesi” saymak da yanlış olur: router artık `external_blocked` bütçe kararı üretmiyor; API kapısı reddi executor'da sıradaki yerel yürütücüye geçiyor ve yerel üretim başarılıysa `ok=True, source="ollama"` dönüyor. (`agents/local_first_router.py:255–277`; `agents/assistant_executor.py:342–350,370–390`; Ek A çağrı sayımı.)

**[EMİN DEĞİLİM] İmzada açık kalmaması gerekenler:** `ok=False/answer=None` için söylenecek metin, yanlış “limit doldu” açıklamasının önlenmesi, `source/blocked/error` alanlarının ekran/telemetri/hafıza karşılığı ve retlerin başarı/öğrenme gibi işlenmemesi. Mevcut telemetri `source/ok/blocked` saklar, fakat ses adaptörü yerine geçmez. (`agents/telemetry_event_store.py:55–69`; `main.py:201–213`.)

## S2 — Gecikme bedeli

### Gerçek ölçüm ve ölçülemeyen fark

1. B12 ham süreleri yeniden okunup medyan hesaplandı: **18.739,3 / 9.444,0 / 12.464,0 / 5.428,3 ms → p50 10.954,0 ms**. 1.500 ms ile aritmetik fark **9.454 ms**; bu, eski kuru `chat()` örnekleminin hedefle farkıdır, birleşmenin ek maliyeti değildir. (`automation/SES_GECIKMESI_20260906-2116.json:11,19,27,35,50,70`; Ek A.)
2. Bu oturumda gerçek `ModelCascade.select()` kodu için 1.000 ısınma + 10.000 çağrı ölçüldü: **p50 0,0016 ms; p95 0,0018 ms; max 0,0173 ms**. Üç girdi dönüşümlü kullanıldı: `merhaba`, `nerede kaldik`, `mimarisi nasil`; süre `perf_counter_ns` ile yalnız `select` çevresinde alındı, p95 en yakın sıra yöntemiyle 9.500'üncü örnektir. Bu bir CPU mikroölçümüdür; disk, ağ, embedding, LLM, telemetri veya ses içermez. (`agents/model_cascade.py:64–107`; Ek A tekrar komutu/çıktısı.)
3. **[ÖLÇÜLEMEDİ] [EMİN DEĞİLİM] `p50(yeni hat) - p50(eski hat)` ve yönü yok:** eski dört örnek yeni hattın eşlenmiş karşılığı değildir; eski dosya `llama3.1:latest` ve kuru modu kaydeder, yeni gerçek hat bu denetimde çalıştırılmadı. (`automation/SES_GECIKMESI_20260906-2116.json:3–5`; Ek A kapsam kaydı.)

Canlı hattı çalıştırmak salt okuma değildir: `chat()` kalıcı hafızaya, `ask()` telemetriye yazar; VectorMemory constructor'ı kalıcı Chroma koleksiyonu kurar. Bu denetimde ölçüm saf kod ve sahte I/O uçlarıyla sınırlı tutuldu; eski kayıt yeni canlı ölçüm diye sunulmadı. (`agent/local_agent.py:873–877`; `agents/assistant_executor.py:197–199`; `agents/telemetry_event_store.py:68–69`; `tools/vector_memory.py:14–18`; Ek A.)

### Kaç I/O, ne zaman?

Aşağıdaki sayılar Python düzeyinde görünen mantıksal işlemlerdir; fiziksel disk erişimi/syscall sayısı veya Chroma'nın iç işi değildir. (`agents/knowledge_card_store.py:70–82`; `tools/vector_memory.py:36–41`.)

| İşlem | Çalışma koşulu ve sayısı | Günlük sese yalnız executor bağlanırsa |
|---|---|---|
| Deterministik kısa cevap | `_QUICK_REPLIES` eşleşirse router'a uğramadan 0 LLM ve 0 retrieval. Dönüşten önce yine telemetri çağrılır. (`agents/assistant_executor.py:197–227`.) | LifeGraph zemini soru başına eklenirse tam eşleşme bozulabilir; aynı ham selamla aynı yol varsayılamaz. (`main.py:183–188`; `agents/assistant_executor.py:213–214`.) |
| QueryCache | Enjekte edilmişse 1 `get_exact`; mevcut dosya varsa 1 JSON okuma, hit'te 1 tam dosya yazımı. (`agents/local_first_router.py:103–114`; `agents/query_cache.py:42–71`.) | Varsayılan router ve Telegram builder cache enjekte etmiyor: bu bağlantılarda 0. (`agents/local_first_router.py:44,53`; `tools/telegram_agent.py:1371–1382`.) |
| KnowledgeCard | Kısa/boş soru ve cache dönüşünden sonra 1 lookup; `list_cards` tüm mevcut JSONL'yi 1 kez okur ve kartları tarar. Dosya yoksa içerik okuması 0. (`agents/local_first_router.py:116–139`; `agents/knowledge_card_retriever.py:106–119`; `agents/knowledge_card_store.py:70–82`.) | Varsayılan router bu dala ulaşan her soruda lookup yapar; lookup için yeni retriever kurulur, store enjekte değilse store constructor'ı da çalışır. (`agents/local_first_router.py:57–63,134–137`; `agents/knowledge_card_retriever.py:74–79`.) |
| VectorMemory | Kart kaçırırsa 1 `find_similar`; boş koleksiyonda 1 `count`, dolu koleksiyonda **2 `count` + 1 `query(query_texts=[...])`**. İlk kullanım ayrıca lazy PersistentClient/collection kurulumu. (`agents/local_first_router.py:65–86,159–160`; `tools/vector_memory.py:8–18,36–41`.) | Her tur zorunlu değil; kart hit'i bunu keser. **[ÖLÇÜLEMEDİ] [EMİN DEĞİLİM]** Embedding/Chroma iç I/O süresi ve soğuk başlangıç maliyeti ölçülmedi. |
| Redaction / web politika / cascade | Retrieval kaçırdıktan sonra redaction; yalnız enjekte ise web politikası; önceki dallar dönmezse cascade. Gösterilen karar kodunda üretici LLM çağrısı yok. (`agents/local_first_router.py:179–259`; `agents/web_research_policy.py:173–249`; `agents/model_cascade.py:64–107`.) | Redaction varsayılan açık; web politika varsayılan `None`. (`agents/local_first_router.py:45–55`.) |
| Router CostLedger | **0 ledger okuma, 0 tüketim**: parametre yalnız uyumluluk için duruyor. (`agents/local_first_router.py:48–55,255–259`.) | Router eklemek günlük API sayacı bağlamak değildir. (`agents/assistant_executor.py:155–164`.) |
| APIBudgetGate / ledger | Yalnız `api` yürütme denemesinde ve kapı bağlıysa: 1 ledger kontrolü; dosya varsa 1 tam JSONL okuma, izin varsa 1 append; redde append yok. (`agents/assistant_executor.py:342–350`; `agents/api_budget_gate.py:56–59`; `agents/cost_ledger.py:42–67,75–98`.) | Mevcut varsayılan politika yereldir; Telegram builder'da kapı yoktur. Her ses turuna eklenecek sabit ledger I/O yok. (`agents/execution_policy.py:31–38,97–104`; `tools/telegram_agent.py:1376–1382`.) |
| Provider/model yapılandırması | `ask_external` dalında provider selector ve executor/registry lazy yüklenir; provider config dosya kontrolü/okuması ilk başarılı kurulumda, kurulamazsa sonraki denemelerde yeniden yapılabilir. (`agents/assistant_executor.py:120–153,309–320`; `agents/ollama_executor.py:72–80`.) | **[ÖLÇÜLEMEDİ] [EMİN DEĞİLİM]** Soğuk/sıcak kurulumun ms bedeli ayrı ölçülmedi. |
| Telemetri | Normal dönen **her `ask()` için 1 log girişimi/JSONL append**; hata yutulur. Sonuçtaki `latency_ms` bu append'den önce hesaplanmıştır. (`agents/assistant_executor.py:82–97,197–200,405`; `agents/telemetry_event_store.py:39–42,68–69`.) | `result.latency_ms` duvar saati `ask()` süresinin tamamı değildir; S2 ölçerinin `ask` dışına konması gerekir. (`agents/assistant_executor.py:197–200`.) |
| Web araştırması | Yalnız web kararı + researcher bağlıysa; cache/rate limit erken dönebilir, devamında Wikipedia/arXiv/DDG ve koşullu Tavily vardır. Bu dal executor'da ardından cevap LLM'ine gitmeden döner. (`agents/assistant_executor.py:246–275`; `tools/web_research.py:716–746,768–797`.) | **[ÖLÇÜLEMEDİ] [EMİN DEĞİLİM]** Bu sağlayıcıların toplam ağ denemesi ve gecikmesi canlı ölçülmedi; API ledger kontrolü bu dalı çevrelemiyor. (`agents/assistant_executor.py:246–275,342–350`.) |

### Cascade kaç LLM çağırır?

| Sınır | Kanıtlanabilen çağrı sayısı |
|---|---|
| `ModelCascade.select` | **0**: kural tabanlı tek seviye döndürür; L1→L2→L3 üretim/yeterlilik döngüsü yok. (`agents/model_cascade.py:64–107`.) |
| Mevcut varsayılan executor | Kısa cevap/kart/hafıza/cache/red/clarify için **0**; üretim dalında **en fazla 1 Ollama `generate`**. Varsayılan politika cloud kapalıdır. (`agents/assistant_executor.py:212–289,326–356`; `agents/execution_policy.py:31–38,97–104`.) |
| Cloud politika + bağlı ve izin veren bütçe | Standart registry `primary` ve `fallback` olmak üzere en fazla iki farklı anahtar üretir; API başarısız olursa **1 API + 1 Ollama = en fazla 2 üretici yürütücü denemesi**. Bütçe reddinde API çağrısı 0, yerel deneme 1. Ek A'da sahte uçlarla sayıldı. (`agents/executor_registry.py:69–84`; `agents/execution_policy.py:87–94`; `agents/assistant_executor.py:326–395`.) |
| API içi | Repo seviyesinde bir `client.acompletion` çağrı noktası var, explicit retry döngüsü yok. **[ÖLÇÜLEMEDİ] [EMİN DEĞİLİM]** SDK/sağlayıcı iç retry'ları için “en fazla iki HTTP isteği” garantisi verilemez; üst sınır burada yürütücü denemesidir. (`agents/api_executor.py:433–483`.) |
| Yerel günlük normal sohbet | Ana cevap için bir `_ollama.chat(stream=False)`; PDF ayrı RAG yoludur, araçlar koşulludur. Bu nedenle bütün ses istekleri için tek LLM garantisi genellenmez. (`agent/local_agent.py:773–805,811–817,862–863`.) |

**[EMİN DEĞİLİM] Yönlü beklenti:** eşdeğer bir kart/cache hit'i üretimi atladığından hızlanma sağlayabilir; miss yolunda retrieval eklenir; cloud başarısızlığından sonra yerel deneme beklemek seri beklemeyi uzatabilir. Ancak bunların net p50 üzerindeki yönü hit oranına, bağlam boyuna, modele ve hata dağılımına bağlıdır; ms kazancı çıkarılmadı. Dal kanıtları: `agents/assistant_executor.py:234–243,326–395`; `agents/local_first_router.py:134–177`.

### Hızlanma hesabını yanıltan somut ayrıntı

`OllamaExecutor` L2 için `num_predict=350` ve `temperature=0.2` tanımlar, `generate()` bunları `options` olarak verir; fakat varsayılan `_OllamaHTTPClient.generate(..., **kw)` gövdeye `options` koymaz. Sentetik `urlopen` yakalaması gövdede yalnız `model/prompt/stream/keep_alive/system` bulunduğunu doğruladı (Ek A). **350 token sınırı üretim HTTP yolunda uygulanıyor kabul edilemez.** (`agents/ollama_executor.py:50–54,98–115,187–188`.)

Günlük ajan ise SDK `chat()` çağrısına `num_predict=1024`, `num_ctx=4096`, `temperature=0.72` verir; prompt'una hafıza ve proje durumunu da ekler. **[EMİN DEĞİLİM]** Daha kısa/sade cevap sayesinde hızlı görünen bir executor ölçümü, aynı görevi yaptığı kanıtlanmadan kalite kazancı sayılmamalı. (`agent/local_agent.py:775–784,819–859`; `agents/ollama_executor.py:179–188`.)

## S3 — Ne kaybolur, ne gerçekten gelir?

| Yetenek / koruma | Eşdeğerlik ve birleşme riski |
|---|---|
| Açık “yerel kal” | Yerel araç kapısı orijinal mesajı ve sorguyu kontrol eder. Ortak web politikasında bu kontrol yok; Ek A'da yasak içeren soru sahte web araştırmacısına geçti. **Web'i açık builder ile doğrudan değiştirme, mevcut kullanıcı override korumasını geriletir.** Web kapalı varsayılan kurulumda aynı örnek web çıkışı kanıtı değildir. (`agent/local_agent.py:687–691`; `agents/web_research_policy.py:173–249`; `tools/telegram_agent.py:1368–1382`; `agents/assistant_executor.py:246–250`.) |
| B03/A-04 nihai sorgu kapısı | Yerel yol niyeti orijinalden değerlendirir, gerçekten çıkacak sorguyu sanitize eder ve son veri sınıfını yeniden denetler. Router policy sonucu `sanitized_query` kullanır ama aynı son-kapı dizisi yok; researcher sonradan sorguyu ayrıca normalize eder. **[EMİN DEĞİLİM]** Bütün dönüşümler için eşdeğer güvenlik kanıtı yok; A-04'ün kendiliğinden taşındığı söylenemez. (`agent/local_agent.py:703–748`; `agents/local_first_router.py:207–219`; `agents/assistant_executor.py:247–250`; `tools/web_research.py:127–146,716–718`.) |
| PDF niyeti ve gerçek belge cevabı | `_pdf_istegi_mi` açık belge işaretleri arar; yerel `chat()` gerçek yükleme/RAG dalına gider. Executor'ın dalları quick/retrieval/web/block/generate/fallback; aynı PDF yükleme kolu yoktur. Bu ilk olarak **işlev kaybıdır**; kendi başına veri sızıntısı kanıtı değildir. (`agent/local_agent.py:118–138,793–805`; `agents/assistant_executor.py:212–416`.) |
| Canlı proje durumu | `_proje_ctx_guncel` kaynak imzasını kontrol eder, değişimde git log/HUMAN_NEEDED/roadmap/fail log yeniden okunur. Executor üretimi bu bağlamı oluşturmaz/iletmez. LifeGraph zemininin korunması bunun yerine geçmez. (`agent/local_agent.py:339–434,453–491,525–535,824–826`; `main.py:183–188`; `agents/assistant_executor.py:352–356`.) |
| Mevcut “canlı” bağlamın sınırı | Yerel yükleyici de bütün repo gerçeği değildir: git log ve belirtilen dosyaları okur; burada BLACKBOX veya `git status` okuması yoktur. **[EMİN DEĞİLİM]** Bu yüzden yerel bağlamı korumak PUSULA doğruluğunu tek başına ispatlamaz. (`agent/local_agent.py:436–543`; `CLAUDE.md:62–70`.) |
| Diyalog ve unutma | Yerel RAM geçmişi + SQLite son konuşmaları ve `clear_conversations()` sözleşmesi kaybolabilir; executor retrieval hafızası bunlarla aynı değildir. Main'in `temizle` komutu hâlâ `agent.clear_history()` bekler. (`agent/local_agent.py:827–843,887–913`; `memory/memory_manager.py:191–211`; `agents/local_first_router.py:65–94`; `main.py:150–152`.) |
| Ses üslubu, araçlar, temizleme | `VOICE_MODE_DIRECTIVE`, yerel addendum, `_clean_response`, hesap/saat/not/dosya araçları yerel ajandadır. Executor aynı araç-dispatch'i yapmaz; Ollama kolu ortak persona'yı kullanır ama `ask()` ses modu veya sistem bağlamı parametresi taşımaz. API koluna bu çağrıdan persona `system_prompt` da gitmez. (`agent/local_agent.py:273–287,320–332,811–836,865–866`; `agents/assistant_executor.py:197,352–356`; `agents/ollama_executor.py:45–47,179`; `agents/api_executor.py:419–422`.) |
| LifeGraph, donanım nöbetçisi, TTS güvenliği | Bunlar günlük giriş/VoiceIO dışında değildir: yalnız cevap motoru değiştirilip çevre döngüsü korunursa kodları yerinde kalır; bütün `main` akışı değiştirilirse otomatik aktarılmış olmaz. (`main.py:90–118,183–213`; `voice/voice_loop.py:140–177`.) |
| Router redaction | Executor yoluna gerçekten yönlendirilen ve retrieval'dan cevaplanmayan soruda varsayılan guard çalışır; guard hatası engeldir. Bu, gelen her sorunun önce redakte edildiği anlamına gelmez: kart/hafıza cevabı guard'dan önce döner. (`agents/local_first_router.py:141–177,179–204`.) |
| API bütçesi | API seçimi + bağlı kapı gerektirir; kapı yoksa API engellenir ve fallback mümkün olur. Ledger para/token faturası değil, kabul edilen deneme sayar. Web/TTS çıkışlarının bütçesi bu kapıyla kapsanmaz. (`agents/assistant_executor.py:155–172,246–275,342–356`; `agents/cost_ledger.py:59–67`; `voice/voice_loop.py:171–172`.) |
| Bilgi kartları / cache / öğrenme | Kart lookup gelir; QueryCache constructor'a ayrıca bağlanmadan gelmez. Executor'da `crystallize`/kart yazımı yok; router'ın `crystallize_candidate` döndürmesi kayıt yaratmaz. (`agents/local_first_router.py:44,103–114,134–137,268–273`; `agents/assistant_executor.py:197–416`; `tools/telegram_agent.py:1371–1382`.) |
| Güvenli egress'in tümü | Router guard'ı TTS çıkışının yerini tutmaz; retrieval kaynaklı cevap da bulut ses servisine gidebilir, dolayısıyla mevcut son-metni denetleyen VoiceIO kapısı ayrı sorumluluktur. (`agents/assistant_executor.py:234–243`; `voice/voice_loop.py:144–169`.) |

**[EMİN DEĞİLİM] Yarım bağlantının en tehlikeli biçimi:** bazı sorular eski araç yolundan, bazıları executor'dan geçerken arayüzün tüm istekler için tek bütçe/override/hafıza koruması varmış gibi davranması. Ayrı yolların kapı konumları gerçekten farklıdır; bu yüzden korunma kapsamı istek dalıyla birlikte gösterilmelidir. (`agent/local_agent.py:751–761`; `agents/local_first_router.py:179–259`; `agents/assistant_executor.py:342–356`.)

## S4 — En küçük dürüst adım

Bu bölümdeki adımlar **öneridir, uygulanmadı**; uygulama ve mimari değişiklik onayı bu rapordan çıkmaz. (`automation/KART_CODEX_IKI_BEYIN.md:6–10,104–115`.)

| Seçenek | Kazanç / sınır / geri dönüş |
|---|---|
| **A — Ses yoluna executor adaptörü bağlamak** | **[EMİN DEĞİLİM]** Tek giriş hedefini hızlı görünür kılabilir; fakat yalnız `ask()['answer']` bağlantısı S1'deki durum/hata/komut sözleşmesini ve S3'teki override/bağlamı korumaz. Kod revert'i küçük olabilir; yeni telemetri, hafıza veya dış çağrıyı revert geri alamaz. Bu yüzden bugün en küçük *dürüst* adım diye önermiyorum. Gerekçe: `main.py:145–159,193–213`; `agents/assistant_executor.py:197–200,342–356`; `agents/telemetry_event_store.py:68–69`. |
| **B — Sesin eksik davranışlarını önce executor tarafında eşlemek** | **[EMİN DEĞİLİM]** Açık kullanıcı override'ı, proje bağlamı, konuşma durumu ve ses sonucu sözleşmesi tanımlanıp doğrulanabilir; ancak bunları kopyalamak ikinci bakım noktası yaratır, ortak politikayı değiştirmek Telegram davranışını da etkiler. Hepsini tek commit'e doldurmak küçük adım değildir; tek davranışın karakterizasyonuyla daraltılmalıdır. Paylaşılan politika için mevcut karar kaydı da vardır. (`agent/local_agent.py:667–748,819–859`; `agents/assistant_executor.py:197,352–356`; `automation/AHMET_ONAYI_BEKLEYENLER.md:415–433`.) |
| **C — Önce üretime bağlanmayan karşılaştırma/karakterizasyon düzeneği — önerilen** | **[EMİN DEĞİLİM]** Bir sonraki ayrı kart, yalnız ölçer ve sentetik senaryoları tek commit'te eklesin; `main`, runtime profilleri, ortak politika ve gerçek depolar değişmesin. Mevcut enjekte edilebilir ölçer ve executor bağımlılık noktaları başlangıç sağlayabilir. Bu adım farkları ölçer; birleştirme gerçekleştirdiğini iddia etmez. (`scripts/olc_ses_gecikmesi.py:136–165`; `agents/assistant_executor.py:62–80`; `agents/local_first_router.py:37–55`.) |

**[EMİN DEĞİLİM] C için ölçülebilir kabul önerisi:** aynı sentetik veriyle iki adayın (1) ham selam, (2) `nerede kaldık` ve bir repo-durum değişimi, (3) takip sorusu + temizle, (4) kart hit/miss, (5) yerel kal + güncel soru, (6) hassas veri/guard arızası, (7) API bütçe reddi/hatası, (8) açık PDF isteği davranışları yan yana kaydedilsin; desteklenmeyen yetenek hızlı başarı sayılmasın. Bu senaryoların ayrıldığı mevcut sınırlar S1–S3'tedir. (`main.py:150–152`; `agent/local_agent.py:409–434,687–691,796–805`; `agents/assistant_executor.py:234–286,342–365`.)

**[EMİN DEĞİLİM] Süre kabul önerisi:** önce ağsız uçlarla sözleşme/çağrı sayımı; ayrı izinli gerçek yerel model koşusunda model/profil, soru, system/user mesaj uzunluğu, geçmiş boyu, kart hit/miss, cold/warm durum ve tüm `chat/ask` duvar süresi kaydedilsin; her sınıfta örneğin 30 eşlenmiş tur, dönüşümlü eski/yeni sıra, p50/p95 ve başarısız tur sayısı ayrı verilsin. Soğuk/sıcak örnekler karıştırılmasın; bağlam eksiltmek hız başarısı sayılmasın. Mevcut ölçer fonksiyon enjeksiyonuna izin verir fakat `ask()` sözlüğünün nasıl karşılanacağı ayrıca tanımlanmalıdır. (`scripts/olc_ses_gecikmesi.py:136–180`; `agents/assistant_executor.py:197–200`; `agent/local_agent.py:819–859`.)

**[EMİN DEĞİLİM] PUSULA kabulü ayrı kalsın:** metin üretim süresi ve ses-bitişi→ilk-duyulan-ses birlikte raporlansın; ikincisi yoksa açıkça ölçülemedi yazılsın. Mevcut ses ölçeri de VAD sonu/ilk ses olayını doğrudan ölçmediğini belirtiyor. (`scripts/olc_ses_gecikmesi.py:82–86`; `CLAUDE.md:62–70`.)

**[EMİN DEĞİLİM] Geri dönüş ve öz-eleştiri:** C yalnız ölçer/test dosyalarıyla ve izole sahte/geçici depolarla sınırlandırılırsa geri dönüş bir commit revert'i olabilir; mevcut iki üretim hattını daha karmaşık yapmaz. Fakat sahte uçlarla geçen deney canlı GPU, embedding, web ve TTS gecikmesini kanıtlamaz; yalnız mikroölçüm üretip A19 kararını erteleyen kalıcı bir laboratuvara dönüşme riski vardır. Bitirme ölçütü “bağlandı” değil, kayıp davranışların açık listesi ve karşılaştırılabilir süre verisidir. Gerçek depoların yan etkileri: `agents/telemetry_event_store.py:68–69`; `agent/local_agent.py:873–877`; `tools/vector_memory.py:14–18`.

## Ek A — Bu oturumun deney kaydı

Deneyler `python -X utf8 -B -` üzerinden bellekte çalıştırıldı; `-B` bytecode çıktısını kapattı. Aşağıdaki komutlarda üretim constructor'ı yerine yalnız ilgili saf sınıflar/AST parçası, sahte retrieval ve sahte ağ ucu kullanılır; gerçek sır dosyası yükleyen günlük giriş çalıştırılmaz. Günlük girişteki farklı davranışın kaynağı: `main.py:24–28`; yan etkili constructor'lar: `agent/local_agent.py:292–310`, `tools/vector_memory.py:8–18`.

### A1 — Override ve CPU mikroölçümünü tekrar üretme

```python
import ast, json, statistics, time
from pathlib import Path
from types import SimpleNamespace
from agents.data_classifier import _fold_tr, keyword_present
from agents.model_cascade import ModelCascade
from agents.local_first_router import LocalFirstRouter
from agents.assistant_executor import AssistantExecutor
from agents.web_research_policy import WebResearchPolicy

p = Path('agent/local_agent.py')
t = ast.parse(p.read_text(encoding='utf-8-sig'))
nodes = [n for n in t.body if (
    isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
    and n.target.id == '_YEREL_KAL_KOKLERI'
) or (isinstance(n, ast.FunctionDef) and n.name == '_yerel_kal_istendi')]
ns = {'_fold_tr': _fold_tr, 'keyword_present': keyword_present}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(p), 'exec'), ns)
q = 'internete cikma, son haberleri anlat'
r = LocalFirstRouter(web_research_policy=WebResearchPolicy())
r._get_retriever = lambda: SimpleNamespace(lookup=lambda _: {'found': False})
r._recall = lambda _: []
print(ns['_yerel_kal_istendi'](q), WebResearchPolicy().decide(q).allow,
      r.route(q)['decision'])
calls = []
a = AssistantExecutor(router=r, web_researcher=SimpleNamespace(
    research=lambda q, **kw: calls.append(q) or 'synthetic report'))
a._log_telemetry = lambda *args: None
result = a.ask(q)
print(result['ok'], result['source'], calls)

c = ModelCascade()
cases = ['merhaba', 'nerede kaldik', 'mimarisi nasil']
for i in range(1000):
    c.select(cases[i % 3])
samples = []
for i in range(10000):
    start = time.perf_counter_ns()
    c.select(cases[i % 3])
    samples.append((time.perf_counter_ns() - start) / 1e6)
print(statistics.median(samples), sorted(samples)[9499], max(samples))

old = json.loads(Path('automation/SES_GECIKMESI_20260906-2116.json')
                 .read_text(encoding='utf-8'))
print(statistics.median(x['model_ms'] for x in old['turlar']))
```

Bu oturumda kaydedilen çıktılar (kod sınırları: `agent/local_agent.py:75–80`; `agents/local_first_router.py:207–229`; `agents/assistant_executor.py:246–257`; `agents/model_cascade.py:64–107`):

```text
local_override=true; web_policy_allow=true; router.decision=web_research
WEB_HANDOFF: ok=true; source=web_research
fake_web_calls=["internete cikma, son haberleri anlat"]
CASCADE_CPU_MS: n=10000; warmup=1000
p50=0.0016; p95_nearest_rank=0.0018; max=0.0173
B12_RECOMPUTED: n=4; p50_ms=10954.0; excess_over_1500_ms=9454.0
```

Bu ölçümde gerçek kart/vektör deposu, telemetri ve web çağrısı devre dışı bırakıldığı için bulgu **kontrol akışı karşı-örneğidir**, canlı veri sızıntısı veya birleşmiş hat benchmark'ı değildir. Enjeksiyon sınırları yukarıdaki komutta açıkça görünür. (`agents/local_first_router.py:37–55`; `agents/assistant_executor.py:62–80,197–200`.)

### A2 — HTTP seçenek aktarımı

```python
import json
from unittest.mock import patch
from agents.ollama_executor import OllamaExecutor
client = OllamaExecutor()._get_client()
captured = []
class Reply:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return b'{"response":"probe"}'
def fake_open(req, **kwargs):
    captured.append(json.loads(req.data))
    return Reply()
with patch('urllib.request.urlopen', fake_open):
    client.generate(model='synthetic', prompt='probe', system='probe',
                    options={'num_predict': 350, 'temperature': 0.2})
print(captured)
```

Kaydedilen gövde aşağıdadır; `options` yoktur. (`agents/ollama_executor.py:98–115`.)

```json
[{"model":"synthetic","prompt":"probe","stream":false,"keep_alive":"5m","system":"probe"}]
```

### A3 — Üretici yürütücü çağrı sayımı

Gerçek `AssistantExecutor`, `ExecutionPolicy(cloud_api_enabled=True, cloud_levels={'L3'})` ve `ExecutorRegistry` kullanıldı; router L3 kararı döndüren sahte uç, API/Ollama üreticileri sayıcı sahte uçlar, bütçe izin/red sahte uçtu; provider seçimi, sınıflandırma ve telemetri yalnız bu deneyde bellekte sabitlendi. Bu sonuç yalnız executor döngüsü ve bütçe fallback davranışını sınar. (`agents/assistant_executor.py:293–395`; `agents/execution_policy.py:87–94`; `agents/executor_registry.py:69–84`.)

```text
budget_allowed=true, api_ok=true  -> calls=[api],         source=api,    ok=true
budget_allowed=true, api_ok=false -> calls=[api, ollama], source=ollama, ok=true
budget_allowed=false             -> calls=[ollama],      source=ollama, ok=true
```

AST sayımı `git ls-files '*.py'` çıktısını UTF-8-sig okuyup `ast.Call` içinde doğrudan `Name('LocalFirstRouter')` çağrılarını saydı; dinamik alias çağrılarını kapsadığı iddia edilmiyor. Sonuç: `agents/assistant_executor.py:103`, `tools/telegram_agent.py:1371`, `tools/telegram_agent.py:1381`; `tests/` altında 43 çağrı noktası.

## Ek B — Doğrulama sınırı

Çalıştırılan odaklı test komutu ve terminal sonucu aşağıdadır; mevcut testler saf seviye/politika kararlarını sınar. Bu, tam süitin geçtiği iddiası değildir. (`tests/test_y1_model_cascade.py:12–77`; `tests/test_execution_policy.py:4–93`.)

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
& 'C:/Program Files/Python311/python.exe' -X utf8 -B -m pytest tests/test_y1_model_cascade.py tests/test_execution_policy.py -q -p no:cacheprovider
# 14 passed in 0.08s
& 'C:/Program Files/Python311/Scripts/ruff.exe' check . --no-cache --statistics
# Found 283 errors.
```

**[ÖLÇÜLEMEDİ] [EMİN DEĞİLİM] Tam süit / ters sıra için bu oturumdan PASS yok.** Salt okunur görevde bütün testlerin gerçek dosya/servis yan etkileri yalıtılmış bir kopyada doğrulanmadığından tam süit çalıştırılmadı; mevcut kaynak değişiklikleri üzerinde otomatik düzeltme de yapılmadı. Anayasanın tam süit kapısı böylece karşılanmış sayılmıyor. (`CLAUDE.md:186–198,229–237`; `automation/KART_CODEX_IKI_BEYIN.md:6–10,126`.)

## Ek C — Çalışma ağacı ve teslim kaydı

Başlangıç ve ara terminal kayıtları aşağıdadır; bunlar oturum gözlemidir, dosyaların kim tarafından üretildiğine dair atıf değildir. **[EMİN DEĞİLİM]** Başka süreçlerin/kişilerin eşzamanlı çalışma durumu bu denetimden belirlenemedi.

```text
Başlangıç HEAD: 7ceaf3cb5e6a315d4000cdd960ea6c1bc77af42e
Dal: auto/opencode-deepseek
Başlangıç git status --short:
?? automation/KALITE_deepseek_deepseek-chat_20260909-2127.json
?? automation/KALITE_deepseek_deepseek-chat_20260909-2127.md

Ara kontrolde ayrıca görülen değişiklikler:
 M tests/test_quality_runner_api_provider.py
 M tests/test_quality_scorer.py
git diff --stat: 2 files changed, 160 insertions(+)
```

**[EMİN DEĞİLİM] Teslim istisnası:** baştan var olan dosyalar ve bu turda yazmadığım eşzamanlı değişiklikler nedeniyle “git status yalnız raporu gösteriyor / git diff boş” koşulunu tüm çalışma ağacı için üstlenemiyorum; bunları silmek, taşımak veya başka iş adına commit etmek için yetki varsayılmadı. Kullanıcıya mevcut iki dosyanın ne yapılacağı soruldu; yanıt gelmeden taşınmadılar. İstenen sınır: `automation/KART_CODEX_IKI_BEYIN.md:121–127,136`.

**[EMİN DEĞİLİM] Commit yorumu:** kart bir yandan raporun tek commit olmasını, öte yandan git status'ta raporun görünmesini istiyor; son kullanıcı talebindeki “bitince git status yalnız rapor dosyasını göstermeli” koşulu lehine bu teslimde rapor commit edilmeden bırakıldı. İstenen commit mesajı saklıdır: `docs(fizibilite): iki beyin birlestirme -- olcum, kod degismedi`. Push talimatı yoktur, kart push'u yasaklar. (`automation/KART_CODEX_IKI_BEYIN.md:127,136–137`.)

Son rapor kontrolü sırasında kaydedilen ek çalışma ağacı görüntüsü aşağıdadır; ardından raporun yalnız atıf ve teslim metni düzeltildi. Bu görüntü, diğer işlerin sonradan değişmeyeceği iddiası değildir. **[EMİN DEĞİLİM]** Haricî değişikliklerin sahipliği doğrulanmadı.

```text
git status --short:
 M eval/quality_scorer.py
 M eval/run_turkish_quality.py
 M tests/test_quality_runner_api_provider.py
 M tests/test_quality_scorer.py
?? automation/CODEX_IKI_BEYIN_FIZIBILITE_2026-09-09.md
?? automation/KALITE_deepseek_deepseek-chat_20260909-2127.json
?? automation/KALITE_deepseek_deepseek-chat_20260909-2127.md
?? tests/test_llm_anatomisi_olcumu.py

git diff --cached --name-only: boş
git diff 8c428e2 --name-only -- main.py agent/local_agent.py
  agents/assistant_executor.py agents/local_first_router.py
  agents/model_cascade.py agents/ollama_executor.py
  tools/telegram_agent.py voice/voice_loop.py: boş
```

Kritik sekiz dosyanın tabanla farkı boş olduğundan bu rapordaki ana hat incelemesi, HEAD ilerlemesine rağmen kartın tabanındaki aynı kaynakla yapılmıştır; bütün repo için değişiklik yok iddiası kurulmamıştır. Yukarıdaki komut çıktısı bu dar kapsamın teslim kanıtıdır.
