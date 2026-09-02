"""Source Scorer - D1.4.

Scores web research sources before they can become memory candidates.

Goal:
- official / academic / trusted sources get higher scores
- weak / ad-heavy / forum-like sources get lower scores
- source score is metadata, not blind truth
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


@dataclass
class SourceScore:
    url: str
    domain: str
    score: int
    tier: str
    reasons: list[str]
    retrieved_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SourceScorer:
    """Rule-based source reliability scorer."""

    HIGH_TRUST_DOMAINS = [
        "openai.com",
        "anthropic.com",
        "deepmind.google",
        "googleblog.com",
        "microsoft.com",
        "nvidia.com",
        "meta.com",
        "ai.meta.com",
        "mistral.ai",
        "huggingface.co",
        "arxiv.org",
        "nature.com",
        "science.org",
        "mit.edu",
        "stanford.edu",
        "who.int",
        "europa.eu",
        "gov.tr",
        "gov.uk",
        "gov",
        "reuters.com",
        "apnews.com",
    ]

    MEDIUM_TRUST_DOMAINS = [
        "technologyreview.com",
        "wired.com",
        "theverge.com",
        "techcrunch.com",
        "bbc.com",
        "bbc.co.uk",
        "nytimes.com",
        "wsj.com",
        "bloomberg.com",
        "github.com",
        "docs.python.org",
        "developer.mozilla.org",
    ]

    LOW_TRUST_DOMAINS = [
        "pinterest.",
        "facebook.",
        "instagram.",
        "tiktok.",
        "quora.",
        "reddit.",
        "medium.com",
        "eksisozluk",
        "sozluk",
        "youtube.com",
        "webtekno.com",
        "shiftdelete.net",
        "donanimhaber.com",
        "tamindir.com",
        "forum",
        "blogspot.",
    ]

    BAD_PHRASES = [
        "casino",
        "bahis",
        "torrent",
        "apk",
        "crack",
        "adult",
        "escort",
        "bedava indir",
        "full indir",
        "sponsored",
        "advertorial",
    ]

    def score_source(self, url: str, title: str = "", snippet: str = "", retrieved_at: str | None = None) -> SourceScore:
        url = url or ""
        title = title or ""
        snippet = snippet or ""
        retrieved_at = retrieved_at or datetime.now().isoformat(timespec="seconds")

        domain = self._domain(url)
        text = f"{title} {snippet} {url}".lower()

        score = 50
        reasons: list[str] = []

        if not url:
            score -= 30
            reasons.append("missing_url")

        if self._domain_matches(domain, self.HIGH_TRUST_DOMAINS):
            score += 35
            reasons.append("high_trust_domain")

        elif self._domain_matches(domain, self.MEDIUM_TRUST_DOMAINS):
            score += 20
            reasons.append("medium_trust_domain")

        if self._domain_matches(domain, self.LOW_TRUST_DOMAINS):
            score -= 35
            reasons.append("low_trust_domain")

        if any(p in text for p in self.BAD_PHRASES):
            score -= 30
            reasons.append("bad_phrase")

        if len(snippet.strip()) < 40:
            score -= 15
            reasons.append("thin_snippet")

        if re.search(r"\b(official|documentation|docs|whitepaper|paper|research|standard)\b", text):
            score += 10
            reasons.append("documentation_or_research_signal")

        if re.search(r"\b(2025|2026|latest|current|güncel|guncel|son durum|release|changelog)\b", text):
            score += 5
            reasons.append("current_info_signal")

        score = max(0, min(100, score))
        tier = self._tier(score)

        return SourceScore(
            url=url,
            domain=domain,
            score=score,
            tier=tier,
            reasons=reasons or ["neutral"],
            retrieved_at=retrieved_at,
        )

    def score_many(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored = []
        for item in sources:
            if not isinstance(item, dict):
                continue

            scored.append(
                self.score_source(
                    url=str(item.get("url") or item.get("href") or ""),
                    title=str(item.get("title") or ""),
                    snippet=str(item.get("snippet") or item.get("body") or item.get("content") or ""),
                ).to_dict()
            )

        return sorted(scored, key=lambda x: x.get("score", 0), reverse=True)

    def _domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            return ""

    def _domain_matches(self, domain: str, patterns: list[str]) -> bool:
        return any(p in domain for p in patterns)

    def _tier(self, score: int) -> str:
        if score >= 80:
            return "high"
        if score >= 60:
            return "medium"
        if score >= 40:
            return "low"
        return "blocked"


if __name__ == "__main__":
    scorer = SourceScorer()

    samples = [
        {
            "url": "https://openai.com/api/pricing",
            "title": "OpenAI API Pricing",
            "snippet": "Official documentation and current API pricing information for models.",
        },
        {
            "url": "https://arxiv.org/abs/2501.00001",
            "title": "AI research paper",
            "snippet": "A research paper about language model evaluation and benchmark methodology.",
        },
        {
            "url": "https://random-blogspot.example.com/free-ai-tools",
            "title": "Best AI tools sponsored post",
            "snippet": "Sponsored list of tools, click here, free download.",
        },
        {
            "url": "https://reddit.com/r/something/comments/abc",
            "title": "User comment",
            "snippet": "Short.",
        },
    ]

    for item in scorer.score_many(samples):
        print(item)
