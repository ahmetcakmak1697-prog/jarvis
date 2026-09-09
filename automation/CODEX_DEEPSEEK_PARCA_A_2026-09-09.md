# DeepSeek — PARÇA A sonucu, 2026-09-09

**PARÇA A'nın sayısal kabulü karşılandı; PARÇA B başlatılmadı.** Eski üç kalıp vakasının ikisi geçti. Canlı llama koşusu **50/64** verdi; kayıtlı **49/64 tabanı değiştirilmedi** ve altında sonuç gelmediği için persona geri alınmadı. Bununla birlikte DeepSeek'in toplam kalıp sayısı **3 → 3** kaldı: sorun bütünüyle çözülmedi, iki başka vakada tekrar görüldü.

Kart: [KART_DEEPSEEK_10_KUSUR.md](KART_DEEPSEEK_10_KUSUR.md). Oturum başlangıcı: `8b970e0`, `auto/opencode-deepseek`; başlangıç çalışma ağacı temizdi. Bu işin tek kaynak değişikliği `agents/persona.py:56–57` içindeki iki satırdır.

## Önce okunan üç cevap ve gerçek eşleşmeler

Kaynak: [eski DeepSeek 64 vaka kaydı](KALITE_deepseek_deepseek-chat_20260909-2208.json). Değişiklikten önce mevcut puanlayıcıyla tekrar hesap: **54/64**; üçü de yine `boilerplate` ile kaldı. Dedektör `_BOILERPLATE` listesindeki ASCII-fold edilmiş alt dizeleri arıyor (`eval/quality_scorer.py:67–71,382–388`). Karttaki “size nasıl…” tanımı bu üç cevabın birebir alıntısı değildir.

| Vaka | Cevaptaki gerçek bölüm | Eşleşme |
|---|---|---|
| `t1_tone_015` | “Yük değil, iş. Efendim, buradayım — ne gerekiyorsa söyleyin.” | `buradayim` |
| `t1_tech_003` | RAM'e erişimi olmadığını söylüyor; `free -h`, `top`, `ps aux` örneklerinden sonra “... süreç adını veya PID'sini paylaşırsanız daha spesifik yardımcı olabilirim.” diye bitiyor. | `yardimci olabilirim` |
| `t1_tech_008` | Aktif profile erişimi olmadığını söyledikten sonra “... ben Jarvis olarak buradayım ve size hizmet vermeye hazırım.” ekliyor. | `buradayim` |

Üç cevabın tamamı okundu; tam metinleri eski JSON'da sırasıyla `:533`, `:1387`, `:1576` çevresindedir. İlk cevap 60, ikinci 371, üçüncü 334 karakterdir.

## Hipotez ve dar değişiklik

En güçlü aday, `_SADAKAT` içindeki gevezelik maddesinin yasaklamaya çalıştığı yardım sunma kalıbını **prompt'ta doğrudan örneklemesi** idi:

```text
- Sıfır gevezelik. "Size yardımcı olmaktan mutluluk duyarım", "Elbette,
  hemen yapıyorum" gibi yapay zekâ kalıpları kullanma. Doğrudan işe gir.
```

Yerine yeni yasak listesi eklenmeden şu cümle kondu:

```text
- Sıfır gevezelik. Doğrudan işe gir. Yanıtın, sorulan konudaki sonucu
  veya somut sonraki adımı vermesiyle tamamlanır.
```

**[EMİN DEĞİLİM] Nedensellik sınırı:** negatif örneklerin genel “hizmete hazırım” devamını çağırması makul hipotezdir; özellikle “buradayım” kaldırılan cümlede aynen bulunmuyor. Bu deney yalnız silme ablasyonu da değildir: aynı madde, olumlu bir bitirme yönergesiyle yeniden yazıldı. Tek eski/yeni koşudan etkinin tümünü o alıntıya bağlamak doğru olmaz.

Persona'daki “Reddetmek yerine yol göster ... yapabildiğin en yakın şeyi öner” ve proaktif B/C düşünme cümleleri de genel teklifleri teşvik edebilir; bu adayda değiştirilmediler (`agents/persona.py:58–59,84–85`). Yeni otomatik düzeltme turu yapılmadı.

## Canlı sonuçlar

Her modelde aynı sıradaki **64 vaka**, aynı sorular, kategori/seviye eşlemesi ve seed memory kullanıldı. Standart bütçe **400**, dört longform bütçesi **1200**; sıcaklık **0,2**. Yerel model `llama3.1:latest`, bulut model `deepseek/deepseek-chat`. `config/`, puanlayıcı kodu, koşucu kodu, vaka dosyası ve eşikler değişmedi; dosya hash'leri [KANIT.json](PARCA_A_PERSONA_2026-09-09/KANIT.json) içinde doğrulandı.

| Ölçüm | Önceki kayıt | Yeni canlı koşu |
|---|---:|---:|
| DeepSeek toplam | 54/64 | **56/64** |
| Hedef üç vaka | 0/3 | **2/3** |
| DeepSeek tüm kalıp kusurları | 3 | **3** |
| DeepSeek ağ/hata vakası | 1 | **0** |
| llama toplam | 49/64 | **50/64** |
| llama kalıp kusurları | 0 | **0** |
| llama ağ/hata vakası | 0 | **0** |

Yeni ham kayıtlar: [DeepSeek JSON](PARCA_A_PERSONA_2026-09-09/aday/KALITE_deepseek_deepseek-chat_20260909-2344.json), [DeepSeek özet](PARCA_A_PERSONA_2026-09-09/aday/KALITE_deepseek_deepseek-chat_20260909-2344.md), [llama JSON](PARCA_A_PERSONA_2026-09-09/aday/KALITE_llama3.1_latest_20260909-2342.json), [llama özet](PARCA_A_PERSONA_2026-09-09/aday/KALITE_llama3.1_latest_20260909-2342.md).

Hedef sonuçlar:

- **`t1_tone_015` PASS:** “özür dilemeye gerek yok” diye başlayıp birlikte işi halletmeyi ve yeni bir konu seçmeyi öneriyor; dedektörün kalıbı yok. **Nitelik sınırı:** hâlâ gereksiz devam sorusu var, 60 karakterden 252'ye uzamış; puan geçmesi üslubun bütünüyle düzeldiği anlamına gelmiyor.
- **`t1_tech_003` FAIL:** “... daha spesifik yardımcı olabilirim” kapanışı sürüyor; `boilerplate` kaldı. Teknik cevap 502 karakter.
- **`t1_tech_008` PASS:** profil durumuna erişimi olmadığını söylüyor, `[VARSAYIM]` ile kontrol yolunu belirtiyor; “buradayım/hizmete hazırım” kapanışı yok. Cevap 212 karakter.

Yeni kalıp vakaları **`t1_tone_001`** (“Efendim, buyrun. Nasıl yardımcı olabilirim?”) ve **`t1_tr_007`** (“Anlaşıldı efendim. Sistem çalışıyor, ben buradayım.”). Böylece hedefteki iki kazanım toplam kalıp sayısını azaltmadı. DeepSeek'in 54→56 toplam farkı yalnız persona etkisi diye sunulmuyor; eski kayıtta bir ağ hatası da vardı ve vakalar arası oynaklık var.

llama'da eski kayda göre dört vaka geçtiye, üç vaka kaldıya döndü. Yeni kayıplar: `t1_tone_013` (`prompt_leak`), `t1_tech_002` (`grounding`), `t2_grounding_003` (`grounding`). Kazanımlar: `t1_tone_014`, `t1_tr_006`, `t1_tr_013`, `t1_mix_004`. Bu nedenle **50/64 sonucu bütün vakaların tek tek korunduğu iddiası değildir**; kullanıcının toplam tabanın altına düşmeme şartı sağlandı. Kalıcı taban kaydı **49/64** olarak bırakıldı; +1 yeni taban ilan edilmedi.

Kapsam dışı iki gözlem, takip düzeltmesi olmadan:

- `t1_tech_004`: eski cevaptaki “kontrol edemem” puanlayıcının grounding ailesine girmemişti; yeni cevap “erişimim yok” diyor ve geçiyor. Bu oturumda vaka veya grounding dedektörü değiştirilmedi.
- `t2_memory_004`: eski cevap verilen seed memory'yi kullanmayıp adı bilmediğini söylüyordu; yeni cevap seed içindeki **Zeynep** adını veriyor ve geçiyor. Buna yönelik ayrı prompt ayarı yapılmadı.

DeepSeek'in dört longform cevabı yine `done_reason="length"`; bütçe artırılmadı. Bu sonuç PARÇA B'yi başlatma onayı sayılmadı.

## Ölçümün kendisi oynadı mı?

`_BOILERPLATE` ve puanlayıcı dosyası sabit; fakat `_LEAK_NGRAMS`, persona'dan import sırasında türetiliyor (`eval/quality_scorer.py:194–225`). Dolayısıyla “dedektörün bütün verisi değişmedi” denemez: **eski küme 688, yeni küme 690 n-gram; 12 çıktı, 14 girdi**. Mevcut `_QUOTED_EXAMPLE` çok satıra yayılan eski alıntıyı bütünüyle dışlamadığından değişim yalnız eklenen yeni talimatlardan ibaret de değil (`eval/quality_scorer.py:177`). Regex'e dokunulmadı.

Bu etkiyi sonuçtan ayırmak için hem iki eski kaydın hem iki yeni koşunun cevapları, eski ve yeni persona'dan türetilmiş kümelerle **bellekte çapraz puanlandı**:

| Aynı cevap seti | Eski küme | Yeni küme | `failed_checks` farkı |
|---|---:|---:|---|
| Eski DeepSeek | 54/64 | 54/64 | Yok |
| Eski llama (`20260905-1617`) | 49/64 | 49/64 | Yok |
| Yeni DeepSeek | 56/64 | 56/64 | Yok |
| Yeni llama | 50/64 | 50/64 | Yok |

Toplam **256 cevap** için kategori sonuçları ve başarısızlık nedenleri bu küme farkından etkilenmedi. Yeni sonuçları eski dedektörle yeniden etiketleyerek rapor dosyaları değiştirilmedi; çapraz sonuç ayrı kanıt olarak [KANIT.json](PARCA_A_PERSONA_2026-09-09/KANIT.json) içinde tutuldu.

## Çalıştırma ve kapılar

DeepSeek'in ilk, tek vakalık sandbox ön kontrolü `WinError 10061` bağlantı reddi verdi; bu 0/1 sonuç kalite karşılaştırmasına katılmadı ve [ön kontrol kaydı](PARCA_A_PERSONA_2026-09-09/on_kontrol/KALITE_deepseek_deepseek-chat_20260909-2338.json) olarak ayrı tutuldu. Araç ağ onayından sonra tam 64 vaka tekrar çalıştırıldı; tam koşuda hata sayısı sıfır. Anahtar değeri okunup gösterilmedi/loglanmadı; mevcut koşucunun kimlik doğrulama yolu kullanıldı.

```powershell
& 'C:/Program Files/Python311/python.exe' -X utf8 -B -m eval.run_turkish_quality --saglayici deepseek --out automation/PARCA_A_PERSONA_2026-09-09/aday
```

llama için mevcut `run_suite(load_cases(), ask, model='llama3.1:latest', gpu_probe=_nvidia_probe)` çağrıldı; `ask` mevcut `_ollama_ask` fonksiyonunu aynen çağıran, her vakadan önce persona hash'ini kontrol eden ve ilerleme sayısını yazan bir bellek içi sarmalayıcıydı. Sonuç mevcut `write_report()` ile `aday/` altına yazıldı; test/ölçüm kaynak dosyası eklenmedi.

| Kapı | Sonuç | Kayıt |
|---|---|---|
| `py_compile agents/persona.py` + L1/L2/L3 import smoke | PASS | Terminal; üretilen prompt boyları 3104/3131/4658 karakter |
| `pytest tests -q` | **1950 passed, 2 xfailed, 2 warnings; 70,15 s; exit 0** | [Normal sıra](PARCA_A_PERSONA_2026-09-09/pytest_normal.txt) |
| Kök `test_*.py` dosyaları adlarına göre ters sıra, `pytest @files -q` | **1950 passed, 2 xfailed, 2 warnings; 82,05 s; exit 0** | [Ters sıra](PARCA_A_PERSONA_2026-09-09/pytest_reverse.txt) |
| `ruff check . --statistics` | **283 bulgu ≤ 283**; Ruff exit 1 | [Lint kaydı](PARCA_A_PERSONA_2026-09-09/ruff.txt) |
| Bağımsız persona diff incelemesi | **PASS — yalnız diff**, kalite onayı değil | İki satırlık kapsam ve yukarıda açıklanan nedensellik/korpus sınırları incelendi |
| `graphify update .` | AST güncellemesi tamamlandı; 6363 düğüm / 11746 kenar | İlk sandbox erişim engelinden sonra mevcut izinle çalıştırıldı; LLM etiketleme yapılmadı |

Tam testlerdeki iki uyarı `TestCore` sınıflarının constructor taşıması nedeniyle toplanmamasına ilişkin `PytestCollectionWarning`; Ruff temiz denmiyor, mevcut 283 sınırı sağlandı deniyor. Kaynakta başka düzeltme denenmedi.

## Teslim sınırı

Bu işin dosyaları: `agents/persona.py`, bu rapor ve `automation/PARCA_A_PERSONA_2026-09-09/` altındaki ham koşular/kapı/kanıt kayıtları. Başlangıçtan sonra çalışma ağacında ses ölçeriyle ilgili başka değişiklikler belirdi (`scripts/olc_ses_gecikmesi.py`, `tests/test_ses_turu_tts_damgalari.py`, `automation/SES_GECIKMESI_20260909-2345.json`); bu görevde üretilmediler, değiştirilmediler ve bu işin commit kapsamına alınmazlar. Test sayıları çalıştırıldığı andaki ortak çalışma ağacına aittir.

**Karar:** yalnız PARÇA A'nın dar kabulü; persona korunuyor, taban kaydı 49/64, PARÇA B kapalı, push yok. Toplam kalıp sayısındaki 3→3 sonucu ve kalan tek hedef kusuru görünür bırakılıyor.
