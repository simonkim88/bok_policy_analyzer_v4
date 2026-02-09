"""
PDF 딥링크 및 텍스트 검증 도구

기능:
- PDF 내 텍스트 위치 찾기
- 인용 문구 정확성 검증
- PDF 좌표 추출
"""

import pdfplumber
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent
PDF_DIR = PROJECT_ROOT / "data" / "pdfs"


class PDFTextLocator:
    """PDF 텍스트 위치 찾기"""

    def __init__(self, pdf_path: Path):
        """
        초기화

        Args:
            pdf_path: PDF 파일 경로
        """
        self.pdf_path = pdf_path

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    def find_text_coordinates(
        self,
        search_text: str,
        fuzzy: bool = True
    ) -> List[Dict]:
        """
        텍스트 위치 찾기

        Args:
            search_text: 검색할 텍스트
            fuzzy: 유사 매칭 사용 여부

        Returns:
            List of dicts with page, x0, y0, x1, y1, text
        """
        logger.info(f"텍스트 검색: '{search_text[:50]}...'")

        results = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # 페이지 텍스트 추출
                    page_text = page.extract_text()

                    if not page_text:
                        continue

                    # 검색 텍스트가 페이지에 있는지 확인
                    if fuzzy:
                        # 공백/줄바꿈 제거 후 비교
                        search_normalized = search_text.replace(' ', '').replace('\n', '')
                        page_normalized = page_text.replace(' ', '').replace('\n', '')

                        if search_normalized in page_normalized:
                            # 단어 단위로 좌표 찾기
                            words = page.extract_words()

                            # 검색 텍스트의 첫 단어로 시작점 찾기
                            search_words = search_text.split()[:3]  # 처음 3단어

                            for i, word in enumerate(words):
                                if any(sw in word['text'] for sw in search_words):
                                    results.append({
                                        'page': page_num,
                                        'x0': word['x0'],
                                        'y0': word['top'],
                                        'x1': word['x1'],
                                        'y1': word['bottom'],
                                        'text': word['text'],
                                        'found_in_page': True
                                    })
                                    break
                    else:
                        # 정확한 매칭
                        if search_text in page_text:
                            words = page.extract_words()

                            for word in words:
                                if search_text.startswith(word['text']):
                                    results.append({
                                        'page': page_num,
                                        'x0': word['x0'],
                                        'y0': word['top'],
                                        'x1': word['x1'],
                                        'y1': word['bottom'],
                                        'text': word['text'],
                                        'found_in_page': True
                                    })
                                    break

        except Exception as e:
            logger.error(f"PDF 처리 중 오류: {e}")

        logger.info(f"검색 결과: {len(results)}개 위치 발견")

        return results

    def get_page_text(self, page_num: int) -> Optional[str]:
        """
        특정 페이지의 텍스트 추출

        Args:
            page_num: 페이지 번호 (1-based)

        Returns:
            페이지 텍스트 또는 None
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                if page_num < 1 or page_num > len(pdf.pages):
                    logger.warning(f"유효하지 않은 페이지 번호: {page_num}")
                    return None

                page = pdf.pages[page_num - 1]
                return page.extract_text()

        except Exception as e:
            logger.error(f"페이지 텍스트 추출 실패: {e}")
            return None

    def save_coordinates_json(self, output_path: Path):
        """
        전체 텍스트 좌표를 JSON으로 저장

        Args:
            output_path: 출력 파일 경로
        """
        logger.info("PDF 좌표 추출 중...")

        all_coords = []

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    words = page.extract_words()

                    for word in words:
                        all_coords.append({
                            'page': page_num,
                            'x0': word['x0'],
                            'y0': word['top'],
                            'x1': word['x1'],
                            'y1': word['bottom'],
                            'text': word['text']
                        })

            # JSON 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_coords, f, ensure_ascii=False, indent=2)

            logger.info(f"좌표 저장 완료: {output_path} ({len(all_coords)}개 단어)")

        except Exception as e:
            logger.error(f"좌표 저장 실패: {e}")


def verify_quote_accuracy(
    original_text: str,
    extracted_quote: str,
    threshold: float = 0.85
) -> Dict:
    """
    인용 문구 정확성 검증

    TF-IDF 기반 코사인 유사도로 검증

    Args:
        original_text: 원본 텍스트
        extracted_quote: 추출된 인용 문구
        threshold: 유사도 임계값

    Returns:
        Dict with similarity, is_accurate, warning
    """
    try:
        # 텍스트 전처리 (공백/줄바꿈 정규화)
        original_clean = ' '.join(original_text.split())
        quote_clean = ' '.join(extracted_quote.split())

        # TF-IDF 벡터화
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([original_clean, quote_clean])

        # 코사인 유사도 계산
        similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]

        is_accurate = similarity >= threshold
        warning = similarity < threshold

        result = {
            'similarity': float(similarity),
            'is_accurate': is_accurate,
            'warning': warning,
            'threshold': threshold
        }

        if warning:
            logger.warning(
                f"인용 문구 유사도 낮음: {similarity:.3f} < {threshold:.3f}"
            )

        return result

    except Exception as e:
        logger.error(f"유사도 계산 실패: {e}")
        return {
            'similarity': 0.0,
            'is_accurate': False,
            'warning': True,
            'threshold': threshold,
            'error': str(e)
        }


def find_quote_in_pdf(
    pdf_path: Path,
    quote: str,
    context_lines: int = 2
) -> Optional[Dict]:
    """
    PDF에서 인용 문구 찾기 (페이지 번호 포함)

    Args:
        pdf_path: PDF 파일 경로
        quote: 찾을 인용 문구
        context_lines: 전후 맥락 줄 수

    Returns:
        Dict with page_num, quote_location, context_before, context_after
    """
    locator = PDFTextLocator(pdf_path)

    try:
        # 좌표 찾기
        coords = locator.find_text_coordinates(quote, fuzzy=True)

        if not coords:
            logger.warning(f"인용 문구를 찾을 수 없습니다: {quote[:50]}...")
            return None

        # 첫 번째 결과 사용
        first_match = coords[0]
        page_num = first_match['page']

        # 해당 페이지 전체 텍스트
        page_text = locator.get_page_text(page_num)

        if not page_text:
            return None

        # 인용 문구 위치 찾기
        quote_normalized = quote.replace(' ', '').replace('\n', '')
        page_normalized = page_text.replace(' ', '').replace('\n', '')

        # 대략적인 위치 계산
        quote_idx = page_normalized.find(quote_normalized)

        if quote_idx == -1:
            context_before = ""
            context_after = ""
        else:
            # 전후 맥락 추출 (간단히 글자 수 기반)
            context_start = max(0, quote_idx - 200)
            context_end = min(len(page_normalized), quote_idx + len(quote_normalized) + 200)

            context_before = page_normalized[context_start:quote_idx]
            context_after = page_normalized[quote_idx + len(quote_normalized):context_end]

        return {
            'page_num': page_num,
            'quote_location': first_match,
            'context_before': context_before[-100:],  # 마지막 100자
            'context_after': context_after[:100],      # 처음 100자
            'full_page_text': page_text
        }

    except Exception as e:
        logger.error(f"인용 문구 검색 실패: {e}")
        return None


def main():
    """테스트 실행"""
    print("=" * 70)
    print("PDF 도구 모듈 테스트")
    print("=" * 70)

    # 샘플 PDF 파일 찾기
    pdf_files = list(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"\nPDF 파일이 없습니다: {PDF_DIR}")
        print("=" * 70)
        return

    # 첫 번째 PDF 파일 사용
    pdf_path = pdf_files[0]
    print(f"\n테스트 PDF: {pdf_path.name}")

    # 텍스트 위치 찾기
    locator = PDFTextLocator(pdf_path)

    # 첫 페이지 텍스트 추출
    page_text = locator.get_page_text(1)

    if page_text:
        # 처음 100자를 검색 텍스트로 사용
        search_text = page_text[:100]

        print(f"\n검색 텍스트: {search_text[:50]}...")

        coords = locator.find_text_coordinates(search_text)

        print(f"\n검색 결과: {len(coords)}개 위치")

        if coords:
            print(f"첫 번째 결과:")
            print(f"  페이지: {coords[0]['page']}")
            print(f"  좌표: ({coords[0]['x0']:.1f}, {coords[0]['y0']:.1f})")

    # 유사도 검증 테스트
    original = "한국은행 금융통화위원회는 물가상승 압력을 고려하여 기준금리를 인상하기로 결정하였다."
    quote = "금융통화위원회는 물가상승 압력을 고려하여 기준금리를 인상하기로 결정"

    result = verify_quote_accuracy(original, quote)

    print("\n유사도 검증:")
    print(f"  유사도: {result['similarity']:.3f}")
    print(f"  정확성: {'✓' if result['is_accurate'] else '✗'}")

    print("\n=" * 70)


if __name__ == "__main__":
    main()
