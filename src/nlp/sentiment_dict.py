"""
한국은행 통화정책 감성 사전 모듈

매파(Hawkish) vs 비둘기파(Dovish) 키워드 및 N-gram 사전
- 매파: 인플레이션 우려, 금융 불균형, 경기 과열, 금리 인상 시사
- 비둘기파: 경기 둔화 우려, 물가 하락, 성장 약화, 금리 인하/동결 시사
"""

import json
import logging
import re
from typing import Dict, List, Set, Tuple, Optional, cast
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
DICT_DIR = PROJECT_ROOT / "data" / "dictionaries"


@dataclass
class SentimentEntry:
    """감성 사전 엔트리"""
    term: str           # 단어 또는 N-gram
    polarity: str       # 'hawkish' 또는 'dovish'
    weight: float = 1.0  # 가중치 (기본 1.0)
    category: str = ""   # 카테고리 (inflation, growth, financial_stability 등)
    description: str = "" # 설명


class SentimentDictionary:
    """한국은행 통화정책 감성 사전"""

    def __init__(self):
        """감성 사전 초기화"""
        self.hawkish_terms: Dict[str, SentimentEntry] = {}
        self.dovish_terms: Dict[str, SentimentEntry] = {}

        # 기본 사전 로드
        self._build_default_dictionary()

        # 디렉토리 생성
        DICT_DIR.mkdir(parents=True, exist_ok=True)

    def _build_default_dictionary(self):
        """기본 감성 사전 구축"""
        # ========================================
        # 매파적 (Hawkish) 키워드 - 긴축 선호
        # ========================================
        hawkish_keywords = [
            # 핵심 정책 단어
            SentimentEntry("인상", "hawkish", 2.0, "policy", "금리 인상"),
            SentimentEntry("긴축", "hawkish", 2.0, "policy", "긴축 정책"),
            SentimentEntry("정상화", "hawkish", 1.5, "policy", "통화정책 정상화"),
            SentimentEntry("선제적", "hawkish", 1.2, "policy", "선제적 대응"),

            # 인플레이션 관련
            SentimentEntry("물가상승", "hawkish", 1.8, "inflation", "물가 상승 압력"),
            SentimentEntry("상방압력", "hawkish", 1.8, "inflation", "물가 상방 압력"),
            SentimentEntry("상방위험", "hawkish", 1.7, "inflation", "상방 위험"),
            SentimentEntry("상방리스크", "hawkish", 1.7, "inflation", "상방 리스크"),
            SentimentEntry("인플레이션", "hawkish", 1.2, "inflation", "인플레이션 압력"),
            SentimentEntry("기대인플레이션", "hawkish", 1.5, "inflation", "기대인플레이션 상승"),
            SentimentEntry("물가불안", "hawkish", 1.6, "inflation", "물가 불안정"),
            SentimentEntry("물가오름세", "hawkish", 1.5, "inflation", "물가 오름세"),

            # 경기 과열
            SentimentEntry("과열", "hawkish", 1.8, "growth", "경기 과열"),
            SentimentEntry("견조", "hawkish", 1.3, "growth", "견조한 성장"),
            SentimentEntry("호조", "hawkish", 1.2, "growth", "호조세"),
            SentimentEntry("확대", "hawkish", 0.8, "growth", "확대 기조"),
            SentimentEntry("개선", "hawkish", 0.7, "growth", "경기 개선"),

            # 금융 불균형
            SentimentEntry("금융불균형", "hawkish", 2.0, "financial_stability", "금융 불균형"),
            SentimentEntry("가계부채", "hawkish", 1.8, "financial_stability", "가계부채 우려"),
            SentimentEntry("부채증가", "hawkish", 1.7, "financial_stability", "부채 증가"),
            SentimentEntry("부채누증", "hawkish", 1.8, "financial_stability", "부채 누증"),
            SentimentEntry("주택가격", "hawkish", 1.3, "financial_stability", "주택가격 상승"),
            SentimentEntry("부동산", "hawkish", 1.0, "financial_stability", "부동산 가격"),
            SentimentEntry("레버리지", "hawkish", 1.5, "financial_stability", "레버리지 확대"),
            SentimentEntry("자산가격", "hawkish", 1.2, "financial_stability", "자산가격 상승"),

            # 유동성
            SentimentEntry("유동성축소", "hawkish", 1.6, "liquidity", "유동성 축소"),
            SentimentEntry("유동성과잉", "hawkish", 1.5, "liquidity", "유동성 과잉"),
            SentimentEntry("완화축소", "hawkish", 1.8, "liquidity", "완화 정도 축소"),

            # 강한 표현
            SentimentEntry("빅스텝", "hawkish", 2.5, "policy", "50bp 인상"),
            SentimentEntry("추가인상", "hawkish", 2.2, "policy", "추가 금리 인상"),

            # 정책 의도/대응
            SentimentEntry("조기정상화", "hawkish", 2.3, "policy", "조기 정상화"),
            SentimentEntry("추가조치", "hawkish", 2.1, "policy", "추가 조치"),
            SentimentEntry("선제적대응", "hawkish", 2.0, "policy", "선제적 대응"),
            SentimentEntry("정상화속도", "hawkish", 1.7, "policy", "정상화 속도"),
            SentimentEntry("긴축기조", "hawkish", 2.0, "policy", "긴축 기조"),

            # 인플레이션/물가
            SentimentEntry("물가목표상회", "hawkish", 2.3, "inflation", "물가 목표 상회"),
            SentimentEntry("기조적물가", "hawkish", 1.9, "inflation", "기조적 물가"),
            SentimentEntry("근원상승", "hawkish", 2.0, "inflation", "근원물가 상승"),
            SentimentEntry("비용전가", "hawkish", 1.8, "inflation", "비용 전가"),
            SentimentEntry("임금상승압력", "hawkish", 2.0, "inflation", "임금 상승 압력"),
            SentimentEntry("물가상방리스크", "hawkish", 2.2, "inflation", "물가 상방 리스크"),
            SentimentEntry("인플레이션고착", "hawkish", 2.3, "inflation", "인플레이션 고착"),

            # 금융/신용
            SentimentEntry("부동산과열", "hawkish", 2.1, "financial_stability", "부동산 과열"),
            SentimentEntry("투기수요", "hawkish", 1.9, "financial_stability", "투기 수요"),
            SentimentEntry("대출급증", "hawkish", 2.0, "financial_stability", "대출 급증"),
            SentimentEntry("신용리스크", "hawkish", 1.9, "financial_stability", "신용 리스크"),
            SentimentEntry("금융안정리스크", "hawkish", 1.8, "financial_stability", "금융안정 리스크"),
            SentimentEntry("자산시장과열", "hawkish", 2.0, "financial_stability", "자산시장 과열"),
            SentimentEntry("가계대출증가", "hawkish", 2.0, "financial_stability", "가계대출 증가"),

            # 대외
            SentimentEntry("환율절하", "hawkish", 1.7, "external", "환율 절하"),
            SentimentEntry("자본유출", "hawkish", 1.8, "external", "자본 유출"),
            SentimentEntry("수입물가상승", "hawkish", 1.8, "external", "수입물가 상승"),
            SentimentEntry("환율상방압력", "hawkish", 1.7, "external", "환율 상방 압력"),
        ]

        # ========================================
        # 비둘기파적 (Dovish) 키워드 - 완화 선호
        # ========================================
        dovish_keywords = [
            # 핵심 정책 단어
            SentimentEntry("인하", "dovish", 2.0, "policy", "금리 인하"),
            SentimentEntry("완화", "dovish", 1.8, "policy", "완화 기조"),
            SentimentEntry("동결", "dovish", 1.2, "policy", "금리 동결"),
            SentimentEntry("유지", "dovish", 0.8, "policy", "금리 유지"),
            SentimentEntry("지지", "dovish", 1.0, "policy", "경기 지지"),

            # 경기 둔화
            SentimentEntry("둔화", "dovish", 1.8, "growth", "경기 둔화"),
            SentimentEntry("부진", "dovish", 1.7, "growth", "경기 부진"),
            SentimentEntry("위축", "dovish", 1.8, "growth", "경기 위축"),
            SentimentEntry("침체", "dovish", 2.0, "growth", "경기 침체"),
            SentimentEntry("하락", "dovish", 1.3, "growth", "성장 하락"),
            SentimentEntry("감소", "dovish", 1.2, "growth", "성장 감소"),
            SentimentEntry("약화", "dovish", 1.5, "growth", "성장세 약화"),
            SentimentEntry("미약", "dovish", 1.4, "growth", "미약한 성장"),
            SentimentEntry("저조", "dovish", 1.4, "growth", "저조한 성장"),

            # 하방 위험
            SentimentEntry("하방위험", "dovish", 1.8, "risk", "하방 위험"),
            SentimentEntry("하방리스크", "dovish", 1.8, "risk", "하방 리스크"),
            SentimentEntry("하방압력", "dovish", 1.7, "risk", "하방 압력"),
            SentimentEntry("하회", "dovish", 1.3, "risk", "목표 하회"),

            # 불확실성
            SentimentEntry("불확실성", "dovish", 1.5, "risk", "불확실성"),
            SentimentEntry("불확실", "dovish", 1.4, "risk", "불확실"),
            SentimentEntry("리스크", "dovish", 1.0, "risk", "리스크"),
            SentimentEntry("우려", "dovish", 1.2, "risk", "우려"),
            SentimentEntry("변동성", "dovish", 1.1, "risk", "변동성"),

            # 물가 안정
            SentimentEntry("물가안정", "dovish", 1.5, "inflation", "물가 안정"),
            SentimentEntry("안정세", "dovish", 1.3, "inflation", "물가 안정세"),
            SentimentEntry("둔화세", "dovish", 1.4, "inflation", "물가 둔화세"),

            # 수요 약화
            SentimentEntry("수요부진", "dovish", 1.6, "demand", "수요 부진"),
            SentimentEntry("소비부진", "dovish", 1.5, "demand", "소비 부진"),
            SentimentEntry("투자부진", "dovish", 1.5, "demand", "투자 부진"),
            SentimentEntry("수출부진", "dovish", 1.4, "demand", "수출 부진"),

            # 대외 여건
            SentimentEntry("대외불확실성", "dovish", 1.6, "external", "대외 불확실성"),
            SentimentEntry("대외여건", "dovish", 1.0, "external", "대외 여건"),
            SentimentEntry("글로벌불확실성", "dovish", 1.5, "external", "글로벌 불확실성"),

            # 회복 지연
            SentimentEntry("회복지연", "dovish", 1.7, "growth", "회복 지연"),
            SentimentEntry("지연", "dovish", 1.2, "growth", "지연"),

            # 정책 의도/완화
            SentimentEntry("금리인하여지", "dovish", 2.2, "policy", "금리 인하 여지"),
            SentimentEntry("완화기조유지", "dovish", 2.1, "policy", "완화 기조 유지"),
            SentimentEntry("경기부양", "dovish", 2.0, "policy", "경기 부양"),
            SentimentEntry("완화적통화정책", "dovish", 2.0, "policy", "완화적 통화정책"),
            SentimentEntry("정책지원", "dovish", 1.5, "policy", "정책 지원"),

            # 성장/내수
            SentimentEntry("내수부진", "dovish", 2.0, "growth", "내수 부진"),
            SentimentEntry("소비심리위축", "dovish", 2.0, "growth", "소비 심리 위축"),
            SentimentEntry("고용악화", "dovish", 1.9, "growth", "고용 악화"),
            SentimentEntry("투자감소", "dovish", 1.8, "growth", "투자 감소"),
            SentimentEntry("성장둔화", "dovish", 1.9, "growth", "성장 둔화"),
            SentimentEntry("회복더딤", "dovish", 1.8, "growth", "회복 더딤"),
            SentimentEntry("생산감소", "dovish", 1.7, "growth", "생산 감소"),

            # 위험
            SentimentEntry("디플레이션", "dovish", 2.1, "risk", "디플레이션"),
            SentimentEntry("경기하강", "dovish", 2.1, "risk", "경기 하강"),
            SentimentEntry("수출급감", "dovish", 2.0, "risk", "수출 급감"),
            SentimentEntry("경상수지악화", "dovish", 1.9, "risk", "경상수지 악화"),
            SentimentEntry("하방요인", "dovish", 1.7, "risk", "하방 요인"),
            SentimentEntry("침체우려", "dovish", 2.0, "risk", "침체 우려"),
            SentimentEntry("수요위축", "dovish", 1.9, "risk", "수요 위축"),

            # 대외
            SentimentEntry("글로벌경기둔화", "dovish", 2.0, "external", "글로벌 경기 둔화"),
            SentimentEntry("교역감소", "dovish", 1.8, "external", "교역 감소"),
            SentimentEntry("공급망차질", "dovish", 1.8, "external", "공급망 차질"),
            SentimentEntry("통상불확실성", "dovish", 1.8, "external", "통상 불확실성"),
            SentimentEntry("대외수요둔화", "dovish", 1.8, "external", "대외 수요 둔화"),
        ]

        # 사전에 추가
        for entry in hawkish_keywords:
            self.hawkish_terms[entry.term] = entry

        for entry in dovish_keywords:
            self.dovish_terms[entry.term] = entry

        self._normalize_weights()

        logger.info(f"기본 감성 사전 로드: 매파 {len(self.hawkish_terms)}개, 비둘기파 {len(self.dovish_terms)}개")

    def _normalize_weights(self):
        """Normalize weights to have mean=1.0, std=0.5 within each polarity."""
        for terms_dict in [self.hawkish_terms, self.dovish_terms]:
            if not terms_dict:
                continue
            weights = [e.weight for e in terms_dict.values()]
            mean_w = np.mean(weights)
            std_w = np.std(weights) or 1.0
            for entry in terms_dict.values():
                entry.weight = float(1.0 + 0.5 * (entry.weight - mean_w) / std_w)
                entry.weight = max(0.3, min(3.0, entry.weight))

    def add_hawkish_term(
        self,
        term: str,
        weight: float = 1.0,
        category: str = "",
        description: str = ""
    ):
        """매파적 키워드 추가"""
        entry = SentimentEntry(term, "hawkish", weight, category, description)
        self.hawkish_terms[term] = entry

    def add_dovish_term(
        self,
        term: str,
        weight: float = 1.0,
        category: str = "",
        description: str = ""
    ):
        """비둘기파적 키워드 추가"""
        entry = SentimentEntry(term, "dovish", weight, category, description)
        self.dovish_terms[term] = entry

    def get_hawkish_terms(self) -> List[str]:
        """매파적 키워드 리스트 반환"""
        return list(self.hawkish_terms.keys())

    def get_dovish_terms(self) -> List[str]:
        """비둘기파적 키워드 리스트 반환"""
        return list(self.dovish_terms.keys())

    def get_weight(self, term: str) -> Tuple[str, float]:
        """
        키워드의 극성과 가중치 반환

        Returns:
            (극성, 가중치) 튜플. 사전에 없으면 ("neutral", 0.0)
        """
        if term in self.hawkish_terms:
            return ("hawkish", self.hawkish_terms[term].weight)
        elif term in self.dovish_terms:
            return ("dovish", self.dovish_terms[term].weight)
        else:
            return ("neutral", 0.0)

    def match_in_text(self, text: str) -> Dict[str, List[Tuple[str, float]]]:
        """
        텍스트에서 감성 키워드 매칭

        Args:
            text: 분석할 텍스트

        Returns:
            {"hawkish": [(term, weight), ...], "dovish": [(term, weight), ...]}
        """
        matches = {
            "hawkish": [],
            "dovish": []
        }

        # 매파 키워드 매칭
        for term, entry in self.hawkish_terms.items():
            if term in text:
                count = text.count(term)
                matches["hawkish"].append((term, entry.weight * count))

        # 비둘기파 키워드 매칭
        for term, entry in self.dovish_terms.items():
            if term in text:
                count = text.count(term)
                matches["dovish"].append((term, entry.weight * count))

        ngram_matches = self.match_ngrams_in_text(text)
        matches["hawkish"].extend(ngram_matches["hawkish"])
        matches["dovish"].extend(ngram_matches["dovish"])

        return matches

    def match_ngrams_in_text(self, text: str) -> Dict[str, List[Tuple[str, float]]]:
        """텍스트에서 N-gram 패턴 매칭"""
        matches = {"hawkish": [], "dovish": []}

        for ngram in NGRAM_HAWKISH:
            ngram_str = " ".join(ngram)
            pattern = r".{0,20}".join(re.escape(word) for word in ngram)
            occurrences = len(re.findall(pattern, text))
            if occurrences > 0:
                matches["hawkish"].append((ngram_str, 2.0 * occurrences))

        for ngram in NGRAM_DOVISH:
            ngram_str = " ".join(ngram)
            pattern = r".{0,20}".join(re.escape(word) for word in ngram)
            occurrences = len(re.findall(pattern, text))
            if occurrences > 0:
                matches["dovish"].append((ngram_str, 2.0 * occurrences))

        return matches

    def save(self, filepath: Optional[Path] = None):
        """감성 사전을 JSON 파일로 저장"""
        if filepath is None:
            filepath = DICT_DIR / "sentiment_dictionary.json"

        data = {
            "hawkish": [asdict(e) for e in self.hawkish_terms.values()],
            "dovish": [asdict(e) for e in self.dovish_terms.values()]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"감성 사전 저장: {filepath}")

    def load(self, filepath: Optional[Path] = None):
        """JSON 파일에서 감성 사전 로드"""
        if filepath is None:
            filepath = DICT_DIR / "sentiment_dictionary.json"

        if not filepath.exists():
            logger.warning(f"감성 사전 파일 없음: {filepath}")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.hawkish_terms.clear()
        self.dovish_terms.clear()

        for entry_data in data.get("hawkish", []):
            entry = SentimentEntry(**entry_data)
            self.hawkish_terms[entry.term] = entry

        for entry_data in data.get("dovish", []):
            entry = SentimentEntry(**entry_data)
            self.dovish_terms[entry.term] = entry

        logger.info(f"감성 사전 로드: 매파 {len(self.hawkish_terms)}개, 비둘기파 {len(self.dovish_terms)}개")

    def get_statistics(self) -> Dict[str, int | Dict[str, List[str]]]:
        """감성 사전 통계"""
        hawkish_by_cat = defaultdict(list)
        dovish_by_cat = defaultdict(list)

        for entry in self.hawkish_terms.values():
            hawkish_by_cat[entry.category or "기타"].append(entry.term)

        for entry in self.dovish_terms.values():
            dovish_by_cat[entry.category or "기타"].append(entry.term)

        return {
            "total_hawkish": len(self.hawkish_terms),
            "total_dovish": len(self.dovish_terms),
            "hawkish_by_category": dict(hawkish_by_cat),
            "dovish_by_category": dict(dovish_by_cat)
        }


# N-gram 기반 감성 표현 (문맥을 고려한 복합 표현)
NGRAM_HAWKISH = [
    ("물가", "상승", "압력"),
    ("물가", "상방", "압력"),
    ("금융", "불균형", "누증"),
    ("가계", "부채", "증가"),
    ("통화정책", "완화", "정도", "축소"),
    ("주택", "가격", "상승"),
    ("자산", "가격", "상승"),
    ("기대", "인플레이션", "상승"),
    ("수요", "압력", "확대"),
    ("경기", "과열", "우려"),
    ("물가", "목표", "상회"),
    ("금융", "불균형", "확대"),
    ("가계", "대출", "증가"),
    ("선제적", "대응"),
    ("통화정책", "정상화"),
    ("추가", "인상", "필요"),
    ("기조적", "물가", "상승"),
    ("근원", "물가", "상승"),
    ("물가", "상방", "리스크"),
    ("부동산", "과열", "우려"),
    ("주택가격", "상승", "압력"),
    ("대출", "증가세", "확대"),
    ("신용", "리스크", "확대"),
    ("환율", "상승", "압력"),
    ("자본", "유출", "우려"),
    ("정책", "정상화", "속도"),
]

NGRAM_DOVISH = [
    ("성장", "경로", "하방", "리스크"),
    ("수요", "압력", "약화"),
    ("경기", "회복세", "둔화"),
    ("대외", "여건", "불확실성"),
    ("물가", "안정", "목표", "하회"),
    ("소비", "심리", "위축"),
    ("투자", "심리", "위축"),
    ("수출", "증가세", "둔화"),
    ("성장", "모멘텀", "약화"),
    ("고용", "상황", "악화"),
    ("성장", "하방", "위험"),
    ("경기", "회복", "더딘"),
    ("물가", "목표", "근접"),
    ("완화적", "통화정책"),
    ("경기", "하강", "위험"),
    ("내수", "회복", "지연"),
    ("소비", "심리", "위축"),
    ("투자", "감소", "지속"),
    ("고용", "둔화", "우려"),
    ("수출", "둔화", "흐름"),
    ("경상수지", "악화", "우려"),
    ("글로벌", "경기", "둔화"),
    ("교역", "감소", "압력"),
    ("공급망", "차질", "지속"),
    ("디플레이션", "압력", "확대"),
    ("금리", "인하", "여지"),
    ("경기", "부양", "필요"),
]

def main():
    """테스트 실행"""
    # 사전 초기화
    dictionary = SentimentDictionary()

    # 통계 출력
    stats = dictionary.get_statistics()
    print("=" * 60)
    print("감성 사전 통계")
    print("=" * 60)
    print(f"매파 키워드: {stats['total_hawkish']}개")
    print(f"비둘기파 키워드: {stats['total_dovish']}개")

    print("\n[매파 키워드 카테고리별]")
    hawkish_by_category = cast(Dict[str, List[str]], stats.get('hawkish_by_category', {}))
    for cat, terms in hawkish_by_category.items():
        print(f"  {cat}: {', '.join(terms[:5])}{'...' if len(terms) > 5 else ''}")

    print("\n[비둘기파 키워드 카테고리별]")
    dovish_by_category = cast(Dict[str, List[str]], stats.get('dovish_by_category', {}))
    for cat, terms in dovish_by_category.items():
        print(f"  {cat}: {', '.join(terms[:5])}{'...' if len(terms) > 5 else ''}")

    # 사전 저장
    dictionary.save()

    # 샘플 텍스트 분석
    sample_text = """
    위원들은 물가상승 압력이 예상보다 높은 수준을 지속하고 있으며,
    가계부채 증가와 금융불균형 누증에 대한 우려를 표명하였다.
    다만 대외 불확실성이 높은 상황에서 경기 회복세 둔화 가능성도
    염두에 둘 필요가 있다는 의견도 제시되었다.
    """

    print("\n" + "=" * 60)
    print("샘플 텍스트 분석")
    print("=" * 60)
    matches = dictionary.match_in_text(sample_text)

    print("\n[매파 키워드 매칭]")
    for term, weight in matches["hawkish"]:
        print(f"  - {term}: {weight:.1f}")

    print("\n[비둘기파 키워드 매칭]")
    for term, weight in matches["dovish"]:
        print(f"  - {term}: {weight:.1f}")


if __name__ == "__main__":
    main()
