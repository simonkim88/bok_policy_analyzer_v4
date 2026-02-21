# pyright: reportCallIssue=false, reportArgumentType=false, reportReturnType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""
Market Expectation vs Actual Decision Divergence Analysis.

Tracks how market expectations (implied from bond yields and tone)
diverge from actual BOK policy decisions over time.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class ExpectationDivergenceAnalyzer:
    def __init__(self) -> None:
        self.data_dir = PROJECT_ROOT / "data"

    def _load_daily_series(self, relative_csv: str, value_name: str) -> pd.DataFrame:
        path = self.data_dir / relative_csv
        df = pd.read_csv(path, usecols=["TIME", "DATA_VALUE"])
        df["Date"] = pd.to_datetime(df["TIME"].astype(str), format="%Y%m%d", errors="coerce")
        df[value_name] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
        out = df[["Date", value_name]].dropna().sort_values("Date")
        return out.groupby("Date", as_index=False).last()

    def _load_tone(self) -> pd.DataFrame:
        path = self.data_dir / "analysis/tone_index_results.csv"
        tone = pd.read_csv(path)
        tone["Date"] = pd.to_datetime(tone["meeting_date"], errors="coerce")
        tone["tone_index"] = pd.to_numeric(tone["tone_index"], errors="coerce")
        out = tone[["Date", "meeting_date_str", "tone_index"]].dropna().sort_values("Date")
        return out

    def calculate_implied_expectation(self) -> pd.DataFrame:
        """Estimate market rate expectations from yield curve."""
        y3 = self._load_daily_series("08_ecos/bond_yields/ktb_3y.csv", "KTB_3Y")
        y10 = self._load_daily_series("08_ecos/bond_yields/ktb_10y.csv", "KTB_10Y")
        base = self._load_daily_series("08_ecos/base_rate/base_rate.csv", "Base_Rate")

        df = y3.merge(y10, on="Date", how="inner")
        df = df.merge(base, on="Date", how="left")
        df["Base_Rate"] = df["Base_Rate"].ffill()

        df["Yield_Spread"] = df["KTB_10Y"] - df["KTB_3Y"]
        df["Implied_Policy_Rate"] = df["KTB_3Y"] - (0.25 * df["Yield_Spread"])
        df["Implied_Policy_Rate_Smoothed"] = df["Implied_Policy_Rate"].rolling(
            window=20,
            min_periods=1,
        ).mean()

        return df[
            [
                "Date",
                "Base_Rate",
                "KTB_3Y",
                "KTB_10Y",
                "Yield_Spread",
                "Implied_Policy_Rate",
                "Implied_Policy_Rate_Smoothed",
            ]
        ].copy()

    def calculate_divergence(self) -> pd.DataFrame:
        """Calculate cumulative divergence between expected and actual decisions."""
        implied = self.calculate_implied_expectation()
        tone = self._load_tone()

        meetings = pd.merge_asof(
            tone.sort_values("Date"),
            implied.sort_values("Date"),
            on="Date",
            direction="backward",
        )

        meetings["Tone_Adjustment"] = meetings["tone_index"] * 0.25
        meetings["Expected_Rate"] = meetings["Implied_Policy_Rate_Smoothed"] + meetings["Tone_Adjustment"]
        meetings["Actual_Rate"] = meetings["Base_Rate"]
        meetings["Divergence"] = meetings["Expected_Rate"] - meetings["Actual_Rate"]
        meetings["Cumulative_Divergence"] = meetings["Divergence"].cumsum()

        meetings["Expected_Direction"] = np.sign(meetings["Expected_Rate"].diff().fillna(0))
        meetings["Actual_Direction"] = np.sign(meetings["Actual_Rate"].diff().fillna(0))
        meetings["Direction_Match"] = meetings["Expected_Direction"] == meetings["Actual_Direction"]

        return meetings[
            [
                "Date",
                "meeting_date_str",
                "tone_index",
                "Expected_Rate",
                "Actual_Rate",
                "Divergence",
                "Cumulative_Divergence",
                "Expected_Direction",
                "Actual_Direction",
                "Direction_Match",
            ]
        ].copy()

    def get_surprise_events(self) -> pd.DataFrame:
        """Identify meetings with significant expectation surprise."""
        df = self.calculate_divergence()
        threshold = max(0.25, float(df["Divergence"].std(ddof=0) * 1.25))
        events = df[df["Divergence"].abs() >= threshold].copy()
        events["Surprise_Magnitude"] = events["Divergence"].abs()
        events["Surprise_Type"] = np.where(events["Divergence"] > 0, "Hawkish Surprise", "Dovish Surprise")
        return events.sort_values("Surprise_Magnitude", ascending=False).reset_index(drop=True)
