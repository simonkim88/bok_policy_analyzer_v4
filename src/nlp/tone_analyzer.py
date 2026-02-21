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
import re
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
    policy_intent_tone: float = 0.0       # 정책 의도/조건부 문장 톤
    raw_keyword_tone: float = 0.0         # 단순 키워드 매칭 톤
    context_adjusted_tone: float = 0.0    # 문맥 조정 톤
    ngram_tone: float = 0.0               # N-gram 기반 톤


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

    NEGATION_PATTERNS = [
        "아니", "않", "없", "못", "불가", "부정",
        "아닌 것으로", "가능성은 낮", "제한적"
    ]

    AMPLIFIER_PATTERNS = [
        "매우", "상당히", "크게", "현저히", "급격히",
        "대폭", "뚜렷", "확연", "강하게"
    ]

    HEDGING_PATTERNS = [
        "다소", "약간", "소폭", "일부", "제한적",
        "부분적", "일시적", "가능성", "여지"
    ]

    CONTRAST_PATTERNS = [r"에도\s*불구하고", r"이지만", r"지만", r"이나\s", r"그러나"]
    POLICY_INTENT_PATTERNS = [r"할\s*필요", r"필요가\s*있", r"당부", r"대응해야", r"검토"]

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

    def _aggregate_terms(self, items: List[Tuple[str, float]]) -> Dict[str, float]:
        aggregated: Dict[str, float] = {}
        for term, weight in items:
            aggregated[term] = aggregated.get(term, 0.0) + weight
        return aggregated

    def _find_term_positions(self, sentence: str, term: str) -> List[int]:
        if " " in term:
            parts = [re.escape(part) for part in term.split() if part]
            if not parts:
                return []
            pattern = '.{0,20}'.join(parts)
            return [m.start() for m in re.finditer(pattern, sentence)]
        return [m.start() for m in re.finditer(re.escape(term), sentence)]

    def _has_pattern(self, text: str, patterns: List[str]) -> bool:
        return any(re.search(pattern, text) for pattern in patterns)

    def _score_sentence_context(self, sentence: str) -> Tuple[float, float]:
        sent_matches = self.dictionary.match_in_text(sentence)
        hawkish_score = 0.0
        dovish_score = 0.0

        for polarity in ["hawkish", "dovish"]:
            for term, base_weight in sent_matches[polarity]:
                positions = self._find_term_positions(sentence, term)
                if not positions:
                    if polarity == "hawkish":
                        hawkish_score += base_weight
                    else:
                        dovish_score += base_weight
                    continue

                unit_weight = base_weight / max(len(positions), 1)
                for pos in positions:
                    start = max(0, pos - 10)
                    context_window = sentence[start:pos]
                    multiplier = 1.0

                    if any(am in context_window for am in self.AMPLIFIER_PATTERNS):
                        multiplier *= 1.5
                    if any(hd in context_window for hd in self.HEDGING_PATTERNS):
                        multiplier *= 0.5

                    target_polarity = polarity
                    if any(ng in context_window for ng in self.NEGATION_PATTERNS):
                        target_polarity = "dovish" if polarity == "hawkish" else "hawkish"

                    adj_weight = unit_weight * multiplier
                    if target_polarity == "hawkish":
                        hawkish_score += adj_weight
                    else:
                        dovish_score += adj_weight

        return hawkish_score, dovish_score

    def _score_sentence_with_contrast(self, sentence: str) -> Tuple[float, float]:
        for pattern in self.CONTRAST_PATTERNS:
            match = re.search(pattern, sentence)
            if not match:
                continue

            first_clause = sentence[:match.start()].strip()
            second_clause = sentence[match.end():].strip()
            if not second_clause:
                continue

            first_h, first_d = self._score_sentence_context(first_clause)
            second_h, second_d = self._score_sentence_context(second_clause)
            return (0.7 * first_h + 1.3 * second_h, 0.7 * first_d + 1.3 * second_d)

        return self._score_sentence_context(sentence)

    def _score_policy_intent(self, sentence: str, h_score: float, d_score: float) -> float:
        if not self._has_pattern(sentence, self.POLICY_INTENT_PATTERNS):
            return 0.0

        intent_multiplier = 1.2
        if re.search(r"할\s*필요", sentence):
            intent_multiplier = 1.5

        return self.calculate_tone_index(h_score * intent_multiplier, d_score * intent_multiplier)

    def analyze_text(self, text: str, meeting_date: str = "") -> ToneResult:
        """
        텍스트의 톤 분석

        Args:
            text: 분석할 텍스트
            meeting_date: 회의 날짜

        Returns:
            ToneResult 객체
        """
        # 1) 단순 키워드 기준 점수 (기존 방식 유지)
        matches = self.dictionary.match_in_text(text)
        hawkish_terms = self._aggregate_terms(matches["hawkish"])
        dovish_terms = self._aggregate_terms(matches["dovish"])

        hawkish_score = sum(hawkish_terms.values())
        dovish_score = sum(dovish_terms.values())
        raw_keyword_tone = self.calculate_tone_index(hawkish_score, dovish_score)

        # 2) N-gram 전용 톤
        ngram_matches = self.dictionary.match_ngrams_in_text(text)
        ngram_hawkish = sum(weight for _, weight in ngram_matches["hawkish"])
        ngram_dovish = sum(weight for _, weight in ngram_matches["dovish"])
        ngram_tone = self.calculate_tone_index(ngram_hawkish, ngram_dovish)

        # 3) 문장 단위 문맥 조정 톤 + 정책 의도 톤
        sentences = self.preprocessor.split_sentences(text)
        sentence_tones: List[float] = []
        context_h_total = 0.0
        context_d_total = 0.0
        policy_intent_values: List[float] = []

        for sentence in sentences:
            h_score, d_score = self._score_sentence_with_contrast(sentence)
            if re.search(r"할\s*필요", sentence):
                h_score *= 1.5
                d_score *= 1.5

            if h_score > 0 or d_score > 0:
                sent_tone = self.calculate_tone_index(h_score, d_score)
                sentence_tones.append(sent_tone)
                context_h_total += h_score
                context_d_total += d_score

                policy_intent_tone = self._score_policy_intent(sentence, h_score, d_score)
                if policy_intent_tone != 0.0:
                    policy_intent_values.append(policy_intent_tone)

        context_adjusted_tone = self.calculate_tone_index(context_h_total, context_d_total)
        policy_intent_tone = float(np.mean(policy_intent_values)) if policy_intent_values else 0.0

        # 4) 멀티 레이어 결합 톤
        tone_index = (
            0.4 * context_adjusted_tone
            + 0.3 * ngram_tone
            + 0.2 * policy_intent_tone
            + 0.1 * raw_keyword_tone
        )
        tone_index = float(np.clip(tone_index, -1.0, 1.0))

        return ToneResult(
            meeting_date=meeting_date,
            tone_index=tone_index,
            hawkish_score=hawkish_score,
            dovish_score=dovish_score,
            hawkish_terms=hawkish_terms,
            dovish_terms=dovish_terms,
            sentence_tones=sentence_tones,
            total_sentences=len(sentences),
            interpretation=self.interpret_tone(tone_index),
            policy_intent_tone=policy_intent_tone,
            raw_keyword_tone=raw_keyword_tone,
            context_adjusted_tone=context_adjusted_tone,
            ngram_tone=ngram_tone,
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
                "policy_intent_tone": r.policy_intent_tone,
                "raw_keyword_tone": r.raw_keyword_tone,
                "context_adjusted_tone": r.context_adjusted_tone,
                "ngram_tone": r.ngram_tone,
                "sentence_tones": json.dumps(r.sentence_tones) if r.sentence_tones else "",
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
                "total_sentences": r.total_sentences,
                "policy_intent_tone": r.policy_intent_tone,
                "raw_keyword_tone": r.raw_keyword_tone,
                "context_adjusted_tone": r.context_adjusted_tone,
                "ngram_tone": r.ngram_tone,
            })

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 저장: {json_path}")

        return df

    def get_tone_statistics(self, results: List[ToneResult]) -> Dict[str, float | int]:
        """톤 분석 통계"""
        if not results:
            return {}

        tones = [r.tone_index for r in results]

        return {
            "count": int(len(results)),
            "mean": float(np.mean(tones)),
            "std": float(np.std(tones)),
            "min": float(np.min(tones)),
            "max": float(np.max(tones)),
            "median": float(np.median(tones)),
            "hawkish_count": int(sum(1 for t in tones if t > 0.1)),
            "dovish_count": int(sum(1 for t in tones if t < -0.1)),
            "neutral_count": int(sum(1 for t in tones if -0.1 <= t <= 0.1)),
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
            bar = "#" * bar_len + "." * (20 - bar_len)
            direction = "UP"
        else:
            bar = "." * (20 - bar_len) + "#" * bar_len
            direction = "DOWN"
        print(f"{row['meeting_date_str']} | {tone:+.3f} | {direction} {bar}")

    print(f"\n결과 저장 위치: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
