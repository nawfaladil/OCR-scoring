#!/bin/bash
# Start FastAPI backend
uvicorn main_tool.core.api.app:app --reload &
BACKEND_PID=$!
# Start Streamlit frontend
streamlit run main_tool/core/front/front.py &
FRONTEND_PID=$!
# Wait for both to finish
wait $BACKEND_PID $FRONTEND_PID