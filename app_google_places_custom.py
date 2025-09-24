# app_google_places_custom.py — v2 EMBEDDED (logos + persistencia + portada + login)
from __future__ import annotations

import io, os, re, time, math, datetime, base64
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import json
import requests
import pandas as pd
import numpy as np
import streamlit as st
from urllib.parse import urlencode, quote_plus
import tldextract
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# =========================
# CONFIGURACIÓN Y CONSTANTES
# =========================

st.set_page_config(
    page_title="Localizador MultiGremio",
    page_icon="🔎",
    layout="wide"
)

# Clave desde secrets (Streamlit Cloud)
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))

# --- Logos embebidos en B64 (asegúrate de que contengan el base64 correcto) ---
# Sustituye los contenidos entre triple comillas por tus cadenas base64 reales
LOGO_JELPIN_B64 = """
iVBORw0KGgoAAAANSUhEUgAA...
""".strip()

LOGO_MULTI_B64 = """
iVBORw0KGgoAAAANSUhEUgAA...
""".strip()

# =========================
# UTILIDADES
# =========================

def _img_from_b64(b64_str):
    """Decode base64 image safely and return a PIL.Image or None."""
    try:
        if not b64_str:
            return None
        s = b64_str.strip()
        # remove data URL header if present
        s = re.sub(r"^data:image/[^;]+;base64,", "", s, flags=re.I)
        raw = base64.b64decode(s, validate=False)
        bio = io.BytesIO(raw)
        im = Image.open(bio)
        # force load to catch truncated images and convert to RGB to be safe
        im.load()
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        return im
    except Exception:
        return None

def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9\-]+", "-", s.lower()).strip("-")

def normalize_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    if not re.match(r"^https?://", u):
        u = "http://" + u
    return u

def extract_domain(u: str) -> str:
    try:
        ext = tldextract.extract(u)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        return u
    except:
        return u

def st_badge(text: str, color: str = "#EEF1FF", fg: str = "#1E2A5E"):
    st.markdown(
        f"""
        <span style="background:{color};color:{fg};padding:.25rem .5rem;border-radius:.5rem;font-size:.85rem;border:1px solid rgba(0,0,0,.06);">
        {text}
        </span>
        """,
        unsafe_allow_html=True
    )

# =========================
# AUTENTICACIÓN SENCILLA
# =========================
# (usa st.session_state['auth_ok'] para gatear la app)
VALID_USERS = {
    # usuario: contraseña (cámbialos en secrets si quieres)
    os.environ.get("APP_USER", "admin"): os.environ.get("APP_PASS", "1234")
}

def require_login():
    if st.session_state.get("auth_ok"):
        return
    st.title("🔐 Acceso")
    user = st.text_input("Usuario", key="login_user")
    pwd = st.text_input("Contraseña", type="password", key="login_pass")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Entrar"):
            if user in VALID_USERS and VALID_USERS[user] == pwd:
                st.session_state["auth_ok"] = True
                st.success("¡Dentro!")
                st.rerun()
            else:
                st.error("Credenciales inválidas")
    with col2:
        st.info("Acceso restringido para uso interno del equipo.")

require_login()
if not st.session_state.get("auth_ok"):
    st.stop()

# =========================
# PORTADA / CABECERA
# =========================

with st.container():
    c1, c2, c3 = st.columns([1,1,5], vertical_alignment="center")
    with c1:
        im1 = _img_from_b64(LOGO_JELPIN_B64)
        if im1:
            c1.image(im1, width=100)
    with c2:
        im2 = _img_from_b64(LOGO_MULTI_B64)
        if im2:
            c2.image(im2, width=120)
    with c3:
        st.markdown(
            """
            <div style="padding:4px 0 0 0;">
              <h1 style="margin:0;">Localizador MultiGremio</h1>
              <p style="margin:.25rem 0 0 0;color:#5c6370;">
                Búsqueda avanzada en Google Places + scraping de contacto y horarios + dashboard.
              </p>
            </div>
            """, unsafe_allow_html=True
        )

st.divider()

# =========================
# FORMULARIO DE BÚSQUEDA
# =========================

with st.expander("Parámetros de búsqueda", expanded=True):
    col_a, col_b, col_c = st.columns([2,2,1])
    with col_a:
        query = st.text_input("Qué buscar (ej.: 'fontanero, calefacción')", "fontanero")
        location = st.text_input("Centro de la búsqueda", "Madrid, España")
    with col_b:
        radio_km = st.number_input("Radio (km)", 1, 50, 10)
        max_results = st.number_input("Máx. resultados", 10, 200, 50, step=10)
    with col_c:
        ejecutar = st.button("🔎 Buscar")

# =========================
# GOOGLE GEOCODING + PLACES
# =========================

def geocode_latlon(address: str) -> Tuple[float, float]:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    r = requests.get(url, params={"address": address, "key": GOOGLE_API_KEY}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("results"):
        raise ValueError("No se encontraron coordenadas para la ubicación.")
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]

def places_search(
    keyword: str,
    lat: float,
    lon: float,
    radius_m: int,
    pagetoken: Optional[str] = None
) -> Dict:
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "keyword": keyword,
        "location": f"{lat},{lon}",
        "radius": radius_m,
        "key": GOOGLE_API_KEY,
        "language": "es"
    }
    if pagetoken:
        params["pagetoken"] = pagetoken
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def place_details(place_id: str) -> Dict:
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "key": GOOGLE_API_KEY,
        "language": "es",
        "fields": "name,international_phone_number,formatted_phone_number,website,opening_hours,opening_hours.weekday_text,rating,user_ratings_total,formatted_address"
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# =========================
# SCRAPING DE EMAILS
# =========================

EMAIL_REGEX = re.compile(
    r"(?i)(?<![a-z0-9._%+-])([a-z0-9._%+-]+)@([a-z0-9.-]+\.[a-z]{2,})(?![a-z0-9._%+-])"
)

def fetch_url(url: str, timeout: int = 20) -> str:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if "text" in resp.headers.get("Content-Type", ""):
            return resp.text
        return ""
    except:
        return ""

def discover_candidate_pages(base_url: str) -> List[str]:
    base = normalize_url(base_url)
    # páginas típicas donde ponen emails
    candidates = [
        base,
        base.rstrip("/") + "/contacto",
        base.rstrip("/") + "/contact",
        base.rstrip("/") + "/aviso-legal",
        base.rstrip("/") + "/politica-privacidad",
        base.rstrip("/") + "/privacy",
        base.rstrip("/") + "/about",
        base.rstrip("/") + "/quienes-somos",
    ]
    # evitar duplicados conservando orden
    seen = set()
    ordered = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered

def scrape_emails(base_url: str, max_pages: int = 4) -> List[str]:
    emails = set()
    for idx, u in enumerate(discover_candidate_pages(base_url)):
        if idx >= max_pages:
            break
        html = fetch_url(u)
        for m in EMAIL_REGEX.finditer(html):
            emails.add(f"{m.group(1)}@{m.group(2)}")
    return sorted(emails)

# =========================
# ESTADO & PERSISTENCIA
# =========================

if "history" not in st.session_state:
    st.session_state["history"] = []  # [(query, location, result_count, df_head)]
if "last_df" not in st.session_state:
    st.session_state["last_df"] = None

# =========================
# EJECUCIÓN DE BÚSQUEDA
# =========================

results_df = None
if ejecutar:
    try:
        lat, lon = geocode_latlon(location)
        radius_m = int(float(radio_km) * 1000)
        items = []

        next_token = None
        fetched = 0
        while True:
            data = places_search(query, lat, lon, radius_m, pagetoken=next_token)
            for it in data.get("results", []):
                place_id = it.get("place_id", "")
                name = it.get("name", "")
                rating = it.get("rating", None)
                user_ratings = it.get("user_ratings_total", 0)
                address = it.get("vicinity") or it.get("formatted_address", "")

                # Detalles para website, teléfono, horarios
                det = place_details(place_id).get("result", {})
                website = det.get("website", "")
                phone = det.get("international_phone_number") or det.get("formatted_phone_number", "")
                opening = det.get("opening_hours", {})
                weekday_text = (opening or {}).get("weekday_text", [])
                opening_str = " | ".join(weekday_text) if weekday_text else ""

                emails = scrape_emails(website) if website else []

                items.append({
                    "place_id": place_id,
                    "nombre": name,
                    "rating": rating,
                    "opiniones": user_ratings,
                    "direccion": address,
                    "telefono": phone,
                    "web": website,
                    "dominio": extract_domain(website) if website else "",
                    "emails": ", ".join(emails),
                    "horarios": opening_str
                })

                fetched += 1
                if fetched >= int(max_results):
                    break

            if fetched >= int(max_results):
                break

            next_token = data.get("next_page_token")
            if not next_token:
                break
            # Google pide ~2s antes de usar el next_page_token
            time.sleep(2.2)

        results_df = pd.DataFrame(items)
        st.session_state["last_df"] = results_df.copy()

        # actualizar histórico
        count = len(results_df)
        st.session_state["history"].append({
            "query": query,
            "location": location,
            "count": count,
            "ts": datetime.datetime.utcnow().isoformat()
        })

    except Exception as e:
        st.error(f"Error en la búsqueda: {e}")

# =========================
# DASHBOARD
# =========================

st.subheader("📊 Dashboard de últimas búsquedas")
if st.session_state["history"]:
    hist = pd.DataFrame(st.session_state["history"])
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Nº de negocios por búsqueda")
        st.bar_chart(hist.set_index("query")["count"])
    with c2:
        st.caption("Búsquedas por ubicación (conteo)")
        loc_counts = hist["location"].value_counts().rename_axis("location").reset_index(name="veces")
        st.bar_chart(loc_counts.set_index("location")["veces"])
else:
    st.info("Aún no hay histórico. Realiza una búsqueda para ver estadísticas.")

st.divider()

# =========================
# TABLA RESULTADOS + DESCARGA
# =========================

st.subheader("Resultados")
df_show = st.session_state.get("last_df")
if df_show is not None and not df_show.empty:
    st.dataframe(df_show, use_container_width=True)

    def to_excel_bytes(df: pd.DataFrame) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = "Resultados"
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        return bio.read()

    colx, coly = st.columns([1,5])
    with colx:
        xbytes = to_excel_bytes(df_show)
        st.download_button(
            "⬇️ Descargar Excel",
            data=xbytes,
            file_name=f"resultados_{slugify(query)}_{slugify(location)}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with coly:
        st.caption("El listado permanece en pantalla tras la descarga. Para refrescar, vuelve a buscar.")
else:
    st.warning("Sin resultados todavía. Introduce parámetros y pulsa **Buscar**.")

# =========================
# FOOTER
# =========================

st.markdown(
    """
    <div style="margin-top:1rem;color:#6a737d;">
      Versión 2 • Streamlit Cloud • © MultiHelpers & Jelpin
    </div>
    """,
    unsafe_allow_html=True
)
