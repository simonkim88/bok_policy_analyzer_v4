# pyright: basic, reportArgumentType=false
"""Deprecated compatibility wrapper for legacy ECOS loader imports."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from src.data.ecos_data_loader import EcosDataLoader

_loader: Optional[EcosDataLoader] = None


def _get_loader() -> EcosDataLoader:
    global _loader
    if _loader is None:
        _loader = EcosDataLoader()
    return _loader


def fetch_ecos_data(stat_code, item_code1, item_code2="?", cycle_type="M", start_date="20100101", end_date=None):
    """Legacy helper retained for compatibility; prefers configured indicators."""
    loader = _get_loader()
    indicator_map = {
        ("722Y001", "0101000"): loader.get_base_rate,
        ("901Y009", "0"): loader.get_cpi,
        ("200Y104", "1400"): loader.get_gdp,
    }

    func = indicator_map.get((stat_code, item_code1))
    if func is None:
        return pd.DataFrame(columns=["Date", "Value"])
    return func(start_date=start_date, end_date=end_date)


def get_base_rate():
    df = _get_loader().get_base_rate()
    if df.empty:
        return df

    monthly = (
        df.set_index("Date")
        .resample("MS")
        .last()
        .dropna()
        .reset_index()
    )
    monthly["Date"] = monthly["Date"].dt.strftime("%Y%m")
    return monthly[["Date", "Value"]]


def get_cpi():
    df = _get_loader().get_cpi()
    if df.empty:
        return df

    result = df.copy()
    result["Date"] = result["Date"].dt.strftime("%Y%m")
    return result[["Date", "Value"]]


def get_gdp_real():
    df = _get_loader().get_gdp()
    if df.empty:
        return df

    result = df.copy()
    result["Date"] = result["Date"].apply(
        lambda d: f"{d.year}Q{((d.month - 1) // 3) + 1}"
    )
    return result[["Date", "Value"]]
