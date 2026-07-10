#!/bin/bash
cd "$(dirname "$0")"

echo "============================================"
echo " NSE Onm/Decider Screener - starting up"
echo "============================================"
echo ""
echo "Installing/checking required packages (only takes a while the first time)..."

if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo ""
    echo "Python was not found. Install it from https://www.python.org/downloads/"
    echo "then double-click this file again."
    read -p "Press Enter to close..."
    exit 1
fi

$PY -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo "Something went wrong installing packages. See the message above."
    read -p "Press Enter to close..."
    exit 1
fi

echo ""
echo "Starting the app - your browser should open automatically..."
echo "(Keep this window open while you use the app. Close it to stop the app.)"
echo ""
$PY -m streamlit run app.py

read -p "Press Enter to close..."
