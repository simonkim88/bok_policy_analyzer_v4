"""
한국은행 통화정책 분석 데이터베이스 관리 모듈

SQLite 기반 데이터베이스로 다음 정보를 관리합니다:
- 의사록 원본 데이터
- 키워드 및 가중치 (AI 기본값 + 전문가 조정값)
- 시장 지표 데이터 (ECOS, Indexergo 등)
- 톤 분석 결과
- 전문가 주석
"""

import sqlite3
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
print(f"Project Root Added: {PROJECT_ROOT}")

DB_DIR = PROJECT_ROOT / "data" / "db"
DB_PATH = DB_DIR / "bok_analyzer.db"


@dataclass
class ExpertWeight:
    """전문가 가중치 조정 기록"""
    keyword: str
    adjusted_weight: float
    adjustment_reason: str
    expert_name: str
    date_applied: datetime


class DatabaseManager:
    """데이터베이스 관리 클래스"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        데이터베이스 매니저 초기화

        Args:
            db_path: 데이터베이스 파일 경로 (None이면 기본 경로 사용)
        """
        self.db_path = db_path or DB_PATH

        # 디렉토리 생성
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 데이터베이스 초기화
        self._initialize_database()

        logger.info(f"데이터베이스 초기화 완료: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 생성"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        return conn

    def _initialize_database(self):
        """데이터베이스 스키마 생성"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 1. 문서 원본 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_date TEXT UNIQUE NOT NULL,
            raw_text TEXT,
            pdf_path TEXT,
            discussion_section TEXT,
            decision_section TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 2. 키워드 및 AI 기본 가중치 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT UNIQUE NOT NULL,
            polarity TEXT NOT NULL,  -- 'hawkish' or 'dovish'
            base_weight REAL NOT NULL,
            category TEXT,
            description TEXT
        )
        """)

        # 3. 전문가 가중치 조정 이력 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expert_weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword_id INTEGER NOT NULL,
            adjusted_weight REAL NOT NULL,
            adjustment_reason TEXT,
            expert_name TEXT,
            date_applied TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (keyword_id) REFERENCES keywords(id)
        )
        """)

        # 4. 시장 지표 데이터 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_date DATE NOT NULL,
            indicator_name TEXT NOT NULL,  -- 'base_rate', 'ktb_3y', 'usd_krw', etc.
            value REAL,
            source TEXT,  -- 'ECOS', 'Indexergo', etc.
            UNIQUE(indicator_date, indicator_name, source)
        )
        """)

        # 5. 톤 분석 결과 테이블 (향상된 버전)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tone_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_date TEXT NOT NULL,
            tone_index REAL NOT NULL,
            tone_adjusted REAL,  -- α*tone_text + β*market_reaction + γ*news_sentiment
            hawkish_score REAL,
            dovish_score REAL,
            interpretation TEXT,
            market_reaction_score REAL,
            news_sentiment_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_date) REFERENCES documents(meeting_date)
        )
        """)

        # 6. 전문가 주석 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expert_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_date TEXT NOT NULL,
            quote TEXT,
            comment TEXT,
            expert_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_date) REFERENCES documents(meeting_date)
        )
        """)

        # 7. 모델 파라미터 테이블 (α, β, γ 저장)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parameter_name TEXT UNIQUE NOT NULL,
            parameter_value REAL NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        conn.close()

    def save_keywords_from_dict(self, sentiment_dict):
        """
        감성 사전에서 키워드 로드하여 DB에 저장

        Args:
            sentiment_dict: SentimentDictionary 객체
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 매파 키워드
        for term, entry in sentiment_dict.hawkish_terms.items():
            cursor.execute("""
            INSERT OR REPLACE INTO keywords (term, polarity, base_weight, category, description)
            VALUES (?, ?, ?, ?, ?)
            """, (entry.term, entry.polarity, entry.weight, entry.category, entry.description))

        # 비둘기파 키워드
        for term, entry in sentiment_dict.dovish_terms.items():
            cursor.execute("""
            INSERT OR REPLACE INTO keywords (term, polarity, base_weight, category, description)
            VALUES (?, ?, ?, ?, ?)
            """, (entry.term, entry.polarity, entry.weight, entry.category, entry.description))

        conn.commit()
        conn.close()

        logger.info(f"키워드 {len(sentiment_dict.hawkish_terms) + len(sentiment_dict.dovish_terms)}개 저장 완료")

    def save_expert_weight(
        self,
        keyword: str,
        adjusted_weight: float,
        reason: str = "",
        expert_name: str = "User"
    ):
        """
        전문가 가중치 조정 저장

        Args:
            keyword: 키워드
            adjusted_weight: 조정된 가중치
            reason: 조정 사유
            expert_name: 전문가 이름
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 키워드 ID 조회
        cursor.execute("SELECT id FROM keywords WHERE term = ?", (keyword,))
        row = cursor.fetchone()

        if not row:
            logger.warning(f"키워드를 찾을 수 없습니다: {keyword}")
            conn.close()
            return

        keyword_id = row['id']

        # 조정 이력 저장
        cursor.execute("""
        INSERT INTO expert_weights (keyword_id, adjusted_weight, adjustment_reason, expert_name)
        VALUES (?, ?, ?, ?)
        """, (keyword_id, adjusted_weight, reason, expert_name))

        conn.commit()
        conn.close()

        logger.info(f"전문가 가중치 저장: {keyword} = {adjusted_weight}")

    def get_active_weights(self) -> Dict[str, float]:
        """
        현재 활성 가중치 반환 (전문가 조정값 우선, 없으면 기본값)

        Returns:
            {키워드: 가중치} 딕셔너리
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 가장 최근의 전문가 가중치와 기본 가중치를 조인
        cursor.execute("""
        SELECT
            k.term,
            COALESCE(
                (SELECT adjusted_weight
                 FROM expert_weights ew
                 WHERE ew.keyword_id = k.id
                 ORDER BY date_applied DESC
                 LIMIT 1),
                k.base_weight
            ) as active_weight
        FROM keywords k
        """)

        weights = {row['term']: row['active_weight'] for row in cursor.fetchall()}

        conn.close()
        return weights

    def get_all_keywords(self) -> pd.DataFrame:
        """
        모든 키워드와 가중치 정보 반환

        Returns:
            DataFrame with columns: term, polarity, base_weight, active_weight, category
        """
        conn = self._get_connection()

        query = """
        SELECT
            k.term,
            k.polarity,
            k.base_weight,
            k.category,
            k.description,
            COALESCE(
                (SELECT adjusted_weight
                 FROM expert_weights ew
                 WHERE ew.keyword_id = k.id
                 ORDER BY date_applied DESC
                 LIMIT 1),
                k.base_weight
            ) as active_weight,
            (SELECT COUNT(*)
             FROM expert_weights ew
             WHERE ew.keyword_id = k.id) as adjustment_count
        FROM keywords k
        ORDER BY k.polarity, k.category, k.term
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df

    def save_market_data(
        self,
        df: pd.DataFrame,
        indicator_name: str,
        source: str = "ECOS"
    ):
        """
        시장 지표 데이터 일괄 저장

        Args:
            df: DataFrame with 'date' and 'value' columns
            indicator_name: 지표 이름 (예: 'base_rate', 'ktb_3y')
            source: 데이터 출처
        """
        conn = self._get_connection()

        for _, row in df.iterrows():
            try:
                conn.execute("""
                INSERT OR REPLACE INTO market_indicators
                (indicator_date, indicator_name, value, source)
                VALUES (?, ?, ?, ?)
                """, (row['date'], indicator_name, row['value'], source))
            except Exception as e:
                logger.warning(f"시장 데이터 저장 실패: {e}")

        conn.commit()
        conn.close()

        logger.info(f"시장 데이터 저장: {indicator_name} ({len(df)}개 레코드)")

    def get_market_data(
        self,
        indicator_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        시장 지표 데이터 조회

        Args:
            indicator_name: 지표 이름 (None이면 전체)
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)

        Returns:
            DataFrame
        """
        conn = self._get_connection()

        query = "SELECT * FROM market_indicators WHERE 1=1"
        params = []

        if indicator_name:
            query += " AND indicator_name = ?"
            params.append(indicator_name)

        if start_date:
            query += " AND indicator_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND indicator_date <= ?"
            params.append(end_date)

        query += " ORDER BY indicator_date"

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def get_correlation_data(self, lag_days: int = 30) -> pd.DataFrame:
        """
        시차 분석용 데이터 조인 (톤 지수 + 시장 지표)

        Args:
            lag_days: 최대 시차 (일)

        Returns:
            DataFrame with tone_index and market indicators
        """
        conn = self._get_connection()

        # 톤 결과와 시장 지표를 날짜로 조인
        query = """
        SELECT
            t.meeting_date,
            t.tone_index,
            t.tone_adjusted,
            m.indicator_name,
            m.value as indicator_value,
            m.indicator_date
        FROM tone_results t
        LEFT JOIN market_indicators m
            ON date(m.indicator_date) BETWEEN
               date(t.meeting_date, '-' || ? || ' days') AND
               date(t.meeting_date, '+' || ? || ' days')
        ORDER BY t.meeting_date, m.indicator_date
        """

        df = pd.read_sql_query(query, conn, params=(lag_days, lag_days))
        conn.close()

        return df

    def save_tone_result(
        self,
        meeting_date: str,
        tone_index: float,
        tone_adjusted: Optional[float] = None,
        hawkish_score: float = 0.0,
        dovish_score: float = 0.0,
        interpretation: str = "",
        market_reaction_score: Optional[float] = None,
        news_sentiment_score: Optional[float] = None
    ):
        """
        톤 분석 결과 저장

        Args:
            meeting_date: 회의 날짜
            tone_index: 기본 톤 지수
            tone_adjusted: 조정된 톤 지수
            hawkish_score: 매파 점수
            dovish_score: 비둘기파 점수
            interpretation: 해석
            market_reaction_score: 시장 반응 점수
            news_sentiment_score: 뉴스 감성 점수
        """
        conn = self._get_connection()

        conn.execute("""
        INSERT OR REPLACE INTO tone_results
        (meeting_date, tone_index, tone_adjusted, hawkish_score, dovish_score,
         interpretation, market_reaction_score, news_sentiment_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (meeting_date, tone_index, tone_adjusted, hawkish_score, dovish_score,
              interpretation, market_reaction_score, news_sentiment_score))

        conn.commit()
        conn.close()

    def save_expert_comment(
        self,
        meeting_date: str,
        quote: str,
        comment: str,
        expert_name: str = "User"
    ):
        """
        전문가 주석 저장

        Args:
            meeting_date: 회의 날짜
            quote: 인용 문구
            comment: 주석 내용
            expert_name: 전문가 이름
        """
        conn = self._get_connection()

        conn.execute("""
        INSERT INTO expert_comments (meeting_date, quote, comment, expert_name)
        VALUES (?, ?, ?, ?)
        """, (meeting_date, quote, comment, expert_name))

        conn.commit()
        conn.close()

    def get_expert_comments(self, meeting_date: str) -> List[Dict]:
        """
        특정 회의의 전문가 주석 조회

        Args:
            meeting_date: 회의 날짜

        Returns:
            주석 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT quote, comment, expert_name, created_at
        FROM expert_comments
        WHERE meeting_date = ?
        ORDER BY created_at DESC
        """, (meeting_date,))

        comments = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return comments

    def save_model_parameter(self, name: str, value: float, description: str = ""):
        """
        모델 파라미터 저장 (α, β, γ 등)

        Args:
            name: 파라미터 이름 (예: 'alpha', 'beta', 'gamma')
            value: 파라미터 값
            description: 설명
        """
        conn = self._get_connection()

        conn.execute("""
        INSERT OR REPLACE INTO model_parameters (parameter_name, parameter_value, description, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (name, value, description))

        conn.commit()
        conn.close()

    def get_model_parameters(self) -> Dict[str, float]:
        """
        모델 파라미터 조회

        Returns:
            {파라미터명: 값} 딕셔너리
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT parameter_name, parameter_value FROM model_parameters")

        params = {row['parameter_name']: row['parameter_value'] for row in cursor.fetchall()}

        conn.close()

        # 기본값 설정
        if 'alpha' not in params:
            params['alpha'] = 0.5
        if 'beta' not in params:
            params['beta'] = 0.3
        if 'gamma' not in params:
            params['gamma'] = 0.2

        return params

    def close(self):
        """데이터베이스 연결 종료"""
        # SQLite는 각 메서드에서 연결을 열고 닫으므로 여기서는 불필요
        pass


def main():
    """테스트 실행"""
    print("=" * 70)
    print("데이터베이스 초기화 테스트")
    print("=" * 70)

    # 데이터베이스 생성
    db = DatabaseManager()

    # 감성 사전 로드 및 저장
    from src.nlp.sentiment_dict import SentimentDictionary

    sentiment_dict = SentimentDictionary()
    db.save_keywords_from_dict(sentiment_dict)

    # 키워드 조회
    df_keywords = db.get_all_keywords()
    print(f"\n저장된 키워드 수: {len(df_keywords)}")
    print("\n샘플 키워드:")
    print(df_keywords.head(10))

    # 모델 파라미터 저장
    db.save_model_parameter('alpha', 0.5, 'Text Tone Weight')
    db.save_model_parameter('beta', 0.3, 'Market Reaction Weight')
    db.save_model_parameter('gamma', 0.2, 'News Sentiment Weight')

    params = db.get_model_parameters()
    print(f"\n모델 파라미터: {params}")

    print(f"\n데이터베이스 위치: {DB_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
