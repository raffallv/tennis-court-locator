import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
from streamlit_geolocation import streamlit_geolocation

# Page configuration optimized for mobile/tablet browsers
st.set_page_config(
    page_title="US Tennis Court Locator",
    page_icon="🎾",
    layout="wide"
)

# Clay-court themed background
st.markdown(
    """
    <style>
    .stApp {
        background-color: #B5651D;
    }
    [data-testid="stSidebar"] {
        background-color: #A0522D;
    }
    h1, h2, h3, p, label, .stMarkdown, .stCaption {
        color: #FFF8F0 !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFF8F0 !important;
    }
    .stDataFrame {
        background-color: #FDF6EC;
        border-radius: 8px;
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

# How far around a GPS pin to search, in degrees (~0.4 deg ≈ 25 miles)
GPS_RADIUS_DEG = 0.4

# ---------------------------------------------------------------------------
# Sidebar: location controls
# ---------------------------------------------------------------------------
st.sidebar.header("🔍 Search Controls")

st.sidebar.markdown("**📍 Use my current location**")
gps = streamlit_geolocation()

use_gps = bool(gps and gps.get("latitude") and gps.get("longitude"))

if use_gps:
    st.sidebar.success(f"Locked to your GPS position ({gps['latitude']:.3f}, {gps['longitude']:.3f})")
    selected_state = None
else:
    st.sidebar.caption("Tap the button above, or pick a state below.")
    selected_state = st.sidebar.selectbox(
        "Select State",
        sorted(list(STATE_BOUNDS.keys())),
        index=sorted(STATE_BOUNDS.keys()).index("Nevada")
    )

st.sidebar.subheader("Advanced Filters")
surface_filter = st.sidebar.selectbox("Surface Type", ["All", "Hard", "Clay", "Grass", "Asphalt", "Concrete"])
access_filter = st.sidebar.selectbox("Access Type", ["All", "Yes (Public/Open)", "Private", "Customers", "Members"])
lit_filter = st.sidebar.selectbox("Night Lighting", ["All", "Yes", "No"])
indoor_filter = st.sidebar.selectbox("Court Type", ["All", "Outdoor", "Indoor"])


# Public Overpass mirrors, tried in order if one is down/rate-limited
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]

# Overpass's usage policy asks for an identifiable User-Agent; generic/missing
# ones get rate-limited much more aggressively than requests' default UA.
OVERPASS_HEADERS = {
    "User-Agent": "TennisCourtLocatorApp/1.0 (contact: rafal@nevadagroup.com)"
}


@st.cache_data(ttl=86400)
def fetch_tennis_courts(south, west, north, east):
    overpass_query = f"""
    [out:json][timeout:30];
    (
      node["sport"="tennis"]({south},{west},{north},{east});
      way["sport"="tennis"]({south},{west},{north},{east});
      relation["sport"="tennis"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """

    data = None
    last_error = None

    for mirror_url in OVERPASS_MIRRORS:
        try:
            response = requests.post(
                mirror_url, data=overpass_query, headers=OVERPASS_HEADERS, timeout=25
            )
            # A rate-limited or errored server often returns HTML/plain text, not JSON
            content_type = response.headers.get("Content-Type", "")
            if response.status_code != 200 or "json" not in content_type:
                last_error = f"{mirror_url} returned status {response.status_code} ({content_type or 'no content-type'})"
                continue
            data = response.json()
            break
        except requests.exceptions.RequestException as e:
            last_error = f"{mirror_url}: {e}"
            continue
        except ValueError as e:
            # response.json() failed to parse
            last_error = f"{mirror_url}: invalid JSON ({e})"
            continue

    if data is None:
        st.error(
            "All Overpass servers are currently unavailable or rate-limited. "
            "Please try again in a minute."
        )
        if last_error:
            st.caption(f"Last error: {last_error}")
        return pd.DataFrame()

    try:
        courts = []
        for element in data.get("elements", []):
            if "lat" in element and "lon" in element:
                lat = element["lat"]
                lon = element["lon"]
            elif "center" in element:
                lat = element["center"]["lat"]
                lon = element["center"]["lon"]
            else:
                continue

            tags = element.get("tags", {})
            name = tags.get("name", "Unnamed Tennis Court")
            surface = tags.get("surface", "Unspecified").capitalize()
            lit = tags.get("lit", "Unspecified").capitalize()
            access = tags.get("access", "Yes").capitalize()
            # OSM courts are outdoor unless explicitly tagged indoor=yes
            indoor = "Yes" if tags.get("indoor", "").lower() == "yes" else "No"

            courts.append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "surface": surface,
                "lit": lit,
                "access": access,
                "indoor": indoor
            })

        return pd.DataFrame(courts)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Resolve the bounding box + map view for this run
# ---------------------------------------------------------------------------
if use_gps:
    user_lat, user_lon = gps["latitude"], gps["longitude"]
    south, north = user_lat - GPS_RADIUS_DEG, user_lat + GPS_RADIUS_DEG
    west, east = user_lon - GPS_RADIUS_DEG, user_lon + GPS_RADIUS_DEG
    location_label = "your location"
    zoom_level = 11
else:
    south, west, north, east = STATE_BOUNDS[selected_state]
    user_lat, user_lon = None, None
    location_label = selected_state
    zoom_level = 6 if selected_state not in ["Alaska", "Hawaii"] else 5

with st.spinner(f"Querying nationwide database near {location_label}..."):
    df = fetch_tennis_courts(south, west, north, east)

if not df.empty:
    # Apply Surface Filter
    if surface_filter != "All":
        df = df[df['surface'].str.lower() == surface_filter.lower()]

    # Apply Access Filter
    if access_filter != "All":
        if "Public" in access_filter:
            df = df[df['access'].isin(['Yes', 'Public', 'Open'])]
        else:
            df = df[df['access'].str.lower() == access_filter.lower()]

    # Apply Lighting Filter
    if lit_filter != "All":
        df = df[df['lit'].str.lower() == lit_filter.lower()]

    # Apply Indoor/Outdoor Filter
    if indoor_filter == "Indoor":
        df = df[df['indoor'] == "Yes"]
    elif indoor_filter == "Outdoor":
        df = df[df['indoor'] == "No"]

    st.success(f"Showing {len(df)} matching court locations near {location_label}.")

    # Interactive Map Layout
    view_state = pdk.ViewState(
        latitude=user_lat if use_gps else (south + north) / 2,
        longitude=user_lon if use_gps else (west + east) / 2,
        zoom=zoom_level,
        pitch=0
    )

    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position='[lon, lat]',
            get_color='[0, 150, 255, 200]',
            get_radius=250,
            pickable=True,
            auto_highlight=True,
        )
    ]

    # Show the user's own GPS pin in a distinct color
    if use_gps:
        me_df = pd.DataFrame([{"lat": user_lat, "lon": user_lon, "name": "You"}])
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
        tooltip={"text": "Name: {name}\nSurface: {surface}\nAccess: {access}\nLit: {lit}"}
    )

    st.pydeck_chart(r, use_container_width=True)

    # Search & Directory Table with Direct Navigation Links
    st.subheader("📋 Court Directory & GPS Directions")
    keyword = st.text_input("Filter table by name or keyword:")

    display_df = df.copy()
    if keyword:
        display_df = display_df[display_df['name'].str.contains(keyword, case=False, na=False)]

    # Generate direct Google Maps link column — opens the native Google/Apple
    # Maps app on iOS/Android automatically, falls back to Google Maps web on desktop.
    display_df['Directions'] = display_df.apply(
        lambda row: f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}", axis=1
    )

    st.dataframe(
        display_df[['name', 'surface', 'access', 'lit', 'indoor', 'Directions']],
        column_config={
            "indoor": "Indoor?",
            "Directions": st.column_config.LinkColumn("Map Link", display_text="Open GPS Map 🗺️")
        },
        use_container_width=True
    )
else:
    st.warning(f"No courts found matching your filter criteria near {location_label}.")
