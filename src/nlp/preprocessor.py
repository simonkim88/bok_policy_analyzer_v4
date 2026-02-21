"""
한국은행 의사록 텍스트 전처리 모듈

의사록 텍스트에서:
- 불용어 제거
- 섹션 분리 (토의 내용, 의결 문구)
- 문장 분리
- 위원별 발언 추출
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ProcessedMinutes:
    """전처리된 의사록 데이터"""
    meeting_date: str
    raw_text: str
    # 섹션별 텍스트
    discussion_section: str = ""  # 토의 내용
    decision_section: str = ""    # 의결 문구
    # 문장 리스트
    sentences: List[str] = field(default_factory=list)
    # 위원별 발언
    member_opinions: List[Dict[str, str]] = field(default_factory=list)
    # 전처리된 전체 텍스트
    cleaned_text: str = ""


class TextPreprocessor:
    """한국은행 의사록 텍스트 전처리기"""

    # 불용어 리스트 (분석에 노이즈가 되는 상투적 표현)
    STOPWORDS = [
        # 문서 형식 관련
        "페이지", "---", "금융통화위원회", "의사록", "통화정책방향",
        "결정회의", "회의일시", "회의장소",
        # 상투적 표현
        "것으로", "것이", "것임", "있음", "없음", "있는", "없는",
        "바와", "같이", "대해", "대한", "등을", "등이", "등의",
        "이를", "이에", "따라", "따른", "위해", "통해", "관해",
        "또한", "그리고", "그러나", "다만", "한편",
        # 형식적 표현
        "합니다", "됩니다", "입니다", "습니다", "ㅂ니다",
        "하였음", "되었음", "있었음", "하였다", "되었다",
        # 일반적 지시어
        "이번", "금번", "당분간", "향후", "앞으로",
    ]

    # 위원 발언 시작 패턴
    MEMBER_PATTERN = re.compile(
        r'(한\s*위원|일부\s*위원|다른\s*위원|또\s*다른\s*위원|'
        r'대부분의?\s*위원|다수의?\s*위원|몇몇\s*위원|'
        r'일부\s*금통위원|한\s*금통위원|위원들?은?|'
        r'[가-힣]{1,3}\s*위원)',
        re.MULTILINE
    )

    # 섹션 구분 패턴
    DISCUSSION_START_PATTERNS = [
        r'토의\s*내용',
        r'위원들의?\s*토의',
        r'위원.*의견',
        r'금번\s*회의에서',
    ]

    DECISION_START_PATTERNS = [
        r'의결\s*사항',
        r'의결\s*내용',
        r'결정\s*사항',
        r'기준금리.*결정',
        r'금융통화위원회는.*의결',
    ]

    SENTENCE_CONNECTORS = ["다만", "그러나", "한편", "또한", "반면"]

    def __init__(self, use_kss: bool = True):
        """
        전처리기 초기화

        Args:
            use_kss: Korean Sentence Splitter 사용 여부
        """
        self.use_kss = use_kss
        self._kss = None

        if use_kss:
            try:
                import kss
                self._kss = kss
                logger.info("KSS(Korean Sentence Splitter) 로드 완료")
            except ImportError:
                logger.warning("KSS를 설치해주세요: pip install kss")
                self.use_kss = False

    def remove_page_headers(self, text: str) -> str:
        """페이지 헤더/푸터 제거"""
        # "--- 페이지 N ---" 형태 제거
        text = re.sub(r'---\s*페이지\s*\d+\s*---', '', text)
        # 페이지 번호만 있는 라인 제거
        text = re.sub(r'^\s*-?\s*\d+\s*-?\s*$', '', text, flags=re.MULTILINE)
        return text

    def remove_stopwords(self, text: str) -> str:
        """불용어 제거 (단, 문맥 보존을 위해 완전 제거는 하지 않음)"""
        # 불용어는 분석 시점에 필터링하고, 전처리에서는 공백 정규화만 수행
        # 공백 정규화
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        # 특수문자 정리 (괄호 내용 보존)
        text = re.sub(r'[「」『』【】]', '', text)
        text = text.replace('…', '...')
        # 문맥 전환 표현 앞뒤 공백 정리
        text = re.sub(r'\s*(다만|그러나|한편|또한)\s*', r' \1 ', text)
        # 연속 공백 제거
        text = re.sub(r' +', ' ', text)
        # 연속 줄바꿈 제거
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

    def extract_sections(self, text: str) -> Tuple[str, str]:
        """
        의사록에서 토의 내용과 의결 문구 섹션 분리

        Returns:
            (토의 내용, 의결 문구) 튜플
        """
        discussion = ""
        decision = ""

        # 토의 내용 섹션 찾기
        discussion_match = None
        for pattern in self.DISCUSSION_START_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                discussion_match = match
                break

        # 의결 사항 섹션 찾기
        decision_match = None
        for pattern in self.DECISION_START_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                decision_match = match
                break

        # 섹션 추출
        if discussion_match and decision_match:
            if discussion_match.start() < decision_match.start():
                discussion = text[discussion_match.start():decision_match.start()]
                decision = text[decision_match.start():]
            else:
                decision = text[decision_match.start():discussion_match.start()]
                discussion = text[discussion_match.start():]
        elif discussion_match:
            discussion = text[discussion_match.start():]
        elif decision_match:
            decision = text[decision_match.start():]
        else:
            # 섹션 구분이 없으면 전체를 토의 내용으로
            discussion = text

        return discussion.strip(), decision.strip()

    def split_sentences(self, text: str) -> List[str]:
        """
        문장 분리

        Args:
            text: 입력 텍스트

        Returns:
            문장 리스트
        """
        if self.use_kss and self._kss:
            try:
                sentences = self._kss.split_sentences(text)
                return [str(s).strip() for s in sentences if str(s).strip()]
            except Exception as e:
                logger.warning(f"KSS 문장 분리 실패, 기본 분리 사용: {e}")

        # 기본 문장 분리 (마침표, 물음표, 느낌표 + 전환 표현 기준)
        connector_pattern = '|'.join(self.SENTENCE_CONNECTORS)
        split_pattern = rf'(?<=[.?!;])\s+|(?<=다)\s+(?=({connector_pattern}))'
        sentences = re.split(split_pattern, text)
        # 캡처 그룹으로 들어온 전환 표현 조각 제거
        connector_set = set(self.SENTENCE_CONNECTORS)
        sentences = [s for s in sentences if s and s not in connector_set]
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    def extract_member_opinions(self, text: str) -> List[Dict[str, str]]:
        """
        위원별 발언 추출

        Returns:
            [{"member": "한 위원", "opinion": "발언 내용"}, ...]
        """
        opinions = []

        # 위원 발언 패턴으로 텍스트 분할
        parts = self.MEMBER_PATTERN.split(text)

        current_member = None
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # 위원 패턴에 매치되면 다음 부분이 해당 위원의 발언
            if self.MEMBER_PATTERN.match(part):
                current_member = part
            elif current_member:
                # 발언 내용 정제
                opinion_text = self.normalize_text(part)
                if len(opinion_text) > 20:  # 너무 짧은 발언 제외
                    opinions.append({
                        "member": current_member,
                        "opinion": opinion_text
                    })
                current_member = None

        return opinions

    def process(self, text: str, meeting_date: str = "") -> ProcessedMinutes:
        """
        의사록 텍스트 전처리 수행

        Args:
            text: 원본 의사록 텍스트
            meeting_date: 회의 날짜 (YYYY_MM_DD 형식)

        Returns:
            ProcessedMinutes 객체
        """
        result = ProcessedMinutes(
            meeting_date=meeting_date,
            raw_text=text
        )

        # 1. 페이지 헤더 제거
        cleaned = self.remove_page_headers(text)

        # 2. 텍스트 정규화
        cleaned = self.normalize_text(cleaned)

        # 3. 섹션 분리
        discussion, decision = self.extract_sections(cleaned)
        result.discussion_section = discussion
        result.decision_section = decision

        # 4. 문장 분리 (토의 내용 기준)
        if discussion:
            result.sentences = self.split_sentences(discussion)

        # 5. 위원별 발언 추출
        if discussion:
            result.member_opinions = self.extract_member_opinions(discussion)

        # 6. 전처리된 텍스트 저장
        result.cleaned_text = cleaned

        logger.info(
            f"전처리 완료 [{meeting_date}]: "
            f"문장 {len(result.sentences)}개, "
            f"위원 발언 {len(result.member_opinions)}개"
        )

        return result

    def process_file(self, filepath: Path) -> Optional[ProcessedMinutes]:
        """
        텍스트 파일 전처리

        Args:
            filepath: 텍스트 파일 경로

        Returns:
            ProcessedMinutes 객체 또는 None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()

            # 파일명에서 날짜 추출 (예: minutes_2024_01_11.txt)
            meeting_date = filepath.stem.replace("minutes_", "")

            return self.process(text, meeting_date)

        except Exception as e:
            logger.error(f"파일 처리 실패 [{filepath}]: {e}")
            return None

    def process_directory(self, dir_path: Path) -> List[ProcessedMinutes]:
        """
        디렉토리 내 모든 텍스트 파일 전처리

        Args:
            dir_path: 텍스트 파일 디렉토리

        Returns:
            ProcessedMinutes 리스트
        """
        results = []

        for filepath in sorted(dir_path.glob("*.txt")):
            result = self.process_file(filepath)
            if result:
                results.append(result)

        logger.info(f"총 {len(results)}개 파일 전처리 완료")
        return results


def main():
    """테스트 실행"""
    from pathlib import Path

    # 프로젝트 루트
    project_root = Path(__file__).parent.parent.parent
    texts_dir = project_root / "data" / "texts"

    # 전처리기 초기화
    preprocessor = TextPreprocessor(use_kss=True)

    # 샘플 파일 처리
    sample_files = list(texts_dir.glob("*.txt"))[:3]

    for filepath in sample_files:
        print(f"\n{'='*60}")
        print(f"파일: {filepath.name}")
        print('='*60)

        result = preprocessor.process_file(filepath)

        if result:
            print(f"회의 날짜: {result.meeting_date}")
            print(f"전체 문장 수: {len(result.sentences)}")
            print(f"위원 발언 수: {len(result.member_opinions)}")

            print(f"\n--- 토의 내용 (처음 500자) ---")
            print(result.discussion_section[:500] if result.discussion_section else "없음")

            print(f"\n--- 위원 발언 샘플 ---")
            for op in result.member_opinions[:3]:
                print(f"[{op['member']}] {op['opinion'][:100]}...")


if __name__ == "__main__":
    main()
