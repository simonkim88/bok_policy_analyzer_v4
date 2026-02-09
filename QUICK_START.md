# 빠른 시작 가이드

## 프로그램 실행 방법

### 방법 1: 배치 파일 사용 (가장 간단)

1. `run_app.bat` 파일을 더블클릭
2. 브라우저가 자동으로 열리고 대시보드가 표시됩니다
3. 주소: http://localhost:8501

### 방법 2: 명령줄 사용

```bash
# 1. 가상환경 활성화
venv\Scripts\activate

# 2. Streamlit 앱 실행
streamlit run app.py
```

### 방법 3: Visual Studio Code에서

1. VS Code에서 프로젝트 폴더 열기
2. 터미널에서 가상환경 활성화: `venv\Scripts\activate`
3. 실행: `streamlit run app.py`

---

## 초기 설정 (최초 1회만)

### 1. 데이터베이스 초기화

```bash
venv\Scripts\activate
python src/data/database.py
```

**결과:** `data/db/bok_analyzer.db` 파일 생성

### 2. ECOS API 키 설정 (선택사항)

한국은행 경제통계시스템 데이터를 수집하려면:

1. https://ecos.bok.or.kr/api/ 에서 API 키 발급
2. 환경변수 설정:
   ```bash
   set ECOS_API_KEY=your_api_key_here
   ```
3. 데이터 수집:
   ```bash
   python src/data/ecos_connector.py
   ```

---

## 현재 사용 가능한 기능

### ✅ 기본 기능 (API 키 없이 작동)

- 톤 지수 게이지
- 금리 예측 확률
- 시계열 톤 지수 차트
- 주요 키워드 분석
- 회의별 상세 분석 (Analysis View)

### ⚙️ 신규 추가 기능 (Phase 1 & 2)

- **데이터베이스 기반 관리**: 모든 데이터가 SQLite DB에 저장
- **전문가 설정 페이지** (준비 중):
  - 키워드 가중치 조정
  - 모델 파라미터 튜닝 (α, β, γ)
  - 설정 내보내기/가져오기

### 🔄 고급 기능 (API 키 필요)

- **ECOS 데이터**: 기준금리, 국고채, CPI, CSI, 환율
- **Indexergo 데이터**: 미국 국채, KOSPI 변동성
- **BigKinds 뉴스**: 감성 분석
- **향상된 톤 지수**: Text + Market + News 통합

---

## 문제 해결

### "ModuleNotFoundError: No module named 'xxx'"

가상환경이 활성화되지 않았을 가능성:

```bash
# 가상환경 활성화
venv\Scripts\activate

# 또는 run_app.bat 사용
```

### "톤 분석 결과 파일이 없습니다"

톤 분석을 먼저 실행해야 합니다:

```bash
venv\Scripts\activate
python src/nlp/tone_analyzer.py
```

### "ECOS API 키가 설정되지 않았습니다"

이것은 경고입니다. 기본 기능은 API 키 없이 작동합니다.
ECOS 데이터를 사용하려면 API 키를 설정하세요.

### 포트가 이미 사용 중

다른 Streamlit 앱이 실행 중일 수 있습니다:

```bash
# 다른 포트로 실행
streamlit run app.py --server.port 8502
```

---

## 다음 단계

1. **대시보드 탐색**: 다양한 회의 선택 및 분석 결과 확인
2. **전문가 설정**: 향후 추가될 설정 페이지에서 가중치 조정
3. **데이터 수집**: ECOS API 키 설정 후 실제 경제 데이터 수집
4. **향상된 분석**: tone_analyzer_v2.py로 통합 톤 지수 계산

---

## 유용한 링크

- **ECOS API 가이드**: https://ecos.bok.or.kr/api/
- **BigKinds**: https://www.bigkinds.or.kr/
- **Streamlit 문서**: https://docs.streamlit.io/

---

## 프로젝트 구조

```
bok_policy_analyzer_v2/
├── run_app.bat              # ✅ 간편 실행 스크립트
├── app.py                   # 메인 대시보드
├── data/
│   ├── analysis/            # 분석 결과 (CSV)
│   ├── db/                  # SQLite 데이터베이스
│   └── pdfs/                # 의사록 PDF 파일
├── src/
│   ├── data/                # 데이터 수집 모듈
│   ├── nlp/                 # 톤 분석 모듈
│   ├── models/              # 예측 모델
│   ├── utils/               # 유틸리티
│   └── views/               # UI 뷰
└── venv/                    # 가상환경
```

---

**최종 업데이트:** 2026-02-09
**버전:** 2.0.0-alpha
