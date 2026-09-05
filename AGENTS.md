# AGENTS.md — işaretçi, anayasa değil

**Bu reponun anayasası [`CLAUDE.md`](CLAUDE.md)'dir.** Adı ne olursa olsun,
bu repoda kod üreten her ajan (Codex / Claude Code / GPT / Gemini / Cursor)
oradaki kurallara uyar. Kurallar orada; burada değil.

Burada hiçbir kural **tekrarlanmıyor** ve tekrarlanmayacak.

## Bu dosya neden kopya değil

Bir zamanlar kopyaydı. `graphify install` 2026-09-05 16:37'de `CLAUDE.md`'yi
buraya birebir kopyaladı (16.910 bayt, yalnız "Claude" → "Codex" isim
değişiklikleriyle). Aynı gün Ahmet kararıyla işaretçiye indirildi.

Sebep: **anayasanın iki kopyası olamaz.** Kopyalar kaçınılmaz olarak sapar.
`CLAUDE.md` §13.2'deki test/lint/kalite taban sayıları neredeyse her turda
güncelleniyor; ilk güncellemede kopya sessizce eskir ve bir sonraki ajan
yanlış olanı okur. Bu, `CLAUDE.md` §12'nin belgelediği çelişki sınıfının
aynısıdır (Letta, `HUMAN_NEEDED.md` ↔ `roadmap_state.json`, `auto_runner`) —
farkı, bu kez çelişecek olanın **anayasanın kendisi** olması.

## ⚠️ `graphify install` bunu tekrar üzerine yazarsa

`graphify install` yeniden çalıştırılırsa bu dosyayı `CLAUDE.md`'nin **tam
kopyasıyla yeniden üzerine yazar.** Bu beklenen bir davranıştır, hata değil.

**Doğru davranış: dosyayı yine bu işaretçiye indirmek.** Kopyayı güncellemek,
`CLAUDE.md` ile senkron tutmaya çalışmak ya da iki dosyayı ayrı ayrı bakımda
tutmak — üçü de yanlış.

Bu dosya `.gitignore`'a **bilerek eklenmedi.** Takip edildiği için, graphify
onu bir daha üretirse `git status` büyük bir diff gösterir: sessiz sapma,
gürültülü bir uyarıya döner. Ignore edilseydi kopya geri gelir ve kimse
görmezdi.

---

*Kayıt: 2026-09-05, Ahmet kararı (seçenek b+c).
Gerekçe: `automation/KART_ikinci_anayasa.md`.
Aynı kurulumun ürettiği `.agents/` ve `.codex/` dizinleri `.gitignore`'a
eklendi; içerikleri silinmedi.*
