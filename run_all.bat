@echo off
REM Get the directory where this batch file is located
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

REM Activate your virtual environment
call .\venv\Scripts\activate

REM Start uvicorn in a new terminal window
start "Uvicorn Server" cmd /k uvicorn main_tool.core.api.app:app --reload

REM Start streamlit in another new terminal window
start "Streamlit App" cmd /k streamlit run main_tool/core/front/front.py