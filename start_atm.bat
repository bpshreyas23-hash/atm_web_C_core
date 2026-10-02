@echo off
if not exist atm_core.dll gcc -shared -O2 -o atm_core.dll atm_core.c
if errorlevel 1 pause&exit /b 1
python -m pip install -r requirements.txt
if "%TEXTPLATE_API_TOKEN%"=="" set /p TEXTPLATE_API_TOKEN=Enter Textplate API token: 
if "%TEXTPLATE_TEMPLATE_ID%"=="" set /p TEXTPLATE_TEMPLATE_ID=Enter Textplate template ID: 
if "%FLASK_SECRET_KEY%"=="" set FLASK_SECRET_KEY=local-demo-secret-change-me
start "ATM Browser" http://127.0.0.1:5000
python app.py
