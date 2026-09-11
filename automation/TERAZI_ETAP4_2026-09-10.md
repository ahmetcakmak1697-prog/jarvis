# TERAZİ ETAP 4 — 2026-09-10

**Durum: ZİNCİR DURDU.** Kartın kayıtlı eski hits → kaybolan küme alt-küme kontrolü başarısız. ETAP 5 ve ETAP 6 başlamadı. Commit ve push yapılmadı; değişiklikler inceleme için çalışma ağacında bırakıldı.

Başlangıç HEAD: `ab0b2b1`. Kart: `automation/KART_TERAZI_ZINCIR_2.md`.
Bu rapor hiçbir vakayı “gerçek sızıntı” veya “yanlış alarm” diye sınıflandırmaz; yalnız kümeleri karşılaştırır.

## Önce kırmızı, sonra dar kaynak değişikliği

Yeni `tests/test_leak_method_scope.py::test_requested_risk_test_rollback_heading_is_not_a_leak` testi, “### 6. Risk, Test ve Geri Alma Yolu” cevabının sızıntı olmadığını iddia etti. Kaynak değişmeden **1 başarısız / 1 geçti** görüldü:

```
AssertionError: ['risk test ve', 'test ve geri', 've geri alma']
assert True is False
```

`eval/quality_scorer.py::_instruction_ngrams()`, mevcut korpusundan persona SSOT'undaki `_YONTEM` bloğundan türetilen n-gramları küme farkıyla çıkaracak şekilde değiştirildi. Elle n-gram listesi yazılmadı; üçüncü istisnanın gerekçesi docstring'e eklendi. Küme farkı kullanılması diğer blokların metnini birleştirip yeni sınır n-gramları üretmiyor.

`agents/persona.py` değiştirilmedi. Ölçüm öncesi/sonrası SHA-256 eşitliği doğrulandı. Diğer oturumun dosyalarına dokunulmadı.

Kaynak değişikliği sonrası yeni testler ve `tests/test_quality_scorer.py`: **99 geçti**. Buna `t1_mix_003` kayıtlı cevabını yakalayan test, `test_style_examples_are_not_leaks` ve `test_leak_corpus_is_derived_from_the_persona_ssot` dahildir. Mevcut testler değiştirilmedi.

## Mekanik kapsam ölçümü

- Eski korpus: **690** n-gram.
- Yeni korpus: **631** n-gram.
- Kaybolan küme: **59** n-gram.
- `_YONTEM`'den türeyen küme: **59** n-gram.
- İki kümenin eşitliği: **PASS**.
- Fazladan kayıp: **0**; eklenen n-gram: **0**.
- `automation/KALITE_*.json` kayıtları, alt dizinlerdeki kayıtlar da dahil: **13 dosya, 769 cevap**.
- Kayıtlı kaynakların SHA-256 değerleri değişmedi.
- Kayıtlı `score.prompt_leak` → yeni skor karşılaştırması: **14 True→False**.
- Bu geçişlerin eski hits alt-küme kontrolü: **10 PASS, 4 FAIL**.

Başarısız dört vaka aynı dosyada:
`automation/KALITE_qwen2.5_7b_20260904-2057.json`.

Her birinin eski hits listesi:
`['olmaktan mutluluk duyarim', 'size yardimci olmaktan', 'yardimci olmaktan mutluluk']`.

Bu üç n-gramın hiçbiri bu değişiklikte kaybolan 59 üyelik kümede bulunmuyor. Kartın açık DUR koşulu tetiklendi.

Ayrı tanı ölçümü olarak, bu değişiklikten hemen önceki dedektörle yeniden hesaplanan `prompt_leak` sonuçları da saklandı. O karşılaştırmada **10 True→False** var ve onunun da hits listesi kaybolan kümenin alt kümesi. Yukarıdaki dört vaka, değişiklikten önceki mevcut dedektörde de `False`. Bu ek bilgi kayıtlı eski skor şartını geçersiz kılmak için kullanılmadı; kabul ölçütü değiştirilmedi.

## Tüm kayıtlı True→False geçişleri

Aşağıdaki tablo doğrudan `sonra.json` içindeki mekanik sonuçlardan üretilmiştir.

| Dosya | id | Eski hits | Alt kume |
|---|---|---|---|
| automation/KALITE_alibayram_turkish-gemma-9b-v0.1_20260905-1624.json | t2_longform_001 | test ve geri, ve geri alma | PASS |
| automation/KALITE_alibayram_turkish-gemma-9b-v0.1_20260905-1624.json | t2_longform_002 | test ve geri, ve geri alma | PASS |
| automation/KALITE_alibayram_turkish-gemma-9b-v0.1_20260905-1624.json | t2_longform_004 | test ve geri, ve geri alma | PASS |
| automation/KALITE_deepseek_deepseek-chat_20260909-2127.json | t2_longform_004 | ve geri alma | PASS |
| automation/KALITE_deepseek_deepseek-chat_20260910-0053.json | t2_longform_001 | ve geri alma | PASS |
| automation/KALITE_deepseek_deepseek-chat_20260910-0053.json | t2_longform_002 | ve geri alma | PASS |
| automation/KALITE_deepseek_deepseek-chat_20260910-0053.json | t2_longform_003 | risk test ve, test ve geri, ve geri alma | PASS |
| automation/KALITE_deepseek_deepseek-chat_20260910-0053.json | t2_longform_004 | risk test ve, test ve geri, ve geri alma | PASS |
| automation/KALITE_llama3.1_latest_20260904-2053.json | t1_tr_011 | alternatif yol oner | PASS |
| automation/KALITE_llama3.1_latest_20260910-0103.json | t2_longform_004 | risk test ve, test ve geri, ve geri alma | PASS |
| automation/KALITE_qwen2.5_7b_20260904-2057.json | t1_tone_010 | olmaktan mutluluk duyarim, size yardimci olmaktan, yardimci olmaktan mutluluk | **FAIL** |
| automation/KALITE_qwen2.5_7b_20260904-2057.json | t1_tone_013 | olmaktan mutluluk duyarim, size yardimci olmaktan, yardimci olmaktan mutluluk | **FAIL** |
| automation/KALITE_qwen2.5_7b_20260904-2057.json | t1_tr_010 | olmaktan mutluluk duyarim, size yardimci olmaktan, yardimci olmaktan mutluluk | **FAIL** |
| automation/KALITE_qwen2.5_7b_20260904-2057.json | t1_tr_015 | olmaktan mutluluk duyarim, size yardimci olmaktan, yardimci olmaktan mutluluk | **FAIL** |

## Kapi ve kanit durumu

- Degisiklik oncesi tam suit: 1955 passed, 2 xfailed, 2 warnings (76.55 s).
- Degisiklik sonrasi odakli suit: 99 passed.
- Mekanik kapsam komutu exit code 1: AssertionError; zincir burada durdu.
- Etap sonu tam suit / ters sira / ruff kapisi calistirilmadi; tamamlanma iddiasi yok.
- Commit/push yok; ortak indexe dosya eklenmedi.
- ETAP 5 yeni model kosulari ve taban kaydi yapilmadi. ETAP 6 uygulanmadi.

Kanitlar: [once.json](TERAZI_ETAP4_2026-09-10/once.json), [sonra.json](TERAZI_ETAP4_2026-09-10/sonra.json), [tekrar calistirma betigi](TERAZI_ETAP4_2026-09-10/kapsam_olc.py).

Komut: PYTHONPATH repo kokuyken python -X utf8 -B automation/TERAZI_ETAP4_2026-09-10/kapsam_olc.py
