"""IO helpers to read master and query spreadsheets."""
import time
from typing import List, Any
import pandas as pd
from . import config, preprocessing as pp

def load_master() -> pd.DataFrame:
    """Load master database and pre‑compute canonical forms."""
    print("⏳ Loading master …")
    t0 = time.time()
    cols = [
        config.MASTER_TEXT_COL,
        config.MASTER_FLAG_COL,
        config.PRICE_COL,
        config.UNIT_COL,
    ]
    df = (
        pd.read_excel(config.MASTER_PATH, engine="openpyxl")[cols]
        .dropna(subset=[config.MASTER_TEXT_COL])
        .drop_duplicates()
    )

    df[config.MASTER_FLAG_COL] = (
        df[config.MASTER_FLAG_COL].fillna("").str.lower()
    )
    df[config.UNIT_COL] = df[config.UNIT_COL].fillna("").str.strip().str.lower()
    df[config.PRICE_COL] = pd.to_numeric(
        df[config.PRICE_COL], errors="coerce"
    )

    df["canon"]  = df[config.MASTER_TEXT_COL].map(pp.canon)
    df["tokens"] = df["canon"].str.split().map(set)

    print(f"Master rows: {len(df)}  ({time.time() - t0:.2f}s)\n")
    return df

def load_queries() -> list:
    """Return list of (text, flag, unit) tuples."""
    qdf = pd.read_excel(config.QUERY_PATH)
    need = [config.QUERY_TEXT_COL, config.QUERY_FLAG_COL, config.UNIT_COL]
    if any(c not in qdf.columns for c in need):
        raise ValueError("Query sheet missing required columns")

    return (
        qdf[need]
        .dropna(subset=[config.QUERY_TEXT_COL])
        .values
        .tolist()
    )
