# Codex B10 durum - 2026-09-08

> Tarihsel durma kaydi. Ahmet dort eski testin guclendirilmesini ve B10
> kapanisini onayladi. Guncel sonuc: CODEX_V2_SONUC_2026-09-08.md.


B09 tamamlandi: 4778d72. Iki tam sirada 1870 passed + 1 xfailed;
Ruff 283; kayitli kalite 49/64; bagimsiz inceleme PASS. Push yok.

B10 TAMAMLANMADI; calisma degisiklikleri commit edilmedi.

## Kanit

- tests/test_b10_execution_budget_boundary.py: kaynak degismeden once
  4 FAILED. Yerel cevap sayaci tuketiyor; tek bulut hakki router'da
  tukendigi icin API'ye ulasamiyor; redaction/web policy arizasi buluta geciyor.
- Router erken tuketimi kaldirildi; mevcut APIBudgetGate API calistirma
  sinirinda tuketiyor. CostLedger para degil cagri sayaci olarak belgelendi.
- Iki guard exception dali guvenli engelleme karari donduruyor.
- Odak kosusu: 59 passed, 1 failed. Dort yeni B10 testi gecti.
- Basarisiz mevcut test:
  tests/test_d2_web_router_integration.py::test_policy_exception_fails_closed_to_existing_behavior
  Beklenti: ask_external / clarify / external_blocked.
  Gercek: web_research_blocked.
- py_compile ve git diff --check gecti. B10 tam-suite/ruff/ters-sira kapisi
  ve bagimsiz incelemesi henuz yapilmadi. B09 kapisi B10'a mal edilemez.

## Neden duruldu ve onerilen dar devam

Kart: "Bir sey patlarsa yaz ve dur (section 9)." Yeni test uyumsuzlugu
otomatik duzeltilmedi veya yeniden denenmedi.

Mevcut testin kabul ettigi ask_external guard arizasini disari acar.
external_blocked teknik olarak engeller, fakat AssistantExecutor bu karar
icin yanlis bicimde gunluk limit doldu mesaji verir. Oneri: eski testin
beklentisini web_research_blocked + guard_failed=True olarak guclendirmek;
fail-open kararini basari saymamak. Test contracts/ altinda veya *.spec.py
olmasa da bu yeni basarisizlik sonrasi devam Ahmet'e birakildi.

Degisiklik kapsami: agents/local_first_router.py, agents/cost_ledger.py,
tests/test_b10_execution_budget_boundary.py. Claude'un kaynaklarina,
park edilmis cephelere veya secret/config dosyalarina dokunulmadi.
