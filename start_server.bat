@echo off
echo Starting GenAI OCR Chatbot...
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start Streamlit
echo.
echo Starting Streamlit server...
echo Open your browser to: http://localhost:8501
echo Press Ctrl+C to stop the server
echo.

python -m streamlit run src/ui/streamlit_app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false

pause