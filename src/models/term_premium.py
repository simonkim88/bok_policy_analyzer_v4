# pyright: reportCallIssue=false, reportArgumentType=false, reportReturnType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""
Term Premium Analysis Module.

Decomposes long-term yields into expected short rate + term premium:
KTB_10Y = E(base_rate_avg) + TermPremium
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TermPremiumAnalyzer:
    def __init__(self) -> None:
        self.data_dir = PROJECT_ROOT / "data"

    def _load_daily_series(self, relative_csv: str, value_name: str) -> pd.DataFrame:
        path = self.data_dir / relative_csv
        df = pd.read_csv(path, usecols=["TIME", "DATA_VALUE"])
        df["Date"] = pd.to_datetime(df["TIME"].astype(str), format="%Y%m%d", errors="coerce")
        df[value_name] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
        out = df[["Date", value_name]].dropna().sort_values("Date")
        return out.groupby("Date", as_index=False).last()

    def _to_monthly_last(self, df: pd.DataFrame, value_col: str) -> pd.DataFrame:
        out = df[["Date", value_col]].copy()
        out["Date"] = out["Date"].dt.to_period("M").dt.to_timestamp("M")
        out = out.groupby("Date", as_index=False).last()
        return out

    def _load_monthly_core(self) -> pd.DataFrame:
        y3 = self._load_daily_series("08_ecos/bond_yields/ktb_3y.csv", "KTB_3Y")
        y10 = self._load_daily_series("08_ecos/bond_yields/ktb_10y.csv", "KTB_10Y")
        base = self._load_daily_series("08_ecos/base_rate/base_rate.csv", "Base_Rate")

        y3_m = self._to_monthly_last(y3, "KTB_3Y")
        y10_m = self._to_monthly_last(y10, "KTB_10Y")
        base_m = self._to_monthly_last(base, "Base_Rate")

        merged = y3_m.merge(y10_m, on="Date", how="inner")
        merged = merged.merge(base_m, on="Date", how="inner")
        return merged.sort_values("Date").reset_index(drop=True)

    def calculate_simple(self) -> pd.DataFrame:
        """Simple spread-based term premium (10Y-3Y)."""
        df = self._load_monthly_core().copy()
        df["Spread"] = df["KTB_10Y"] - df["KTB_3Y"]
        df["TermPremium"] = df["Spread"]
        return df[["Date", "KTB_3Y", "KTB_10Y", "TermPremium", "Spread"]].copy()

    def calculate_expectations(self) -> pd.DataFrame:
        """Expectations-hypothesis inspired decomposition."""
        df = self._load_monthly_core().copy()

        # Expected short rate proxy:
        # blend current policy rate + market 3Y signal, then smooth.
        df["Expected_Short_Rate"] = (0.6 * df["KTB_3Y"] + 0.4 * df["Base_Rate"]).rolling(
            window=6,
            min_periods=1,
        ).mean()

        # Approximate 10Y implied by expectations only.
        df["Implied_10Y_Expectations"] = df["Expected_Short_Rate"]
        df["TermPremium"] = df["KTB_10Y"] - df["Implied_10Y_Expectations"]
        df["Spread"] = df["KTB_10Y"] - df["KTB_3Y"]

        return df[
            [
                "Date",
                "Base_Rate",
                "KTB_3Y",
                "KTB_10Y",
                "Expected_Short_Rate",
                "Implied_10Y_Expectations",
                "TermPremium",
                "Spread",
            ]
        ].copy()

    def get_summary(self) -> Dict[str, float | str]:
        """Current term premium state and interpretation."""
        simple = self.calculate_simple()
        model = self.calculate_expectations()

        latest_simple = simple.iloc[-1]
        latest_model = model.iloc[-1]

        premium = float(latest_model["TermPremium"])
        if premium > 0.5:
            interpretation = "Positive term premium: long rates price meaningful risk compensation."
        elif premium < -0.25:
            interpretation = "Negative term premium: long rates imply strong safe-asset demand."
        else:
            interpretation = "Near-neutral term premium: long rates close to expectations path."

        return {
            "date": latest_model["Date"].strftime("%Y-%m-%d"),
            "ktb_3y": float(latest_model["KTB_3Y"]),
            "ktb_10y": float(latest_model["KTB_10Y"]),
            "spread": float(latest_simple["Spread"]),
            "term_premium_simple": float(latest_simple["TermPremium"]),
            "term_premium_model": premium,
            "interpretation": interpretation,
        }
