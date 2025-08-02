"""Core matching logic with numeric‑consistency guard."""
import statistics, time
from typing import List, Tuple, Dict, Any

import pandas as pd
from rapidfuzz import fuzz

from . import config
from . import preprocessing as pp
from . import numeric   # NEW helper for number‑unit extraction

# type alias for one hit row
Match = Tuple[str, int, float, str]  # (text, score, price, unit)

def score_row(q_tokens: set, s_tokens: set, q_can: str, s_can: str) -> int:
    """Compute fuzzy score plus critical‑token penalty."""
    score = fuzz.token_set_ratio(q_can, s_can)
    if any((c in q_tokens) ^ (c in s_tokens) for c in pp.CRITICAL):
        score = int(score * 0.70)
    return score

def find_matches(
    query_raw: str,
    query_flag: str,
    query_unit: str,
    master_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Return match stats + hit details for a single query string."""

    # ── canonicalise query once ───────────────────────────────
    q_can    = pp.canon(query_raw)
    q_tokens = set(q_can.split())

    q_nums   = numeric.extract(query_raw)  # list[(val, unit)]
    has_qnum = bool(q_nums)

    q_flag  = str(query_flag).strip().lower() if isinstance(query_flag, str) else ""
    q_unit  = str(query_unit).strip().lower() if isinstance(query_unit, str) else ""

    # ── candidate prefilter on flag / unit ───────────────────
    cand = master_df
    if q_flag in {"product", "service", "mix"}:
        cand = cand[cand[config.MASTER_FLAG_COL] == q_flag]
    if q_unit:
        cand = cand[cand[config.UNIT_COL] == q_unit]

    hits: List[Match] = []

    for s_text, s_flag, price, unit, s_can, s_tokens in cand.itertuples(index=False, name=None):
        # token overlap gate
        if not (q_tokens & (s_tokens - pp.GENERIC)):
            continue

        # coverage gate
        if pp.coverage(q_tokens, s_tokens) < config.MIN_COVER:
            continue

        # numeric guard --------------------------------------
        if has_qnum:
            c_nums = numeric.extract(s_text)
            if c_nums:
                # both have numbers → require at least one exact pair
                if not any(q == c for q in q_nums for c in c_nums):
                    continue        # size mismatch → skip
            else:
                # query has number, row lacks → mild penalty
                penal_factor = 0.80
            # apply penalty later if defined
        else:
            c_nums = []
            penal_factor = 1.0
        # -----------------------------------------------------

        score = score_row(q_tokens, s_tokens, q_can, s_can)
        score = int(score * penal_factor)

        if score < config.THRESHOLD:
            continue

        hits.append((s_text, score, price, unit))

    # ── priced hits and stats ────────────────────────────────
    priced_hits = [
        (t, sc, pr, u)
        for t, sc, pr, u in hits
        if sc >= config.PRICE_AVG_MIN_SCORE and pd.notna(pr)
    ]
    prices = [pr for _, _, pr, _ in priced_hits]

    return {
        "raw": query_raw,
        "canonical": q_can,
        "unit": q_unit or "?",
        "hits": hits,
        "priced_hits": priced_hits,
        "prices": prices,
    }

def summarise(result: Dict[str, Any]) -> str:
    """Pretty‑print multiline summary suitable for CLI."""
    lines: List[str] = []
    lines.append(f"Query: {result['raw']}  (unit:{result['unit']})")

    if result["prices"]:
        med = statistics.median(result["prices"])
        avg = sum(result["prices"]) / len(result["prices"])
        unit_out = result["priced_hits"][0][3] if result["priced_hits"] else "?"
        lines.append(
            f"   → Median: {med:.2f} ₼ / {unit_out}   |   Mean: {avg:.2f} ₼   (n={len(result['prices'])})"
        )
        if config.SHOW_MATCHES:
            for t, sc, pr, u in result["priced_hits"]:
                lines.append(f"      • {t} – {pr} ₼ / {u}  (score {sc})")
    else:
        lines.append(f"   – no priced matches ≥ {config.PRICE_AVG_MIN_SCORE} –")
        if config.SHOW_MATCHES:
            for t, sc, pr, u in sorted(result["hits"], key=lambda x: x[1], reverse=True)[: config.TOP_N]:
                price_txt = f"{pr} ₼" if pd.notna(pr) else "—"
                lines.append(f"      · {t} – {price_txt} / {u}  (score {sc})")

    return "\n".join(lines)
