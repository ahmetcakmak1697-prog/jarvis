"""Web Research Policy - D1.2.

IntentRouter + QuerySanitizer for safe web research.

This module decides whether a user query may leave the local machine.

Rules:
- local project/file/code questions stay local
- sensitive/private data never goes to web search
- explicit web requests are allowed if sanitized
- current/volatile info requests are allowed if sanitized
- everything else defaults to local/no-web
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class WebResearchDecision:
    allow: bool
    mode: str
    reason: str
    sanitized_query: str
    risk_flags: list[str]
    query_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WebResearchPolicy:
    """Rule-based safety gate before web research."""

    MODE_LOCAL_FILE = "local_file"
    MODE_LOCAL_CODE = "local_code"
    MODE_PROJECT_QA = "project_qa"
    MODE_GENERAL_QA = "general_qa"
    MODE_EXPLICIT_WEB = "explicit_web"
    MODE_CURRENT_INFO = "current_info"
    MODE_SENSITIVE_BLOCKED = "sensitive_blocked"

    EXPLICIT_WEB_TERMS = [
        "internetten bak",
        "webden bak",
        "google'dan bak",
        "google dan bak",
        "online bak",
        "ara?t?r",
        "arastir",
        "g?ncel ara?t?r",
        "guncel arastir",
        "son durumu ara?t?r",
        "son durumu arastir",
        "web ara?t?r",
        "web arastir",
    ]

    CURRENT_INFO_TERMS = [
        "g?ncel",
        "guncel",
        "son durum",
        "son haber",
        "bug?n",
        "bugun",
        "bu hafta",
        "bu ay",
        "2025",
        "2026",
        "fiyat",
        "kur",
        "d?viz",
        "doviz",
        "stok",
        "mevzuat",
        "kanun",
        "y?netmelik",
        "yonetmelik",
        "api de?i?ti mi",
        "api degisti mi",
        "model s?r?m?",
        "model surumu",
        "release",
        "changelog",
    ]

    LOCAL_PROJECT_TERMS = [
        "jarvis",
        "proje",
        "projede",
        "proje i?inde",
        "proje icinde",
        "dosyada",
        "klas?rde",
        "klasorde",
        "repo",
        "git status",
        "git log",
        "commit",
        "task_executor",
        "jarvis_brain",
        "jarvis_server",
        "telegram_agent",
        "project_intelligence",
        "project_reporter",
    ]

    LOCAL_FILE_PATTERNS = [
        r"\b[\w\-]+\.(py|json|txt|md|ps1|env|db|sqlite)\b",
        r"\b[A-Za-z]:\\",
        r"\.\\",
        r"/mnt/data/",
        r"/home/",
        r"memory/",
        r"tools/",
        r"agents/",
    ]

    CODE_TERMS = [
        "kod",
        "class ",
        "def ",
        "function",
        "traceback",
        "exception",
        "stack trace",
        "import ",
        "endpoint",
        "api/tasks",
        "sat?r",
        "satir",
        "select-string",
        "get-content",
        "powershell",
    ]

    SENSITIVE_PATTERNS = [
        r"(?i)\b(api[_-]?key|token|secret|password|passwd|parola|?ifre|sifre)\b",
        r"(?i)\bTELEGRAM_BOT_TOKEN\b",
        r"(?i)\bTAVILY_API_KEY\b",
        r"(?i)\bOPENAI_API_KEY\b",
        r"(?i)\.env\b",
        r"(?i)\btc\s*kimlik\b",
        r"(?i)\bkimlik\s*numaram\b",
        r"(?i)\btelefon\s*numaram\b",
        r"(?i)\badresim\b",
        r"(?i)\biban\b",
        r"(?i)\bkredi\s*kart[?i]\b",
        r"(?i)\bssh\s+key\b",
        r"(?i)-----BEGIN .*PRIVATE KEY-----",
    ]

    REDACTION_PATTERNS = [
        (r"(?i)(api[_-]?key|token|secret|password|passwd|parola|?ifre|sifre)\s*[:=]\s*['\"]?[^'\"\s]+", r"\1=[REDACTED]"),
        (r"(?i)(TELEGRAM_BOT_TOKEN|TAVILY_API_KEY|OPENAI_API_KEY)\s*[:=]\s*['\"]?[^'\"\s]+", r"\1=[REDACTED]"),
        (r"(?i)(telefon\s*numaram)\s*[:=]?\s*[\d\s\-\+\(\)]{6,}", r"\1 [REDACTED]"),
        (r"(?i)(iban)\s*[:=]?\s*[A-Z]{2}\d[\w\s]{10,}", r"\1 [REDACTED]"),
    ]

    def decide(self, query: str, context: dict[str, Any] | None = None) -> WebResearchDecision:
        original = query or ""
        context = context or {}
        q = original.strip()
        q_low = self._normalize(q)

        risk_flags: list[str] = []

        if not q:
            return self._decision(False, self.MODE_GENERAL_QA, "Bo? sorgu.", "", risk_flags)

        sensitive_hits = self._sensitive_hits(q)
        if sensitive_hits:
            risk_flags.extend(sensitive_hits)
            sanitized = self.sanitize(q)
            return self._decision(
                False,
                self.MODE_SENSITIVE_BLOCKED,
                "Sorgu hassas/?zel bilgi i?eriyor; web'e g?nderilmedi.",
                sanitized,
                risk_flags,
            )

        if self._is_local_file_query(q, q_low):
            return self._decision(
                False,
                self.MODE_LOCAL_FILE,
                "Sorgu lokal dosya/proje i?eri?iyle ilgili; web yerine lokal ara?lar kullan?lmal?.",
                q,
                ["local_file"],
            )

        if self._is_code_query(q, q_low):
            return self._decision(
                False,
                self.MODE_LOCAL_CODE,
                "Sorgu kod/hata/proje analiziyle ilgili; web'e ??k?lmad?.",
                q,
                ["local_code"],
            )

        if self._is_project_query(q_low) and not self._has_explicit_web(q_low):
            return self._decision(
                False,
                self.MODE_PROJECT_QA,
                "Sorgu JARVIS/proje ba?lam?nda; a??k web iste?i yok.",
                q,
                ["project_local"],
            )

        sanitized = self.sanitize(q)

        if self._has_explicit_web(q_low):
            return self._decision(
                True,
                self.MODE_EXPLICIT_WEB,
                "Kullan?c? a??k?a web ara?t?rmas? istedi; sorgu sanitizer'dan ge?ti.",
                sanitized,
                risk_flags,
            )

        if self._needs_current_info(q_low):
            return self._decision(
                True,
                self.MODE_CURRENT_INFO,
                "Sorgu g?ncel/de?i?ken bilgi gerektiriyor; sorgu sanitizer'dan ge?ti.",
                sanitized,
                risk_flags,
            )

        return self._decision(
            False,
            self.MODE_GENERAL_QA,
            "A??k web iste?i veya g?ncel bilgi ihtiyac? yok; lokal cevap tercih edildi.",
            sanitized,
            risk_flags,
        )

    def sanitize(self, query: str) -> str:
        sanitized = query or ""
        for pattern, repl in self.REDACTION_PATTERNS:
            try:
                sanitized = re.sub(pattern, repl, sanitized)
            except re.error:
                # Defensive guard: malformed sanitizer pattern must not crash policy.
                continue
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized

    def _decision(
        self,
        allow: bool,
        mode: str,
        reason: str,
        sanitized_query: str,
        risk_flags: list[str],
    ) -> WebResearchDecision:
        return WebResearchDecision(
            allow=allow,
            mode=mode,
            reason=reason,
            sanitized_query=sanitized_query,
            risk_flags=list(dict.fromkeys(risk_flags)),
            query_hash=self._hash(sanitized_query),
        )

    def _normalize(self, text: str) -> str:
        table = str.maketrans({
            "?": "i", "?": "i",
            "?": "g", "?": "g",
            "?": "u", "?": "u",
            "?": "s", "?": "s",
            "?": "o", "?": "o",
            "?": "c", "?": "c",
        })
        return (text or "").translate(table).lower()

    def _hash(self, query: str) -> str:
        return hashlib.sha256((query or "").encode("utf-8", errors="ignore")).hexdigest()[:16]

    def _has_explicit_web(self, q_low: str) -> bool:
        return any(self._normalize(term) in q_low for term in self.EXPLICIT_WEB_TERMS)

    def _needs_current_info(self, q_low: str) -> bool:
        return any(self._normalize(term) in q_low for term in self.CURRENT_INFO_TERMS)

    def _is_project_query(self, q_low: str) -> bool:
        return any(self._normalize(term) in q_low for term in self.LOCAL_PROJECT_TERMS)

    def _is_code_query(self, q: str, q_low: str) -> bool:
        return any(self._normalize(term) in q_low for term in self.CODE_TERMS)

    def _is_local_file_query(self, q: str, q_low: str) -> bool:
        if any(re.search(pattern, q) for pattern in self.LOCAL_FILE_PATTERNS):
            return True
        return any(self._normalize(term) in q_low for term in ["dosya", "klasor", "klas?r", "satir", "sat?r"])

    def _sensitive_hits(self, q: str) -> list[str]:
        hits = []
        for pattern in self.SENSITIVE_PATTERNS:
            try:
                if re.search(pattern, q):
                    label = pattern.replace("(?i)", "")[:40]
                    hits.append(label)
            except re.error:
                continue
        return hits


if __name__ == "__main__":
    policy = WebResearchPolicy()

    samples = [
        "Merhaba nas?ls?n?",
        "jarvis_brain.py i?inde research_and_learn nerede ge?iyor?",
        "internetten bak: OpenAI son model fiyatlar? 2026",
        "g?ncel dolar kuru nedir?",
        "TELEGRAM_BOT_TOKEN=123456 bunu webden kontrol et",
        "Telefon numaram 555 ile ba?l?yor, bunu ara?t?r",
        "Python traceback hatas?n? dosyada bul",
        "OpenAI API de?i?ti mi?",
    ]

    for sample in samples:
        d = policy.decide(sample)
        print("---")
        print(sample)
        print(d.to_dict())
