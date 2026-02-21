# BOK Policy Analyzer v4 - 종합 분석 및 개선 계획서

> **작성일**: 2026-02-19  
> **기준 문서**: 02-12 회의록, 데이터 전략 1&2, 테일러룰 기반 통화정책 다이어그램  
> **대상 프로젝트**: `D:\Programing\bok_policy_analyzer_v4`

---

## 1. 현재 시스템 진단 (AS-IS)

### 1.1 아키텍처 개요

```
app.py (Streamlit 메인)
├── src/views/          ← UI 레이어 (4개 뷰)
│   ├── analysis_view.py / analysis_view_2026.py (중복)
│   ├── taylor_view.py
│   └── settings_view.py
├── src/nlp/            ← NLP 분석 (톤 인덱스)
│   ├── tone_analyzer.py / tone_analyzer_v2.py (중복)
│   ├── preprocessor.py
│   └── sentiment_dict.py
├── src/models/         ← 예측 모델
│   ├── rate_predictor.py
│   ├── backtest.py
│   └── lag_analysis.py
├── src/crawlers/       ← 데이터 수집
│   ├── bok_minutes_crawler.py
│   ├── bok_outlook_crawler.py
│   └── pdf_downloader.py
├── src/data/           ← 데이터 연동
│   ├── ecos_api.py / ecos_connector.py (중복)
│   ├── database.py
│   ├── bigkinds_api_client.py
│   └── indexergo_scraper.py
├── src/utils/          ← 유틸리티
│   ├── charts.py, pdf_tools.py, styles.py
├── src/ecos_loader.py  ← ECOS 직접 로더
└── src/taylor_rule.py  ← 테일러 룰 계산
```

### 1.2 핵심 문제점 진단

#### P1. 데이터 리포지토리 부재 (Critical)
| 항목 | 현황 | 문제 |
|------|------|------|
| 의사록 (Minutes) | 2021~2025 (40건 PDF+TXT) | 정리되어 있으나 `/pdfs/`, `/texts/`에 분산 |
| 통화정책방향 결정문 | 2026-01 (1건만) | **2021~2025 결정문 전체 누락** |
| 기자간담회 | 2026-01 모두발언만 | **Q&A 전사본 전체 누락**, 2021~2025 전체 누락 |
| ECOS 경제지표 | **폴더만 존재, 데이터 0건** | 테일러 룰 계산 시 실시간 API 호출 의존 |
| 시장 데이터 | **수집 체계 없음** | 국채금리, 환율, 주가 데이터 미확보 |
| 뉴스/감성 데이터 | **수집 체계 없음** | 뉴스 감성 분석 불가 |
| 금융안정보고서 | **미수집** | 가계부채, 부동산 데이터 미확보 |
| 경제전망보고서 | **미수집** (Crawler만 존재) | GDP/CPI 전망치 미확보 |
| processed/ | **비어있음** | 정제 파이프라인 미구현 |
| models/ | **비어있음** | 학습 모델 저장 체계 없음 |

#### P2. 코드 품질 문제 (High)
- **API 키 하드코딩**: `LZUNMUPZQ4FFUITEF1R7` 소스코드 내 노출 (ecos_loader.py 등 복수 파일)
- **모듈 중복**: tone_analyzer.py ↔ v2, analysis_view.py ↔ 2026, ecos_api.py ↔ ecos_connector.py
- **하드코딩된 날짜/경로**: extract_oct_quotes.py, read_last_oct_pages.py (특정 2025-10 고정)
- **금리 이력 하드코딩**: RATE_HISTORY가 코드 내 딕셔너리로 관리 (2025-11-27 이후 미반영)
- **이중 가상환경**: `venv/`와 `venv_new/` 공존
- **빈 에러 처리**: 일부 except 블록에서 조용히 실패

#### P3. Crawler 한계 (High)
- **의사록만 크롤링 가능**: bok_minutes_crawler.py는 의사록만 타겟
- **결정문/기자간담회 크롤링 미구현**: fetch_bok_links.py가 URL은 찾지만 체계적 다운로드 없음
- **경제전망 크롤러 불완전**: bok_outlook_crawler.py 존재하나 PDF 텍스트 파싱 불완전
- **시장 데이터 크롤러 없음**: KRX, KOFIA, 코스콤 연동 미구현
- **뉴스 크롤러 없음**: BigKinds API 클라이언트만 존재 (미완성)
- **스케줄링 없음**: 수동 실행 의존, 자동 수집 체계 부재

#### P4. 테일러 룰 모델 한계 (Medium)
- **기본 테일러 룰만 구현**: 금리 = r* + π + α(π - π*) + β(y)
- **금융안정 변수 미반영**: 가계대출, 부동산 등 회의록에서 요구한 확장변수 없음
- **톤 인덱스 미통합**: 테일러 룰과 톤 분석이 분리되어 있음
- **텀 프리미엄 분석 없음**: 채권금리 분해 모듈 미구현
- **기대-실제 괴리 분석 없음**: 시장 기대 vs 실제 발표 차이 분석 미구현

#### P5. NLP/감성 분석 한계 (Medium)
- **단순 키워드 매칭**: 문맥 미반영, N-gram/임베딩 미적용
- **가중치 의미 불명확**: 회의록에서 지적된 0.5~3 가중치 체계의 모호성
- **톤 인덱스 미정의**: 다층 구조(중앙은행 톤 vs 시장 수용 톤) 미구현
- **톤 파라미터 부재**: 정책 실행 확률 모델 없음

---

## 2. Data Repository 구축 계획

### 2.1 목표 폴더 구조

```
data/
├── 01_minutes/                    ← 금융통화위원회 의사록
│   ├── pdf/                       ← 원본 PDF
│   │   ├── minutes_2021_01.pdf
│   │   ├── ...
│   │   └── minutes_2026_01.pdf
│   └── txt/                       ← 추출 텍스트
│       ├── minutes_2021_01.txt
│       └── ...
│
├── 02_decision_statements/        ← 통화정책방향 의결문
│   ├── pdf/
│   └── txt/
│
├── 03_press_conferences/          ← 총재 기자간담회
│   ├── opening_remarks/           ← 모두발언 PDF
│   ├── q_and_a/                   ← Q&A 전사본 PDF
│   └── txt/                       ← 추출 텍스트
│
├── 04_stability_reports/          ← 금융안정보고서 (신규)
│   ├── pdf/
│   └── txt/
│
├── 05_policy_reports/             ← 통화신용정책보고서
│   ├── pdf/
│   └── txt/
│
├── 06_economic_outlook/           ← 경제전망보고서 (신규)
│   ├── pdf/
│   └── txt/
│
├── 07_research_papers/            ← BOK 경제연구/이슈분석 (신규)
│   ├── pdf/
│   └── txt/
│
├── 08_ecos/                       ← ECOS API 정형 데이터 (신규 강화)
│   ├── base_rate/                 ← 기준금리 시계열
│   ├── cpi/                       ← 소비자물가지수
│   ├── gdp/                       ← GDP 성장률
│   ├── employment/                ← 고용지표
│   ├── money_supply/              ← 통화량 (M1/M2)
│   ├── bop/                       ← 국제수지
│   └── lending_rates/             ← 여수신 금리
│
├── 09_market_data/                ← 시장 데이터 (신규)
│   ├── bond_yields/               ← 국고채 금리 (KOFIA)
│   ├── exchange_rates/            ← 환율
│   ├── stock_indices/             ← 주가지수
│   └── credit_spreads/            ← 신용 스프레드
│
├── 10_news_sentiment/             ← 뉴스 감성 데이터 (신규)
│   ├── raw/                       ← BigKinds 원본
│   └── processed/                 ← 감성 점수화
│
├── 11_household_finance/          ← 금융안정 지표 (신규)
│   ├── household_debt/            ← 가계부채
│   ├── housing_prices/            ← 부동산 가격
│   └── credit_indicators/         ← 신용지표
│
├── analysis/                      ← 분석 결과물
│   ├── tone_index_results.csv
│   └── tone_index_results.json
│
├── db/                            ← 데이터베이스
│   └── bok_analyzer.db
│
├── dictionaries/                  ← 사전/사전류
│   └── sentiment_dictionary.json
│
├── models/                        ← 학습된 모델
│   ├── tone_model/
│   └── rate_prediction_model/
│
├── raw/                           ← 크롤링 원본 메타데이터
│   └── minutes_YYYY.json
│
├── processed/                     ← 정제 완료 데이터
│   ├── merged_indicators.parquet
│   └── tone_time_series.parquet
│
└── manifests/                     ← 데이터 목록 관리 (신규)
    ├── data_inventory.json        ← 전체 파일 목록
    ├── acquisition_log.json       ← 수집 이력
    └── missing_data_checklist.md  ← 수작업 다운로드 가이드
```

### 2.2 현재 확보 파일 인벤토리

#### 확보 완료 (이관 대상)

| 카테고리 | 파일 수 | 기간 | 현재 위치 | 이관 대상 |
|---------|--------|------|---------|---------|
| 의사록 PDF | 41건 | 2021.01~2026.01 | `data/pdfs/` + `data/01_minutes/pdf/` | `data/01_minutes/pdf/` 통합 |
| 의사록 TXT | 41건 | 2021.01~2026.01 | `data/texts/` + `data/01_minutes/txt/` | `data/01_minutes/txt/` 통합 |
| 결정문 PDF | 1건 | 2026.01 | `data/02_decision_statements/pdf/` | 유지 |
| 결정문 TXT | 1건 | 2026.01 | `data/02_decision_statements/txt/` | 유지 |
| 모두발언 PDF | 1건 | 2026.01 | `data/03_press_conferences/opening_remarks/` | 유지 |
| 모두발언 TXT | 1건 | 2026.01 | `data/03_press_conferences/txt/` | 유지 |
| 정책보고서 PDF | 1건 | 2026.01 | `data/05_policy_reports/` | 유지 |
| 크롤링 메타 JSON | 6건 | 2021~2026 | `data/raw/` | 유지 |
| 톤 분석 결과 | 2건 | 2021~2026 | `data/analysis/` | 유지 |
| 감성 사전 | 1건 | - | `data/dictionaries/` | 유지 |
| SQLite DB | 1건 | - | `data/db/` | 유지 |
| **합계** | **97건** | | | |

#### 확보 필요 파일 (Crawler 강화 대상)

| 카테고리 | 필요 건수 | 수집 방법 | 우선순위 |
|---------|---------|---------|---------|
| 결정문 PDF (2021~2025) | ~40건 | **Crawler 강화** | P1 - 필수 |
| 기자간담회 모두발언 (2021~2025) | ~40건 | **Crawler 강화** | P1 - 필수 |
| 기자간담회 Q&A (2021~2026) | ~41건 | **수작업 다운로드** (비공개 많음) | P2 - 중요 |
| ECOS 경제지표 (기준금리 시계열) | 월별 데이터 | **API 자동수집** | P1 - 필수 |
| ECOS 경제지표 (CPI) | 월별 데이터 | **API 자동수집** | P1 - 필수 |
| ECOS 경제지표 (GDP) | 분기별 데이터 | **API 자동수집** | P1 - 필수 |
| 경제전망보고서 (연4회) | ~20건 (5년) | **Crawler 강화** | P2 - 중요 |
| 금융안정보고서 (반기) | ~10건 (5년) | **수작업 다운로드** | P2 - 중요 |
| 통화신용정책보고서 (반기) | ~10건 (5년) | **수작업 다운로드** | P2 - 중요 |
| 국고채 금리 (일별) | 시계열 | **KOFIA API/크롤링** | P3 - 선택 |
| 뉴스 데이터 (금통위 전후) | 이벤트별 | **BigKinds API** | P3 - 선택 |
| 가계부채 통계 | 분기별 | **ECOS API** | P3 - 선택 |
| 부동산 가격지수 | 월별 | **KB부동산/ECOS** | P3 - 선택 |

### 2.3 Crawler 강화 계획

#### 현재 Crawler 구조
```
src/crawlers/
├── bok_minutes_crawler.py    ← 의사록 게시판 크롤링 (잘 동작)
├── bok_outlook_crawler.py    ← 경제전망 검색 (불완전)
└── pdf_downloader.py         ← PDF 다운로드 + 텍스트 추출 (잘 동작)
```

#### 강화 후 Crawler 구조
```
src/crawlers/
├── base/
│   ├── bok_base_crawler.py           ← 공통 크롤링 로직 (리팩토링)
│   └── pdf_downloader.py            ← PDF 다운로드 + TXT 추출
│
├── bok/
│   ├── minutes_crawler.py            ← 의사록 크롤러 (기존 강화)
│   ├── decision_statement_crawler.py ← 결정문 크롤러 (신규)
│   ├── press_conference_crawler.py   ← 기자간담회 크롤러 (신규)
│   ├── outlook_crawler.py            ← 경제전망보고서 크롤러 (기존 강화)
│   ├── stability_report_crawler.py   ← 금융안정보고서 크롤러 (신규)
│   └── research_crawler.py           ← BOK 연구자료 크롤러 (신규)
│
├── market/
│   ├── kofia_bond_crawler.py         ← 국고채 금리 (신규)
│   ├── krx_stock_crawler.py          ← 주가지수 (신규)
│   └── exchange_rate_crawler.py      ← 환율 (신규)
│
├── ecos/
│   ├── ecos_bulk_downloader.py       ← ECOS 일괄 다운로드 (신규)
│   └── ecos_indicator_config.yaml    ← 지표 코드 설정 (신규)
│
├── news/
│   └── bigkinds_crawler.py           ← 뉴스 감성 수집 (기존 강화)
│
└── scheduler/
    └── crawl_scheduler.py            ← 자동 수집 스케줄러 (신규)
```

#### 주요 강화 사항

**1. 결정문 크롤러 (신규 - P1)**
- 대상: `https://www.bok.or.kr/portal/bbs/B0000001/list.do?menuNo=200029`
- 검색 키워드: "통화정책방향"
- 2021~2025 40건 일괄 수집
- PDF 다운로드 + 텍스트 추출 자동화

**2. 기자간담회 크롤러 (신규 - P1)**
- 대상: 한국은행 보도자료 게시판
- 검색 키워드: "기자간담회", "모두발언"
- 모두발언 PDF 자동 수집
- Q&A는 별도 게시판/첨부파일 확인 필요

**3. ECOS 일괄 다운로드 (신규 - P1)**
- 주요 지표 코드 설정 파일 (YAML)로 관리
- 기준금리: `722Y001/0101000` (일별)
- CPI: `901Y009/0` (월별)
- GDP: `200Y002/10111` (분기별)
- 통화량 M2: `101Y004/BBGA00` (월별)
- 자동 날짜 범위 생성 + Parquet 저장
- 잠정치/확정치 구분 관리

**4. 자동 수집 스케줄러 (신규 - P2)**
- 금통위 일정에 맞춘 자동 트리거 (연 8회)
- ECOS 경제지표 일일/월별 업데이트
- 수집 로그 + 실패 알림

### 2.4 수작업 다운로드 가이드 (Crawler로 수집 불가한 항목)

아래 파일들은 웹 크롤링으로 자동 수집이 어려워, 수작업으로 다운로드하여 지정 폴더에 배치해야 합니다.

#### 수작업 다운로드 대상 #1: 기자간담회 Q&A 전사본

| 항목 | 내용 |
|------|------|
| **파일 유형** | 기자간담회 질의응답(Q&A) 전사본 |
| **저장 위치** | `data/03_press_conferences/q_and_a/qa_YYYY_MM.pdf` |
| **수집 방법** | 한국은행 홈페이지 > 통화정책 > 통화정책방향 > 각 회의별 상세 페이지 |
| **URL** | `https://www.bok.or.kr/portal/bbs/B0000001/list.do?menuNo=200029` |
| **참고** | Q&A 전사본은 별도 첨부파일로 제공되거나, 기자간담회 영상에서 별도 추출 필요. 일부 회의는 Q&A 비공개일 수 있음 |
| **파일명 규칙** | `qa_YYYY_MM.pdf` (예: `qa_2024_01.pdf`) |
| **필요 건수** | 2021~2025: 약 40건 |

#### 수작업 다운로드 대상 #2: 금융안정보고서

| 항목 | 내용 |
|------|------|
| **파일 유형** | 금융안정보고서 (Financial Stability Report) |
| **저장 위치** | `data/04_stability_reports/pdf/stability_YYYY_HN.pdf` |
| **수집 방법** | 한국은행 홈페이지 > 조사/연구 > 금융안정보고서 |
| **URL** | `https://www.bok.or.kr/portal/bbs/P0002353/list.do?menuNo=200706` |
| **파일명 규칙** | `stability_YYYY_H1.pdf` / `stability_YYYY_H2.pdf` (반기별) |
| **필요 건수** | 2021~2025: 약 10건 |

#### 수작업 다운로드 대상 #3: 통화신용정책보고서

| 항목 | 내용 |
|------|------|
| **파일 유형** | 통화신용정책보고서 |
| **저장 위치** | `data/05_policy_reports/pdf/monetary_credit_YYYY_HN.pdf` |
| **수집 방법** | 한국은행 홈페이지 > 통화정책 > 통화신용정책보고서 |
| **URL** | `https://www.bok.or.kr/portal/bbs/P0002350/list.do?menuNo=200433` |
| **파일명 규칙** | `monetary_credit_YYYY_H1.pdf` / `monetary_credit_YYYY_H2.pdf` |
| **필요 건수** | 2021~2025: 약 10건 |

#### 수작업 다운로드 대상 #4: 경제전망보고서

| 항목 | 내용 |
|------|------|
| **파일 유형** | 경제전망보고서 (수정전망 포함) |
| **저장 위치** | `data/06_economic_outlook/pdf/outlook_YYYY_QN.pdf` |
| **수집 방법** | 한국은행 홈페이지 > 조사/연구 > 경제전망보고서 |
| **URL** | `https://www.bok.or.kr/portal/bbs/P0002955/list.do?menuNo=200793` |
| **파일명 규칙** | `outlook_YYYY_Q1.pdf` ~ `outlook_YYYY_Q4.pdf` (연 4회: 2,5,8,11월) |
| **필요 건수** | 2021~2025: 약 20건 |

#### 수작업 다운로드 대상 #5: 한국의 통화정책 (단행본)

| 항목 | 내용 |
|------|------|
| **파일 유형** | "한국의 통화정책" 해설서 |
| **저장 위치** | `data/07_research_papers/pdf/monetary_policy_handbook.pdf` |
| **수집 방법** | 한국은행 홈페이지 > 간행물 검색 |
| **참고** | 부정기 발간, 통화정책 운영 체계 전반 설명. 테일러 룰 배경이론 이해에 필수 |

#### 수작업 다운로드 대상 #6: 알기 쉬운 경제지표해설

| 항목 | 내용 |
|------|------|
| **파일 유형** | "알기 쉬운 경제지표해설" |
| **저장 위치** | `data/07_research_papers/pdf/economic_indicators_guide.pdf` |
| **수집 방법** | 한국은행 홈페이지 > 간행물 검색 |
| **참고** | GDP, CPI 등 지표 산출 방법론 이해에 필요 |

---

## 3. 전반적 프로그램 개선 계획

### 3.1 Phase 1: Data Foundation (데이터 기반 구축) - 2주

| # | 과제 | 상세 | 우선순위 |
|---|------|------|---------|
| 1.1 | 폴더 구조 재편 | 2.1절 목표 구조로 파일 이관/정리 | P1 |
| 1.2 | 기존 의사록 이관 | `data/pdfs/` → `data/01_minutes/pdf/` 파일명 통일 | P1 |
| 1.3 | 결정문 크롤러 개발 | 2021~2025 결정문 40건 일괄 수집 | P1 |
| 1.4 | 기자간담회 크롤러 개발 | 2021~2025 모두발언 40건 수집 | P1 |
| 1.5 | ECOS 일괄 다운로더 개발 | 기준금리/CPI/GDP 등 핵심 지표 Parquet 저장 | P1 |
| 1.6 | API 키 보안화 | `.env` 파일로 이관, 코드 내 하드코딩 제거 | P1 |
| 1.7 | 수작업 다운로드 가이드 작성 | 2.4절 기반 체크리스트 생성 | P1 |
| 1.8 | 데이터 매니페스트 생성 | `data/manifests/data_inventory.json` 자동 생성 스크립트 | P2 |

### 3.2 Phase 2: Crawler Enhancement (크롤러 강화) - 2주

| # | 과제 | 상세 | 우선순위 |
|---|------|------|---------|
| 2.1 | 크롤러 베이스 클래스 리팩토링 | 공통 로직 추출 (세션 관리, 재시도, 로깅) | P1 |
| 2.2 | PDF 텍스트 추출 파이프라인 통합 | 모든 크롤러가 PDF→TXT 자동 변환 | P1 |
| 2.3 | ECOS 지표 설정 YAML 구현 | 지표 코드/주기/포맷을 설정파일로 관리 | P1 |
| 2.4 | 경제전망보고서 크롤러 개선 | bok_outlook_crawler.py 완성 (GDP/CPI 전망치 파싱) | P2 |
| 2.5 | BigKinds 뉴스 크롤러 완성 | bigkinds_api_client.py 미완성 부분 구현 | P2 |
| 2.6 | 시장 데이터 크롤러 (국고채) | KOFIA API 연동 또는 한국은행 채권금리 데이터 | P3 |
| 2.7 | 수집 스케줄러 구현 | 금통위 일정 기반 자동 트리거 | P3 |

### 3.3 Phase 3: Code Quality & Architecture (코드 품질 개선) - 1주

| # | 과제 | 상세 | 우선순위 |
|---|------|------|---------|
| 3.1 | 중복 모듈 통합 | tone_analyzer v1/v2, analysis_view/2026, ecos_api/connector 통합 | P1 |
| 3.2 | 하드코딩 제거 | RATE_HISTORY → DB, 날짜/경로 → 설정파일 | P1 |
| 3.3 | 가상환경 정리 | venv/ 삭제, venv_new/ → venv 단일화 | P2 |
| 3.4 | 로깅 체계 구축 | 빈 logs/ 폴더에 실제 로깅 구현 | P2 |
| 3.5 | 일회성 스크립트 정리 | extract_oct_quotes.py, read_last_oct_pages.py 삭제 또는 범용화 | P2 |
| 3.6 | 설정 파일 도입 | `config.yaml` or `settings.py`로 모든 설정 중앙 관리 | P2 |

### 3.4 Phase 4: Taylor Rule Enhancement (테일러 룰 고도화) - 3주

| # | 과제 | 상세 | 우선순위 |
|---|------|------|---------|
| 4.1 | 확장 테일러 룰 구현 | 금융안정 변수(가계부채, 부동산) 추가 | P1 |
| 4.2 | 톤 인덱스 → 테일러 룰 통합 | 톤 인덱스를 독립변수 추정에 활용하는 2단계 모델 | P1 |
| 4.3 | 톤 인덱스 재정의 | 텍스트 분석 + 시장 반응 + 뉴스 감성 합성 지표 | P1 |
| 4.4 | 톤 파라미터 분리 | 정책 실행 확률 모델 (방향 vs 크기 vs 확신도) | P2 |
| 4.5 | 텀 프리미엄 분석 모듈 | 10년물 = 기대기준금리 + 텀 프리미엄 분해 | P2 |
| 4.6 | 기대-실제 괴리 모듈 | 시장 기대치 vs 실제 발표 차이 누적 시각화 | P2 |
| 4.7 | 백테스트 프레임워크 강화 | 과거 시점 예측 → 적중률/설명력/정확도 자동 산출 | P2 |

### 3.5 Phase 5: NLP Upgrade (NLP 고도화) - 2주

| # | 과제 | 상세 | 우선순위 |
|---|------|------|---------|
| 5.1 | 가중치 체계 재설계 | 수학적 정규화 + 카테고리별 가중치 | P1 |
| 5.2 | 문맥 기반 분석 도입 | 단어 조합, N-gram, 문장 수준 맥락 반영 | P1 |
| 5.3 | 다층 톤 인덱스 구현 | 중앙은행 톤 인덱스 + 시장 수용 톤 인덱스 분리 | P2 |
| 5.4 | LLM 기반 분석 연동 | 외부 LLM API를 통한 심층 텍스트 분석 (선택) | P3 |
| 5.5 | 감성사전 확장 | 현재 sentiment_dictionary.json 확장 + 버전 관리 | P2 |

### 3.6 Phase 6: Visualization & UI (시각화 개선) - 1주

| # | 과제 | 상세 | 우선순위 |
|---|------|------|---------|
| 6.1 | 테일러 룰 대시보드 | 적정금리 vs 실제금리 실시간 괴리 차트 | P1 |
| 6.2 | 톤 인덱스 타임라인 | 매파/비둘기파 트렌드 + 금통위 이벤트 마커 | P1 |
| 6.3 | 기대-실제 괴리 누적 차트 | 시장 기대 vs 발표 차이의 시계열 | P2 |
| 6.4 | 텀 프리미엄 분해 차트 | 10년 국채금리 = 기대금리 + 텀 프리미엄 | P2 |
| 6.5 | 데이터 커버리지 대시보드 | 어떤 데이터가 수집/미수집 상태인지 현황판 | P3 |

---

## 4. 실행 로드맵 요약

```
Week 1-2:  [Phase 1] 데이터 기반 구축 + 폴더 정리 + 수작업 다운로드
Week 3-4:  [Phase 2] 크롤러 강화 + ECOS 파이프라인
Week 5:    [Phase 3] 코드 품질 개선 + 리팩토링
Week 6-8:  [Phase 4] 테일러 룰 고도화 + 톤 인덱스 통합
Week 9-10: [Phase 5] NLP 고도화
Week 11:   [Phase 6] 시각화 개선 + 통합 테스트
```

### 즉시 실행 항목 (Quick Wins)

1. **API 키 `.env` 이관** - 보안 위험 즉시 해소
2. **기존 의사록 파일 이관** - `data/pdfs/` → `data/01_minutes/pdf/`
3. **빈 폴더 구조 생성** - 2.1절 전체 구조 mkdir
4. **중복 모듈 정리** - tone_analyzer_v2.py를 기본으로, v1 삭제
5. **venv/ 삭제** - venv_new/ 하나로 통일

---

## 5. 참고: 테일러 룰 기반 통화정책 분석 모델 구조도

다이어그램 (`테일러룰기반 통화정책.png`)이 보여주는 전체 시스템:

```
[입력 변수]                      [이론적 기반]         [출력 및 분석]
┌────────────────┐              ┌──────────────┐    ┌──────────────────┐
│ 톤 인덱스       │              │              │    │ 기준금리 예측     │
│ - 텍스트 분석    │──매파/비둘기──▷│              │    │ - 현재 권장 금리   │
│ - 시장 반응      │   신호       │              │    │ - 미래 금리 경로   │
│ - 뉴스 감성      │              │  테일러 룰    │──▷ │                  │
├────────────────┤              │   기반        │    │ 시장금리 해석     │
│ 톤 파라미터      │──정책 확률──▷│  통화정책     │    │ - 채권금리 = 기대  │
│ - 50bp 인상 70% │              │  분석 모델    │    │   금리 + 텀프리미엄│
├────────────────┤              │              │    │                  │
│ 금융안정 변수    │──금융안정──▷ │  (기준금리    │    │ 기대-실제 괴리    │
│ - 가계대출       │              │   예측의     │    │ - 시장 기대치 vs  │
│ - 부동산 가격    │              │   핵심 엔진) │    │   실제 발표 차이   │
│ - 신용 지표      │              │              │    │                  │
├────────────────┤              │              │    │ 투자 시사점       │
│ 시장 데이터      │──시장 신호──▷│              │    │ - 채권/주식/부동산│
│ - 국채금리       │              └──────────────┘    │   자산별 전략     │
│ - 환율          │                    │              └──────────────────┘
│ - 주가지수       │                    │
├────────────────┤                    │ 검증
│ 거시경제 지표    │──거시지표──▷       ▼
│ (한국은행 API)   │              ┌──────────────────┐
│ - GDP, CPI      │              │ 검증 및 개선      │
│ - 실업률, 산업생산│              │ - 백테스트        │
└────────────────┘              │ - 전문가 검증     │
                                 │ - 성능 지표       │
                                 │   (정확도/설명력/적중률)│
                                 └──────────────────┘
```

이 구조도가 보여주듯, 현재 시스템은 **좌측 입력 변수 대부분이 미확보** 상태이며, **데이터 리포지토리 구축이 모든 개선의 전제조건**입니다.
