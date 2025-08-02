import re, json, pathlib
from typing import Set
import advertools as adv

# ── BASIC NORMALISATION COMPONENTS ─────────────────────────────────
TRANSLIT = str.maketrans("ğiçşöüə", "gıcsoae")
STOP_AZ  = adv.stopwords["azerbaijani"]

SUFFIXES = [
    "lanması", "lənməsi", "lanma", "lənmə", "nması", "nməsi",
    "ması", "məsi", "ların", "lərin", "ları", "ləri", "lar", "lər"
]
SUFFIXES.sort(key=len, reverse=True)   # longest first for greedy strip


def _base_norm(tok: str) -> str:
    """Lower‑case + transliterate + strip first matching suffix."""
    tok = tok.lower().translate(TRANSLIT)
    for suf in SUFFIXES:
        if tok.endswith(suf):
            tok = tok[:-len(suf)]
            break
    return tok

# ── LOAD SINGLE VOCAB FILE ─────────────────────────────────────────
VOCAB_PATH = pathlib.Path(__file__).with_name("vocab.json")
if not VOCAB_PATH.exists():
    raise FileNotFoundError(f"Vocabulary file {VOCAB_PATH} is missing")

with VOCAB_PATH.open(encoding="utf-8") as f:
    _v = json.load(f)

# Canonicalise synonyms first
SYN: dict[str, str] = {
    _base_norm(k): _base_norm(v) for k, v in _v.get("synonyms", {}).items()
}

# Add transliterated variants automatically
SYN.update({
    k.translate(TRANSLIT): v.translate(TRANSLIT)
    for k, v in list(SYN.items())
    if k.translate(TRANSLIT) != k
})

# Now we can define full norm_token that honours single‑word synonyms

def norm_token(token: str) -> str:
    base = _base_norm(token)
    return SYN.get(base, base)

# Build sets for matcher logic
GENERIC: Set[str]  = {norm_token(t) for t in _v.get("generic", [])}
CRITICAL: Set[str] = {norm_token(t) for t in _v.get("critical", [])}

# ── PUBLIC APIS USED BY MATCHER & DIAGNOSTICS ──────────────────────

def canon(text: str) -> str:
    """Canonicalise arbitrary description text (query or master row)."""
    if not isinstance(text, str):
        return ""

    # multi‑word synonym replacements (phrases containing spaces)
    lowered = text.lower().translate(TRANSLIT)
    for phrase, repl in SYN.items():
        if " " in phrase:
            lowered = lowered.replace(phrase, repl)

    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    tokens = [norm_token(t) for t in cleaned.split() if t not in STOP_AZ]
    return " ".join(tokens)


def coverage(a: Set[str], b: Set[str]) -> float:
    """Simple coverage metric used in matching logic."""
    return len(a & b) / max(1, len(a))
