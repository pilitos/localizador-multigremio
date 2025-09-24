import io
import os
import time
import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
import tldextract


# =========================
# Configuración de página
# =========================
st.set_page_config(page_title="Localizador Multigremio v2", layout="wide", page_icon="🔎")
st.title("🔎 Localizador Multigremio v2")
st.caption("Búsqueda multi-gremio en Google Places con deduplicado, detalles opcionales y exportación CSV/XLSX.")


# =========================
# Utilidades
# =========================
def api_key() -> str:
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        st.stop()  # aborta con el aviso de abajo
        return ""


def _req(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Solicitud GET con manejo básico de errores."""
    for _ in range(3):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 200:
            data = r.json()
            status = data.get("status")
            # OK | ZERO_RESULTS | OVER_QUERY_LIMIT | INVALID_REQUEST | etc.
            if status in ("OK", "ZERO_RESULTS"):
                return data
            # Si el next_page_token aún no está listo
            if status == "INVALID_REQUEST" and "next_page_token" in params:
                time.sleep(2.1)
                continue
            # Si rate limit, intentamos una pequeña espera
            if status in ("OVER_QUERY_LIMIT", "RESOURCE_EXHAUSTED"):
                time.sleep(2.5)
                continue
            return data
        time.sleep(0.8)
    r.raise_for_status()
    return {}


def geocode_location(location_text: str) -> Optional[Tuple[float, float]]:
    """Acepta 'lat,lng' o una dirección y devuelve (lat, lng)."""
    location_text = (location_text or "").strip()
    if "," in location_text:
        try:
            lat, lng = location_text.split(",", 1)
            return float(lat.strip()), float(lng.strip())
        except Exception:
            pass

    # Geocoding si es una dirección
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    data = _req(url, {"address": location_text, "key": api_key()})
    results = data.get("results", [])
    if not results:
        return None
    loc = results[0]["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])


@st.cache_data(show_spinner=False, ttl=60 * 10)
def text_search_one_page(query: str, lat: float, lng: float, radius: int, pagetoken: Optional[str] = None) -> Dict[str, Any]:
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "location": f"{lat},{lng}",
        "radius": radius,
        "language": "es",
        "region": "es",
        "key": api_key(),
    }
    if pagetoken:
        params["pagetoken"] = pagetoken
    return _req(url, params)


@st.cache_data(show_spinner=False, ttl=60 * 60)
def place_details(place_id: str) -> Dict[str, Any]:
    """Detalles (web/teléfono). Campos acotados para cuota/velocidad."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,international_phone_number,website,opening_hours",
        "language": "es",
        "key": api_key(),
    }
    return _req(url, params)


def gather_results_for_query(
    query: str,
    lat: float,
    lng: float,
    radius: int,
    page_limit: int,
    max_results: int,
    want_details: bool,
    seen_ids: set,
    progress: Optional[st.progress] = None,
) -> List[Dict[str, Any]]:
    """Descarga hasta N páginas por query; deduplica por place_id; opcionalmente añade detalles."""
    collected: List[Dict[str, Any]] = []
    next_page: Optional[str] = None
    page = 0

    while page < page_limit and len(collected) < max_results:
        data = text_search_one_page(query, lat, lng, radius, next_page)
        results = data.get("results", [])
        for r in results:
            pid = r.get("place_id")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)

            item = {
                "gremio": query,
                "name": r.get("name"),
                "address": r.get("formatted_address"),
                "latitude": r.get("geometry", {}).get("location", {}).get("lat"),
                "longitude": r.get("geometry", {}).get("location", {}).get("lng"),
                "rating": r.get("rating"),
                "reviews": r.get("user_ratings_total"),
                "price_level": r.get("price_level"),
                "open_now": r.get("opening_hours", {}).get("open_now") if r.get("opening_hours") else None,
                "business_status": r.get("business_status"),
                "types": ", ".join(r.get("types", [])),
                "place_id": pid,
                "google_maps_url": f"https://maps.google.com/?cid={pid}",
                "website": None,
                "phone": None,
                "domain": None,
            }

            if want_details:
                det = place_details(pid)
                result_det = det.get("result", {}) if det else {}
                phone = result_det.get("international_phone_number") or result_det.get("formatted_phone_number")
                web = result_det.get("website")
                item["phone"] = phone
                item["website"] = web
                if web:
                    ext = tldextract.extract(web)
                    dom = ".".join([p for p in [ext.domain, ext.suffix] if p])
                    item["domain"] = dom or None
                # ligera pausa para no saturar
                time.sleep(0.05)

            collected.append(item)
            if len(collected) >= max_results:
                break

        next_page = data.get("next_page_token")
        page += 1
        if progress:
            progress.progress(min(1.0, (page / float(page_limit))))
        if not next_page:
            break
        # La token tarda ~2s en activarse
        time.sleep(2.1)

    return collected


def filter_df(df: pd.DataFrame, min_rating: float, only_open: bool) -> pd.DataFrame:
    out = df.copy()
    if min_rating > 0:
        out = out[(out["rating"].fillna(0) >= min_rating)]
    if only_open:
        out = out[(out["open_now"] == True)]
    return out.reset_index(drop=True)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buff = io.StringIO()
    df.to_csv(buff, index=False)
    return buff.getvalue().encode("utf-8-sig")


def to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buff = io.BytesIO()
    with pd.ExcelWriter(buff, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="resultados")
    return buff.getvalue()


# =========================
# Sidebar / Controles
# =========================
with st.sidebar:
    st.header("⚙️ Parámetros")

    gremios_text = st.text_area(
        "Gremios / búsquedas (uno por línea)",
        value="fontanero\ncerrajero\nelectricista",
        height=120,
        help="Introduce cada gremio en una línea. Se hará una búsqueda por cada uno.",
    )

    location_input = st.text_input(
        "Ubicación (lat,lng o dirección)",
        value="40.4168,-3.7038",
        help="Puedes poner 'lat,lng' o una dirección (ej. 'Sevilla, España').",
    )

    radius = st.slider("Radio (m)", 200, 50000, 5000, step=100)
    page_limit = st.selectbox("Páginas por gremio (máx 3)", options=[1, 2, 3], index=2)
    max_per_gremio = st.number_input("Máximo resultados por gremio", 10, 180, 60, step=10)
    want_details = st.checkbox("Añadir detalles (teléfono / web)", value=True,
                               help="Usa Place Details; más preciso pero consume más cuota.")
    min_rating = st.slider("⭐ Rating mínimo", 0.0, 5.0, 0.0, step=0.1)
    only_open = st.checkbox("Solo abiertos ahora", value=False)

    st.markdown("---")
    run = st.button("🔍 Buscar", use_container_width=True)


# =========================
# Ejecución
# =========================
if run:
    key = api_key()  # forzó lectura/validación
    st.info("Usando Google Places con idioma/región **es**. Recuerda definir `GOOGLE_API_KEY` en tus *Secrets*.")

    loc = geocode_location(location_input)
    if not loc:
        st.error("No se pudo geocodificar la ubicación. Revisa el valor introducido.")
        st.stop()
    lat, lng = loc

    gremios = [g.strip() for g in gremios_text.splitlines() if g.strip()]
    if not gremios:
        st.warning("Añade al menos un gremio.")
        st.stop()

    progress = st.progress(0.0)
    all_rows: List[Dict[str, Any]] = []
    seen: set = set()

    status_ph = st.empty()
    for i, g in enumerate(gremios, start=1):
        status_ph.info(f"Buscando **{g}** ({i}/{len(gremios)})…")
        rows = gather_results_for_query(
            g,
            lat, lng,
            radius=radius,
            page_limit=int(page_limit),
            max_results=int(max_per_gremio),
            want_details=bool(want_details),
            seen_ids=seen,
            progress=progress,
        )
        all_rows.extend(rows)

    status_ph.empty()
    progress.empty()

    if not all_rows:
        st.warning("No se obtuvieron resultados.")
        st.stop()

    df = pd.DataFrame(all_rows)

    # Filtros en memoria
    df_filtered = filter_df(df, min_rating=min_rating, only_open=only_open)

    st.success(f"✅ {len(df_filtered)} resultados (sin duplicados).")

    # Vista de datos
    with st.expander("Ver tabla de resultados", expanded=True):
        st.dataframe(df_filtered, use_container_width=True, height=420)

    # Mapa
    try:
        map_df = df_filtered.dropna(subset=["latitude", "longitude"]).rename(columns={"longitude": "lon", "latitude": "lat"})
        st.map(map_df[["lat", "lon"]], zoom=11)
    except Exception:
        pass

    # Descargas
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Descargar CSV",
            data=to_csv_bytes(df_filtered),
            file_name="resultados_gremios.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "📥 Descargar Excel",
            data=to_xlsx_bytes(df_filtered),
            file_name="resultados_gremios.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # Resumen rápido
    with st.expander("Resumen por gremio"):
        st.dataframe(
            df_filtered.groupby("gremio", as_index=False)
            .agg(total=("place_id", "count"), media_rating=("rating", "mean"))
            .sort_values("total", ascending=False),
            use_container_width=True,
        )
else:
    st.info("Configura los parámetros en la barra lateral y pulsa **Buscar**.")
