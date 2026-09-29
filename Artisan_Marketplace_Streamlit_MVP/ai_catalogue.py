import os,json,base64
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

BASE_DIR=Path(__file__).resolve().parent
load_dotenv(BASE_DIR/".env")
GROQ_API_KEY=os.getenv("GROQ_API_KEY")
MODEL_NAME="qwen/qwen3.8-27b"
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. Create .env in the project root.")
client=Groq(api_key=GROQ_API_KEY)

def generate_catalogue(image_path):
    p=Path(image_path)
    mime={".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png",".webp":"image/webp"}.get(p.suffix.lower(),"application/octet-stream")
    data=base64.b64encode(p.read_bytes()).decode()
    prompt="""Analyze this artisan product image. Return only JSON with:
product_name, description, category, tags (array), keywords (array).
Do not invent precise material, region, certification, dimensions or technique unless reasonably visible."""
    r=client.chat.completions.create(model=MODEL_NAME,messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:{mime};base64,{data}"}}]}],response_format={"type":"json_object"},temperature=.2)
    result=json.loads(r.choices[0].message.content)
    for k in ["product_name","description","category","tags","keywords"]:
        if k not in result: raise ValueError(f"Missing field: {k}")
    return result
