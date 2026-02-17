"""
BOK Tone Index 분석 모듈

의사록 텍스트에서 통화정책 톤 지수를 산출합니다.

Tone Index 공식:
    Tone_t = (N(Hawkish_t) - N(Dovish_t)) / (N(Hawkish_t) + N(Dovish_t) + ε)

    - Tone = +1: 완전 매파 (강한 긴축 선호)
    - Tone = 0: 중립
    - Tone = -1: 완전 비둘기파 (강한 완화 선호)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter
import json
from datetime import datetime

from .sentiment_dict import SentimentDictionary
from .preprocessor import TextPreprocessor, ProcessedMinutes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "analysis"


@dataclass
class ToneResult:
    """톤 분석 결과"""
    meeting_date: str
    tone_index: float                    # -1 ~ +1 사이의 톤 지수
    hawkish_score: float                 # 매파 점수 (가중 빈도)
    dovish_score: float                  # 비둘기파 점수 (가중 빈도)
    hawkish_terms: Dict[str, float] = field(default_factory=dict)  # 매파 키워드별 점수
    dovish_terms: Dict[str, float] = field(default_factory=dict)   # 비둘기파 키워드별 점수
    sentence_tones: List[float] = field(default_factory=list)      # 문장별 톤
    total_sentences: int = 0
    interpretation: str = ""             # 톤 해석


class ToneAnalyzer:
    """BOK 톤 분석기"""

    # 톤 해석 기준
    TONE_THRESHOLDS = {
        "strong_hawkish": 0.3,
        "moderate_hawkish": 0.1,
        "neutral": -0.1,
        "moderate_dovish": -0.3,
        # below -0.3: strong_dovish
    }

    def __init__(
        self,
        dictionary: Optional[SentimentDictionary] = None,
        preprocessor: Optional[TextPreprocessor] = None,
        epsilon: float = 1e-6
    ):
        """
        톤 분석기 초기화

        Args:
            dictionary: 감성 사전 (None이면 기본 사전 사용)
            preprocessor: 전처리기 (None이면 기본 설정 사용)
            epsilon: 분모 0 방지용 상수
        """
        self.dictionary = dictionary or SentimentDictionary()
        self.preprocessor = preprocessor or TextPreprocessor(use_kss=False)
        self.epsilon = epsilon

        # 출력 디렉토리 생성
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def calculate_tone_index(
        self,
        hawkish_score: float,
        dovish_score: float
    ) -> float:
        """
        톤 지수 계산

        공식: (Hawkish - Dovish) / (Hawkish + Dovish + ε)

        Returns:
            -1 ~ +1 사이의 톤 지수
        """
        denominator = hawkish_score + dovish_score + self.epsilon
        tone = (hawkish_score - dovish_score) / denominator
        return np.clip(tone, -1.0, 1.0)

    def interpret_tone(self, tone_index: float) -> str:
        """톤 지수 해석"""
        if tone_index >= self.TONE_THRESHOLDS["strong_hawkish"]:
            return "강한 매파 (Strong Hawkish)"
        elif tone_index >= self.TONE_THRESHOLDS["moderate_hawkish"]:
            return "온건 매파 (Moderate Hawkish)"
        elif tone_index >= self.TONE_THRESHOLDS["neutral"]:
            return "중립 (Neutral)"
        elif tone_index >= self.TONE_THRESHOLDS["moderate_dovish"]:
            return "온건 비둘기파 (Moderate Dovish)"
        else:
            return "강한 비둘기파 (Strong Dovish)"

    def analyze_text(self, text: str, meeting_date: str = "") -> ToneResult:
        """
        텍스트의 톤 분석

        Args:
            text: 분석할 텍스트
            meeting_date: 회의 날짜

        Returns:
            ToneResult 객체
        """
        # 감성 키워드 매칭
        matches = self.dictionary.match_in_text(text)

        # 매파/비둘기파 점수 계산
        hawkish_terms = {term: weight for term, weight in matches["hawkish"]}
        dovish_terms = {term: weight for term, weight in matches["dovish"]}

        hawkish_score = sum(hawkish_terms.values())
        dovish_score = sum(dovish_terms.values())

        # 톤 지수 계산
        tone_index = self.calculate_tone_index(hawkish_score, dovish_score)

        # 문장별 톤 분석
        sentences = self.preprocessor.split_sentences(text)
        sentence_tones = []

        for sentence in sentences:
            sent_matches = self.dictionary.match_in_text(sentence)
            h_score = sum(w for _, w in sent_matches["hawkish"])
            d_score = sum(w for _, w in sent_matches["dovish"])
            if h_score > 0 or d_score > 0:
                sent_tone = self.calculate_tone_index(h_score, d_score)
                sentence_tones.append(sent_tone)

        return ToneResult(
            meeting_date=meeting_date,
            tone_index=tone_index,
            hawkish_score=hawkish_score,
            dovish_score=dovish_score,
            hawkish_terms=hawkish_terms,
            dovish_terms=dovish_terms,
            sentence_tones=sentence_tones,
            total_sentences=len(sentences),
            interpretation=self.interpret_tone(tone_index)
        )

    def analyze_processed_minutes(self, minutes: ProcessedMinutes) -> ToneResult:
        """
        전처리된 의사록 분석

        Args:
            minutes: ProcessedMinutes 객체

        Returns:
            ToneResult 객체
        """
        # 토의 내용 섹션을 주로 분석 (의결 문구는 형식적인 내용이 많음)
        text = minutes.discussion_section or minutes.cleaned_text
        return self.analyze_text(text, minutes.meeting_date)

    def analyze_file(self, filepath: Path) -> Optional[ToneResult]:
        """
        텍스트 파일 분석

        Args:
            filepath: 텍스트 파일 경로

        Returns:
            ToneResult 객체 또는 None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()

            meeting_date = filepath.stem.replace("minutes_", "")
            return self.analyze_text(text, meeting_date)

        except Exception as e:
            logger.error(f"파일 분석 실패 [{filepath}]: {e}")
            return None

    def analyze_directory(
        self,
        dir_path: Path,
        save_results: bool = True
    ) -> List[ToneResult]:
        """
        디렉토리 내 모든 의사록 분석

        Args:
            dir_path: 텍스트 파일 디렉토리
            save_results: 결과 저장 여부

        Returns:
            ToneResult 리스트
        """
        results = []

        for filepath in sorted(dir_path.glob("*.txt")):
            result = self.analyze_file(filepath)
            if result:
                results.append(result)
                logger.info(
                    f"[{result.meeting_date}] "
                    f"Tone: {result.tone_index:+.3f} ({result.interpretation})"
                )

        if save_results and results:
            self.save_results(results)

        return results

    def results_to_dataframe(self, results: List[ToneResult]) -> pd.DataFrame:
        """분석 결과를 DataFrame으로 변환"""
        data = []
        for r in results:
            # 날짜 파싱 (2024_01_11 -> 2024-01-11)
            try:
                date_str = r.meeting_date.replace("_", "-")
                date = pd.to_datetime(date_str)
            except:
                date = None

            data.append({
                "meeting_date": date,
                "meeting_date_str": r.meeting_date,
                "tone_index": r.tone_index,
                "hawkish_score": r.hawkish_score,
                "dovish_score": r.dovish_score,
                "interpretation": r.interpretation,
                "total_sentences": r.total_sentences,
                "hawkish_terms_count": len(r.hawkish_terms),
                "dovish_terms_count": len(r.dovish_terms),
                # 주요 키워드 (상위 5개)
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

        return df

    def save_results(
        self,
        results: List[ToneResult],
        filename: str = "tone_index_results"
    ):
        """결과 저장"""
        # DataFrame으로 변환
        df = self.results_to_dataframe(results)

        # CSV 저장
        csv_path = OUTPUT_DIR / f"{filename}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"CSV 저장: {csv_path}")

        # JSON 저장 (상세 정보 포함)
        json_path = OUTPUT_DIR / f"{filename}.json"
        json_data = []
        for r in results:
            json_data.append({
                "meeting_date": r.meeting_date,
                "tone_index": r.tone_index,
                "hawkish_score": r.hawkish_score,
                "dovish_score": r.dovish_score,
                "interpretation": r.interpretation,
                "hawkish_terms": r.hawkish_terms,
                "dovish_terms": r.dovish_terms,
                "sentence_tones": r.sentence_tones[:20],  # 처음 20개만
                "total_sentences": r.total_sentences
            })

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 저장: {json_path}")

        return df

    def get_tone_statistics(self, results: List[ToneResult]) -> Dict:
        """톤 분석 통계"""
        if not results:
            return {}

        tones = [r.tone_index for r in results]

        return {
            "count": len(results),
            "mean": np.mean(tones),
            "std": np.std(tones),
            "min": np.min(tones),
            "max": np.max(tones),
            "median": np.median(tones),
            "hawkish_count": sum(1 for t in tones if t > 0.1),
            "dovish_count": sum(1 for t in tones if t < -0.1),
            "neutral_count": sum(1 for t in tones if -0.1 <= t <= 0.1),
        }


def main():
    """메인 실행: 전체 의사록 톤 분석"""
    print("=" * 70)
    print("한국은행 금융통화위원회 의사록 톤 분석")
    print("=" * 70)

    # 분석기 초기화
    analyzer = ToneAnalyzer()

    # 텍스트 파일 디렉토리
    # Phase 1 Update: Read from structured directories
    texts_dir = DATA_DIR / "01_minutes/txt"

    if not texts_dir.exists():
        print(f"텍스트 디렉토리가 없습니다: {texts_dir}")
        return

    # 전체 분석 수행
    print(f"\n분석 대상: {texts_dir}")
    results = analyzer.analyze_directory(texts_dir, save_results=True)

    # 통계 출력
    stats = analyzer.get_tone_statistics(results)

    print("\n" + "=" * 70)
    print("분석 결과 요약")
    print("=" * 70)
    print(f"분석 회의 수: {stats['count']}개")
    print(f"평균 톤 지수: {stats['mean']:+.3f}")
    print(f"표준편차: {stats['std']:.3f}")
    print(f"최소값: {stats['min']:+.3f}")
    print(f"최대값: {stats['max']:+.3f}")
    print(f"중앙값: {stats['median']:+.3f}")
    print(f"\n톤 분포:")
    print(f"  - 매파적 (>0.1): {stats['hawkish_count']}회")
    print(f"  - 중립 (-0.1~0.1): {stats['neutral_count']}회")
    print(f"  - 비둘기파적 (<-0.1): {stats['dovish_count']}회")

    # 시계열 출력
    df = analyzer.results_to_dataframe(results)
    print("\n" + "=" * 70)
    print("시계열 톤 지수")
    print("=" * 70)
    for _, row in df.iterrows():
        tone = row['tone_index']
        bar_len = int(abs(tone) * 20)
        if tone >= 0:
            bar = "█" * bar_len + "░" * (20 - bar_len)
            direction = "▲"
        else:
            bar = "░" * (20 - bar_len) + "█" * bar_len
            direction = "▼"
        print(f"{row['meeting_date_str']} | {tone:+.3f} | {direction} {bar}")

    print(f"\n결과 저장 위치: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
