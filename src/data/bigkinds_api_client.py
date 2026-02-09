"""
BigKinds 뉴스 API 클라이언트

한국언론진흥재단의 BigKinds 서비스를 통해 뉴스 데이터 수집
- 한국은행 관련 뉴스
- 감성 분석 (긍정/부정/중립)
- 개체명 인식 (NER)

API 키 필요: https://www.bigkinds.or.kr/
"""

import requests
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "bigkinds"
CONFIG_FILE = PROJECT_ROOT / "config" / "bigkinds_config.json"


class BigKindsClient:
    """BigKinds API 클라이언트"""

    BASE_URL = "https://api.bigkinds.or.kr"  # 실제 API URL로 변경 필요

    def __init__(self, api_key: Optional[str] = None):
        """
        클라이언트 초기화

        Args:
            api_key: BigKinds API 키 (None이면 설정 파일에서 로드)
        """
        self.api_key = api_key or self._load_api_key()

        if not self.api_key:
            logger.warning("BigKinds API 키가 설정되지 않았습니다")

        # 출력 디렉토리 생성
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load_api_key(self) -> Optional[str]:
        """설정 파일에서 API 키 로드"""
        if not CONFIG_FILE.exists():
            return None

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('bigkinds_api_key')
        except Exception as e:
            logger.error(f"API 키 로드 실패: {e}")
            return None

    def search_news(
        self,
        keywords: List[str],
        start_date: str,
        end_date: str,
        max_results: int = 100
    ) -> List[Dict]:
        """
        뉴스 검색

        Args:
            keywords: 검색 키워드 리스트
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            max_results: 최대 결과 수

        Returns:
            뉴스 기사 리스트
        """
        logger.info(f"뉴스 검색: {keywords} ({start_date} ~ {end_date})")

        # BigKinds API 호출 로직
        # 실제로는 API 명세에 따라 구현 필요
        # 여기서는 더미 데이터 반환

        logger.warning("BigKinds API 연동이 필요합니다. 더미 데이터를 반환합니다")

        # 더미 뉴스 데이터
        dummy_articles = []

        for i in range(min(10, max_results)):
            article = {
                'id': f'news_{i+1}',
                'title': f'한국은행, 기준금리 관련 뉴스 {i+1}',
                'content': '한국은행이 물가상승 압력과 경기 둔화 우려 속에서 통화정책 방향을 논의했다.',
                'published_date': start_date,
                'source': '경제신문',
                'url': f'https://example.com/news/{i+1}',
                'entities': {
                    'persons': ['이창용'],
                    'organizations': ['한국은행', '금융통화위원회'],
                    'locations': ['서울']
                }
            }
            dummy_articles.append(article)

        logger.info(f"뉴스 검색 완료: {len(dummy_articles)}개 기사")

        return dummy_articles

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        텍스트 감성 분석

        Args:
            text: 분석할 텍스트

        Returns:
            {'positive': 0.x, 'neutral': 0.x, 'negative': 0.x}
        """
        # 간단한 키워드 기반 감성 분석 (실제로는 더 정교한 모델 사용)
        positive_keywords = ['상승', '개선', '확대', '호조', '증가', '긍정']
        negative_keywords = ['하락', '둔화', '위축', '부진', '감소', '우려', '불확실성']

        text_lower = text.lower()

        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)
        total = pos_count + neg_count

        if total == 0:
            return {'positive': 0.0, 'neutral': 1.0, 'negative': 0.0}

        # 정규화
        pos_score = pos_count / total if total > 0 else 0
        neg_score = neg_count / total if total > 0 else 0
        neu_score = max(0, 1 - pos_score - neg_score)

        return {
            'positive': pos_score,
            'neutral': neu_score,
            'negative': neg_score
        }

    def fetch_bok_related_news(
        self,
        meeting_date: str,
        days_before: int = 5,
        days_after: int = 5
    ) -> pd.DataFrame:
        """
        한국은행 회의 전후 뉴스 수집

        Args:
            meeting_date: 회의 날짜 (YYYY-MM-DD)
            days_before: 회의 전 n일
            days_after: 회의 후 n일

        Returns:
            뉴스 DataFrame
        """
        # 날짜 범위 계산
        meeting_dt = datetime.strptime(meeting_date, '%Y-%m-%d')
        start_date = (meeting_dt - timedelta(days=days_before)).strftime('%Y-%m-%d')
        end_date = (meeting_dt + timedelta(days=days_after)).strftime('%Y-%m-%d')

        # 뉴스 검색
        keywords = ['한국은행', '금통위', '통화정책', '기준금리']
        articles = self.search_news(keywords, start_date, end_date)

        # DataFrame 변환
        data = []
        for article in articles:
            sentiment = self.analyze_sentiment(article['content'])

            data.append({
                'id': article['id'],
                'title': article['title'],
                'content': article['content'],
                'published_date': article['published_date'],
                'source': article['source'],
                'url': article['url'],
                'sentiment_positive': sentiment['positive'],
                'sentiment_neutral': sentiment['neutral'],
                'sentiment_negative': sentiment['negative'],
                'sentiment_score': sentiment['positive'] - sentiment['negative'],
                'meeting_date': meeting_date
            })

        df = pd.DataFrame(data)

        logger.info(f"뉴스 수집 완료: {len(df)}개 기사")

        return df

    def calculate_news_sentiment_aggregate(
        self,
        meeting_date: str,
        days_before: int = 5,
        days_after: int = 5
    ) -> float:
        """
        회의 전후 뉴스 감성 점수 종합

        Args:
            meeting_date: 회의 날짜
            days_before: 회의 전 n일
            days_after: 회의 후 n일

        Returns:
            -1 ~ +1 범위의 감성 점수
        """
        df_news = self.fetch_bok_related_news(meeting_date, days_before, days_after)

        if df_news.empty:
            return 0.0

        # 평균 감성 점수 계산
        avg_sentiment = df_news['sentiment_score'].mean()

        logger.info(f"[{meeting_date}] 뉴스 감성 점수: {avg_sentiment:.3f}")

        return avg_sentiment

    def save_news_data(
        self,
        df: pd.DataFrame,
        filename: Optional[str] = None
    ):
        """
        뉴스 데이터 저장

        Args:
            df: 뉴스 DataFrame
            filename: 파일명 (None이면 자동 생성)
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"bok_news_{timestamp}.csv"

        filepath = DATA_DIR / filename

        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        logger.info(f"뉴스 데이터 저장: {filepath}")

    def load_saved_news(self, filename: str) -> Optional[pd.DataFrame]:
        """
        저장된 뉴스 데이터 로드

        Args:
            filename: 파일명

        Returns:
            DataFrame 또는 None
        """
        filepath = DATA_DIR / filename

        if not filepath.exists():
            logger.warning(f"파일이 존재하지 않습니다: {filepath}")
            return None

        df = pd.read_csv(filepath)

        logger.info(f"뉴스 데이터 로드: {filepath} ({len(df)}개 기사)")

        return df


def main():
    """테스트 실행"""
    print("=" * 70)
    print("BigKinds 뉴스 데이터 수집 테스트")
    print("=" * 70)

    client = BigKindsClient()

    # 특정 회의 날짜 전후 뉴스 수집
    meeting_date = "2025-11-27"

    print(f"\n회의 날짜: {meeting_date}")
    print("뉴스 수집 중...")

    df_news = client.fetch_bok_related_news(meeting_date, days_before=5, days_after=5)

    # 결과 출력
    print("\n" + "=" * 70)
    print("수집 결과")
    print("=" * 70)
    print(f"수집된 뉴스: {len(df_news)}개")

    if not df_news.empty:
        print(f"\n감성 분포:")
        print(f"  - 긍정: {df_news['sentiment_positive'].mean():.2f}")
        print(f"  - 중립: {df_news['sentiment_neutral'].mean():.2f}")
        print(f"  - 부정: {df_news['sentiment_negative'].mean():.2f}")
        print(f"  - 종합 점수: {df_news['sentiment_score'].mean():.3f}")

        print(f"\n샘플 뉴스:")
        print(df_news[['title', 'published_date', 'sentiment_score']].head())

        # 저장
        client.save_news_data(df_news)

    print(f"\n저장 위치: {DATA_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
