# AHMET ONAYI BEKLEYENLER

Gözetimsiz çalışma sırasında karar kapısına gelindiğinde buraya yazılır ve
bağımsız bir sonraki işe geçilir. **Hiçbiri Claude tarafından kararlaştırılmaz.**

Açıldı: 2026-09-01, gözetimsiz oturum.

---

## KARARLANMIŞ (2026-09-01)

- **A1** Turkish-Gemma indirme → **HAYIR** (şimdilik). Önce mistral-nemo
  çıkışının kulakla etkisi görülecek; ölçülmemiş iyileştirmenin üstüne yeni
  değişken eklenmeyecek. 8K bağlam sınırı da gerçek risk.
- **A2** `runtime_profiles.json` → **EVET**: `local_main` → `llama3.1`,
  `local_small` → `qwen2.5:7b` (değişmiyor). Profil değişikliği tek başına
  dursun diye **en son, ayrı commit'te** uygulanıyor.
- **A3** SkillSpector → `run_python_code` ajan sözlüğünden çıkarıldı;
  `tools.py` değişmedi. `__pycache__` bulguları gürültü olarak işaretlendi.
- **A4** `_load_project_context()` dinamikleştirilmesi → **EVET**, sözleşme
  değişikliği onaylandı.

---

## A5 — `analyze_file` de ulaşılamıyor (YENİ)

`_detect_tool()` yalnız 6 araca yol açıyor; `analyze_file` ajanın araç
sözlüğünde ama hiçbir tetikleyiciye bağlı değil — `run_python_code` ile aynı
durumda. `exec`/`eval` içermediği için A3 turunda **kapsam dışı bırakıldı**.

**Seçenekler:** (a) sözlükten çıkar (ölü yüzey azalır), (b) bir
`TOOL_TRIGGERS["analyze_file"]` girdisi ekle (araç kullanılabilir hâle gelir).
`tests/test_local_agent_tool_surface.py::test_no_loaded_tool_is_unreachable`
bunu bilinen istisna olarak tutuyor; karar verilince liste güncellenir.

---

## A1 — Turkish-Gemma-9b-T1 indirilsin mi?

**Karar:** Model indirme insan kapısıdır (§9 + kartın açık talimatı).

`docs/HARDWARE_AND_LOCAL_LLM_RESEARCH.md` §4'e göre 1450 soruluk insan
değerlendirmesinde **%68,65** ile Qwen3-32B'yi (%67,20) geçmiş; Q4 ~5,5 GB,
8 GB'a sığıyor. Zayıflığı: Gemma 2 tabanlı, bağlam **8K**, araç kullanımı
zayıf — JARVIS'in prompt'u (persona + proje durumu + hafıza) 8K'yı zorlayabilir.

**Durum:** İndirilmedi. Kıyas yalnız kurulu üç modelle yapıldı.
**Gerekli olan:** "indir" / "indirme" kararı.

---

## A2 — `runtime_profiles.json` değişikliği (ADIM C çıktısı)

**Karar:** Aktif profildeki `local_main` değişikliği yalnız Ahmet'in.

Kıyas tablosu `automation/MODEL_KIYASI_0901.md`. Kazanan ilan edilmedi,
dosyaya dokunulmadı. Profilin kendi notu zaten *"local_main icin Qwen'e
gecis HALA benchmark bekliyor"* diyor — benchmark artık var, karar yok.

**Gerekli olan:** Tablodaki veriye bakıp `local_main` kalsın mı, değişsin mi.

---

## A3 — SkillSpector bulguları (4 madde)

`automation/SKILLSPECTOR_RAPORU.md` sonundaki karar listesi. Özet:

1. `run_python_code` aracı (`exec()`, `tools.py:482`) kalsın mı?
2. `auto_updater.py` canlı mı, ölü kod mu? (park edilmiş AUTO cephesi olabilir)
3. Kurulu skill'ler güncellendiğinde yeniden taransın mı?
4. `agents/retrieval_priority.py:9` "Memory Manipulation" bulgusu elle bakılsın.

**Hiçbiri düzeltilmedi** — kart "sınıflandır, düzeltme" diyordu.

---

## A4 — `_load_project_context()` eskimiş durum bloğu

**Sorun:** `agent/local_agent.py` içinde proje durumu sabit yazılı ve üç satır
`roadmap_state.json`'la çelişiyor (E1-S4 DONE ama kodda BEKLIYOR; E1-S5
APPROVED ama kodda "henuz kod yok"; T1-S2 Resolved ama kodda BEKLIYOR).
Model bu tabloyu her turda görüyor ve canlı testte *"tasarım aşamasındayız"*
dedi — halüsinasyon değil, eskimiş veriyi sadakatle tekrar etmesi.

**Neden kendi başıma yapmadım:** `tests/test_local_agent_grounding.py` içindeki
`test_load_project_context_includes_known_state` bu eskimiş dizeleri
(`"BEKLIYOR"`, `"Proaktif bildirimler: CANLI DEGIL"`) **sabitliyor**. Düzeltmek
o testi değiştirmeyi gerektirir → §13.1 sözleşme kilidi → sorulur.

**Önerim:**
1. Durum `roadmap_state.json`'dan okunsun (`steps[].status` + `evidence.verdict`),
   sabit metin kalmasın. Dosya yoksa/bozuksa blok **boş** dönsün — uydurma
   durum yerine hiç durum yeğdir (mevcut fail-safe deseni korunur).
2. `JARVIS_PROACTIVE_ENABLED=0` iddiası **doğru**, kaldırılmasın.
3. Test, sabit dizeler yerine "blok `roadmap_state.json`'daki verdict'lerle
   tutarlı" iddiasına çevrilsin.

**Ayrıca bulunan test kusuru (ADIM 1'de raporlanmıştı):**
`_call_real_loader()` gerçek metodu bir **replikayla** değiştiriyor
(`patch.object(LocalJarvisAgent, "_load_project_context", patched_loader)`).
176/186/203/213 satırlarındaki dört test gerçek fonksiyonu değil, testin
içine yazılmış kopyayı ölçüyor. Replika, gerçekteki `T1_S2_FAIL_LOG.md`
okumasını ve "Onemli Kural" bloğunu içermiyor — yani zaten sapmış.

**Gerekli olan:** Yukarıdaki 3 maddeye onay; sonra test-first uygulanır.
