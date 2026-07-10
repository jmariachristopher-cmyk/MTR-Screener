@echo off
echo ============================================
echo  NSE Onm/Decider Screener - starting up
echo ============================================
echo.
echo Installing/checking required packages (only takes a while the first time)...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Something went wrong installing packages. Do you have Python installed?
    echo Download it from https://www.python.org/downloads/ if not - during
    echo install, make sure to tick "Add Python to PATH".
    pause
    exit /b 1
)

echo.
echo Starting the app - your browser should open automatically...
echo (Keep this black window open while you use the app. Close it to stop the app.)
echo.
python -m streamlit run app.py

pause
