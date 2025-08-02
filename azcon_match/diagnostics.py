"""
azcon_match.diagnostics
~~~~~~~~~~~~~~~~~~~~~~~
Developer-facing helpers for peeking inside the canonicalisation and
token-matching pipeline.  Useful when you want to understand *why* a
query hit (or missed) a particular master row.
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Set

import re
from . import preprocessing as pp


@dataclass
class CanonTrace:
    raw: str                       # original string
    lowered: str                   # lower-case + translit
    phrase_replaced: str           # after multi-word SYN replacements
    cleaned: str                   # punctuation stripped
    tokens: List[str]              # token list before stop-word removal
    tokens_nostop: List[str]       # after stop-word filter
    norm_tokens: List[str]         # after suffix strip + single-word SYN
    norm_set: Set[str]

    def as_dict(self) -> Dict:
        return asdict(self)


def trace(text: str) -> CanonTrace:
    """
    Return a CanonTrace with every intermediate step of canonisation.
    """
    raw = text or ""
    lowered = raw.lower().translate(pp.TRANSLIT)

    # multi-word synonym replacement (same loop as pp.canon)
    phrase_replaced = lowered
    for phrase, repl in pp.SYN.items():
        if " " in phrase:
            phrase_replaced = phrase_replaced.replace(phrase, repl)

    cleaned = re.sub(r"[^\w\s]", " ", phrase_replaced)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    tokens = cleaned.split()
    tokens_nostop = [t for t in tokens if t not in pp.STOP_AZ]
    norm_tokens = [pp.norm_token(t) for t in tokens_nostop]
    norm_set = set(norm_tokens)

    return CanonTrace(
        raw, lowered, phrase_replaced, cleaned,
        tokens, tokens_nostop, norm_tokens, norm_set
    )


def compare(a: str, b: str) -> Dict[str, any]:
    """
    Quick diff between two strings *after* canonicalisation.

    Returns:
        {
          'a_trace': CanonTrace,
          'b_trace': CanonTrace,
          'overlap': set(...),
          'only_in_a': set(...),
          'only_in_b': set(...),
          'coverage_a': float,   # same metric as matcher.coverage(a,b)
          'coverage_b': float,
          'critical_mismatch': bool,
        }
    """
    ta, tb = trace(a), trace(b)

    overlap = ta.norm_set & tb.norm_set
    only_a  = ta.norm_set - tb.norm_set
    only_b  = tb.norm_set - ta.norm_set

    crit_mismatch = any(
        (c in ta.norm_set) ^ (c in tb.norm_set) for c in pp.CRITICAL
    )

    return {
        "a_trace": ta,
        "b_trace": tb,
        "overlap": overlap,
        "only_in_a": only_a,
        "only_in_b": only_b,
        "coverage_a": pp.coverage(ta.norm_set, tb.norm_set),
        "coverage_b": pp.coverage(tb.norm_set, ta.norm_set),
        "critical_mismatch": crit_mismatch,
    }
# ─── diagnostics.py (append) ─────────────────────────────────────────
import pandas as pd
from pathlib import Path
from . import preprocessing as pp          # same module we already use

def overview():
    """
    Get a snapshot of current vocab resources.

    Returns a dict:
        {
          'synonyms':  pd.DataFrame(columns=['variant', 'canonical']),
          'generic':   list[str],
          'critical':  list[str],
        }
    """
    syn_df = (
        pd.DataFrame([(k, v) for k, v in pp.SYN.items() if k != v],
                     columns=["variant", "canonical"])
        .sort_values(["canonical", "variant"])
        .reset_index(drop=True)
    )

    return {
        "synonyms": syn_df,
        "generic":  sorted(pp.GENERIC),
        "critical": sorted(pp.CRITICAL),
    }


def save_overview(path: str | Path):
    """
    Dump the three lists to a single Excel file.

    Each sheet:
        • Synonyms – two-column table
        • GenericTokens
        • CriticalTokens
    """
    path = Path(path)
    data = overview()

    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        data["synonyms"].to_excel(xl, sheet_name="Synonyms", index=False)

        # write generic / critical as single-column sheets
        pd.DataFrame({"generic": data["generic"]}).to_excel(
            xl, sheet_name="GenericTokens", index=False
        )
        pd.DataFrame({"critical": data["critical"]}).to_excel(
            xl, sheet_name="CriticalTokens", index=False
        )

    return path
