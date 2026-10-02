@echo off
echo Building C core...
gcc -shared -O2 -o atm_core.dll atm_core.c
if errorlevel 1 (echo Build failed.&pause&exit /b 1)
echo Built atm_core.dll
python -m pip install -r requirements.txt
set /p TEXTPLATE_API_TOKEN=Enter Textplate API token: 
set /p TEXTPLATE_TEMPLATE_ID=Enter Textplate template ID: 
set FLASK_SECRET_KEY=local-demo-secret-change-me
python app.py
