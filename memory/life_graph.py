"""memory/life_graph.py — çıkarılan olguları kalıcı hafızaya yazar ve geri okur.

Eşik 3'ün ikinci yarısı. `memory/entity_extractor.py` konuşmadan olguyu
çıkarır; bu modül onu `world/people.json`'a ve append-only olay dökümüne
işler, sonra "Eşimin doğum günü ne zamandı?" sorusuna **gerçek kayıttan**
cevap verir.

**İki eksenli güvenlik (CLAUDE.md §7) burada uygulanır:**

* *Güven ekseni*: içerik Ahmet'in kendi ağzından geliyor → güvenilir.
* *Veri sınıfı*: sağlık ve finans **hassastır** → otomatik kalıcı hafızaya
  yazılmaz, onay kuyruğuna gider. Hassas değer olay dökümüne düz metin
  olarak da yazılmaz; yalnızca kategorisi kaydedilir.

**En kritik sözleşme: `recall()` UYDURMAZ.** Kayıt yoksa `found=False` döner
ve nedenini söyler. Denetimde ölçülen asıl kusur buydu — model "Geçen hafta
ne konuştuk?" sorusuna olmamış bir konuşma anlatıyordu. Bu modülün varlık
sebebi, modele tahmin ettirmek yerine **zemin** vermektir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.data_classifier import _fold_tr
from memory.entity_extractor import ExtractedFact, extract

__all__ = ["RecallResult", "LifeGraph", "remember_exchange"]

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_PEOPLE = _REPO / "world" / "people.json"
_DEFAULT_EVENTS = _REPO / "memory" / "life_events.jsonl"

#: İlişki -> Türkçe etiket. Zemin metnini insanın okuduğu gibi yazmak için.
_ETIKET = {
    "es": "eş", "ogul": "oğul", "kiz": "kız", "anne": "anne",
    "baba": "baba", "kardes": "kardeş", "self": "kendisi",
}

_NITELIK_ETIKET = {"ad": "adı", "dogum_gunu": "doğum günü"}


@dataclass
class RecallResult:
    """Hatırlama sonucu. `found=False` iken `answer` daima boştur."""

    found: bool
    answer: str = ""
    source: Optional[str] = None
    reason: Optional[str] = None


class LifeGraph:
    """`world/people.json` üzerinde yaşayan kişisel yaşam grafiği."""

    def __init__(
        self,
        people_path: Path | str | None = None,
        events_path: Path | str | None = None,
    ) -> None:
        self.people_path = Path(people_path) if people_path else _DEFAULT_PEOPLE
        self.events_path = Path(events_path) if events_path else _DEFAULT_EVENTS

    # ------------------------------------------------------------------ #
    # Okuma
    # ------------------------------------------------------------------ #

    def _load(self) -> Dict[str, Any]:
        try:
            veri = json.loads(self.people_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": 1, "people": []}
        if not isinstance(veri, dict):
            return {"schema_version": 1, "people": []}
        veri.setdefault("schema_version", 1)
        veri.setdefault("people", [])
        return veri

    def people(self) -> List[Dict[str, Any]]:
        return list(self._load().get("people", []))

    def events(self) -> List[Dict[str, Any]]:
        if not self.events_path.exists():
            return []
        olaylar = []
        for satir in self.events_path.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if not satir:
                continue
            try:
                olaylar.append(json.loads(satir))
            except json.JSONDecodeError:
                continue
        return olaylar

    # ------------------------------------------------------------------ #
    # Yazma
    # ------------------------------------------------------------------ #

    def _write_people(self, veri: Dict[str, Any]) -> None:
        self.people_path.parent.mkdir(parents=True, exist_ok=True)
        self.people_path.write_text(
            json.dumps(veri, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _append_event(self, olay: Dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(olay, ensure_ascii=False) + "\n")

    def remember(self, fact: ExtractedFact) -> Dict[str, Any]:
        """Bir olguyu hafızaya işler.

        Hassas olgular kalıcı hafızaya **yazılmaz**; `review_queue` hedefiyle
        geri döner ve çağıran taraf onları onay kuyruğuna koyar.
        """
        ts = datetime.now(timezone.utc).isoformat()

        if fact.sensitive:
            # Hassas değer olay dökümüne DÜZ METİN yazılmaz: yalnız kategori
            # ve zaman. Ne konuşulduğu değil, konuşulduğu kaydedilir.
            self._append_event({
                "ts": ts,
                "category": fact.category,
                "relation": fact.relation,
                "sensitive": True,
                "stored": False,
                "raw_text": "[hassas içerik kaydedilmedi]",
            })
            return {
                "stored": False,
                "target": "review_queue",
                "reason": f"sensitive category: {fact.category}",
            }

        veri = self._load()
        kisiler = veri["people"]

        if fact.relation == "self":
            hedef = self._ensure_person(kisiler, "ahmet", "Ahmet", None)
        else:
            hedef = self._ensure_person(
                kisiler,
                f"{fact.relation}_of_ahmet",
                fact.value if fact.attribute == "ad" else None,
                fact.relation,
            )

        nitelikler = hedef.setdefault("attributes", {})
        if fact.attribute == "ad":
            hedef["name"] = fact.value
        elif fact.attribute:
            nitelikler[fact.attribute] = fact.value
        else:
            hedef.setdefault("notes", [])
            if fact.raw_text not in hedef["notes"]:
                hedef["notes"].append(fact.raw_text)

        kaynak = hedef.setdefault("provenance", [])
        kaynak.append({"ts": ts, "raw_text": fact.raw_text,
                       "confidence": fact.confidence})

        self._write_people(veri)
        self._append_event({
            "ts": ts,
            "category": fact.category,
            "relation": fact.relation,
            "attribute": fact.attribute,
            "value": fact.value,
            "sensitive": False,
            "stored": True,
            "raw_text": fact.raw_text,
        })
        return {"stored": True, "target": "life_graph", "reason": None}

    @staticmethod
    def _ensure_person(kisiler, kisi_id, ad, relation) -> Dict[str, Any]:
        for k in kisiler:
            if k.get("id") == kisi_id:
                return k
        yeni = {"id": kisi_id, "name": ad or kisi_id}
        if relation:
            yeni["relation"] = relation
        kisiler.append(yeni)
        return yeni

    # ------------------------------------------------------------------ #
    # Hatırlama — uydurma yasak
    # ------------------------------------------------------------------ #

    def recall(self, question: str) -> RecallResult:
        """Soruyu gerçek kayıttan cevaplar. Kayıt yoksa açıkça söyler."""
        if not question or not question.strip():
            return RecallResult(found=False, reason="boş soru")

        fold = _fold_tr(question)

        iliski = None
        for anahtar in ("esim", "karim", "kocam", "oglum", "kizim",
                        "annem", "babam", "kardesim"):
            if anahtar in fold:
                iliski = {
                    "esim": "es", "karim": "es", "kocam": "es",
                    "oglum": "ogul", "kizim": "kiz", "annem": "anne",
                    "babam": "baba", "kardesim": "kardes",
                }[anahtar]
                break

        if iliski is None:
            return RecallResult(
                found=False,
                reason="soruda tanınan bir kişi yok; bu konuda kayıt yok",
            )

        kisi = next((k for k in self.people() if k.get("relation") == iliski), None)
        if kisi is None:
            return RecallResult(
                found=False,
                reason=f"{_ETIKET.get(iliski, iliski)} hakkında kayıt yok",
            )

        nitelikler = kisi.get("attributes", {})
        if "dogum" in fold:
            deger = nitelikler.get("dogum_gunu")
            if not deger:
                return RecallResult(
                    found=False,
                    reason=f"{_ETIKET.get(iliski)} doğum günü için kayıt yok",
                )
            return RecallResult(
                found=True,
                answer=f"{_ETIKET.get(iliski, iliski).capitalize()} doğum günü: {deger}",
                source="life_graph",
            )

        ad = kisi.get("name")
        if ad and ad != kisi.get("id"):
            return RecallResult(
                found=True,
                answer=f"{_ETIKET.get(iliski, iliski).capitalize()} adı: {ad}",
                source="life_graph",
            )

        return RecallResult(
            found=False,
            reason=f"{_ETIKET.get(iliski, iliski)} için kayıtlı ayrıntı yok",
        )

    def recall_context(self) -> str:
        """Modele verilecek **zemin** metni.

        Uydurmayı engellemenin doğru yolu modele "uydurma" demek değil, ona
        gerçeği vermektir. Kayıt yoksa boş string döner — boş zemin, yanlış
        zeminden iyidir.
        """
        satirlar: List[str] = []
        for kisi in self.people():
            iliski = kisi.get("relation")
            if not iliski:
                continue
            etiket = _ETIKET.get(iliski, iliski)
            ad = kisi.get("name")
            if ad and ad != kisi.get("id"):
                satirlar.append(f"- {etiket} adı: {ad}")
            for nitelik, deger in (kisi.get("attributes") or {}).items():
                satirlar.append(
                    f"- {etiket} {_NITELIK_ETIKET.get(nitelik, nitelik)}: {deger}"
                )
        return "\n".join(satirlar)


def remember_exchange(
    user_msg: str,
    graph: Optional[LifeGraph] = None,
) -> List[Dict[str, Any]]:
    """Bir konuşma turundan olguları çıkarıp hafızaya işler.

    `main.py` bunu her turda çağırır. Hassas olgular kalıcı yazılmaz; sonuç
    listesinde `target="review_queue"` olarak görünürler.
    """
    graph = graph or LifeGraph()
    return [graph.remember(olgu) for olgu in extract(user_msg)]
