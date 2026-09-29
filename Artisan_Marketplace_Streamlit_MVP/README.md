# Artisan AI Marketplace — Streamlit MVP

## Run
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Put your Groq key in `.env`, then:
```powershell
streamlit run app.py
```
Open http://localhost:8501.

For Streamlit Community Cloud, add `GROQ_API_KEY` in the app Secrets instead of uploading `.env`.

Marketplace buttons prepare listing data only; production publishing should use official/approved integrations.
