# Cloud Windows PC 배포 가이드 (BOK Policy Analyzer)

이 가이드는 클라우드 환경의 윈도우 PC(예: AWS EC2 Windows, Azure VM, 또는 원격 접속 가능한 윈도우 서버)에서 `BOK Policy Analyzer`를 설치하고 실행하여 외부에서 접속할 수 있도록 하는 방법을 설명합니다.

## 1. 필수 프로그램 설치

클라우드 PC에 원격 접속한 후 다음 프로그램들을 설치해주세요.

### 1-1. Python 설치
1. [Python 공식 다운로드 페이지](https://www.python.org/downloads/)에서 **Python 3.9 이상** 버전을 다운로드합니다.
2. **설치 시 주의사항**: 설치 화면 맨 아래의 **"Add Python to PATH"** 체크박스를 **반드시 체크**하세요.
3. "Install Now"를 클릭하여 설치합니다.

### 1-2. Git 설치
1. [Git 공식 다운로드 페이지](https://git-scm.com/download/win)에서 윈도우용 Git을 다운로드하여 설치합니다.
2. 기본 설정 그대로 "Next"를 눌러 설치를 완료합니다.

## 2. 프로젝트 다운로드 (Clone)

명령 프롬프트(cmd) 또는 PowerShell을 **관리자 권한**으로 실행합니다.

```powershell
# 프로젝트를 저장할 폴더로 이동 (예: C:\Data)
cd C:\
mkdir Data
cd Data

# GitHub 저장소 복제
git clone https://github.com/simonkim88/bok_policy_analyzer.git
cd bok_policy_analyzer
```

## 3. 가상 환경 설정 및 패키지 설치

```powershell
# 가상 환경 생성 (이름: venv)
python -m venv venv

# 가상 환경 활성화
.\venv\Scripts\activate

# (활성화되면 프롬프트 앞에 (venv)가 표시됩니다)

# 필수 라이브러리 설치
pip install -r requirements.txt
```

## 4. 방화벽 설정 (외부 접속 허용)

클라우드 PC 외부에서 이 웹사이트에 접속하려면 **8501 포트**를 열어야 합니다.

### 4-1. 윈도우 방화벽 설정
1. 윈도우 검색창에 **"방화벽 상태 확인"** 또는 **"Windows Defender 방화벽"** 검색 -> 실행.
2. 좌측 메뉴에서 **"고급 설정"** 클릭.
3. **"인바운드 규칙"** -> 우측의 **"새 규칙..."** 클릭.
4. **포트(Port)** 선택 -> 다음.
5. **TCP** 선택, 특정 로컬 포트에 `8501` 입력 -> 다음.
6. **연결 허용** 선택 -> 다음.
7. 도메인, 개인, 공용 모두 체크 -> 다음.
8. 이름: `Streamlit App (8501)` -> 마침.

### 4-2. 클라우드 콘솔 보안 그룹 설정 (AWS/Azure/GCP의 경우)
*   **AWS EC2**: 보안 그룹(Security Group) 설정에서 인바운드 규칙에 `Custom TCP`, Port `8501`, Source `0.0.0.0/0` (Anywhere) 추가.
*   **Azure VM**: 네트워킹(Networking) 설정에서 인바운드 포트 규칙 추가.

## 5. 앱 실행 및 접속

### 앱 실행
PowerShell(가상환경 활성화 상태)에서 다음 명령어를 실행합니다.

```powershell
streamlit run app.py
```

### 외부 접속
*   실행 후 터미널에 `Network URL: http://...:8501`이 표시될 수 있습니다.
*   자신의 PC 브라우저에서 **`http://[클라우드PC의_공인IP]:8501`** 로 접속합니다.

## 6. (고급) 백그라운드 서비스로 실행하기

터미널을 닫아도 앱이 계속 실행되게 하려면, 배치 파일을 만들고 실행합니다.

1. `run_app.bat` 파일을 프로젝트 폴더에 생성하고 내용을 작성합니다:
   ```batch
   @echo off
   cd /d "C:\Data\bok_policy_analyzer"
   call venv\Scripts\activate
   streamlit run app.py --server.headless true
   ```
2. 이 파일을 더블 클릭하여 실행하면 창이 떠있는 동안 서버가 돌아갑니다.
