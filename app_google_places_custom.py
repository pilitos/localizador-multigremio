# app_google_places_custom.py
from __future__ import annotations

import io, os, re, time, math, datetime, json, base64
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

# app_google_places_custom.py — v2 EMBEDDED (logos + persistencia + portada + login)
from __future__ import annotations

import io, os, re, time, math, datetime, base64
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import streamlit as st
import tldextract
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

st.set_page_config(page_title="Localizador multigremio — Google Places v1 + OSM",
                   page_icon="🧭", layout="wide")

# ─────────────────────────── Logos embebidos ───────────────────────────
DEFAULT_LOGO_JELPIN_B64 = """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"""
DEFAULT_LOGO_CLOUD_B64 = """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jtImmOPTJ2j+deNW4sox0oU2/Wy/zPtMD4TYydnjcTGK7RTk/vfKl+J6N4d/Zp8HaIQ9zbz6xKP4r2T5f++FwPzr5zE8SY6vpBqC8v8ANn6Rl/htkWC1qxdV/wB56fcrI9O0vSbPRrZbaxtIbOBekcEYRfyH86+bqValWXNUk2/N3P0nDYXD4OmqWGpqEV0SSX4F3ArM6wxQAtABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAmM0AGKBWEx9fzoCwY6dfzoCwuKBhjFAC0AFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFABQAUAFAH/2Q=="""

def _b64_to_image_bytes(b64: str) -> bytes:
    if not b64: return b""
    return base64.b64decode(b64.encode("ascii"))

# ─────────────────────────── Barra lateral (logo opcional) ───────────────────────────
with st.sidebar:
    st.subheader("Logo (opcional)")
    logo_file = st.file_uploader("Sube tu logo (PNG/JPG)", type=["png","jpg","jpeg"], accept_multiple_files=False)
    show_logo_width = st.slider("Ancho del logo (px)", 80, 400, 160, 10)

# ─────────────────────────── Cabecera ───────────────────────────
col_logo, col_title = st.columns([1,4])
with col_logo:
    if logo_file:
        st.image(logo_file, width=show_logo_width)
    else:
        c1, c2 = st.columns(2)
        with c1:
            if DEFAULT_LOGO_JELPIN_B64:
                st.image(_b64_to_image_bytes(DEFAULT_LOGO_JELPIN_B64), width=int(show_logo_width/1.4))
        with c2:
            if DEFAULT_LOGO_CLOUD_B64:
                st.image(_b64_to_image_bytes(DEFAULT_LOGO_CLOUD_B64), width=int(show_logo_width/1.4))
with col_title:
    st.title("🧭 Localizador multigremio — Google Places v1 + OSM")
    st.caption("Búsqueda por provincia / CPs / radio · Gremios y palabras clave · Rating/Opiniones · Email desde web.")

# ─────────────────────────── Modelos ───────────────────────────
@dataclass
class Business:
    gremio: str
    name: str
    street: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    source: str = "Google"
    place_id: Optional[str] = None  # v1 id
    def full_address(self) -> str:
        return self.street or ""

# ─────────────────────────── Utilidades ───────────────────────────
HEADERS_HTML = {"User-Agent":"localizador-custom/1.0","Accept":"text/html,application/json"}
EMAIL_REGEX = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s\.-]?)?(?:\(?\d{2,4}\)?[\s\.-]?)?\d{3,4}[\s\.-]?\d{3,4}")

def normalize_domain(url: Optional[str]) -> Optional[str]:
    if not url: return None
    if not re.match(r"^https?://", url, re.I): url = "http://" + url
    ext = tldextract.extract(url)
    return ".".join([p for p in [ext.domain, ext.suffix] if p]) if ext.domain else None

def dedupe_businesses(items: List[Business]) -> List[Business]:
    seen=set(); out=[]
    for b in items:
        k=(re.sub(r"\W+","",b.name.lower()) if b.name else "",
           normalize_domain(b.website) if b.website else None,
           b.phone or "", b.email or "")
        if k in seen: continue
        seen.add(k); out.append(b)
    return out

def fetch_html(url: str, timeout: int = 20):
    try:
        r = requests.get(url, headers=HEADERS_HTML, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type",""):
            return r.text
    except requests.RequestException:
        return None
    return None

def guess_contact_pages(website: str) -> List[str]:
    if not website: return []
    if not website.lower().startswith(("http://","https://")):
        website = "http://" + website
    base = website.rstrip("/")
    paths = ["", "/", "/contacto", "/contact", "/aviso-legal", "/legal", "/privacidad", "/privacy"]
    seen=set(); out=[]
    for p in paths:
        u = base + p
        if u not in seen: seen.add(u); out.append(u)
    return out

def extract_email_from_site(website: str, delay: float = 0.8):
    if not website: return None, None
    best_phone=None
    for url in guess_contact_pages(website):
        html = fetch_html(url)
        if not html: continue
        emails = EMAIL_REGEX.findall(html or "")
        phones = [re.sub(r"\s+"," ",p.strip()) for p in PHONE_REGEX.findall(html or "")]
        if phones:
            best_phone = sorted(set(phones), key=lambda x: len(re.sub(r"\D","",x)))[-1]
        if emails:
            time.sleep(delay)
            return sorted(set(emails), key=len)[0], best_phone
        time.sleep(delay)
    return None, best_phone

# ─────────────────────────── Geocoding (OSM) ───────────────────────────
NOMINATIM_URL="https://nominatim.openstreetmap.org/search"
def geocode_one(q:str):
    r=requests.get(NOMINATIM_URL, params={"q":q,"format":"jsonv2","limit":1,"addressdetails":1},
                   headers=HEADERS_HTML, timeout=30); r.raise_for_status()
    data=r.json()
    if not data: raise RuntimeError(f"No se pudo geocodificar '{q}'.")
    return data[0]
def geocode_latlon(q:str)->Tuple[float,float]:
    d=geocode_one(q); return float(d["lat"]), float(d["lon"])
def geocode_bbox(q:str)->Tuple[float,float,float,float]:
    d=geocode_one(q); bb=d.get("boundingbox")
    if not bb or len(bb)<4: raise RuntimeError("No se obtuvo bounding box de la provincia.")
    south,north,west,east=map(float,bb); return south,north,west,east

# ─────────────────────────── Google Places API v1 ───────────────────────────
V1_BASE="https://places.googleapis.com/v1"
def google_api_key()->Optional[str]:
    return st.session_state.get("google_api_key_ui") or os.getenv("GOOGLE_API_KEY")

# Gremio → tipos oficiales
GREMIO_TO_TYPES = {
    "Fontaneros": ["plumber"],
    "Electricistas": ["electrician"],
    "Cerrajeros": ["locksmith"],
    "Reparación de electrodomésticos": ["appliance_store", "electronics_store", "home_goods_store"],
    "Carpinteros": ["carpenter"],
    "Pintores": ["painter"],
    "Dentistas": ["dentist"],
    "Abogados": ["lawyer"],
    "Fisioterapeutas": ["physiotherapist"],
    "Psicólogos": ["psychologist"],
    "Informáticos": ["electronics_store", "computer_store"],
}

def v1_text_search(query:str, location:Optional[Tuple[float,float]]=None, radius_m:Optional[int]=None,
                   language:str="es"):
    key=google_api_key()
    if not key: return [], {"status":"NO_KEY"}
    headers={
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount"
        ),
        "Content-Type": "application/json"
    }
    body={"textQuery":query,"languageCode":language,"regionCode":"ES"}
    if location and radius_m:
        body["locationBias"]={"circle":{"center":{"latitude":location[0], "longitude":location[1]},"radius":float(radius_m)}}
    r=requests.post(f"{V1_BASE}/places:searchText", headers=headers, json=body, timeout=30); r.raise_for_status()
    data=r.json()
    return data.get("places",[]) or [], (data or {})

def v1_nearby(center: Tuple[float,float], radius_m: int, include_types: list, language: str = "es"):
    key = google_api_key()
    if not key:
        return [], {"status": "NO_KEY"}
    if not include_types:
        return [], {"status": "SKIPPED_NO_TYPES"}
    headers = {
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount"
        ),
        "Content-Type": "application/json",
    }
    body = {
        "maxResultCount": 60,
        "languageCode": language,
        "rankPreference": "POPULARITY",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": center[0], "longitude": center[1]},
                "radius": float(radius_m),
            }
        },
        "includedPrimaryTypes": include_types,
    }
    r = requests.post(f"{V1_BASE}/places:searchNearby", headers=headers, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("places", []) or [], (data or {})

def v1_to_business(p:Dict[str,Any], gremio:str)->Business:
    name=(p.get("displayName") or {}).get("text") if isinstance(p.get("displayName"), dict) else p.get("displayName")
    addr=p.get("formattedAddress")
    phone=p.get("nationalPhoneNumber")
    web=p.get("websiteUri")
    rating=p.get("rating"); reviews=p.get("userRatingCount")
    loc=p.get("location") or {}
    lat=loc.get("latitude"); lon=loc.get("longitude")
    pid=p.get("id")
    return Business(gremio=gremio, name=name or "", street=addr, phone=phone, website=web,
                    rating=rating, reviews=reviews, lat=lat, lon=lon, source="Google", place_id=pid)

# ─────────────────────────── OSM opcional ───────────────────────────
OVERPASS_URL="https://overpass-api.de/api/interpreter"
def overpass_query(q:str)->dict:
    resp=requests.post(OVERPASS_URL, data={"data":q}, headers=HEADERS_HTML, timeout=120); resp.raise_for_status(); return resp.json()
def parse_osm_elements(elements:List[dict],gremio:str)->List[Business]:
    out=[]
    for el in elements:
        t=el.get("tags",{}); name=t.get("name")
        if not name: continue
        addr=", ".join([p for p in [
            t.get("addr:street") or t.get("addr:road"),
            t.get("addr:housenumber"),
            t.get("addr:postcode"),
            t.get("addr:city") or t.get("addr:town") or t.get("addr:village"),
            t.get("addr:state"),
            t.get("addr:country")
        ] if p])
        lat=el.get("lat") or (el.get("center",{}) or {}).get("lat")
        lon=el.get("lon") or (el.get("center",{}) or {}).get("lon")
        out.append(Business(gremio=gremio,name=name,street=addr,source="OSM",lat=lat,lon=lon))
    return out

# ─────────────────────────── UI ───────────────────────────
with st.sidebar:
    st.header("Parámetros de búsqueda")
    gremios_text = st.text_area("Gremios (uno por línea)", "Fontaneros\nElectricistas\nReparación de electrodomésticos\nCerrajeros", height=140)
    gremios = [g.strip() for g in gremios_text.splitlines() if g.strip()]

    extra_kw_text = st.text_input("Palabras clave extra (coma)", "SAT, urgencias, 24h")
    extra_keywords = [k.strip() for k in extra_kw_text.split(",") if k.strip()]

    fuente=st.selectbox("Fuentes", ["Google Places","OSM","Ambas"], index=0)
    modo=st.radio("Modo de zona", ["Provincia","Códigos postales","Radio"], index=0)

    provincia=None; postcodes=None; centro=None; radio_km=None; grid_km=None; pc_radio_km=None
    if modo=="Provincia":
        provincia=st.text_input("Provincia","Madrid")
        grid_km=st.number_input("Malla/Radio (km)", 5.0, 80.0, 25.0, 5.0)
    elif modo=="Códigos postales":
        postcodes=[pc.strip() for pc in st.text_input("CPs (espacios)","28001 28012 28932").split() if pc.strip()]
        pc_radio_km=st.number_input("Radio (km) por CP", 1.0, 20.0, 4.0, 1.0)
    else:
        centro=st.text_input("Centro","Móstoles, Madrid")
        radio_km=st.number_input("Radio (km)", 1.0, 50.0, 20.0, 1.0)

    st.subheader("Google API (v1)")
    st.text_input("GOOGLE_API_KEY", value=os.getenv("GOOGLE_API_KEY",""), key="google_api_key_ui", type="password")
    idioma=st.selectbox("Idioma", ["es","en"], index=0)

    st.subheader("Email desde web")
    scrape_email=st.checkbox("Intentar obtener email/teléfono desde la web", value=True)
    scrape_delay=st.slider("Delay scraping (s)", 0.2, 3.0, 0.8, 0.1)

    st.subheader("Salida")
    base_filename = st.text_input("Nombre base del fichero", "resultado")
    save_latest = st.checkbox("Guardar también *_latest", value=True)

    lanzar=st.button("🔎 Buscar")

# ─────────────────────────── Progreso ───────────────────────────
def _prepare_progress(total_steps: int):
    ph_title = st.empty()
    bar = st.progress(0)
    ph_detail = st.empty()
    return ph_title, bar, ph_detail, max(1, total_steps)

def _step_progress(ph_title, bar, ph_detail, step, total, msg=""):
    pct = min(100, int(step * 100 / total))
    ph_title.info(f"🔥 estamos buscando a fuego... {pct}%")
    bar.progress(pct)
    if msg: ph_detail.write(msg)

# ─────────────────────────── Lógica ───────────────────────────
def grid_over_bbox(south,north,west,east,step_km):
    pts=[]; lat_step=step_km/111.0; mid=(south+north)/2.0; lon_step=step_km/(111.0*max(0.1, math.cos(math.radians(mid))))
    lat=south
    while lat<=north:
        lon=west
        while lon<=east:
            pts.append((lat,lon)); lon+=lon_step
        lat+=lat_step
    return pts

def build_queries(g:str, provincia:Optional[str], extras:List[str])->List[str]:
    out=[]
    if provincia:
        out.append(f"{g} en {provincia}")
        for kw in extras: out.append(f"{g} {kw} en {provincia}")
    else:
        out.append(g)
        for kw in extras: out.append(f"{g} {kw}")
    return out

def google_run_v1(gremio:str, center:Tuple[float,float], radius_km:float, provincia:Optional[str],
                  extras:List[str], idioma:str):
    allres=[]; first_meta={}
    # 1) TextSearch
    for q in build_queries(gremio, provincia, extras):
        res, meta = v1_text_search(q, location=center, radius_m=int(radius_km*1000), language=idioma)
        if not first_meta: first_meta=meta
        allres+=res
        time.sleep(0.2)
    # 2) Nearby si hay tipos
    if len(allres)<30:
        include_types = GREMIO_TO_TYPES.get(gremio, [])
        try:
            res2, meta2 = v1_nearby(center, int(radius_km*1000), include_types, idioma)
            allres+=res2
            if not first_meta: first_meta=meta2
        except requests.HTTPError as e:
            pass
    return allres, first_meta

# ─────────────────────────── Run ───────────────────────────
if lanzar:
    items: List[Business] = []

    # calcular pasos
    total_steps = 1
    if fuente in ("Google Places","Ambas"):
        if modo=="Provincia":
            s,n,w,e = geocode_bbox(f"{provincia}, España")
            pts = grid_over_bbox(s,n,w,e,grid_km or 25.0)
            total_steps = len(gremios) * len(pts)
        elif modo=="Códigos postales":
            total_steps = len(gremios) * len(postcodes or [])
        else:
            total_steps = len(gremios)
    ph_title, bar, ph_detail, total = _prepare_progress(total_steps)
    step = 0

    if fuente in ("Google Places","Ambas"):
        if modo=="Provincia":
            south,north,west,east = geocode_bbox(f"{provincia}, España")
            for g in gremios:
                for c in grid_over_bbox(south,north,west,east,grid_km or 25.0):
                    res, meta = google_run_v1(g, c, grid_km or 25.0, provincia, extra_keywords, idioma)
                    for r in res: items.append(v1_to_business(r,g))
                    step += 1
                    _step_progress(ph_title, bar, ph_detail, step, total, f"Provincia {provincia} · {g}")
                    time.sleep(0.1)
        elif modo=="Códigos postales":
            for pc in (postcodes or []):
                lat,lon=geocode_latlon(f"{pc}, España")
                for g in gremios:
                    res, meta=google_run_v1(g, (lat,lon), pc_radio_km or 4.0, None, extra_keywords, idioma)
                    for r in res: items.append(v1_to_business(r,g))
                step += 1
                _step_progress(ph_title, bar, ph_detail, step, total, f"CP {pc}")
                time.sleep(0.1)
        else:
            lat,lon=geocode_latlon(centro or "Madrid, España")
            for g in gremios:
                res, meta=google_run_v1(g, (lat,lon), radio_km or 5.0, None, extra_keywords, idioma)
                for r in res: items.append(v1_to_business(r,g))
                step += 1
                _step_progress(ph_title, bar, ph_detail, step, total, f"Radio {radio_km} km · {g}")
                time.sleep(0.1)

    # dedupe
    items = dedupe_businesses(items)

    # emails desde web
    if (st.sidebar.checkbox if False else lambda *a, **k: True)("dummy"):
        pass
    if st.session_state.get("dummy", None) is None:
        st.session_state["dummy"] = True
    if (True):  # scrape_email ya puesto en la barra lateral arriba
        if 'scrape_email' in globals() and scrape_email and items:
            extra_total = len(items)
            total += extra_total
            for i, b in enumerate(items, 1):
                if not b.email and b.website:
                    try:
                        email, phone = extract_email_from_site(b.website, delay=scrape_delay)
                        if email: b.email = email
                        if phone and not b.phone: b.phone = phone
                    except Exception:
                        pass
                step += 1
                _step_progress(ph_title, bar, ph_detail, step, total, f"Emails desde web ({i}/{extra_total})")

    # salida
    df = pd.DataFrame([{
        "Gremio": b.gremio,
        "Nombre": b.name,
        "Dirección": b.full_address(),
        "Teléfono": b.phone,
        "Email": b.email,
        "Web": b.website,
        "Rating": b.rating,
        "Opiniones": b.reviews,
        "Lat": b.lat, "Lon": b.lon,
        "Fuente": b.source
    } for b in items])

    st.success(f"Resultados: {len(df)}")
    st.dataframe(df, use_container_width=True)

    def to_csv_bytes(df): return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    def to_excel_bytes(df):
        wb=Workbook(); ws=wb.active; ws.title="Resultado"
        for r in dataframe_to_rows(df,index=False,header=True): ws.append(r)
        out=io.BytesIO(); wb.save(out); return out.getvalue()

    c1,c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ CSV", data=to_csv_bytes(df), file_name=f"{base_filename}.csv", mime="text/csv")
    with c2:
        st.download_button("⬇️ Excel", data=to_excel_bytes(df),
                           file_name=f"{base_filename}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    out_dir=os.path.join(os.getcwd(),"salidas"); os.makedirs(out_dir, exist_ok=True)
    stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path=os.path.join(out_dir, f"{base_filename}_{stamp}.csv")
    xlsx_path=os.path.join(out_dir, f"{base_filename}_{stamp}.xlsx")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    try:
        with open(xlsx_path,"wb") as f: f.write(to_excel_bytes(df))
    except Exception as e:
        xlsx_path=f"(No guardado: {e})"
    if save_latest:
        latest_csv=os.path.join(out_dir, f"{base_filename}_latest.csv")
        latest_xlsx=os.path.join(out_dir, f"{base_filename}_latest.xlsx")
        try:
            df.to_csv(latest_csv, index=False, encoding="utf-8-sig")
            with open(latest_xlsx,"wb") as f: f.write(to_excel_bytes(df))
        except Exception:
            pass
    st.info(f"📁 Guardado en:\n- CSV: `{csv_path}`\n- Excel: `{xlsx_path}`")

