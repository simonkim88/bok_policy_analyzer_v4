"""
향상된 BOK Tone Index 분석 모듈 (V2)

기존 톤 분석에 시장 반응과 뉴스 감성을 통합:

Tone_Adjusted = α · Tone_Text + β · Market_Reaction + γ · News_Sentiment

where:
  - α (Text): 텍스트 기반 톤 지수 가중치 (기본 0.5)
  - β (Market): 시장 반응 가중치 (기본 0.3)
  - γ (News): 뉴스 감성 가중치 (기본 0.2)
  - α + β + γ = 1.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import sys

# 기존 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.nlp.tone_analyzer import ToneAnalyzer, ToneResult
from src.nlp.sentiment_dict import SentimentDictionary
from src.data.database import DatabaseManager
from src.data.ecos_connector import EcosConnector
from src.data.bigkinds_api_client import BigKindsClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "analysis"


@dataclass
class EnhancedToneResult(ToneResult):
    """향상된 톤 분석 결과"""
    tone_adjusted: float = 0.0                    # 조정된 톤 지수
    market_reaction_score: float = 0.0            # 시장 반응 점수
    news_sentiment_score: float = 0.0             # 뉴스 감성 점수
    alpha: float = 0.5                            # 텍스트 가중치
    beta: float = 0.3                             # 시장 가중치
    gamma: float = 0.2                            # 뉴스 가중치
    market_reaction_details: Dict = field(default_factory=dict)
    news_sentiment_details: Dict = field(default_factory=dict)


class EnhancedToneAnalyzer(ToneAnalyzer):
    """향상된 BOK 톤 분석기"""

    def __init__(
        self,
        dictionary: Optional[SentimentDictionary] = None,
        db_manager: Optional[DatabaseManager] = None,
        ecos_connector: Optional[EcosConnector] = None,
        bigkinds_client: Optional[BigKindsClient] = None,
        alpha: float = 0.5,
        beta: float = 0.3,
        gamma: float = 0.2
    ):
        """
        향상된 톤 분석기 초기화

        Args:
            dictionary: 감성 사전
            db_manager: 데이터베이스 매니저
            ecos_connector: ECOS 커넥터
            bigkinds_client: BigKinds 클라이언트
            alpha: 텍스트 톤 가중치
            beta: 시장 반응 가중치
            gamma: 뉴스 감성 가중치
        """
        super().__init__(dictionary)

        self.db = db_manager or DatabaseManager()
        self.ecos = ecos_connector or EcosConnector(db_manager=self.db)
        self.bigkinds = bigkinds_client or BigKindsClient()

        # 가중치 검증
        total = alpha + beta + gamma
        if abs(total - 1.0) > 0.01:
            logger.warning(f"가중치 합계가 1.0이 아닙니다: {total:.3f}. 정규화합니다.")
            alpha = alpha / total
            beta = beta / total
            gamma = gamma / total

        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        # 데이터베이스에서 가중치 로드 (있으면)
        params = self.db.get_model_parameters()
        if 'alpha' in params:
            self.alpha = params['alpha']
        if 'beta' in params:
            self.beta = params['beta']
        if 'gamma' in params:
            self.gamma = params['gamma']

        logger.info(f"향상된 톤 분석기 초기화 (α={self.alpha}, β={self.beta}, γ={self.gamma})")

    def _calculate_market_reaction(
        self,
        meeting_date: str
    ) -> Tuple[float, Dict]:
        """
        시장 반응 계산

        Args:
            meeting_date: 회의 날짜 (YYYY-MM-DD 또는 YYYY_MM_DD)

        Returns:
            (market_reaction_score, details)
        """
        # 날짜 형식 통일
        meeting_date_std = meeting_date.replace('_', '-')

        try:
            # ECOS 커넥터를 통해 시장 반응 계산
            market_reaction = self.ecos.calculate_market_reaction(
                meeting_date_std,
                days_before=5,
                days_after=10
            )

            details = {
                'meeting_date': meeting_date_std,
                'days_window': '[-5, +10]',
                'score': market_reaction
            }

            return market_reaction, details

        except Exception as e:
            logger.warning(f"시장 반응 계산 실패: {e}")
            return 0.0, {}

    def _calculate_news_sentiment(
        self,
        meeting_date: str
    ) -> Tuple[float, Dict]:
        """
        뉴스 감성 계산

        Args:
            meeting_date: 회의 날짜

        Returns:
            (news_sentiment_score, details)
        """
        # 날짜 형식 통일
        meeting_date_std = meeting_date.replace('_', '-')

        try:
            # BigKinds 클라이언트를 통해 뉴스 감성 계산
            news_sentiment = self.bigkinds.calculate_news_sentiment_aggregate(
                meeting_date_std,
                days_before=5,
                days_after=5
            )

            details = {
                'meeting_date': meeting_date_std,
                'days_window': '[-5, +5]',
                'score': news_sentiment
            }

            return news_sentiment, details

        except Exception as e:
            logger.warning(f"뉴스 감성 계산 실패: {e}")
            return 0.0, {}

    def calculate_enhanced_tone(
        self,
        text: str,
        meeting_date: str,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        gamma: Optional[float] = None
    ) -> EnhancedToneResult:
        """
        향상된 톤 지수 계산

        Args:
            text: 의사록 텍스트
            meeting_date: 회의 날짜
            alpha: 텍스트 가중치 (None이면 기본값 사용)
            beta: 시장 가중치 (None이면 기본값 사용)
            gamma: 뉴스 가중치 (None이면 기본값 사용)

        Returns:
            EnhancedToneResult 객체
        """
        # 가중치 설정
        alpha = alpha if alpha is not None else self.alpha
        beta = beta if beta is not None else self.beta
        gamma = gamma if gamma is not None else self.gamma

        # 1. 기본 텍스트 톤 분석
        base_result = self.analyze_text(text, meeting_date)

        # 2. 시장 반응 계산
        market_reaction, market_details = self._calculate_market_reaction(meeting_date)

        # 3. 뉴스 감성 계산
        news_sentiment, news_details = self._calculate_news_sentiment(meeting_date)

        # 4. 종합 톤 지수 계산
        tone_adjusted = (
            alpha * base_result.tone_index +
            beta * market_reaction +
            gamma * news_sentiment
        )

        # -1 ~ +1 범위로 클리핑
        tone_adjusted = np.clip(tone_adjusted, -1.0, 1.0)

        # 5. 향상된 결과 객체 생성
        enhanced_result = EnhancedToneResult(
            meeting_date=base_result.meeting_date,
            tone_index=base_result.tone_index,
            hawkish_score=base_result.hawkish_score,
            dovish_score=base_result.dovish_score,
            hawkish_terms=base_result.hawkish_terms,
            dovish_terms=base_result.dovish_terms,
            sentence_tones=base_result.sentence_tones,
            total_sentences=base_result.total_sentences,
            interpretation=self.interpret_tone(tone_adjusted),  # 조정된 톤으로 해석
            tone_adjusted=tone_adjusted,
            market_reaction_score=market_reaction,
            news_sentiment_score=news_sentiment,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            market_reaction_details=market_details,
            news_sentiment_details=news_details
        )

        logger.info(
            f"[{meeting_date}] "
            f"Text: {base_result.tone_index:+.3f}, "
            f"Market: {market_reaction:+.3f}, "
            f"News: {news_sentiment:+.3f} "
            f"→ Adjusted: {tone_adjusted:+.3f} ({enhanced_result.interpretation})"
        )

        return enhanced_result

    def analyze_directory_enhanced(
        self,
        dir_path: Path,
        save_results: bool = True
    ) -> List[EnhancedToneResult]:
        """
        디렉토리 내 모든 의사록을 향상된 분석으로 처리

        Args:
            dir_path: 텍스트 파일 디렉토리
            save_results: 결과 저장 여부

        Returns:
            EnhancedToneResult 리스트
        """
        results = []

        for filepath in sorted(dir_path.glob("*.txt")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()

                meeting_date = filepath.stem.replace("minutes_", "")

                result = self.calculate_enhanced_tone(text, meeting_date)
                results.append(result)

                # 데이터베이스에 저장
                self.db.save_tone_result(
                    meeting_date=result.meeting_date,
                    tone_index=result.tone_index,
                    tone_adjusted=result.tone_adjusted,
                    hawkish_score=result.hawkish_score,
                    dovish_score=result.dovish_score,
                    interpretation=result.interpretation,
                    market_reaction_score=result.market_reaction_score,
                    news_sentiment_score=result.news_sentiment_score
                )

            except Exception as e:
                logger.error(f"파일 분석 실패 [{filepath}]: {e}")

        if save_results and results:
            self.save_enhanced_results(results)

        return results

    def save_enhanced_results(
        self,
        results: List[EnhancedToneResult],
        filename: str = "enhanced_tone_index_results"
    ):
        """
        향상된 결과 저장

        Args:
            results: EnhancedToneResult 리스트
            filename: 파일명
        """
        # DataFrame으로 변환
        data = []
        for r in results:
            try:
                date_str = r.meeting_date.replace("_", "-")
                date = pd.to_datetime(date_str)
            except:
                date = None

            data.append({
                "meeting_date": date,
                "meeting_date_str": r.meeting_date,
                "tone_index": r.tone_index,
                "tone_adjusted": r.tone_adjusted,
                "market_reaction": r.market_reaction_score,
                "news_sentiment": r.news_sentiment_score,
                "hawkish_score": r.hawkish_score,
                "dovish_score": r.dovish_score,
                "interpretation": r.interpretation,
                "alpha": r.alpha,
                "beta": r.beta,
                "gamma": r.gamma,
                "total_sentences": r.total_sentences,
                "top_hawkish": ", ".join(sorted(r.hawkish_terms.keys(),
                                                key=lambda x: r.hawkish_terms[x],
                                                reverse=True)[:5]),
                "top_dovish": ", ".join(sorted(r.dovish_terms.keys(),
                                               key=lambda x: r.dovish_terms[x],
                                               reverse=True)[:5]),
            })

        df = pd.DataFrame(data)
        if "meeting_date" in df.columns:
            df = df.sort_values("meeting_date")

        # CSV 저장
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = OUTPUT_DIR / f"{filename}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV 저장: {csv_path}")

        return df

    def update_model_parameters(self, alpha: float, beta: float, gamma: float):
        """
        모델 파라미터 업데이트

        Args:
            alpha: 텍스트 가중치
            beta: 시장 가중치
            gamma: 뉴스 가중치
        """
        # 가중치 합 검증
        total = alpha + beta + gamma
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"가중치 합계는 1.0이어야 합니다. 현재: {total:.3f}")

        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        # 데이터베이스에 저장
        self.db.save_model_parameter('alpha', alpha, 'Text Tone Weight')
        self.db.save_model_parameter('beta', beta, 'Market Reaction Weight')
        self.db.save_model_parameter('gamma', gamma, 'News Sentiment Weight')

        logger.info(f"모델 파라미터 업데이트: α={alpha}, β={beta}, γ={gamma}")


def main():
    """테스트 실행"""
    print("=" * 70)
    print("향상된 BOK 톤 분석기 테스트 (V2)")
    print("=" * 70)

    # 분석기 초기화
    analyzer = EnhancedToneAnalyzer()

    # 샘플 텍스트
    sample_text = """
    위원들은 물가상승 압력이 예상보다 높은 수준을 지속하고 있으며,
    가계부채 증가와 금융불균형 누증에 대한 우려를 표명하였다.
    다만 대외 불확실성이 높은 상황에서 경기 회복세 둔화 가능성도
    염두에 둘 필요가 있다는 의견도 제시되었다.
    """

    meeting_date = "2025-11-27"

    print(f"\n분석 대상: {meeting_date}")
    print(f"가중치: α={analyzer.alpha}, β={analyzer.beta}, γ={analyzer.gamma}")

    # 향상된 톤 분석
    result = analyzer.calculate_enhanced_tone(sample_text, meeting_date)

    # 결과 출력
    print("\n" + "=" * 70)
    print("분석 결과")
    print("=" * 70)
    print(f"텍스트 톤 지수:    {result.tone_index:+.3f}")
    print(f"시장 반응 점수:    {result.market_reaction_score:+.3f}")
    print(f"뉴스 감성 점수:    {result.news_sentiment_score:+.3f}")
    print(f"─" * 70)
    print(f"조정된 톤 지수:    {result.tone_adjusted:+.3f}")
    print(f"해석:             {result.interpretation}")

    print("\n계산 과정:")
    print(f"  {result.alpha:.2f} × {result.tone_index:+.3f} (텍스트)")
    print(f"+ {result.beta:.2f} × {result.market_reaction_score:+.3f} (시장)")
    print(f"+ {result.gamma:.2f} × {result.news_sentiment_score:+.3f} (뉴스)")
    print(f"= {result.tone_adjusted:+.3f}")

    print("\n=" * 70)


if __name__ == "__main__":
    main()
