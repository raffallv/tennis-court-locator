import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from streamlit_geolocation import streamlit_geolocation

APP_VERSION = "v1 (clean rebuild — Google Places)"

# ---------------------------------------------------------------------------
# Page setup + theme
# ---------------------------------------------------------------------------
st.set_page_config(page_title="US Tennis Court Locator", page_icon="🎾", layout="wide")

st.markdown(
    """
    <style>
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #B5651D !important;
    }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] { background-color: #A0522D !important; }
    h1, h2, h3, p, span, label, .stMarkdown, .stCaption, .stAlert { color: #FFF8F0 !important; }
    [data-testid="stSidebar"] * { color: #FFF8F0 !important; }
    .stDataFrame { background-color: #FDF6EC; border-radius: 8px; }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="base-input"],
    [data-testid="stSidebar"] input {
        background-color: #3C9A40 !important;
        border: 1px solid #2C7A30 !important;
        color: #FFFFFF !important;
        font-weight: 600;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] svg { fill: #FFFFFF !important; }
    [data-testid="stSidebar"] input::placeholder { color: #E8F5E9 !important; opacity: 1 !important; }
    div[data-baseweb="popover"] li { background-color: #3C9A40 !important; color: #FFFFFF !important; }
    div[data-baseweb="popover"] li:hover { background-color: #2C7A30 !important; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🎾 US Tennis Court Locator")
st.markdown("Find real, verified tennis facilities across the US — powered by Google Places.")

STATE_NAMES = sorted([
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
])

RADIUS_OPTIONS_MI = {"5 miles": 5, "10 miles": 10, "25 miles": 25, "50 miles": 50}
GOOGLE_NEARBY_MAX_RADIUS_M = 50000  # hard cap enforced by Google's API

APP_USER_AGENT = {"User-Agent": "TennisCourtLocatorApp/1.0 (contact: rafal@nevadagroup.com)"}
GOOGLE_API_KEY = st.secrets.get("GOOGLE_PLACES_API_KEY")

FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.websiteUri,places.nationalPhoneNumber,places.types,places.businessStatus"
)
INDOOR_TYPE_HINTS = {"gym", "fitness_center", "sports_complex", "sports_club", "wellness_center"}

TENNIS_BALL_ICON = {
    "url": (
        "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0"
        "PSI2NCIgdmlld0JveD0iMCAwIDY0IDY0Ij4KICA8Y2lyY2xlIGN4PSIzMiIgY3k9IjMyIiByPSIzMCIgZmlsbD0iI0NDRkYwMCIgc3Ry"
        "b2tlPSIjMWExYTFhIiBzdHJva2Utd2lkdGg9IjIiLz4KICA8cGF0aCBkPSJNIDMyIDIgQyAyMCAxMiwgMjAgNTIsIDMyIDYyIiBmaWxs"
        "PSJub25lIiBzdHJva2U9IiNGRkZGRkYiIHN0cm9rZS13aWR0aD0iMy41Ii8+CiAgPHBhdGggZD0iTSAzMiAyIEMgNDQgMTIsIDQ0IDUy"
        "LCAzMiA2MiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjRkZGRkZGIiBzdHJva2Utd2lkdGg9IjMuNSIvPgo8L3N2Zz4K"
    ),
    "width": 64, "height": 64, "anchorY": 32,
}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("🔍 Search Controls")

search_mode = st.sidebar.radio("Search by", ["ZIP Code", "State", "My GPS Location"], index=0)

selected_state = None
zip_code = None
gps = None
radius_label = None

if search_mode == "State":
    selected_state = st.sidebar.selectbox("Select State", STATE_NAMES, index=STATE_NAMES.index("Nevada"))
elif search_mode == "ZIP Code":
    zip_code = st.sidebar.text_input("Enter a US ZIP code", max_chars=10, placeholder="e.g. 89101")
    radius_label = st.sidebar.selectbox("Search radius", list(RADIUS_OPTIONS_MI.keys()), index=1)
else:
    st.sidebar.markdown("**📍 Tap to detect your GPS location**")
    gps = streamlit_geolocation()
    if gps and gps.get("latitude") and gps.get("longitude"):
        st.sidebar.success(f"Locked to ({gps['latitude']:.3f}, {gps['longitude']:.3f})")
    else:
        st.sidebar.caption("Tap the button above to detect your location. If nothing happens, check your browser's site permissions — location may be blocked.")
    radius_label = st.sidebar.selectbox("Search radius", list(RADIUS_OPTIONS_MI.keys()), index=2)

st.sidebar.subheader("Filters")
indoor_filter = st.sidebar.selectbox("Court Type (best-effort guess)", ["All", "Outdoor", "Indoor / Gym"])

st.sidebar.divider()
if st.sidebar.button("🔄 Clear cache & retry"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"Build: {APP_VERSION}")

if not GOOGLE_API_KEY:
    st.error(
        "Google Places API key not configured. Add GOOGLE_PLACES_API_KEY under "
        "your app's Settings → Secrets in Streamlit Cloud, then reboot the app."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def geocode_zip(zip_code_str):
    """Look up a US ZIP code's centroid. Nominatim first (matches real
    locations reliably), Zippopotam.us as a fast fallback."""
    zip_code_str = zip_code_str.strip()
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"postalcode": zip_code_str, "country": "us", "format": "json", "limit": 1}
        resp = requests.get(url, params=params, headers=APP_USER_AGENT, timeout=15)
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except (requests.exceptions.RequestException, ValueError):
        pass
    try:
        resp = requests.get(f"https://api.zippopotam.us/us/{zip_code_str}", headers=APP_USER_AGENT, timeout=10)
        if resp.status_code == 200:
            places = resp.json().get("places", [])
            if places:
                return float(places[0]["latitude"]), float(places[0]["longitude"])
    except (requests.exceptions.RequestException, ValueError):
        pass
    return None


def _places_to_dataframe(places):
    rows = []
    for p in places:
        if p.get("businessStatus") == "CLOSED_PERMANENTLY":
            continue
        loc = p.get("location", {})
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if lat is None or lon is None:
            continue
        types = set(p.get("types", []))
        name = (p.get("displayName") or {}).get("text") or "Unnamed"
        rows.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "address": p.get("formattedAddress", ""),
            "phone": p.get("nationalPhoneNumber"),
            "website": p.get("websiteUri"),
            "indoor": "Yes" if types & INDOOR_TYPE_HINTS else "No",
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset="name", keep="first").reset_index(drop=True)
    return df


@st.cache_data(ttl=3600)
def search_nearby(lat, lon, radius_m):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": GOOGLE_API_KEY, "X-Goog-FieldMask": FIELD_MASK}
    body = {
        "includedTypes": ["tennis_court"],
        "maxResultCount": 20,
        "rankPreference": "DISTANCE",
        "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": radius_m}}
    }
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=20)
    except requests.exceptions.RequestException as e:
        return pd.DataFrame(), f"request_error: {e}"
    if resp.status_code != 200:
        return pd.DataFrame(), f"api_error {resp.status_code}: {resp.text[:300]}"
    return _places_to_dataframe(resp.json().get("places", [])), None


@st.cache_data(ttl=3600)
def search_text(query):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": GOOGLE_API_KEY, "X-Goog-FieldMask": FIELD_MASK}
    body = {"textQuery": query, "includedType": "tennis_court", "maxResultCount": 20, "regionCode": "US"}
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=20)
    except requests.exceptions.RequestException as e:
        return pd.DataFrame(), f"request_error: {e}"
    if resp.status_code != 200:
        return pd.DataFrame(), f"api_error {resp.status_code}: {resp.text[:300]}"
    return _places_to_dataframe(resp.json().get("places", [])), None


# ---------------------------------------------------------------------------
# Run the search
# ---------------------------------------------------------------------------
point_mode = False
user_lat, user_lon = None, None

if search_mode == "My GPS Location" and gps and gps.get("latitude") and gps.get("longitude"):
    user_lat, user_lon = gps["latitude"], gps["longitude"]
    point_mode = True
    location_label = "your location"
    pin_label = "You"
    zoom_level = 11
    radius_m = min(RADIUS_OPTIONS_MI[radius_label] * 1609, GOOGLE_NEARBY_MAX_RADIUS_M)
    with st.spinner(f"Searching for tennis courts near {location_label}..."):
        df, error = search_nearby(user_lat, user_lon, radius_m)

elif search_mode == "ZIP Code" and zip_code:
    with st.spinner(f"Looking up ZIP {zip_code}..."):
        coords = geocode_zip(zip_code.strip())
    if coords is None:
        st.error(f"Couldn't look up ZIP code '{zip_code}' right now. Try 'Clear cache & retry'.")
        st.stop()
    user_lat, user_lon = coords
    point_mode = True
    location_label = f"ZIP {zip_code}"
    pin_label = f"ZIP {zip_code}"
    zoom_level = 12
    radius_m = min(RADIUS_OPTIONS_MI[radius_label] * 1609, GOOGLE_NEARBY_MAX_RADIUS_M)
    st.caption(f"Geocoded ZIP {zip_code} to ({user_lat:.4f}, {user_lon:.4f}) — searching {radius_label}.")
    with st.spinner(f"Searching for tennis courts near {location_label}..."):
        df, error = search_nearby(user_lat, user_lon, radius_m)

elif search_mode == "State":
    selected_state = selected_state or "Nevada"
    location_label = selected_state
    zoom_level = 6 if selected_state not in ["Alaska", "Hawaii"] else 5
    with st.spinner(f"Searching for tennis courts in {location_label}..."):
        df, error = search_text(f"tennis courts in {selected_state}, USA")

else:
    st.info("Enter a ZIP code or tap the GPS button in the sidebar to search.")
    st.stop()

if error:
    st.error("Couldn't reach Google Places right now. Try 'Clear cache & retry'.")
    st.caption(f"Details: {error}")
    st.stop()

st.caption(f"Found {len(df)} verified tennis facilities near {location_label} (results capped at 20 per query by Google).")

if not df.empty:
    if indoor_filter == "Indoor / Gym":
        df = df[df['indoor'] == "Yes"]
    elif indoor_filter == "Outdoor":
        df = df[df['indoor'] == "No"]

    st.success(f"Showing {len(df)} matching court locations near {location_label}.")

    if point_mode:
        view_lat, view_lon = user_lat, user_lon
    elif not df.empty:
        view_lat, view_lon = df['lat'].mean(), df['lon'].mean()
    else:
        view_lat, view_lon = 39.5, -98.35

    view_state = pdk.ViewState(latitude=view_lat, longitude=view_lon, zoom=zoom_level, pitch=0)

    df = df.copy()
    df['icon_data'] = [TENNIS_BALL_ICON] * len(df)

    layers = [
        pdk.Layer("IconLayer", data=df, get_icon='icon_data', get_position='[lon, lat]',
                  get_size=4, size_scale=8, pickable=True)
    ]

    if point_mode:
        me_df = pd.DataFrame([{"lat": user_lat, "lon": user_lon, "name": pin_label}])
        layers.append(
            pdk.Layer("ScatterplotLayer", data=me_df, get_position='[lon, lat]',
                      get_color='[255, 0, 0, 220]', get_radius=150, pickable=True)
        )

    r = pdk.Deck(
        layers=layers, initial_view_state=view_state,
        map_style="road", map_provider="carto",
        tooltip={"text": "{name}\n{address}"}
    )
    st.pydeck_chart(r, use_container_width=True)

    st.subheader("📋 Court Directory & GPS Directions")
    keyword = st.text_input("Filter table by name or keyword:")

    display_df = df.copy()
    if keyword:
        display_df = display_df[display_df['name'].str.contains(keyword, case=False, na=False)]

    display_df['Directions'] = display_df.apply(
        lambda row: f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}", axis=1
    )

    st.dataframe(
        display_df[['name', 'address', 'phone', 'indoor', 'website', 'Directions']],
        column_config={
            "name": "Name", "address": "Address", "phone": "Phone", "indoor": "Indoor/Gym?",
            "website": st.column_config.LinkColumn("Website", display_text="Visit Site 🌐"),
            "Directions": st.column_config.LinkColumn("Map Link", display_text="Open GPS Map 🗺️")
        },
        use_container_width=True
    )
else:
    st.warning(f"No tennis courts found near {location_label}.")
