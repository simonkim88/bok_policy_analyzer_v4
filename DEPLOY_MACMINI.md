# 🍎 Mac Mini 배포 가이드 — BOK Policy Analyzer v4

## 📋 사전 요구사항

| 항목 | 최소 요구 |
|------|-----------|
| macOS | 12 (Monterey) 이상 |
| Python | 3.10 ~ 3.12 |
| RAM | 4GB 이상 |
| 디스크 | 1GB 이상 여유 공간 |
| 네트워크 | 인터넷 연결 (ECOS API 사용) |

---

## 🚀 설치 절차

### Step 1: Homebrew & Python 설치 (없는 경우)

```bash
# Homebrew 설치
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.12 설치
brew install python@3.12
```

### Step 2: 프로젝트 다운로드

```bash
cd ~/Projects   # 원하는 디렉토리로 변경 가능
git clone https://github.com/simonkim88/bok_policy_analyzer_v4.git
cd bok_policy_analyzer_v4
```

### Step 3: 가상환경 생성 & 활성화

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 4: 의존성 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **⚠️ 참고:** `kss` 패키지가 설치 중 오류가 발생하면 아래 명령으로 빌드 도구를 먼저 설치하세요:
> ```bash
> xcode-select --install
> pip install kss
> ```

### Step 5: 환경변수 설정 (.env 파일)

`.env` 파일은 `.gitignore`에 포함되어 있어 GitHub에 업로드되지 않습니다.  
수동으로 생성해야 합니다:

```bash
cat > .env << 'EOF'
# ECOS API Key (https://ecos.bok.or.kr/api/)
ECOS_API_KEY=여기에_API_KEY_입력
EOF
```

> **💡 ECOS API 키 발급:** [한국은행 ECOS API](https://ecos.bok.or.kr/api/) 에서 무료로 발급 가능합니다.

### Step 6: 앱 실행

```bash
streamlit run app.py
```

실행 후 터미널에 다음과 같은 메시지가 나타납니다:

```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

브라우저에서 **http://localhost:8501** 로 접속하면 대시보드를 볼 수 있습니다.

---

## 🔄 간편 실행 스크립트 사용

프로젝트에 포함된 `run_app.sh`를 사용할 수도 있습니다:

```bash
chmod +x run_app.sh
./run_app.sh
```

---

## 🌐 외부 접속 설정 (같은 네트워크)

Mac Mini를 서버로 사용하여 다른 기기에서 접속하려면:

### 방법 1: 같은 Wi-Fi/LAN 내에서 접속

```bash
# Mac Mini의 IP 확인
ifconfig | grep "inet " | grep -v 127.0.0.1

# Streamlit을 모든 인터페이스에서 수신하도록 실행
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

다른 기기에서 `http://Mac Mini의 IP:8501` 로 접속합니다.

### 방법 2: macOS 방화벽 설정

**시스템 환경설정 → 네트워크 → 방화벽**에서 8501 포트를 열어줍니다.

또는 터미널에서:
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/python3
```

---

## 🔁 백그라운드에서 항상 실행 (자동 시작)

Mac Mini를 서버로 상시 운영하려면:

### Option A: `nohup` 사용 (간단)

```bash
cd ~/Projects/bok_policy_analyzer_v4
source venv/bin/activate
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 8501 > logs/streamlit.log 2>&1 &
```

### Option B: `launchd` 서비스 등록 (재부팅 시 자동 시작)

```bash
cat > ~/Library/LaunchAgents/com.bok.analyzer.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bok.analyzer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd ~/Projects/bok_policy_analyzer_v4 && source venv/bin/activate && streamlit run app.py --server.address 0.0.0.0 --server.port 8501</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/bok-analyzer-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/bok-analyzer-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# 서비스 등록 & 시작
launchctl load ~/Library/LaunchAgents/com.bok.analyzer.plist
```

서비스 관리:
```bash
# 중지
launchctl unload ~/Library/LaunchAgents/com.bok.analyzer.plist

# 재시작
launchctl unload ~/Library/LaunchAgents/com.bok.analyzer.plist
launchctl load ~/Library/LaunchAgents/com.bok.analyzer.plist
```

---

## 🌍 외부 인터넷에서 접속 (Cloudflare Tunnel)

집 밖에서도 접속하려면 Cloudflare Tunnel을 사용합니다:

```bash
# cloudflared 설치
brew install cloudflare/cloudflare/cloudflared

# 임시 터널 (도메인 없이 빠르게 테스트)
cloudflared tunnel --url http://localhost:8501
```

고정 도메인이 필요하면 [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) 에서 설정합니다.

---

## ❓ 트러블슈팅

| 증상 | 해결 방법 |
|------|-----------|
| `command not found: python3` | `brew install python@3.12` |
| `pip install` 빌드 에러 | `xcode-select --install` 실행 후 재시도 |
| `kss` 설치 실패 | `pip install kss==6.0.1` 특정 버전으로 시도 |
| 포트 8501 사용 중 | `streamlit run app.py --server.port 8502` |
| `.env` 파일 누락 경고 | Step 5에서 `.env` 파일 생성 확인 |
| `ModuleNotFoundError` | `source venv/bin/activate` 후 재시도 |

---

## 📁 프로젝트 구조 (참고)

```
bok_policy_analyzer_v4/
├── app.py                  # 메인 Streamlit 앱
├── config.yaml             # 설정 파일
├── requirements.txt        # Python 패키지 목록
├── .env                    # ECOS API 키 (직접 생성 필요)
├── run_app.sh              # Linux/Mac 실행 스크립트
├── src/                    # 소스 코드
│   ├── models/             # 예측 모델
│   ├── views/              # 화면 뷰
│   └── utils/              # 유틸리티
└── data/                   # 데이터 디렉토리
    ├── 01_minutes/         # 의사록
    ├── 02_decision_statements/  # 통화정책방향 결정문
    ├── 08_ecos/            # ECOS 경제 데이터
    └── analysis/           # 분석 결과
```
