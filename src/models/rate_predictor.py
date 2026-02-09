"""
금리 결정 확률 예측 모델

BOK Tone Index를 기반으로 다음 금통위의 금리 결정(인상/동결/인하) 확률을 예측합니다.

모델: 다항 로짓 (Multinomial Logit) 또는 순서형 로짓 (Ordered Logit)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timedelta


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# sklearn을 선택사항으로 변경 (Python 3.14에서 빌드 문제 해결)
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score, TimeSeriesSplit
    from sklearn.metrics import classification_report, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn을 사용할 수 없습니다. 간단한 휴리스틱 방법을 사용합니다.")

try:
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = DATA_DIR / "models"


@dataclass
class PredictionResult:
    """예측 결과"""
    meeting_date: str
    prob_hike: float      # 인상 확률
    prob_hold: float      # 동결 확률
    prob_cut: float       # 인하 확률
    predicted_action: str  # 예측된 행동
    confidence: float      # 신뢰도
    tone_index: float      # 현재 톤 지수


class RatePredictor:
    """금리 결정 확률 예측기"""

    # 한국은행 기준금리 변동 이력 (실제 데이터)
    # 출처: 한국은행 ECOS
    RATE_HISTORY = {
        # 2021년
        "2021_01_15": (0.50, "hold"),
        "2021_02_25": (0.50, "hold"),
        "2021_04_15": (0.50, "hold"),
        "2021_05_27": (0.50, "hold"),
        "2021_07_15": (0.50, "hold"),
        "2021_08_26": (0.75, "hike"),  # +25bp
        "2021_10_12": (0.75, "hold"),
        "2021_11_25": (1.00, "hike"),  # +25bp
        # 2022년
        "2022_01_14": (1.25, "hike"),  # +25bp
        "2022_02_24": (1.25, "hold"),
        "2022_04_14": (1.50, "hike"),  # +25bp
        "2022_05_26": (1.75, "hike"),  # +25bp
        "2022_07_13": (2.25, "hike"),  # +50bp (빅스텝)
        "2022_08_25": (2.50, "hike"),  # +25bp
        "2022_10_12": (3.00, "hike"),  # +50bp (빅스텝)
        "2022_11_24": (3.25, "hike"),  # +25bp
        # 2023년
        "2023_01_13": (3.50, "hike"),  # +25bp
        "2023_02_23": (3.50, "hold"),
        "2023_04_11": (3.50, "hold"),
        "2023_05_25": (3.50, "hold"),
        "2023_07_13": (3.50, "hold"),
        "2023_08_24": (3.50, "hold"),
        "2023_10_19": (3.50, "hold"),
        "2023_11_30": (3.50, "hold"),
        # 2024년
        "2024_01_11": (3.50, "hold"),
        "2024_02_22": (3.50, "hold"),
        "2024_04_12": (3.50, "hold"),
        "2024_05_23": (3.50, "hold"),
        "2024_07_11": (3.50, "hold"),
        "2024_08_22": (3.50, "hold"),
        "2024_10_11": (3.25, "cut"),   # -25bp
        "2024_11_28": (3.00, "cut"),   # -25bp
        # 2025년
        "2025_01_16": (3.00, "hold"),
        "2025_02_25": (2.75, "cut"),   # -25bp
        "2025_04_17": (2.75, "hold"),
        "2025_05_29": (2.50, "cut"),   # -25bp
        "2025_07_10": (2.50, "hold"),
        "2025_08_28": (2.50, "hold"),
        "2025_10_23": (2.50, "hold"),
        "2025_11_27": (2.50, "hold"),
    }

    ACTION_MAP = {"hike": 1, "hold": 0, "cut": -1}
    ACTION_LABELS = {1: "인상", 0: "동결", -1: "인하"}

    def __init__(self):
        """예측기 초기화"""
        self.model = None
        if SKLEARN_AVAILABLE:
            self.scaler = StandardScaler()
        else:
            self.scaler = None
        self.is_fitted = False

        # 디렉토리 생성
        MODEL_DIR.mkdir(parents=True, exist_ok=True)

    def load_tone_data(self) -> pd.DataFrame:
        """톤 분석 결과 로드"""
        tone_path = DATA_DIR / "analysis" / "tone_index_results.csv"

        if not tone_path.exists():
            raise FileNotFoundError(f"톤 분석 결과 파일이 없습니다: {tone_path}")

        df = pd.read_csv(tone_path)
        return df

    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        학습 데이터 준비

        Args:
            df: 톤 분석 결과 DataFrame

        Returns:
            (X, y) 튜플
        """
        X_list = []
        y_list = []

        for _, row in df.iterrows():
            meeting_date = row['meeting_date_str']

            # 해당 회의의 금리 결정 확인
            if meeting_date not in self.RATE_HISTORY:
                continue

            rate, action = self.RATE_HISTORY[meeting_date]
            y = self.ACTION_MAP[action]

            # 특성 추출
            features = [
                row['tone_index'],
                row['hawkish_score'],
                row['dovish_score'],
                row['hawkish_terms_count'],
                row['dovish_terms_count'],
            ]

            X_list.append(features)
            y_list.append(y)

        return np.array(X_list), np.array(y_list)

    def train(self, df: Optional[pd.DataFrame] = None):
        """
        모델 학습

        Args:
            df: 톤 분석 결과 DataFrame (None이면 파일에서 로드)
        """
        if df is None:
            try:
                df = self.load_tone_data()
            except FileNotFoundError:
                logger.warning("톤 분석 결과 파일이 없습니다. 휴리스틱 모드로 작동합니다.")
                self.is_fitted = False
                return

        if not SKLEARN_AVAILABLE:
            logger.info("scikit-learn이 없어 간단한 룰 기반 방법을 사용합니다.")
            self.is_fitted = True  # 룰 기반이므로 학습 없이 사용 가능
            return

        X, y = self.prepare_training_data(df)

        if len(X) < 10:
            logger.warning("학습 데이터가 부족합니다")
            self.is_fitted = True  # 룰 기반으로 fallback
            return

        # 스케일링
        X_scaled = self.scaler.fit_transform(X)

        # 로지스틱 회귀 (다항 분류)
        self.model = LogisticRegression(
            solver='lbfgs',
            max_iter=1000
        )

        self.model.fit(X_scaled, y)
        self.is_fitted = True

        # 학습 결과 평가
        y_pred = self.model.predict(X_scaled)
        accuracy = accuracy_score(y, y_pred)

        logger.info(f"모델 학습 완료: 정확도 {accuracy:.2%}")
        logger.info(f"학습 샘플 수: {len(X)}")

        # 교차 검증 (시계열 분할)
        try:
            tscv = TimeSeriesSplit(n_splits=3)
            cv_scores = cross_val_score(self.model, X_scaled, y, cv=tscv)
            logger.info(f"교차 검증 정확도: {cv_scores.mean():.2%} (±{cv_scores.std():.2%})")

            return {
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'n_samples': len(X)
            }
        except Exception as e:
            logger.warning(f"교차 검증 실패: {e}")
            return {
                'accuracy': accuracy,
                'cv_mean': 0.0,
                'cv_std': 0.0,
                'n_samples': len(X)
            }

    def predict(self, tone_result: Dict) -> PredictionResult:
        """
        다음 금통위 금리 결정 확률 예측

        Args:
            tone_result: 톤 분석 결과 (딕셔너리)

        Returns:
            PredictionResult 객체
        """
        # sklearn이 없거나 모델이 학습되지 않았으면 룰 기반 예측 사용
        if not SKLEARN_AVAILABLE or not self.is_fitted or self.model is None:
            return self._rule_based_predict(tone_result)

        # 특성 추출
        features = np.array([[
            tone_result.get('tone_index', 0),
            tone_result.get('hawkish_score', 0),
            tone_result.get('dovish_score', 0),
            tone_result.get('hawkish_terms_count', 0),
            tone_result.get('dovish_terms_count', 0),
        ]])

        # 스케일링
        features_scaled = self.scaler.transform(features)

        # 확률 예측
        probs = self.model.predict_proba(features_scaled)[0]
        classes = self.model.classes_

        # 클래스별 확률 매핑
        prob_dict = dict(zip(classes, probs))
        prob_hike = prob_dict.get(1, 0.0)
        prob_hold = prob_dict.get(0, 0.0)
        prob_cut = prob_dict.get(-1, 0.0)

        # 예측 행동
        pred_class = self.model.predict(features_scaled)[0]
        predicted_action = self.ACTION_LABELS.get(pred_class, "동결")
        confidence = max(probs)

        return PredictionResult(
            meeting_date=tone_result.get('meeting_date_str', ''),
            prob_hike=prob_hike,
            prob_hold=prob_hold,
            prob_cut=prob_cut,
            predicted_action=predicted_action,
            confidence=confidence,
            tone_index=tone_result.get('tone_index', 0)
        )

    def _rule_based_predict(self, tone_result: Dict) -> PredictionResult:
        """
        규칙 기반 예측 (모델이 없을 때 사용)

        톤 지수에 따른 단순 규칙:
        - tone > 0.2: 인상 가능성 높음
        - -0.2 < tone < 0.2: 동결 가능성 높음
        - tone < -0.2: 인하 가능성 높음
        """
        tone = tone_result.get('tone_index', 0)

        if tone > 0.2:
            prob_hike = 0.6 + tone * 0.3
            prob_hold = 0.3 - tone * 0.1
            prob_cut = 0.1 - tone * 0.05
            predicted_action = "인상"
        elif tone < -0.2:
            prob_cut = 0.6 + abs(tone) * 0.3
            prob_hold = 0.3 - abs(tone) * 0.1
            prob_hike = 0.1 - abs(tone) * 0.05
            predicted_action = "인하"
        else:
            prob_hold = 0.7
            prob_hike = 0.15 + tone * 0.2
            prob_cut = 0.15 - tone * 0.2
            predicted_action = "동결"

        # 확률 정규화
        total = prob_hike + prob_hold + prob_cut
        prob_hike /= total
        prob_hold /= total
        prob_cut /= total

        return PredictionResult(
            meeting_date=tone_result.get('meeting_date_str', ''),
            prob_hike=prob_hike,
            prob_hold=prob_hold,
            prob_cut=prob_cut,
            predicted_action=predicted_action,
            confidence=max(prob_hike, prob_hold, prob_cut),
            tone_index=tone
        )

    def evaluate_historical(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        과거 데이터에 대한 예측 정확도 평가

        Returns:
            평가 결과 DataFrame
        """
        if df is None:
            df = self.load_tone_data()

        results = []

        for _, row in df.iterrows():
            meeting_date = row['meeting_date_str']

            # 실제 금리 결정 확인
            if meeting_date not in self.RATE_HISTORY:
                continue

            rate, actual_action = self.RATE_HISTORY[meeting_date]

            # 예측
            prediction = self.predict(row.to_dict())

            # 예측 vs 실제 비교
            actual_label = self.ACTION_LABELS.get(self.ACTION_MAP[actual_action], "동결")
            is_correct = prediction.predicted_action == actual_label

            results.append({
                'meeting_date': meeting_date,
                'tone_index': row['tone_index'],
                'actual_action': actual_label,
                'predicted_action': prediction.predicted_action,
                'prob_hike': prediction.prob_hike,
                'prob_hold': prediction.prob_hold,
                'prob_cut': prediction.prob_cut,
                'confidence': prediction.confidence,
                'is_correct': is_correct,
                'actual_rate': rate
            })

        result_df = pd.DataFrame(results)

        if len(result_df) > 0:
            accuracy = result_df['is_correct'].mean()
            logger.info(f"과거 데이터 예측 정확도: {accuracy:.2%} ({result_df['is_correct'].sum()}/{len(result_df)})")

        return result_df

    def get_latest_prediction(self) -> Optional[PredictionResult]:
        """최신 의사록 기반 다음 금통위 예측"""
        try:
            df = self.load_tone_data()
            latest = df.iloc[-1].to_dict()
            return self.predict(latest)
        except Exception as e:
            logger.error(f"예측 실패: {e}")
            return None


def main():
    """메인 실행"""
    print("=" * 70)
    print("한국은행 금리 결정 확률 예측 모델")
    print("=" * 70)

    predictor = RatePredictor()

    # 모델 학습
    print("\n[1] 모델 학습")
    train_result = predictor.train()
    if train_result:
        print(f"  - 학습 정확도: {train_result['accuracy']:.2%}")
        print(f"  - 교차 검증: {train_result['cv_mean']:.2%} (±{train_result['cv_std']:.2%})")

    # 과거 데이터 평가
    print("\n[2] 과거 데이터 예측 평가")
    eval_df = predictor.evaluate_historical()

    if len(eval_df) > 0:
        print(f"\n{'회의일':<15} {'톤':<8} {'실제':<6} {'예측':<6} {'신뢰도':<8} {'정확'}")
        print("-" * 60)
        for _, row in eval_df.iterrows():
            correct_mark = "O" if row['is_correct'] else "X"
            print(f"{row['meeting_date']:<15} {row['tone_index']:+.3f}  "
                  f"{row['actual_action']:<6} {row['predicted_action']:<6} "
                  f"{row['confidence']:.1%}    {correct_mark}")

    # 최신 예측
    print("\n[3] 다음 금통위 예측")
    prediction = predictor.get_latest_prediction()
    if prediction:
        print(f"\n기준 의사록: {prediction.meeting_date}")
        print(f"현재 톤 지수: {prediction.tone_index:+.3f}")
        print(f"\n다음 금통위 금리 결정 확률:")
        print(f"  - 인상: {prediction.prob_hike:.1%}")
        print(f"  - 동결: {prediction.prob_hold:.1%}")
        print(f"  - 인하: {prediction.prob_cut:.1%}")
        print(f"\n예측: {prediction.predicted_action} (신뢰도: {prediction.confidence:.1%})")


if __name__ == "__main__":
    main()
