"""Entity + fact extraction — regex NLP with confidence and intent calibration."""
from __future__ import annotations

import re
from typing import List, Tuple

_STOP = {
    "i", "im", "ive", "me", "my", "you", "your", "the", "a", "an", "and", "or",
    "but", "so", "if", "is", "are", "was", "be", "am", "do", "does", "did",
    "have", "has", "had", "will", "would", "can", "could", "it", "its", "this",
    "that", "what", "how", "when", "where", "why", "not", "no", "yes", "ok",
    "please", "thanks", "hello", "hi", "hey", "good", "great", "well", "just",
    "very", "really", "about", "with", "from", "for", "in", "on", "at", "to",
    "of", "as", "by", "user", "one", "two", "now", "today", "tomorrow",
}

_HEDGES = re.compile(r"\b(?:think|maybe|probably|guess|perhaps|wonder|suppose|doubt)\b", re.I)

# (pattern, relation, confidence, source)
_FACT_PATTERNS: List[Tuple[re.Pattern, str, float, str]] = [
    (re.compile(r"\bremember (?:that )?(.{5,100})", re.I), "remembered", 0.95, "stated"),
    (re.compile(r"\bmy ([\w\s\-]{2,30}?) (?:is|are|equals|=)\s+([^,.?!]{1,60})", re.I), "has_value", 0.60, "inferred"),
    (re.compile(r"\bi (?:am|'m)\s+(?:an?\s+)?([^,.?!]{2,50})", re.I), "is_a", 0.55, "inferred"),
    (re.compile(r"\bi (?:like|love|enjoy|prefer)\s+([^,.?!]{2,50})", re.I), "likes", 0.60, "inferred"),
    (re.compile(r"\bi (?:hate|dislike)\s+([^,.?!]{2,50})", re.I), "dislikes", 0.60, "inferred"),
    (re.compile(r"\bi (?:work|working) (?:on|at|for)\s+([^,.?!]{2,50})", re.I), "works_on", 0.55, "inferred"),
    (re.compile(r"\bi(?:'m| am) (?:building|making|creating)\s+([^,.?!]{2,50})", re.I), "builds", 0.55, "inferred"),
]

_PROPER_NOUN = re.compile(r"\b([A-Z][\w\-]*(?:\s+[A-Z][\w\-]*)+)\b")
_TECH_TOKEN = re.compile(r"\b([A-Z][a-z]+[A-Z][\w]*|[A-Z]{2,}[\w\-]*|[\w]+\.(?:js|py|ts|vrm|db))\b")


def _dedupe(items: List[str], cap: int) -> List[str]:
    seen: set = set()
    out = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out[:cap]


def extract_entities(text: str) -> List[str]:
    found: List[str] = []
    for rx in (_PROPER_NOUN, _TECH_TOKEN):
        for m in rx.finditer(text):
            tok = m.group(1).strip()
            if tok.lower() not in _STOP and len(tok) > 1:
                found.append(tok)
    for rx, _rel, _conf, _src in _FACT_PATTERNS:
        for m in rx.finditer(text):
            for g in m.groups():
                if g and len(g.strip()) > 1:
                    found.append(g.strip()[:60])
    return _dedupe(found, 12)


def extract_facts(text: str) -> List[Tuple[str, str, float, str]]:
    """Returns (relation, object, confidence, source) tuples against subject 'user'."""
    facts: List[Tuple[str, str, float, str]] = []
    has_hedge = bool(_HEDGES.search(text))

    for rx, relation, base_conf, source in _FACT_PATTERNS:
        for m in rx.finditer(text):
            groups = [g.strip().rstrip(".") for g in m.groups() if g and g.strip()]
            if not groups:
                continue

            obj = (
                f"{groups[0]} = {groups[1]}"[:80]
                if relation == "has_value" and len(groups) >= 2
                else groups[0][:80]
            )

            conf = base_conf
            src = source
            if has_hedge and source != "stated":
                conf = max(0.2, conf - 0.25)

            facts.append((relation, obj, conf, src))
    return facts[:5]
