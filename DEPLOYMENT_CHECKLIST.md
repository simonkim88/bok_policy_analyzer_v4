# BOK Policy Analyzer v3 Deployment Checklist (Windows Server)

To ensure a smooth deployment to your Windows Server environment (e.g., Azure VM, AWS EC2 Windows, On-Premise), please follow this checklist.

## 1. Prerequisites (Server Setup)
- [ ] **Python Verified**: Ensure Python 3.10+ is installed and added to PATH.
  ```powershell
  python --version
  ```
- [ ] **Microsoft C++ Build Tools**: Required for compiling some Python packages like `wordcloud` if pre-built wheels are not available.
  - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- [ ] **Fonts**: Ensure Korean fonts (e.g., `Malgun Gothic`) are installed. Windows Server Core editions might lack these by default.

## 2. Application Setup
- [ ] **Clone/Copy Repository**:
  - Use Git or simply copy the project folder to the server (e.g., `C:\Apps\bok_policy_analyzer_v3`).
- [ ] **Virtual Environment Setup**:
  Open PowerShell or Command Prompt as Administrator:
  ```powershell
  cd C:\Apps\bok_policy_analyzer_v3
  python -m venv venv
  .\venv\Scripts\activate
  ```
- [ ] **Install Python Dependencies**:
  ```powershell
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

## 3. Configuration & Data
- [ ] **Existing Data**: The application comes pre-loaded with historical data (`data/analysis/tone_index_results.csv`).
- [ ] **Firewall**: Ensure Windows Firewall allows inbound traffic on port `8501`.
  ```powershell
  # Example PowerShell command to open port 8501
  New-NetFirewallRule -DisplayName "Allow Streamlit 8501" -Direction Inbound -LocalPort 8501 -Protocol TCP -Action Allow
  ```

## 4. Running the Application
- [ ] **Run Command**:
  You can use the provided `run_app_server.bat` script or run manually:
  ```powershell
  streamlit run app.py --server.port 8501
  ```
- [ ] **Access**: Open a browser and navigate to `http://localhost:8501` or `http://<SERVER_IP>:8501`.

## 5. Troubleshooting
- **Execution Policy**: If scripts fail to run, you might need to change the execution policy:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
- **Encoding Issues**: If you see broken characters in the console, try running `chcp 65001` before starting the app.

---
**Deployment Ready!** 🚀
