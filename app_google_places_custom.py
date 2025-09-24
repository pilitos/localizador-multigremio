# app_google_places_custom.py — v2 EMBEDDED (logos + persistencia + portada + login)
# Adaptado para Streamlit Cloud / Python 3.13
# - Sin dependencias de PyArrow (no se usa)
# - Geocoding cacheado para respetar límites OSM
# - Encabezado User-Agent configurable por secrets/entorno
# - Guardado a disco envuelto en try/except (entornos solo-lectura)

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

# ---------- Config & Auth ----------
st.set_page_config(page_title="Localizador multigremio — Google Places v1 + OSM (v2)",
                   page_icon="🧭", layout="wide")

def google_api_key() -> Optional[str]:
    return (
        (st.secrets.get("GOOGLE_API_KEY") if hasattr(st, "secrets") else None)
        or os.getenv("GOOGLE_API_KEY")
        or st.session_state.get("google_api_key_ui")
    )


def require_login():
    APP_PASSWORD = (
        os.getenv("APP_PASSWORD")
        or (st.secrets.get("APP_PASSWORD") if hasattr(st, "secrets") else None)
    )
    if not APP_PASSWORD:
        st.warning("🔓 APP_PASSWORD no configurado. La app está sin protección (modo desarrollo).")
        return
    if not st.session_state.get("auth_ok"):
        st.title("🔐 Acceso")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if pw == APP_PASSWORD:
                st.session_state["auth_ok"] = True
                st.success("¡Dentro!")
                try:
                    st.rerun()
                except Exception:
                    try:
                        st.experimental_rerun()
                    except Exception:
                        pass
            else:
                st.error("Contraseña incorrecta")
        st.stop()


require_login()

# ---------- Header con logos embebidos (sin ficheros) ----------
LOGO_JELPIN_B64 = "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"
LOGO_MULTI_B64 = "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"


def _img_from_b64(b64: str) -> bytes:
    try:
        return base64.b64decode(b64.encode("ascii"))
    except Exception:
        return b""

col_logo, col_title = st.columns([1,4])
with col_logo:
    c1, c2 = st.columns(2)
    c1.image(_img_from_b64(LOGO_JELPIN_B64), width=100)
    c2.image(_img_from_b64(LOGO_MULTI_B64), width=100)
with col_title:
    st.title("🧭 Localizador multigremio — Google Places v1 + OSM (v2)")
    st.caption("Horarios, ratings/opiniones, emails mejorados, dashboard, login, logos embebidos.")

# ---------- Models & Utils ----------
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
    place_id: Optional[str] = None
    open_now: Optional[bool] = None
    open_today: Optional[str] = None
    google_maps: Optional[str] = None

    def full_address(self) -> str:
        return self.street or ""

# ---- HTTP headers (configurable UA) ----
HEADERS_HTML: Dict[str, str] = {"User-Agent": "localizador-custom/2.0", "Accept": "text/html,application/json"}
_custom_ua = (
    (st.secrets.get("USER_AGENT") if hasattr(st, "secrets") else None)
    or os.getenv("USER_AGENT")
)
if _custom_ua:
    HEADERS_HTML["User-Agent"] = _custom_ua

EMAIL_REGEX = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s\.-]?)?(?:\(?\d{2,4}\)?[\s\.-]?)?\d{3,4}[\s\.-]?\d{3,4}")
OBFUSCATED_EMAIL = re.compile(r"([A-Z0-9._%+\-]+)\s*[\[\(]?at[\]\)]\s*([A-Z0-9.\-]+)\s*[\[\(]?dot[\]\)]\s*([A-Z]{2,})", re.I)


def normalize_domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    ext = tldextract.extract(url)
    return ".".join([p for p in [ext.domain, ext.suffix] if p]) if ext.domain else None


def dedupe_businesses(items: List[Business]) -> List[Business]:
    seen = set()
    out: List[Business] = []
    for b in items:
        k = (
            re.sub(r"\W+", "", b.name.lower()) if b.name else "",
            normalize_domain(b.website) if b.website else None,
            b.phone or "",
            b.email or "",
        )
        if k in seen:
            continue
        seen.add(k)
        out.append(b)
    return out


def fetch_html(url: str, timeout: int = 20):
    try:
        r = requests.get(url, headers=HEADERS_HTML, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
            return r.text
    except requests.RequestException:
        return None
    return None


def _same_domain(base: str, href: str) -> bool:
    try:
        b = urlparse(base).netloc.split(":")[0].lower()
        h = urlparse(href).netloc.split(":")[0].lower()
        if not h:  # relative
            return True
        return b.endswith(h) or h.endswith(b) or b == h
    except Exception:
        return False


def _extract_emails_phones_from_html(html: str) -> Tuple[list, list]:
    emails = set(EMAIL_REGEX.findall(html or ""))
    for m in re.findall(r'href=["\']mailto:([^"\']+)["\']', html or "", flags=re.I):
        emails.add(m.split("?")[0])
    for a, b, c in OBFUSCATED_EMAIL.findall(html or ""):
        emails.add(f"{a}@{b}.{c}")
    phones = [re.sub(r"\s+", " ", p.strip()) for p in PHONE_REGEX.findall(html or "")]
    return sorted(emails), phones


def guess_contact_pages(website: str) -> List[str]:
    if not website:
        return []
    if not website.lower().startswith(("http://", "https://")):
        website = "http://" + website
    base = website.rstrip("/")
    paths = [
        "",
        "/",
        "/contacto",
        "/contact",
        "/aviso-legal",
        "/legal",
        "/privacidad",
        "/privacy",
        "/quienes-somos",
        "/about",
        "/empresa",
    ]
    out = []
    seen = set()
    for p in paths:
        u = urljoin(base + "/", p.lstrip("/"))
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out


def extract_email_from_site(website: str, delay: float = 0.8, max_pages: int = 8):
    if not website:
        return None, None
    if not website.lower().startswith(("http://", "https://")):
        website = "http://" + website
    base = website.rstrip("/")
    queue = guess_contact_pages(base)
    seen = set(queue)
    best_email = None
    best_phone = None
    pages = 0
    while queue and pages < max_pages:
        url = queue.pop(0)
        html = fetch_html(url)
        pages += 1
        if not html:
            time.sleep(delay)
            continue
        emails, phones = _extract_emails_phones_from_html(html)
        if phones and not best_phone:
            import re as _re

            def _digits(x):
                return len(_re.sub(r"\D", "", x))

            best_phone = sorted(set(phones), key=_digits)[-1]
        if emails and not best_email:
            best_email = sorted(set(emails), key=len)[0]
        for href in re.findall(r'href=["\']([^"\']+)["\']', html or "", flags=re.I):
            nxt = urljoin(url, href)
            if nxt in seen:
                continue
            if not _same_domain(base, nxt):
                continue
            if any(s in nxt.lower() for s in ["/wp-json", "/feed", "/tag/", "/category/", "tel:", "mailto:"]):
                continue
            seen.add(nxt)
            queue.append(nxt)
        if best_email and best_phone:
            break
        time.sleep(delay)
    return best_email, best_phone


# ---------- Geocoding ----------
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


@st.cache_data(ttl=3600, show_spinner=False)
def geocode_one(q: str):
    # Incluir email opcional (mejores prácticas Nominatim)
    contact_email = (
        (st.secrets.get("CONTACT_EMAIL") if hasattr(st, "secrets") else None)
        or os.getenv("CONTACT_EMAIL")
    )
    params = {"q": q, "format": "jsonv2", "limit": 1, "addressdetails": 1}
    if contact_email:
        params["email"] = contact_email
    r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS_HTML, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise RuntimeError(f"No se pudo geocodificar '{q}'.")
    return data[0]


def geocode_latlon(q: str) -> Tuple[float, float]:
    d = geocode_one(q)
    return float(d["lat"]), float(d["lon"])


def geocode_bbox(q: str) -> Tuple[float, float, float, float]:
    d = geocode_one(q)
    bb = d.get("boundingbox")
    if not bb or len(bb) < 4:
        raise RuntimeError("No se obtuvo bounding box de la provincia.")
    south, north, west, east = map(float, bb)
    return south, north, west, east


# ---------- Google Places v1 ----------
V1_BASE = "https://places.googleapis.com/v1"
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


def _post_json(url, headers, body, timeout=30):
    try:
        r = requests.post(url, headers=headers, json=body, timeout=timeout)
        if r.status_code != 200:
            try:
                err = r.json()
            except Exception:
                err = r.text[:800]
            msg = f"HTTP {r.status_code} at {url.split('/')[-1]}: {err}"
            if st.session_state.get("diagnostico"):
                st.error(msg)
            return None, {"status": "ERROR", "error": msg}
        return r.json(), {}
    except requests.RequestException as e:
        msg = f"RequestException at {url.split('/')[-1]}: {e}"
        if st.session_state.get("diagnostico"):
            st.error(msg)
        return None, {"status": "ERROR", "error": msg}


def v1_text_search(
    query: str,
    location: Optional[Tuple[float, float]] = None,
    radius_m: Optional[int] = None,
    language: str = "es",
):
    key = google_api_key()
    if not key:
        return [], {"status": "NO_KEY"}
    headers = {
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,"
            "places.googleMapsUri,places.currentOpeningHours,places.regularOpeningHours"
        ),
        "Content-Type": "application/json",
    }
    body = {"textQuery": query, "languageCode": language, "regionCode": "ES"}
    if location and radius_m:
        body["locationBias"] = {
            "circle": {
                "center": {"latitude": location[0], "longitude": location[1]},
                "radius": float(radius_m),
            }
        }
    data, meta_err = _post_json(f"{V1_BASE}/places:searchText", headers, body, timeout=30)
    if data is None:
        return [], meta_err
    return data.get("places", []) or [], (data or {})


def v1_nearby(center: Tuple[float, float], radius_m: int, include_types: list, language: str = "es"):
    key = google_api_key()
    if not key:
        return [], {"status": "NO_KEY"}
    if not include_types:
        return [], {"status": "SKIPPED_NO_TYPES"}
    headers = {
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,"
            "places.googleMapsUri,places.currentOpeningHours,places.regularOpeningHours"
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
    data, meta_err = _post_json(f"{V1_BASE}/places:searchNearby", headers, body, timeout=30)
    if data is None:
        return [], meta_err
    return data.get("places", []) or [], (data or {})


def _opening_text(place: Dict[str, Any]) -> Tuple[Optional[bool], Optional[str]]:
    oh = place.get("currentOpeningHours") or {}
    open_now = oh.get("openNow")
    weekday = oh.get("weekdayDescriptions") or []
    try:
        today_idx = datetime.datetime.today().weekday()
        today_line = (
            weekday[today_idx]
            if 0 <= today_idx < len(weekday)
            else (weekday[0] if weekday else None)
        )
    except Exception:
        today_line = weekday[0] if weekday else None
    return open_now, today_line


def v1_to_business(p: Dict[str, Any], gremio: str) -> Business:
    name = (
        (p.get("displayName") or {}).get("text")
        if isinstance(p.get("displayName"), dict)
        else p.get("displayName")
    )
    addr = p.get("formattedAddress")
    phone = p.get("nationalPhoneNumber")
    web = p.get("websiteUri")
    rating = p.get("rating")
    reviews = p.get("userRatingCount")
    loc = p.get("location") or {}
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    pid = p.get("id")
    gmaps = p.get("googleMapsUri")
    open_now, today_text = _opening_text(p)
    return Business(
        gremio=gremio,
        name=name or "",
        street=addr,
        phone=phone,
        website=web,
        rating=rating,
        reviews=reviews,
        lat=lat,
        lon=lon,
        source="Google",
        place_id=pid,
        open_now=open_now,
        open_today=today_text,
        google_maps=gmaps,
    )


# ---------- Sidebar (parámetros) ----------
with st.sidebar:
    st.header("Parámetros de búsqueda")
    gremios_text = st.text_area(
        "Gremios (uno por línea)",
        "Fontaneros\nElectricistas\nReparación de electrodomésticos\nCerrajeros",
        height=140,
    )
    gremios = [g.strip() for g in gremios_text.splitlines() if g.strip()]

    extra_kw_text = st.text_input("Palabras clave extra (coma)", "SAT, urgencias, 24h")
    extra_keywords = [k.strip() for k in extra_kw_text.split(",") if k.strip()]

    fuente = st.selectbox("Fuentes", ["Google Places", "OSM", "Ambas"], index=0)
    modo = st.radio("Modo de zona", ["Provincia", "Códigos postales", "Radio"], index=0)

    provincia = None
    postcodes = None
    centro = None
    radio_km = None
    grid_km = None
    pc_radio_km = None
    if modo == "Provincia":
        provincia = st.text_input("Provincia", "Madrid")
        grid_km = st.number_input("Malla/Radio (km)", 5.0, 80.0, 25.0, 5.0)
    elif modo == "Códigos postales":
        postcodes = [
            pc.strip()
            for pc in st.text_input("CPs (espacios)", "28001 28012 28932").split()
            if pc.strip()
        ]
        pc_radio_km = st.number_input("Radio (km) por CP", 1.0, 20.0, 4.0, 1.0)
    else:
        centro = st.text_input("Centro", "Móstoles, Madrid")
        radio_km = st.number_input("Radio (km)", 1.0, 50.0, 20.0, 1.0)

    st.subheader("Google API (v1)")
    st.text_input(
        "GOOGLE_API_KEY",
        value=os.getenv("GOOGLE_API_KEY", ""),
        key="google_api_key_ui",
        type="password",
        help="También puedes configurarlo en Secrets.",
    )
    idioma = st.selectbox("Idioma", ["es", "en"], index=0)
    diagnostico = st.checkbox("Mostrar diagnóstico", value=False, key="diagnostico")

    st.subheader("Email desde web")
    scrape_email = st.checkbox("Intentar obtener email/teléfono desde la web", value=True)
    scrape_delay = st.slider("Delay scraping (s)", 0.2, 3.0, 0.8, 0.1)

    st.subheader("Salida")
    base_filename = st.text_input("Nombre base del fichero", "resultado")
    st.session_state.base_filename = base_filename
    save_latest = st.checkbox("Guardar también *_latest", value=True)

    lanzar = st.button("🔎 Buscar")


# ---------- Progress helpers ----------
def _prepare_progress(total_steps: int):
    ph_title = st.empty()
    bar = st.progress(0)
    ph_detail = st.empty()
    return ph_title, bar, ph_detail, max(1, total_steps)


def _step_progress(ph_title, bar, ph_detail, step, total, msg=""):
    pct = min(100, int(step * 100 / total))
    ph_title.info(f"🔥 estamos buscando a fuego... {pct}%")
    bar.progress(pct)
    if msg:
        ph_detail.write(msg)


# ---------- Search orchestration ----------
def grid_over_bbox(south, north, west, east, step_km):
    pts = []
    lat_step = step_km / 111.0
    mid = (south + north) / 2.0
    lon_step = step_km / (111.0 * max(0.1, math.cos(math.radians(mid))))
    lat = south
    while lat <= north:
        lon = west
        while lon <= east:
            pts.append((lat, lon))
            lon += lon_step
        lat += lat_step
    return pts


def build_queries(g: str, provincia: Optional[str], extras: List[str]) -> List[str]:
    out = []
    if provincia:
        out.append(f"{g} en {provincia}")
        for kw in extras:
            out.append(f"{g} {kw} en {provincia}")
    else:
        out.append(g)
        for kw in extras:
            out.append(f"{g} {kw}")
    return out


def google_run_v1(
    gremio: str,
    center: Tuple[float, float],
    radius_km: float,
    provincia: Optional[str],
    extras: List[str],
    idioma: str,
):
    allres = []
    first_meta = {}
    for q in build_queries(gremio, provincia, extras):
        res, meta = v1_text_search(q, location=center, radius_m=int(radius_km * 1000), language=idioma)
        if not first_meta:
            first_meta = meta
        allres += res
        time.sleep(0.2)
    if len(allres) < 30:
        include_types = GREMIO_TO_TYPES.get(gremio, [])
        try:
            res2, meta2 = v1_nearby(center, int(radius_km * 1000), include_types, idioma)
            allres += res2
            first_meta = first_meta or meta2
        except requests.HTTPError:
            pass
    return allres, first_meta


# ---------- Run ----------
if lanzar:
    if not google_api_key():
        st.warning("⚠️ Falta GOOGLE_API_KEY. Configúralo en el panel lateral o en *Secrets*.")

    items: List[Business] = []

    total_steps = 1
    if fuente in ("Google Places", "Ambas"):
        if modo == "Provincia":
            s, n, w, e = geocode_bbox(f"{provincia}, España")
            pts = grid_over_bbox(s, n, w, e, grid_km or 25.0)
            total_steps = len(gremios) * len(pts)
        elif modo == "Códigos postales":
            total_steps = len(gremios) * len(postcodes or [])
        else:
            total_steps = len(gremios)
    ph_title, bar, ph_detail, total = _prepare_progress(total_steps)
    step = 0

    if fuente in ("Google Places", "Ambas"):
        if modo == "Provincia":
            south, north, west, east = geocode_bbox(f"{provincia}, España")
            for g in gremios:
                for c in grid_over_bbox(south, north, west, east, grid_km or 25.0):
                    res, meta = google_run_v1(g, c, grid_km or 25.0, provincia, extra_keywords, idioma)
                    for r in res:
                        items.append(v1_to_business(r, g))
                    step += 1
                    _step_progress(ph_title, bar, ph_detail, step, total, f"Provincia {provincia} · {g}")
        elif modo == "Códigos postales":
            for pc in (postcodes or []):
                lat, lon = geocode_latlon(f"{pc}, España")
                for g in gremios:
                    res, meta = google_run_v1(g, (lat, lon), pc_radio_km or 4.0, None, extra_keywords, idioma)
                    for r in res:
                        items.append(v1_to_business(r, g))
                step += 1
                _step_progress(ph_title, bar, ph_detail, step, total, f"CP {pc}")
        else:
            lat, lon = geocode_latlon(centro or "Madrid, España")
            for g in gremios:
                res, meta = google_run_v1(g, (lat, lon), radio_km or 5.0, None, extra_keywords, idioma)
                for r in res:
                    items.append(v1_to_business(r, g))
                step += 1
                _step_progress(ph_title, bar, ph_detail, step, total, f"Radio {radio_km} km · {g}")

    items = dedupe_businesses(items)

    if scrape_email and items:
        extra_total = len(items)
        total += extra_total
        for i, b in enumerate(items, 1):
            if not b.email and b.website:
                try:
                    email, phone = extract_email_from_site(b.website, delay=scrape_delay, max_pages=8)
                    if email:
                        b.email = email
                    if phone and not b.phone:
                        b.phone = phone
                except Exception:
                    pass
            step += 1
            _step_progress(
                ph_title, bar, ph_detail, step, total, f"Emails desde web ({i}/{extra_total})"
            )

    df = pd.DataFrame(
        [
            {
                "Gremio": b.gremio,
                "Nombre": b.name,
                "Dirección": b.full_address(),
                "Teléfono": b.phone,
                "Email": b.email,
                "Web": b.website,
                "Rating": b.rating,
                "Opiniones": b.reviews,
                "AbiertoAhora": b.open_now,
                "HorarioHoy": b.open_today,
                "GoogleMaps": b.google_maps,
                "Lat": b.lat,
                "Lon": b.lon,
                "Fuente": b.source,
            }
            for b in items
        ]
    )

    # Persistir resultados para no perderlos tras descargas/reruns
    st.session_state.df = df
    st.session_state.busqueda_meta = {
        "timestamp": datetime.datetime.now(),
        "modo": modo,
        "provincia": provincia,
        "postcodes": postcodes,
        "centro": centro,
        "radio_km": radio_km,
        "grid_km": grid_km,
        "gremios": gremios,
        "extras": extra_keywords,
        "n": len(df),
    }
    hist = st.session_state.get("historial_busquedas", [])
    hist.append(
        {
            "ts": st.session_state.busqueda_meta["timestamp"],
            "resultado": len(df),
            "gremios": ",".join(gremios),
        }
    )
    st.session_state.historial_busquedas = hist[-20:]  # últimas 20

    st.success(f"Resultados: {len(df)}")
    # --- Dashboard ---
    st.subheader("📊 Resumen")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Negocios", len(df))
    with c2:
        try:
            st.metric("Rating medio", round(df["Rating"].dropna().astype(float).mean(), 2))
        except Exception:
            st.metric("Rating medio", "—")
    with c3:
        try:
            st.metric("Con email", int(df["Email"].notna().sum()))
        except Exception:
            st.metric("Con email", "—")

    try:
        st.write("Distribución de ratings")
        bins = pd.cut(df["Rating"].astype(float), bins=[0, 1, 2, 3, 4, 5], include_lowest=True)
        st.bar_chart(bins.value_counts().sort_index())
    except Exception:
        pass

    try:
        st.write("Negocios por gremio")
        st.bar_chart(df["Gremio"].value_counts())
    except Exception:
        pass

    try:
        df_map = df[["Lat", "Lon"]].dropna()
        if not df_map.empty:
            st.write("Mapa de resultados")
            st.map(df_map.rename(columns={"Lat": "lat", "Lon": "lon"}))
    except Exception:
        pass

    st.dataframe(df, use_container_width=True)

    # --- Downloads & Save ---
    def to_csv_bytes(df):
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    def to_excel_bytes(df):
        wb = Workbook()
        ws = wb.active
        ws.title = "Resultado"
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ CSV", data=to_csv_bytes(df), file_name=f"{base_filename}.csv", mime="text/csv"
        )
    with c2:
        st.download_button(
            "⬇️ Excel",
            data=to_excel_bytes(df),
            file_name=f"{base_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # Guardados locales (no críticos en Streamlit Cloud)
    try:
        out_dir = os.path.join(os.getcwd(), "salidas")
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(out_dir, f"{base_filename}_{stamp}.csv")
        xlsx_path = os.path.join(out_dir, f"{base_filename}_{stamp}.xlsx")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        try:
            with open(xlsx_path, "wb") as f:
                f.write(to_excel_bytes(df))
        except Exception as e:
            xlsx_path = f"(No guardado: {e})"
        if save_latest:
            latest_csv = os.path.join(out_dir, f"{base_filename}_latest.csv")
            latest_xlsx = os.path.join(out_dir, f"{base_filename}_latest.xlsx")
            try:
                df.to_csv(latest_csv, index=False, encoding="utf-8-sig")
                with open(latest_xlsx, "wb") as f:
                    f.write(to_excel_bytes(df))
            except Exception:
                pass
        st.info(f"📁 Guardado en:\n- CSV: `{csv_path}`\n- Excel: `{xlsx_path}`")
    except Exception:
        # Entornos sin escritura
        pass

# ---------- Re-pintar último resultado si no se lanza búsqueda ----------
elif "df" in st.session_state and isinstance(st.session_state.df, pd.DataFrame):
    df = st.session_state.df
    st.info(
        f"Mostrando los últimos resultados: {len(df)} filas. (Se mantendrán hasta que busques de nuevo)"
    )

    st.subheader("📊 Resumen")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Negocios", len(df))
    with c2:
        try:
            st.metric("Rating medio", round(df["Rating"].dropna().astype(float).mean(), 2))
        except Exception:
            st.metric("Rating medio", "—")
    with c3:
        try:
            st.metric("Con email", int(df["Email"].notna().sum()))
        except Exception:
            st.metric("Con email", "—")

    try:
        st.write("Distribución de ratings")
        bins = pd.cut(df["Rating"].astype(float), bins=[0, 1, 2, 3, 4, 5], include_lowest=True)
        st.bar_chart(bins.value_counts().sort_index())
    except Exception:
        pass

    try:
        st.write("Negocios por gremio")
        st.bar_chart(df["Gremio"].value_counts())
    except Exception:
        pass

    try:
        df_map = df[["Lat", "Lon"]].dropna()
        if not df_map.empty:
            st.write("Mapa de resultados")
            st.map(df_map.rename(columns={"Lat": "lat", "Lon": "lon"}))
    except Exception:
        pass

    st.dataframe(df, use_container_width=True)

    def to_excel_bytes(df):
        wb = Workbook()
        ws = wb.active
        ws.title = "Resultado"
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()

    base_filename = st.session_state.get("base_filename", "resultado")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ CSV",
            data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
            file_name=f"{base_filename}.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            "⬇️ Excel",
            data=to_excel_bytes(df),
            file_name=f"{base_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ---------- Portada si no hay resultados aún ----------
else:
    st.subheader("🗂️ Últimas búsquedas")
    hist = st.session_state.get("historial_busquedas", [])
    if not hist:
        st.write(
            "Aquí verás un resumen de las últimas búsquedas (se llenará al empezar a usar la herramienta)."
        )
    else:
        hdf = pd.DataFrame(hist)
        col1, col2 = st.columns(2)
        with col1:
            st.write("Resultados por búsqueda (últimas 20)")
            st.line_chart(hdf.set_index("ts")["resultado"])
        with col2:
            st.write("Top gremios recientes")
            cnt: Dict[str, int] = {}
            for gtxt in hdf["gremios"].fillna(""):
                for g in [x.strip() for x in gtxt.split(",") if x.strip()]:
                    cnt[g] = cnt.get(g, 0) + 1
            if cnt:
                import pandas as _pd

                st.bar_chart(_pd.Series(cnt).sort_values(ascending=False))
    st.caption(
        "Consejo: añade varias palabras clave (SAT, urgencias, 24h) para ampliar resultados."
    )
