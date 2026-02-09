# 한국은행 통화정책 분석 웹사이트 업그레이드 구현 요약

## 구현 완료 날짜
2026-02-09

## 구현된 Phase

### ✅ Phase 1: 데이터 통합 및 백엔드 강화

#### 1.1 신규 파일 생성

**데이터 수집 모듈:**
- ✅ `src/data/database.py` - SQLite 데이터베이스 관리
- ✅ `src/data/indexergo_scraper.py` - Indexergo 자본시장 데이터 스크레이퍼
- ✅ `src/data/bigkinds_api_client.py` - BigKinds 뉴스 API 클라이언트
- ✅ `src/data/ecos_connector.py` - ECOS API 고도화 (시차 분석 포함)

**NLP 모듈:**
- ✅ `src/nlp/tone_analyzer_v2.py` - 향상된 톤 분석기 (α·text + β·market + γ·news)

**분석 모듈:**
- ✅ `src/models/lag_analysis.py` - 리딩/래깅 지표 분석

**유틸리티 모듈:**
- ✅ `src/utils/charts.py` - 고도화된 차트 생성
- ✅ `src/utils/pdf_tools.py` - PDF 딥링크 및 텍스트 검증

**뷰 모듈:**
- ✅ `src/views/settings_view.py` - 전문가 설정 UI

#### 1.2 데이터베이스 스키마

**생성된 테이블:**
- `documents` - 의사록 원본
- `keywords` - 키워드 및 AI 기본 가중치
- `expert_weights` - 전문가 가중치 조정 이력
- `market_indicators` - 시장 지표 데이터
- `tone_results` - 톤 분석 결과 (향상된 버전)
- `expert_comments` - 전문가 주석
- `model_parameters` - 모델 파라미터 (α, β, γ)

#### 1.3 향상된 톤 지수 모델

**공식:**
```
Tone_Adjusted = α · Tone_Text + β · Market_Reaction + γ · News_Sentiment

where:
  - α (기본 0.5): 텍스트 톤 가중치
  - β (기본 0.3): 시장 반응 가중치
  - γ (기본 0.2): 뉴스 감성 가중치
  - α + β + γ = 1.0
```

**구성 요소:**
- `Tone_Text`: 기존 의사록 텍스트 분석
- `Market_Reaction`: 의사록 발표 전후(T-5 ~ T+10일) 시장 변화
- `News_Sentiment`: BigKinds 뉴스 감성 분석 (T-5 ~ T+5일)

#### 1.4 의존성 추가

**requirements.txt 추가:**
- `selenium>=4.10.0` - 웹 스크레이핑
- `ekonlpy>=2.0.0` - 한국어 NLP
- `wordcloud>=1.9.2` - 워드클라우드
- `Pillow>=10.0.0` - 이미지 처리
- `openpyxl>=3.1.0` - Excel 처리

---

### ✅ Phase 2: 전문가 개입형 시스템 (부분 완료)

#### 2.1 전문가 가중치 조정 UI

**구현 내용:**
- ✅ `src/views/settings_view.py`
  - 키워드 가중치 조정 (슬라이더 UI)
  - 모델 파라미터 조정 (α, β, γ)
  - 설정 저장/복원 기능

**기능:**
- 매파/비둘기파 키워드별 가중치 조정 (0.5 ~ 3.0)
- 가중치 합 자동 검증 및 정규화
- 데이터베이스 연동 (변경 이력 저장)
- CSV 내보내기/가져오기

#### 2.2 PDF 딥링크 기능

**구현 내용:**
- ✅ `src/utils/pdf_tools.py`
  - PDF 텍스트 좌표 추출
  - 인용 문구 검색 및 페이지 식별
  - TF-IDF 기반 유사도 검증

**기능:**
- `PDFTextLocator` 클래스: 텍스트 위치 찾기
- `verify_quote_accuracy()`: 인용 문구 정확성 검증 (임계값 0.85)
- `find_quote_in_pdf()`: PDF 내 인용 문구 찾기 + 맥락 추출

#### 2.3 리딩/래깅 지표 분석

**구현 내용:**
- ✅ `src/models/lag_analysis.py`
  - 교차 상관관계 (Cross-Correlation) 계산
  - 최적 시차 식별
  - 선행/후행 관계 판단

**기능:**
- `LagAnalyzer` 클래스
- `calculate_cross_correlation()`: -30 ~ +30일 시차 분석
- `identify_lead_lag_relationship()`: 선행/후행 관계 식별
- 시각화: 시차 상관관계 플롯

---

### 🔄 Phase 3: UI/UX 고도화 (진행 중)

#### 3.1 3대 리서치 축 탭 구조

**계획:**
- 📊 통화신용정책
- 🏛️ 금융안정정책
- 🌍 국제금융경제
- ⚙️ 전문가 설정

**아직 구현 필요:**
- [ ] app.py 리팩토링 (3대 탭 구조)
- [ ] 각 탭별 뷰 함수 분리

#### 3.2 고도화된 시각화

**구현 내용:**
- ✅ `src/utils/charts.py`
  - 시장 반응 차트 (의사록 발표 전후)
  - 키워드 영향력 분석 차트
  - 워드클라우드 (매파/비둘기파 색상 구분)
  - 다변량 시계열 차트
  - 상관관계 히트맵

#### 3.3 사실성 검증 및 전문가 주석

**구현 내용:**
- ✅ PDF 딥링크 도구 (pdf_tools.py)
- ✅ 데이터베이스 주석 테이블 (expert_comments)

**아직 구현 필요:**
- [ ] analysis_view.py 수정 (검증된 인용 + 주석 UI)

---

## 사용 방법

### 1. 데이터베이스 초기화

```bash
python src/data/database.py
```

**결과:**
- `data/db/bok_analyzer.db` 생성
- 키워드 및 기본 가중치 저장

### 2. ECOS 데이터 수집

```bash
# 환경변수 설정
export ECOS_API_KEY=your_api_key

# 데이터 수집
python src/data/ecos_connector.py
```

**결과:**
- 기준금리, 국고채, CPI, CSI, 환율 데이터 수집
- 데이터베이스에 저장

### 3. Indexergo 및 BigKinds 데이터 수집

```bash
# Indexergo 데이터
python src/data/indexergo_scraper.py

# BigKinds 뉴스
python src/data/bigkinds_api_client.py
```

**참고:**
- 현재는 더미 데이터 생성
- 실제 API 연동 시 API 키 필요

### 4. 향상된 톤 분석 실행

```bash
python src/nlp/tone_analyzer_v2.py
```

**결과:**
- 텍스트 + 시장 + 뉴스 통합 톤 지수 계산
- `data/analysis/enhanced_tone_index_results.csv` 생성

### 5. 대시보드 실행

```bash
streamlit run app.py
```

**접근:**
- http://localhost:8501
- 전문가 설정 탭에서 가중치 조정 가능

---

## 주요 개선 사항

### 데이터 정합성
- ✅ 톤 지수와 금리 예측 간 논리적 연결 강화
- ✅ 다중 데이터 소스 통합 (ECOS + Indexergo + BigKinds)
- ✅ 시차 분석으로 선행/후행 관계 명확화

### 신뢰성
- ✅ PDF 딥링크로 인용 문구 검증 가능
- ✅ TF-IDF 기반 유사도 검증
- ✅ 전문가 주석 기능

### 전문성
- ✅ 전문가 도메인 지식 주입 (가중치 조정)
- ✅ 모델 파라미터 실시간 조정
- ✅ 변경 이력 추적

### 투명성
- ✅ 선행/후행 지표 분석
- ✅ 키워드 영향력 분석
- ✅ 데이터베이스 기반 감사 추적

---

## 다음 단계

### 단기 (1주)
1. [ ] app.py 3대 탭 구조로 리팩토링
2. [ ] 각 탭별 콘텐츠 채우기
3. [ ] analysis_view.py에 PDF 딥링크 통합
4. [ ] 전문가 주석 UI 구현

### 중기 (2-3주)
1. [ ] ECOS API 키 설정 및 실제 데이터 수집
2. [ ] Indexergo 실제 API 연동 (또는 FRED API 사용)
3. [ ] BigKinds API 키 발급 및 연동
4. [ ] 워드클라우드 한글 폰트 설정

### 장기 (1개월+)
1. [ ] 백테스팅 기능 추가
2. [ ] 예측 모델 성능 평가
3. [ ] 사용자 매뉴얼 작성
4. [ ] 배포 가이드 작성

---

## 파일 구조

```
bok_policy_analyzer_v2/
├── app.py                          # 메인 대시보드 (TODO: 3대 탭 구조로 수정)
├── requirements.txt                # ✅ 의존성 업데이트 완료
├── data/
│   ├── db/
│   │   └── bok_analyzer.db        # ✅ SQLite 데이터베이스
│   ├── indexergo/                 # Indexergo 데이터
│   ├── bigkinds/                  # BigKinds 데이터
│   └── ecos/                      # ECOS 데이터
├── src/
│   ├── data/
│   │   ├── database.py            # ✅ 데이터베이스 관리
│   │   ├── indexergo_scraper.py   # ✅ Indexergo 스크레이퍼
│   │   ├── bigkinds_api_client.py # ✅ BigKinds 클라이언트
│   │   └── ecos_connector.py      # ✅ ECOS 고도화
│   ├── nlp/
│   │   └── tone_analyzer_v2.py    # ✅ 향상된 톤 분석기
│   ├── models/
│   │   └── lag_analysis.py        # ✅ 시차 분석
│   ├── utils/
│   │   ├── charts.py              # ✅ 고도화 차트
│   │   └── pdf_tools.py           # ✅ PDF 도구
│   └── views/
│       ├── settings_view.py       # ✅ 전문가 설정 UI
│       └── analysis_view.py       # TODO: PDF 딥링크 통합
└── README.md                       # TODO: 업데이트 필요
```

---

## 검증 방법

### 단위 테스트
각 모듈을 독립적으로 실행하여 테스트:

```bash
python src/data/database.py
python src/data/ecos_connector.py
python src/nlp/tone_analyzer_v2.py
python src/models/lag_analysis.py
python src/utils/charts.py
python src/utils/pdf_tools.py
```

### 통합 테스트
전체 파이프라인 실행:

```bash
# 1. DB 초기화
python src/data/database.py

# 2. 데이터 수집
python src/data/ecos_connector.py

# 3. 톤 분석
python src/nlp/tone_analyzer_v2.py

# 4. 대시보드 실행
streamlit run app.py
```

---

## 주의사항

### API 키 설정

**ECOS API:**
```bash
export ECOS_API_KEY=your_ecos_key
```

**BigKinds API:**
- `config/bigkinds_config.json` 생성 필요
```json
{
  "bigkinds_api_key": "your_bigkinds_key"
}
```

### 한글 폰트
- 워드클라우드 생성 시 한글 폰트 필요
- Windows: 맑은 고딕 (malgun.ttf) 자동 감지
- Linux: NanumGothic 설치 필요

### 데이터베이스 백업
- `data/db/bok_analyzer.db` 정기적으로 백업 권장

---

## 문의 및 기여

**이슈 리포트:**
- GitHub Issues 사용

**기여 가이드:**
- Pull Request 환영

---

**Last Updated:** 2026-02-09
**Version:** 2.0.0-alpha
