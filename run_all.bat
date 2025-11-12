@echo off
start cmd /k "uvicorn main_tool.core.api.app:app --reload"
start cmd /k "streamlit run main_tool/core/front/front.py"