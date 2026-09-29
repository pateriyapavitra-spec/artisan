import json, os, uuid
from pathlib import Path
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
CATALOGUE_DIR = BASE_DIR / "catalogue"
UPLOAD_DIR = BASE_DIR / "uploads"
EXPORT_DIR = BASE_DIR / "exports"
PRODUCTS_FILE = CATALOGUE_DIR / "products.json"
for d in (CATALOGUE_DIR, UPLOAD_DIR, EXPORT_DIR): d.mkdir(exist_ok=True)
if not PRODUCTS_FILE.exists(): PRODUCTS_FILE.write_text("[]", encoding="utf-8")

st.set_page_config(page_title="Artisan AI Marketplace", page_icon="🧵", layout="wide")

def load_products():
    try: return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    except: return []

def save_products(p):
    PRODUCTS_FILE.write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")

def base_price(material, hours, craft):
    mult={"Low":.90,"Medium":1.0,"High":1.20}[craft]
    return round((material + hours*50)*mult, 2)

def ai_price(data):
    key=os.getenv("GROQ_API_KEY")
    if key:
        try:
            from groq import Groq
            c=Groq(api_key=key)
            prompt=f"""Price this handmade Indian artisan product as decision support.
Do not claim live market data. Return JSON only:
{{"suggested_price":number,"minimum_price":number,"maximum_price":number,
"confidence":number,"factors":["string"],"explanation":"string"}}
Data: {json.dumps(data, ensure_ascii=False)}"""
            r=c.chat.completions.create(model="qwen/qwen3.8-27b",
                messages=[{"role":"user","content":prompt}],
                response_format={"type":"json_object"}, temperature=.2)
            return json.loads(r.choices[0].message.content)
        except Exception:
            pass
    b=base_price(data["material_cost"],data["hours"],data["craftsmanship"])
    return {"suggested_price":round(b),"minimum_price":round(b),
            "maximum_price":round(b*1.2),"confidence":55,
            "factors":["Material cost","Labour estimate","Craftsmanship level"],
            "explanation":"Local cost-based fallback estimate."}

def export_listing(product, market):
    payload=dict(product)
    payload["marketplace"]=market
    payload["status"]="prepared"
    payload["prepared_at"]=datetime.utcnow().isoformat()+"Z"
    payload["note"]="Prepared listing data; not automatically published."
    path=EXPORT_DIR/f"{product['id']}_{market.lower().replace(' ','_')}.json"
    path.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    return payload,path

if "catalogue" not in st.session_state: st.session_state.catalogue=None
if "image_path" not in st.session_state: st.session_state.image_path=None
if "pricing" not in st.session_state: st.session_state.pricing=None

products=load_products()
st.sidebar.title("🧵 Artisan AI")
page=st.sidebar.radio("Navigation",["🏠 Dashboard","📷 AI Catalogue","💰 AI Pricing","🛒 Marketplace","📦 Saved Products"])
st.sidebar.caption("SIH26090 prototype")

if page=="🏠 Dashboard":
    st.title("🧵 Artisan AI Marketplace")
    st.write("Turn a product photo into a structured catalogue, pricing guidance and marketplace-ready data.")
    a,b,c,d=st.columns(4)
    a.metric("Products",len(products)); b.metric("Priced",sum(bool(p.get("suggested_price")) for p in products))
    c.metric("Catalogue fields","AI"); d.metric("Marketplaces","3")
    st.subheader("Workflow")
    st.write("📷 Upload → 🤖 AI Catalogue → ✏️ Edit → 💰 Price → 🛒 Prepare marketplace listing")

elif page=="📷 AI Catalogue":
    st.title("📷 AI Smart Catalogue")
    up=st.file_uploader("Upload product image",type=["jpg","jpeg","png","webp"])
    if up:
        ext=Path(up.name).suffix or ".jpg"
        path=UPLOAD_DIR/f"{uuid.uuid4().hex}{ext}"
        path.write_bytes(up.getbuffer()); st.session_state.image_path=str(path)
        st.image(up,use_container_width=True)
        if st.button("🤖 Generate AI Catalogue",type="primary"):
            try:
                from ai_catalogue import generate_catalogue
                with st.spinner("AI is analyzing the image..."):
                    st.session_state.catalogue=generate_catalogue(str(path))
                st.success("Catalogue generated.")
            except Exception as e: st.error(str(e))
    if st.session_state.catalogue:
        x=st.session_state.catalogue
        with st.form("catalogue_form"):
            name = st.text_input(
    "Product name",
    x.get("product_name", ""),
    key="catalogue_product_name"
)

desc = st.text_area(
    "Description",
    x.get("description", ""),
    height=150,
    key="catalogue_description"
)

cat = st.text_input(
    "Category",
    x.get("category", ""),
    key="catalogue_category"
)

tags = st.text_input(
    "Tags",
    ", ".join(x.get("tags", [])),
    key="catalogue_tags"
)

keys = st.text_input(
    "Keywords",
    ", ".join(x.get("keywords", [])),
    key="catalogue_keywords"
)
            st.subheader("Product details")
            material=st.text_input("Material")
            craft=st.selectbox("Craftsmanship",["Low","Medium","High"],index=1)
            hours=st.number_input("Production hours",0.0,10000.0,1.0,.5)
            cost=st.number_input("Material cost (₹)",0.0,10000000.0,0.0,50.0)
            region=st.text_input("Region")
            price=st.number_input("Existing price (₹)",0.0,10000000.0,0.0,50.0)
            inventory=st.number_input("Inventory",0,100000,1)
            save=st.form_submit_button("💾 Save Catalogue",type="primary")
        if save:
            pid=uuid.uuid4().hex[:12]
            product={"id":pid,"product_name":name,"description":desc,"category":cat,
              "tags":[i.strip() for i in tags.split(",") if i.strip()],
              "keywords":[i.strip() for i in keys.split(",") if i.strip()],
              "material":material,"craftsmanship_level":craft,"production_effort_hours":hours,
              "material_cost":cost,"region":region,"existing_price":price or None,
              "inventory":inventory,"suggested_price":None,"pricing":None,
              "marketplaces":[],"image_path":st.session_state.image_path}
            products.append(product); save_products(products); st.success("Product saved.")

elif page=="💰 AI Pricing":
    st.title("💰 AI Pricing Engine")
    if not products: st.info("Save a product first.")
    else:
        ids=[p["id"] for p in products]
        selected=st.selectbox("Product",ids,format_func=lambda i:next(p["product_name"] for p in products if p["id"]==i))
        p=next(p for p in products if p["id"]==selected)
        cost=st.number_input("Material cost (₹)",0.0,1e7,float(p.get("material_cost") or 0),50.0)
        hours=st.number_input("Production hours",0.0,1e4,float(p.get("production_effort_hours") or 0),.5)
        craft=st.selectbox("Craftsmanship",["Low","Medium","High"],index=["Low","Medium","High"].index(p.get("craftsmanship_level","Medium")))
        region=st.text_input("Region",p.get("region",""))
        if st.button("✨ Suggest AI Price",type="primary"):
            st.session_state.pricing=ai_price({"product":p["product_name"],"category":p["category"],"material_cost":cost,"hours":hours,"craftsmanship":craft,"region":region})
        if st.session_state.pricing:
            r=st.session_state.pricing
            a,b,c,d=st.columns(4)
            a.metric("Suggested",f"₹{r['suggested_price']:,.0f}"); b.metric("Minimum",f"₹{r['minimum_price']:,.0f}")
            c.metric("Maximum",f"₹{r['maximum_price']:,.0f}"); d.metric("Confidence",f"{r['confidence']}%")
            st.write(r.get("explanation",""))
            for f in r.get("factors",[]): st.write("• "+f)
            if st.button("✅ Apply Suggested Price"):
                p["suggested_price"]=r["suggested_price"]; p["pricing"]=r
                save_products(products); st.success("Price applied.")

elif page=="🛒 Marketplace":
    st.title("🛒 Marketplace Listing Preparation")
    st.info("This prepares listing data. It does not bypass seller onboarding or automatically publish.")
    if not products: st.info("Save a product first.")
    else:
        selected=st.selectbox("Product",[p["id"] for p in products],format_func=lambda i:next(p["product_name"] for p in products if p["id"]==i))
        p=next(p for p in products if p["id"]==selected)
        market=st.selectbox("Marketplace",["Amazon Karigar","ONDC","GeM"])
        if st.button("📦 Prepare Listing",type="primary"):
            payload,path=export_listing(p,market)
            if market not in p["marketplaces"]: p["marketplaces"].append(market)
            save_products(products); st.success("Listing prepared.")
            st.download_button("⬇️ Download Listing JSON",json.dumps(payload,indent=2,ensure_ascii=False),path.name,"application/json")

else:
    st.title("📦 Saved Products")
    if not products: st.info("No products saved yet.")
    for p in products:
        with st.expander(f"{p.get('product_name','Untitled')} — {p.get('category','')}"):
            if p.get("image_path") and Path(p["image_path"]).exists(): st.image(p["image_path"],width=250)
            st.write("**Description:**",p.get("description",""))
            st.write("**Price:**",p.get("suggested_price") or "Not set")
            st.write("**Marketplaces:**",", ".join(p.get("marketplaces",[])) or "None")
