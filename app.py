import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from streamlit_geolocation import streamlit_geolocation
from shapely.geometry import Point, Polygon

APP_VERSION = "v11 (higher-contrast basemap)"

# Page configuration optimized for mobile/tablet browsers
st.set_page_config(
    page_title="US Tennis Court Locator",
    page_icon="🎾",
    layout="wide"
)

# Clay-court themed background with grass-green input controls throughout
st.markdown(
    """
    <style>
    html, body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background-color: #B5651D !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }
    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"] {
        background-color: #A0522D !important;
    }
    h1, h2, h3, p, span, label, .stMarkdown, .stCaption, .stAlert {
        color: #FFF8F0 !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFF8F0 !important;
    }
    .stDataFrame {
        background-color: #FDF6EC;
        border-radius: 8px;
    }

    /* Grass green styling for every dropdown and text input in the sidebar */
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] div[data-baseweb="base-input"],
    [data-testid="stSidebar"] input {
        background-color: #3C9A40 !important;
        border: 1px solid #2C7A30 !important;
        color: #FFFFFF !important;
        font-weight: 600;
    }
    [data-testid="stSidebar"] div[data-baseweb="select"] svg {
        fill: #FFFFFF !important;
    }
    [data-testid="stSidebar"] input::placeholder {
        color: #E8F5E9 !important;
        opacity: 1 !important;
    }
    /* Dropdown menu list items when opened */
    div[data-baseweb="popover"] li {
        background-color: #3C9A40 !important;
        color: #FFFFFF !important;
    }
    div[data-baseweb="popover"] li:hover {
        background-color: #2C7A30 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🎾 US Tennis Court Locator")
st.markdown("Find, filter, and map tennis courts across all 50 states, including Alaska and Hawaii.")

# Comprehensive bounding boxes for all 50 states (south, west, north, east)
STATE_BOUNDS = {
    "Alabama": (30.2, -88.5, 35.0, -84.9),
    "Alaska": (51.2, -179.1, 71.4, -129.9),
    "Arizona": (31.3, -114.8, 37.0, -109.0),
    "Arkansas": (33.0, -94.6, 36.5, -89.6),
    "California": (32.5, -124.4, 42.0, -114.1),
    "Colorado": (37.0, -109.0, 41.0, -102.0),
    "Connecticut": (40.9, -73.7, 42.1, -71.8),
    "Delaware": (38.4, -75.8, 39.8, -75.0),
    "Florida": (24.5, -87.6, 31.0, -79.8),
    "Georgia": (30.3, -85.6, 35.0, -80.8),
    "Hawaii": (18.9, -160.2, 22.2, -154.8),
    "Idaho": (42.0, -117.2, 49.0, -111.0),
    "Illinois": (37.0, -91.5, 42.5, -87.5),
    "Indiana": (37.8, -88.1, 41.8, -84.8),
    "Iowa": (40.4, -96.6, 43.5, -90.1),
    "Kansas": (37.0, -102.0, 40.0, -94.6),
    "Kentucky": (36.5, -89.6, 39.1, -81.9),
    "Louisiana": (28.9, -94.0, 33.0, -88.8),
    "Maine": (43.1, -71.1, 47.5, -66.9),
    "Maryland": (37.9, -79.5, 39.7, -75.0),
    "Massachusetts": (41.2, -73.5, 42.9, -69.9),
    "Michigan": (41.7, -90.4, 48.3, -82.4),
    "Minnesota": (43.5, -97.2, 49.4, -89.5),
    "Mississippi": (30.2, -91.6, 35.0, -88.1),
    "Missouri": (36.0, -95.8, 40.6, -89.1),
    "Montana": (44.4, -116.0, 49.0, -104.0),
    "Nebraska": (40.0, -104.0, 43.0, -95.3),
    "Nevada": (35.0, -120.0, 42.0, -114.0),
    "New Hampshire": (42.7, -72.6, 45.3, -70.7),
    "New Jersey": (38.9, -75.6, 41.4, -73.9),
    "New Mexico": (31.3, -109.0, 37.0, -103.0),
    "New York": (40.5, -79.8, 45.0, -71.8),
    "North Carolina": (33.8, -84.3, 36.6, -75.4),
    "North Dakota": (45.9, -104.0, 49.0, -97.2),
    "Ohio": (38.4, -84.8, 42.3, -80.5),
    "Oklahoma": (33.6, -103.0, 37.0, -94.4),
    "Oregon": (41.9, -124.6, 46.3, -116.5),
    "Pennsylvania": (39.7, -80.5, 42.3, -74.7),
    "Rhode Island": (41.1, -71.9, 42.0, -71.1),
    "South Carolina": (32.0, -83.3, 35.2, -78.5),
    "South Dakota": (42.5, -104.0, 45.9, -96.4),
    "Tennessee": (35.0, -90.3, 36.7, -81.6),
    "Texas": (25.8, -106.6, 36.5, -93.5),
    "Utah": (37.0, -114.0, 42.0, -109.0),
    "Vermont": (42.7, -73.4, 45.0, -71.5),
    "Virginia": (36.5, -83.7, 39.5, -75.2),
    "Washington": (45.5, -124.7, 49.0, -116.9),
    "West Virginia": (37.2, -82.6, 40.6, -77.7),
    "Wisconsin": (42.5, -92.9, 47.1, -86.8),
    "Wyoming": (41.0, -111.1, 45.0, -104.0)
}

# How far around a point (GPS pin or ZIP centroid) to search, in degrees
POINT_RADIUS_DEG = 0.4  # roughly 25 miles

# Overpass and Nominatim both require an identifiable User-Agent per their
# usage policies; generic/missing ones get rate-limited far more aggressively.
APP_USER_AGENT = {
    "User-Agent": "TennisCourtLocatorApp/1.0 (contact: rafal@nevadagroup.com)"
}

# ---------------------------------------------------------------------------
# Sidebar: search method
# ---------------------------------------------------------------------------
st.sidebar.header("🔍 Search Controls")

search_mode = st.sidebar.radio(
    "Search by",
    ["State", "ZIP Code", "My GPS Location"],
    index=0
)

selected_state = None
zip_code = None
gps = None

if search_mode == "State":
    selected_state = st.sidebar.selectbox(
        "Select State",
        sorted(list(STATE_BOUNDS.keys())),
        index=sorted(STATE_BOUNDS.keys()).index("Nevada")
    )
elif search_mode == "ZIP Code":
    zip_code = st.sidebar.text_input("Enter a US ZIP code", max_chars=10, placeholder="e.g. 89101")
else:
    st.sidebar.markdown("**📍 Tap to detect your GPS location**")
    gps = streamlit_geolocation()
    if gps and gps.get("latitude") and gps.get("longitude"):
        st.sidebar.success(f"Locked to your GPS position ({gps['latitude']:.3f}, {gps['longitude']:.3f})")
    else:
        st.sidebar.caption("Tap the button above to detect your location.")

st.sidebar.subheader("Advanced Filters")
surface_filter = st.sidebar.selectbox("Surface Type", ["All", "Hard", "Clay", "Grass", "Asphalt", "Concrete"])
access_filter = st.sidebar.selectbox("Access Type", ["All", "Yes (Public/Open)", "Private", "Customers", "Members"])
lit_filter = st.sidebar.selectbox("Night Lighting", ["All", "Yes", "No"])
indoor_filter = st.sidebar.selectbox("Court Type", ["All", "Outdoor", "Indoor"])

st.sidebar.divider()
if st.sidebar.button("🔄 Clear cache & retry"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(f"Build: {APP_VERSION}")


# Public Overpass mirrors, tried in order if one is down/rate-limited
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]


@st.cache_data(ttl=3600)
def geocode_zip(zip_code_str):
    """Look up a US ZIP code's centroid via Nominatim. Returns (lat, lon) or None."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"postalcode": zip_code_str, "country": "us", "format": "json", "limit": 1}
    try:
        resp = requests.get(url, params=params, headers=APP_USER_AGENT, timeout=15)
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except requests.exceptions.RequestException:
        pass
    return None


def run_overpass_query(query):
    """POST a query to each Overpass mirror in turn. Returns parsed JSON or None."""
    for mirror_url in OVERPASS_MIRRORS:
        try:
            response = requests.post(mirror_url, data=query, headers=APP_USER_AGENT, timeout=25)
            content_type = response.headers.get("Content-Type", "")
            if response.status_code != 200 or "json" not in content_type:
                continue
            return response.json()
        except (requests.exceptions.RequestException, ValueError):
            continue
    return None


@st.cache_data(ttl=3600)
def fetch_tennis_courts(south, west, north, east):
    # Single combined query: tennis courts (with center point) AND named
    # parks/recreation grounds (with full geometry, for point-in-polygon
    # matching so we can label courts that sit inside a named public park).
    combined_query = f"""
    [out:json][timeout:30];
    (
      node["sport"~"tennis"]({south},{west},{north},{east});
      way["sport"~"tennis"]({south},{west},{north},{east});
      relation["sport"~"tennis"]({south},{west},{north},{east});
    );
    out center tags;
    (
      way["leisure"="park"]["name"]({south},{west},{north},{east});
      way["leisure"="recreation_ground"]["name"]({south},{west},{north},{east});
    );
    out geom;
    """

    data = run_overpass_query(combined_query)

    if data is None:
        st.error(
            "All Overpass servers are currently unavailable or rate-limited. "
            "Try the 'Clear cache & retry' button in the sidebar in a minute."
        )
        return pd.DataFrame(), 0

    try:
        raw_tennis = []
        named_parks = []  # list of (Polygon, name)

        for element in data.get("elements", []):
            tags = element.get("tags", {})

            if "tennis" in tags.get("sport", "").lower():
                if "lat" in element and "lon" in element:
                    lat, lon = element["lat"], element["lon"]
                elif "center" in element:
                    lat, lon = element["center"]["lat"], element["center"]["lon"]
                else:
                    continue
                raw_tennis.append({"lat": lat, "lon": lon, "tags": tags})

            elif tags.get("leisure") in ("park", "recreation_ground") and "name" in tags:
                geometry = element.get("geometry")
                if geometry and len(geometry) >= 3:
                    try:
                        poly = Polygon([(pt["lon"], pt["lat"]) for pt in geometry])
                        if poly.is_valid:
                            named_parks.append((poly, tags["name"]))
                    except Exception:
                        continue

        total_found = len(raw_tennis)
        courts = []

        for item in raw_tennis:
            lat, lon, tags = item["lat"], item["lon"], item["tags"]
            name = tags.get("name")
            surface = tags.get("surface", "Unspecified").capitalize()
            lit = tags.get("lit", "Unspecified").capitalize()
            access = tags.get("access", "Yes").capitalize()
            indoor = "Yes" if (
                tags.get("indoor", "").lower() == "yes"
                or bool(tags.get("building"))
                or tags.get("leisure") in ("sports_centre", "fitness_centre")
            ) else "No"
            website = tags.get("website") or tags.get("contact:website") or tags.get("url")

            # If the court itself has no name, check whether it sits inside
            # a named public park/recreation ground and borrow that name.
            if not name and not website:
                point = Point(lon, lat)
                for poly, park_name in named_parks:
                    if poly.contains(point):
                        name = f"{park_name} (public courts)"
                        break

            # Still nothing verifiable — skip it.
            if not name and not website:
                continue

            courts.append({
                "name": name if name else "Unnamed (has website)",
                "lat": lat,
                "lon": lon,
                "surface": surface,
                "lit": lit,
                "access": access,
                "indoor": indoor,
                "website": website
            })

        result_df = pd.DataFrame(courts)

        # Collapse duplicate entries for the same facility (multi-court
        # complexes often get one OSM node per individual court). Keep one
        # row per name, preferring the copy that has a website if any do.
        if not result_df.empty:
            result_df["_has_site"] = result_df["website"].notna()
            result_df = result_df.sort_values("_has_site", ascending=False)
            result_df = result_df.drop_duplicates(subset="name", keep="first")
            result_df = result_df.drop(columns="_has_site").reset_index(drop=True)

        return result_df, total_found
    except Exception as e:
        st.error(f"Error processing data: {e}")
        return pd.DataFrame(), 0


# ---------------------------------------------------------------------------
# Resolve the bounding box + map view for this run
# ---------------------------------------------------------------------------
point_mode = False
user_lat, user_lon = None, None

if search_mode == "My GPS Location" and gps and gps.get("latitude") and gps.get("longitude"):
    user_lat, user_lon = gps["latitude"], gps["longitude"]
    point_mode = True
    location_label = "your location"
    pin_label = "You"
    zoom_level = 11

elif search_mode == "ZIP Code" and zip_code:
    with st.spinner(f"Looking up ZIP {zip_code}..."):
        coords = geocode_zip(zip_code.strip())
    if coords is None:
        st.error(f"Couldn't find ZIP code '{zip_code}'. Double-check it and try again.")
        st.stop()
    user_lat, user_lon = coords
    point_mode = True
    location_label = f"ZIP {zip_code}"
    pin_label = f"ZIP {zip_code}"
    zoom_level = 11

elif search_mode == "State":
    selected_state = selected_state or "Nevada"
    location_label = selected_state
    zoom_level = 6 if selected_state not in ["Alaska", "Hawaii"] else 5

else:
    st.info("Enter a ZIP code or tap the GPS button in the sidebar to search.")
    st.stop()

if point_mode:
    south, north = user_lat - POINT_RADIUS_DEG, user_lat + POINT_RADIUS_DEG
    west, east = user_lon - POINT_RADIUS_DEG, user_lon + POINT_RADIUS_DEG
else:
    south, west, north, east = STATE_BOUNDS[selected_state]

with st.spinner(f"Querying nationwide database near {location_label}..."):
    df, total_found = fetch_tennis_courts(south, west, north, east)

st.caption(f"Found {total_found} total tennis court entries near {location_label}; {len(df)} have a verifiable name, park, or website.")

if not df.empty:
    if surface_filter != "All":
        df = df[df['surface'].str.lower() == surface_filter.lower()]

    if access_filter != "All":
        if "Public" in access_filter:
            df = df[df['access'].isin(['Yes', 'Public', 'Open'])]
        else:
            df = df[df['access'].str.lower() == access_filter.lower()]

    if lit_filter != "All":
        df = df[df['lit'].str.lower() == lit_filter.lower()]

    if indoor_filter == "Indoor":
        df = df[df['indoor'] == "Yes"]
    elif indoor_filter == "Outdoor":
        df = df[df['indoor'] == "No"]

    st.success(f"Showing {len(df)} matching court locations near {location_label}.")

    view_state = pdk.ViewState(
        latitude=user_lat if point_mode else (south + north) / 2,
        longitude=user_lon if point_mode else (west + east) / 2,
        zoom=zoom_level,
        pitch=0
    )

    # Tennis ball icon marker — a self-contained SVG data URI so the map
    # doesn't depend on any external image host. IconLayer (unlike TextLayer)
    # reliably renders bitmap/vector icons rather than relying on the
    # browser's emoji font, which deck.gl's text renderer doesn't use.
    TENNIS_BALL_ICON = {
        "url": (
            "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2NCIgaGVpZ2h0"
            "PSI2NCIgdmlld0JveD0iMCAwIDY0IDY0Ij4KICA8Y2lyY2xlIGN4PSIzMiIgY3k9IjMyIiByPSIzMCIgZmlsbD0iI0NDRkYwMCIgc3Ry"
            "b2tlPSIjMWExYTFhIiBzdHJva2Utd2lkdGg9IjIiLz4KICA8cGF0aCBkPSJNIDMyIDIgQyAyMCAxMiwgMjAgNTIsIDMyIDYyIiBmaWxs"
            "PSJub25lIiBzdHJva2U9IiNGRkZGRkYiIHN0cm9rZS13aWR0aD0iMy41Ii8+CiAgPHBhdGggZD0iTSAzMiAyIEMgNDQgMTIsIDQ0IDUy"
            "LCAzMiA2MiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjRkZGRkZGIiBzdHJva2Utd2lkdGg9IjMuNSIvPgo8L3N2Zz4K"
        ),
        "width": 64,
        "height": 64,
        "anchorY": 32,
    }

    df = df.copy()
    df['icon_data'] = [TENNIS_BALL_ICON] * len(df)

    layers = [
        pdk.Layer(
            "IconLayer",
            data=df,
            get_icon='icon_data',
            get_position='[lon, lat]',
            get_size=4,
            size_scale=8,
            pickable=True,
        )
    ]

    if point_mode:
        me_df = pd.DataFrame([{"lat": user_lat, "lon": user_lon, "name": pin_label}])
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=me_df,
                get_position='[lon, lat]',
                get_color='[255, 0, 0, 220]',
                get_radius=150,
                pickable=True,
            )
        )

    r = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="road",
        map_provider="carto",
        tooltip={"text": "Name: {name}\nSurface: {surface}\nAccess: {access}\nLit: {lit}"}
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
        display_df[['name', 'surface', 'access', 'lit', 'indoor', 'website', 'Directions']],
        column_config={
            "name": "Name",
            "indoor": "Indoor?",
            "website": st.column_config.LinkColumn("Website", display_text="Visit Site 🌐"),
            "Directions": st.column_config.LinkColumn("Map Link", display_text="Open GPS Map 🗺️")
        },
        use_container_width=True
    )
else:
    st.warning(f"No courts found matching your filter criteria near {location_label}.")
