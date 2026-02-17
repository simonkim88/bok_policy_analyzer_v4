#!/bin/bash
# Convenient script to launch the app on Linux/Cloud
set -e

echo "Starting BOK Policy Analyzer v3..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Ensuring dependencies are up to date..."
pip install -r requirements.txt

echo "Running Streamlit app..."
streamlit run app.py
