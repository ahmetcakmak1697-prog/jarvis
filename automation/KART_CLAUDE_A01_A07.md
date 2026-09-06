# KART — Claude: ses/ajan hattındaki denetim bulguları

**Kime:** Claude Code (VS Code) · **Veren:** Ahmet, 2026-09-06
**Kaynak:** `automation/CODEX_A_DOGRULAMA_2026-09-06.md` — Codex'in bağımsız
denetimi, verdict **BLOCKER**

Bu kart, danışmanın bugün yazdığı kodda **bulunan gerçek kusurları** kapatır.
Kusurları danışman yazdı, Codex buldu, danışman üçünü bağımsız doğruladı.

**Dosya kümen:** `agent/local_agent.py` · `voice/voice_loop.py` ·
`scripts/olc_ses_gecikmesi.py` + testleri.
Codex aynı anda `tools/`, `memory/`, `agents/` üzerinde çalışıyor — **oraya
dokunma**, çakışırsınız.

---

## A-01 — BLOCKER: başarısız seslendirme "başarılı ölçüm" sayılıyor

`scripts/olc_ses_gecikmesi.py`

Codex sahte bir `ConnectionError("FAKE_NETWORK_DROP")` enjekte etti; hiç ses
üretilmediği hâlde tur **geçerli tam ölçüm** olarak kaydedildi:
`{"exit_code": 0, "mode": "tam", "reported_turns": 1, "error_visible": false}`

Üç ayrı sebep birleşiyor:

1. `VoiceIO.say()` istisnayı **bilerek** yutar — o katmanın sözleşmesi
   "ses asla tek yol değildir" (`voice_loop.py` docstring). Bu davranış
   **doğru ve değişmemeli**; hata ölçüm tarafında yakalanmalı.
2. `build_default_voice_io(enabled=True)` çağrısına `notify` verilmedi, bu
   yüzden VoiceIO'nun hata bildirimi varsayılan no-op'a gidiyor.
3. Kurulum istisna fırlatmadan `enabled=False` bir VoiceIO döndürse bile
   betik `ses_aktif=True` ve `mod="tam"` yazıyor.

**Yapılacak:** başarısız bir tur **geçerli ölçüm sayılmasın** ve hata
**görünsün**. Ölçüm hattı, ölçtüğü şey olmadığında sessizce başarılı
raporlayamaz — böyle bir hat, hat olmamasından kötüdür.

`notify` bağla ve gelen uyarıları tura işle. `mod="tam"` yalnız gerçekten
seslendirme yapıldıysa yazılsın. Başarılı bir turda **ilk ses olayının
kanıtı** olmalı.

## A-02 — CONCERN: ölçülen aralık PUSULA aralığı değil

Aynı dosya. Docstring "VAD sonu → ilk ses" ölçtüğünü söylüyor; kod başka iki
sınır kullanıyor:

- `t0` **`dinle()` çağrılmadan önce** başlıyor. Ama `vio.prompt()` mikrofon
  kaydını, kullanıcının konuşmasını, STT'yi ve gerekirse klavye beklemesini
  kapsıyor. PUSULA'nın aralığı **konuşma bitince** başlar.
- `t3` `say()` **dönünce** alınıyor; varsayılan oynatıcı sesin bitmesini
  bekliyor. PUSULA **ilk ses duyulduğunda** biter.

Codex'in deterministik senaryosu: gerçek aralık **700 ms**, betiğin ölçtüğü
**7200 ms** — on kat.

**Yapılacak:** ya ölçümü gerçek sınırlara taşı (VAD konuşma-sonu olayı → ilk
ses olayı), ya da **alan adlarını ölçtükleri şeye göre düzelt** ve docstring'in
iddiasını gerçeğe indir. İkisi arasında seçim yaparken B11'in dersini hatırla:
*yanlış etiketli bir ölçüm, doğru bir ölçüm gibi karar verdirir.*

Gerçek sınırlar ölçülemiyorsa bunu **açıkça yaz**; uydurma.

**Mevcut kayıt hakkında:** `automation/SES_GECIKMESI_20260906-2116.json`
dürüstçe `mod=kuru` diyor ve o sayılar (`p50 10954 ms`) `ajan.chat()` dönüş
süreleridir — geçerli, ama canlı ses gecikmesi değil. **Bu dosyayı yeniden
yazma.** Danışmanın "darboğaz prompt işleme" yorumu ölçüm değil çıkarımdı;
prompt/üretim dilimleri ayrılmadı. Dilimleme eklersen bu ayrı bir kazanç olur.

## A-06 — CONCERN: parmak izi commit'i görmüyor (PUSULA'yı doğrudan etkiliyor)

`agent/local_agent.py` — `_proje_ctx_imzasi()`

**Kanıtlandı.** Bu worktree'de:

```
HEAD mtime           : 2026-06-17   (üç ay önce, commit'lerde DEĞİŞMİYOR)
refs/heads/... mtime : 2026-09-06 21:21:20
son commit           : 2026-09-06 21:21:20
```

`HEAD` sembolik bir referans (`ref: refs/heads/auto/opencode-deepseek`) ve
commit atıldığında **içeriği de mtime'ı da değişmiyor**; değişen `refs/heads/`
altındaki dosya. Yani B06 düzeltmesi kurulma sebebini yapmıyor.

Ek eksikler (Codex):
- Yükleyicinin okuduğu `automation/T1_S2_FAIL_LOG.md` imzada yok.
- `gitdir: ../.git` gibi **göreli** bir işaretçi worktree köküne göre
  çözülmüyor (bu repoda mutlak yazılı, ama başka worktree'de kırılır).
- Worktree'lerde ortak `packed-refs` de izlenmiyor.

**Yapılacak:** HEAD sembolikse **işaret ettiği ref dosyasını** izle;
`packed-refs`'i de hesaba kat; yükleyicinin okuduğu **her** kaynağı imzaya al.
Doğrulama: gerçek bir commit atıldıktan sonra imza değişmeli — testi buna göre
yaz, dosyaya `touch` atarak değil.

## A-07 — CONCERN: PDF yönlendirmesi yanlış pozitif ve negatif üretiyor

`agent/local_agent.py` — `_pdf_istegi_mi()`

Doğrulandı:

```
README.md nedir?   -> True    (yanlış: kod sorusu PDF/RAG yoluna gidiyor)
belge ne demek?    -> True    (yanlış)
PDFyi oku          -> False   (yanlış: açık PDF isteği kaçıyor)
PDFleri incele     -> False   (yanlış)
```

İki ayrı sebep: `.md` uzantısını listeye almak fazla geniş; kısa "pdf" kökünde
kelime sınırı Türkçe ekleri kesiyor ("pdfyi", "pdfleri").

**Yapılacak:** uzantı listesini gerçek belge isteklerine daralt; "pdf" kökünde
Türkçe ekleri karşıla. Her iki yönü de teste bağla — mevcut
`tests/test_pdf_branch_hijack.py`'ye vaka ekle, var olanları silme.

## A-04 — CONCERN: nihai sorgunun veri sınıfı yeniden denetlenmiyor

`agent/local_agent.py` — `_egress_kapisi()`

Codex'in kanıtı: `paara rola FAKE_AUDIT_MARKER son haberler` girdisi,
kırpıldıktan sonra `parola FAKE_AUDIT_MARKER son ler` olarak sahte web aracına
**ulaştı — 1 çağrı**.

Sebep: `decide()` **orijinal** metne, `sanitize()` **dönüştürülmüş** sorguya
uygulanıyor. Nihai sorguya `decide()` uygulansaydı hassas sayılacaktı;
sanitizer boşluklu `parola X` biçimini temizlemiyor.

Danışman kırpma bozukluğunu "yalnız kalite hatası" diye sınıflandırmıştı;
bu birleşimde **güvenlik etkisi var** ve o triyaj yanlıştı.

**Yapılacak:** dışarı çıkacak **nihai** sorgu da veri sınıfı denetiminden
geçsin. Boşluklu hassas desen (`parola X`, `api key X`) hâlâ paylaşılan
`web_research_policy.py`'nin borcu — orayı bu kartta değiştirme, ama nihai
denetim eklenince mevcut `strict xfail` kırmızı yanarsa **söyle, gevşetme**.

---

## Disiplin

- Her madde için **önce düşen testi yaz, kırmızı olduğunu gör.**
- Her madde **ayrı commit**; commit mesajı neyin ölçüldüğünü yazsın.
- Kapı: `pytest tests -q` iki sırada, `ruff check .` **≤ 290**,
  taban testi hâlâ **49**.
- Commit yalnız isimli dosya. **Push yok.**
- `tools/`, `memory/`, `agents/`, `agent/jarvis_agent.py` → **Codex'te.**
- `jarvis_server.py` → park edilmiş cepheye komşu, Ahmet'in kararı bekliyor.
- Bir şey patlarsa **yaz ve dur** (§9).
