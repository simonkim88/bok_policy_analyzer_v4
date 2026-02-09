
# 🖥️ Windows Server 2016 설치 및 운영 가이드

본 가이드는 **Windows Server 2016 (RAM 2GB)** 환경에서 `BOK Policy Analyzer v2`를 설치하고 운영하기 위한 절차를 설명합니다.

---

## 📋 1. 사전 준비 사항 (Prerequisites)

서버 환경이 제한적(RAM 2GB)이므로, 불필요한 리소스 소모를 줄이는 것이 중요합니다.

### 1-1. 필수 프로그램 설치
다음 프로그램들을 순서대로 다운로드하여 설치해 주세요:

1.  **Git for Windows**: 소스 코드를 다운로드하기 위해 필요합니다.
    *   다운로드 (64-bit): [https://git-scm.com/download/win](https://git-scm.com/download/win)
    *   설치 시 기본 설정(Next 계속 클릭)으로 진행해도 무방합니다.

2.  **Python 3.10 이상 (64-bit)**: 프로그램 구동을 위한 언어 환경입니다.
    *   다운로드: [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
    *   **중요:** 설치 첫 화면에서 **"Add Python to PATH"** 체크박스를 반드시 선택하세요!

### 1-2. 성능 최적화 (2GB RAM 대응)
서버의 물리 메모리가 부족할 경우 프로그램이 강제 종료될 수 있습니다. **가상 메모리(Pagefile)**를 넉넉하게 설정해 주세요.

1.  **내 PC** 우클릭 -> **속성** -> **고급 시스템 설정**
2.  **고급** 탭 -> **성능** 설정 -> **고급** 탭 -> **가상 메모리** 변경
3.  "모든 드라이브에 대한 페이징 파일 크기 자동 관리" 체크 해제
4.  **사용자 지정 크기**:
    *   **처음 크기**: 4096 (4GB)
    *   **최대 크기**: 8192 (8GB)
5.  **설정** -> **확인** 후 재부팅

---

## 🚀 2. 설치 및 실행 (Installation)

명령 프롬프트(CMD) 또는 PowerShell을 관리자 권한으로 실행하여 아래 명령어를 차례로 입력하세요.

### 2-1. 소스 코드 다운로드
원하는 폴더(예: `C:\Projects`)로 이동 후 코드를 가져옵니다.

```powershell
mkdir C:\Projects
cd C:\Projects
git clone https://github.com/simonkim88/bok_policy_analyzer_v2.git
cd bok_policy_analyzer_v2
```

### 2-2. 가상환경 설정 (권장)
시스템 파이썬과 분리된 독립된 환경을 만듭니다.

```powershell
# 가상환경 생성 (이름: venv)
python -m venv venv

# 가상환경 활성화
.\venv\Scripts\activate
```
*(커맨드 라인 앞에 `(venv)`가 표시되면 성공입니다)*

### 2-3. 라이브러리 설치
필요한 패키지들을 설치합니다. *서버 사양에 따라 5~10분 정도 소요될 수 있습니다.*

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ▶️ 3. 프로그램 실행

설치가 완료되면 간편하게 실행할 수 있습니다.

### 방법 A: 배치 파일 사용 (가장 쉬움)
폴더 내의 `run_app.bat` 파일을 더블 클릭하면 자동으로 서버가 실행됩니다.

### 방법 B: 수동 실행
```powershell
streamlit run app.py
```

---

## 🌐 4. 외부 접속 설정 (Firewall)

외부(내 PC, 스마트폰 등)에서 서버의 대시보드에 접속하려면 방화벽 포트를 열어야 합니다.

1.  **시작 메뉴** -> "Windows 방화벽(Windows Firewall with Advanced Security)" 검색 및 실행.
2.  좌측 **인바운드 규칙 (Inbound Rules)** 클릭 -> 우측 **새 규칙 (New Rule)** 클릭.
3.  **포트 (Port)** 선택 -> 다음.
4.  **TCP** 선택, 특정 로컬 포트에 `8501` 입력 -> 다음.
5.  **연결 허용 (Allow the connection)** 선택 -> 다음.
6.  프로필 모두 체크 (도메인, 개인, 공용) -> 다음.
7.  이름에 "Streamlit App (8501)" 입력 -> 마침.

이제 브라우저 주소창에 `http://[서버_공인IP]:8501`을 입력하여 접속할 수 있습니다.

---

### ❓ 자주 묻는 질문 (FAQ)

**Q: "python"을 찾을 수 없다는 에러가 나옵니다.**
A: Python 설치 시 "Add to PATH"를 체크하지 않은 경우입니다. Python을 재설치하거나 환경 변수를 수동으로 등록해야 합니다.

**Q: Microsoft Visual C++ 14.0 required 에러가 발생합니다.**
A: `pip install` 중 이 에러가 나면 [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/)를 설치해야 합니다. "C++를 사용한 데스크톱 개발" 워크로드를 선택하여 설치하세요. (약 6GB 필요)

**Q: 실행 중 메모리 부족(MemoryError)으로 꺼집니다.**
A: 위 1-2 항목의 가상 메모리 설정을 늘려주세요. 또한 실행 중인 다른 프로그램(Chrome 등)을 모두 종료해 주세요.
