# KART — B01: `calculate` sandbox kaçışını kapat

**Durum:** ✅ KAPANDI — commit `7b85d8c` (2026-09-06). `eval` kaldırıldı, yerine
AST beyaz listesi kondu; istismar danışman tarafından yeniden sınandı ve
reddediliyor. Nitelik erişimi, comprehension, lambda ve `__import__`/`open`/
`globals` düğüm türü seviyesinde kapalı. Kapı: pytest 1732 (iki sıra), ruff 292.

**Öncelik:** Codex denetiminde 1. sıra
**Kaynak:** İki bağımsız denetim (envanter §H + Codex başmühendis raporu B01),
danışman tarafından **çalışan istismarla doğrulandı** (2026-09-06)

---

## Kanıt — bu teorik değil

`tools/tools.py:509`:

```python
result = eval(expression, {"__builtins__": {}}, safe_dict)
```

`{"__builtins__": {}}` bir sandbox sanılıyor; değil. Danışman kendi makinesinde
doğruladı:

```
calculate("2**10")                              -> 1024            (normal, doğru)
calculate("[c for c in ().__class__.__base__.__subclasses__()
           if c.__name__=='catch_warnings'][0].__init__
           .__globals__['__builtins__']['sum']([20,22])")   -> 42  (KAÇIŞ)
```

`sum` yerine `open`, `__import__('os').system`, `exec` de aynı `__globals__`
zincirinden erişilebilir. Nesne grafiği üzerinden Python'un tüm yerleşik
işlevlerine ulaşılıyor.

**Neden önemli — tek satırlık kod değil, bir yüzey:**
- `calculate`, yerel ajana yükleniyor ve `hesapla/calculate` tetikleyicisinden
  doğrudan çağrılıyor (`agent/local_agent.py:364`). `run_python_code`'un yerel
  listeden çıkarılmış olması **bu ikinci yolu kapatmıyor.**
- Codex B02 ile birleşince (kimlik doğrulamasız `gui.py`, `0.0.0.0:5000`)
  ağdan erişilebilir bir uzak kod çalıştırmaya dönüşür. **B02 ayrı kart**;
  bu kart yalnız B01.

---

## Yapılacak iş — CLAUDE.md §4: önce hatayı üreten test

### 1. Düşen testi yaz, KIRMIZI olduğunu gör

`tests/` altına yeni dosya. En az şu vakalar, **LocalJarvisAgent'tan gerçek
`calculate`'e kadar** gelen girdiyle (araç sözlüğüne bakmakla yetinme —
Codex'in özel uyarısı):

- **Kaçış reddedilir:** yukarıdaki `catch_warnings` ifadesi artık sayı değil
  hata döndürüyor. `__class__`, `__base__`, `__subclasses__`, `__globals__`,
  `__init__`, `__builtins__` içeren her ifade reddediliyor.
- **Normal çalışmaya devam:** `2**10`, `sqrt(144)`, `sin(pi/4)*100`,
  `abs(-5)`, `round(3.14159, 2)` — hepsi doğru sonuç.
- **Sınır:** aşırı büyük işlem (`9**9**9` gibi) reddediliyor ya da
  sınırlanıyor — kaynak tükenmesi de bir saldırı.

Testi çalıştır, **kırmızı olduğunu gör.** Yeşil bir test hiçbir şey kanıtlamaz.

### 2. Kaynağı düzelt — adopt-over-build (§9)

**Önce mevcut çözümü ara.** `eval`'i elle "güvenli" kılmaya çalışmak (kara
liste) tarihsel olarak hep delinmiştir — kara liste değil **beyaz liste**
gerekir. Sıra:

1. Python standart kütüphanesi yeterli mi? `ast.parse(expr, mode="eval")` +
   izin verilen düğüm türleri beyaz listesi (`BinOp`, `UnaryOp`, `Num`,
   `Call` yalnız izinli math adlarına). Bağımlılık eklemez.
2. Olgun bir kütüphane gerekiyorsa (`simpleeval` gibi) **Ahmet'e sor** —
   yeni bağımlılık kararı bu kartta verilmez (§9, DANIŞMAN MODU).

`__builtins__` numarasını yamamak, `getattr` filtresi eklemek gibi
**nokta çözümler yasak** — kaçış yüzeyi `eval`'in kendisi.

### 3. Kapıyı geç

Test yeşile döndüğünde: `pytest tests -q` **iki sırada**, `ruff check .` ≤ 293.

---

## Yasaklar

1. **Yalnız `calculate` ve onun testi.** B02–B12 ayrı kartlar; onlara dokunma.
   Özellikle `gui.py`'ye, `agent/jarvis_agent.py`'ye, router'a dokunma.
2. **Test sözleşmesi değişmez** (§13.1). Var olan bir testi gevşeterek değil,
   kaynağı düzelterek geçir.
3. **Yeni bağımlılık kararı yok** — gerekiyorsa dur ve Ahmet'e sor.
4. `.env` okunmaz. Auto-fix retry yok: patlarsa yaz ve dur (§9).
5. Envanterin bulduğu diğer `exec`/`eval` noktalarına (`tools/tools.py:482`
   `run_python_code`, API yolu) **dokunma** — onlar B09'un konusu, ayrı kart.

## Bitti sayılma ölçütü

- `catch_warnings` istismarı artık hata döndürüyor; envanterdeki ve Codex'teki
  ifade sınandı.
- Normal hesaplar hâlâ doğru — regresyon yok.
- Düşen test önce yazıldı, kırmızı görüldü, sonra geçti.
- Düzeltme LocalJarvisAgent → calculate tam yolunda sınandı, yalnız fonksiyon
  birim testinde değil.
- `pytest tests -q` yeşil (iki sırada), `ruff check .` ≤ 293.
- Commit: yalnız isimli dosya. Push yok. **Bittiğinde dur.**
