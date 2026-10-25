import streamlit as st
import requests
import pandas as pd
import ipaddress
import sqlite3

st.set_page_config(
    page_title="IP Geolocation Explorer",
    page_icon="🌍",
    layout="wide"
)

# Custom dashboard styling
st.markdown("""
<style>

.stApp { background-color: #f4f7fb; color: #243447; }
h1 { color: #12345a !important; font-weight: 750; }
h2, h3 { color: #234b73 !important; }
.stApp p, .stApp label, .stMarkdown { color: #34465a; }
.stTextInput input {
    background-color: #ffffff !important;
    color: #243447 !important;
    border: 1px solid #cbd8e6 !important;
    border-radius: 8px;
}
section[data-testid="stSidebar"] {
    background-color: #E8F1FA !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span {
    color: #17365D !important;
}

/* CSV upload box */
div[data-testid="stFileUploader"] section {
    background-color: #E8F1FA !important;
    border: 2px dashed #8AB4DE !important;
    border-radius: 12px !important;
}

/* Text inside CSV upload box */
div[data-testid="stFileUploader"] section,
div[data-testid="stFileUploader"] section span,
div[data-testid="stFileUploader"] section small,
div[data-testid="stFileUploader"] section button {
    color: #17365D !important;
}

/* Browse / Upload button */
div[data-testid="stFileUploader"] section button {
    background-color: #1769AA !important;
    color: #FFFFFF !important;
    border: none !important;
}

.stTextInput input::placeholder { color: #77869a !important; }
div[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #dce6f1;
    padding: 18px;
    border-radius: 12px;
    box-shadow: 0 3px 10px rgba(25, 55, 90, 0.06);
}
div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] {
    color: #12345a !important;
}
.stButton > button {
    background-color: #1769aa !important;
    color: #ffffff !important;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
}
.stButton > button:hover {
    background-color: #104e80 !important;
    color: #ffffff !important;
}
div[data-testid="stDataFrame"] {
    border: 1px solid #dce6f1;
    border-radius: 10px;
}
hr { border-color: #dce6f1; }

/* Light background for database table row numbers */
div[data-testid="stDataFrame"] [role="rowheader"] {
    background-color: #E8F1FA !important;
    color: #17365D !important;
}

/* Light background for table corner and row index */
div[data-testid="stDataFrame"] [role="gridcell"] {
    color: #17365D !important;
}

</style>
""", unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.title("🌍 IP Explorer")
    st.caption("IP Geolocation Dashboard")
    st.markdown("---")
    st.subheader("Navigation")

    page = st.radio(
        "Go to",
        [
            "🏠 Home",
            "🔎 IP Lookup",
            "📁 CSV Analysis",
            "📊 Results & Charts",
            "🗄️ Database Records"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption("Built with Python and Streamlit")
    st.caption("Geolocation data is approximate.")

API_URL = "https://ipwho.is/"


def lookup_ip(ip):
    """Get geolocation information for one public IP address."""
    try:
        ip = str(ip).strip()
        address = ipaddress.ip_address(ip)

        if not address.is_global:
            return {
                "ip": ip,
                "success": False,
                "error": "Enter a public IP address."
            }

        response = requests.get(API_URL + ip, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data.get("success", False):
            return {
                "ip": ip,
                "success": False,
                "error": data.get("message", "Lookup failed")
            }

        connection = data.get("connection") or {}
        timezone = data.get("timezone") or {}

        return {
            "ip": data.get("ip", ip),
            "success": True,
            "country": data.get("country"),
            "region": data.get("region"),
            "city": data.get("city"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "postal": data.get("postal"),
            "continent": data.get("continent"),
            "isp": connection.get("isp"),
            "organization": connection.get("org"),
            "asn": connection.get("asn"),
            "timezone": timezone.get("id")
        }

    except ValueError:
        return {
            "ip": str(ip),
            "success": False,
            "error": "Invalid IP address."
        }
    except requests.RequestException as error:
        return {
            "ip": str(ip),
            "success": False,
            "error": f"Network error: {error}"
        }


def save_results(results_df):
    """Append lookup results to the local SQLite database."""
    connection = sqlite3.connect("ip_geolocation.db")
    try:
        results_df.to_sql(
            "ip_geolocation",
            connection,
            if_exists="append",
            index=False
        )
    finally:
        connection.close()


# HOME PAGE
if page == "🏠 Home":
    st.title("🌍 IP Geolocation Explorer")
    st.markdown("### Welcome to your IP analytics dashboard")
    st.write(
        "Explore public IP addresses, view approximate geographic "
        "locations, analyze multiple IPs using CSV files, and visualize "
        "your lookup results."
    )
    st.info("Choose a section from the sidebar to get started.")

# IP LOOKUP PAGE
elif page == "🔎 IP Lookup":
    st.title("🔎 Look Up an IP Address")
    st.caption(
        "Enter a public IPv4 or IPv6 address to explore its approximate "
        "geographic location and network details."
    )

    ip_input = st.text_input(
        "Enter a public IP address",
        placeholder="Example: 8.8.8.8"
    )

    if st.button("Look Up IP"):
        if not ip_input.strip():
            st.warning("Please enter an IP address.")
        else:
            with st.spinner("Looking up IP address..."):
                result = lookup_ip(ip_input)

            if result["success"]:
                st.success("Lookup successful!")
                st.session_state["results_df"] = pd.DataFrame([result])
                save_results(pd.DataFrame([result]))
                st.success("IP result saved to database!")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("IP Address", result["ip"])
                    st.write("**Country:**", result.get("country"))
                    st.write("**Region:**", result.get("region"))
                    st.write("**City:**", result.get("city"))
                    st.write("**Continent:**", result.get("continent"))

                with col2:
                    st.write("**Latitude:**", result.get("latitude"))
                    st.write("**Longitude:**", result.get("longitude"))
                    st.write("**ISP:**", result.get("isp"))
                    st.write("**Organization:**", result.get("organization"))
                    st.write("**Timezone:**", result.get("timezone"))

                if result.get("latitude") is not None and result.get("longitude") is not None:
                    st.map(pd.DataFrame([{
                        "lat": result["latitude"],
                        "lon": result["longitude"]
                    }]))

                st.caption(
                    "IP geolocation is approximate and does not identify "
                    "a person's exact physical address."
                )
            else:
                st.error(result.get("error", "Lookup failed."))

# CSV ANALYSIS PAGE
elif page == "📁 CSV Analysis":
    st.title("📁 Bulk IP Analysis")
    st.write("Upload a CSV file containing a column named `ip`.")

    uploaded_file = st.file_uploader(
        "Choose your CSV file",
        type=["csv"]
    )

    if uploaded_file is not None:
        try:
            input_df = pd.read_csv(uploaded_file)

            if "ip" not in input_df.columns:
                st.error("Your CSV must contain a column named 'ip'.")
            else:
                st.write("### Input Data")
                st.dataframe(input_df, use_container_width=True)

                if st.button("Process CSV"):
                    ips = input_df["ip"].dropna().astype(str).str.strip()
                    ips = ips[ips != ""].drop_duplicates().tolist()

                    if not ips:
                        st.warning("No IP addresses found in the CSV.")
                    elif len(ips) > 100:
                        st.warning(
                            "For this demo, process at most 100 unique IPs "
                            "at a time to avoid excessive API requests."
                        )
                    else:
                        results = []
                        progress = st.progress(0)
                        status = st.empty()

                        for index, ip in enumerate(ips):
                            status.write(
                                f"Looking up {ip} ({index + 1}/{len(ips)})"
                            )
                            results.append(lookup_ip(ip))
                            progress.progress((index + 1) / len(ips))

                        results_df = pd.DataFrame(results)
                        st.session_state["results_df"] = results_df
                        save_results(results_df)
                        st.success(
                            "CSV processing complete. Results saved to database!"
                        )
                        st.info(
                            "Open **Results & Charts** in the sidebar to view "
                            "the summary, table, and charts."
                        )
        except Exception as error:
            st.error(f"Could not read the CSV file: {error}")

# RESULTS AND CHARTS PAGE
elif page == "📊 Results & Charts":
    st.title("📊 Results & Charts")

    if "results_df" not in st.session_state or st.session_state["results_df"].empty:
        st.info(
            "No results are available yet. Use IP Lookup or process a CSV file first."
        )
    else:
        results_df = st.session_state["results_df"]
        successful_df = results_df[results_df["success"] == True].copy()

        total = len(results_df)
        successful = len(successful_df)
        failed = total - successful

        st.subheader("📊 Lookup Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🌐 Total IPs", total)
        with col2:
            st.metric("✅ Successful Lookups", successful)
        with col3:
            st.metric("⚠️ Failed Lookups", failed)

        st.subheader("Lookup Results")
        st.dataframe(results_df, use_container_width=True)

        st.download_button(
            "Download Results as CSV",
            data=results_df.to_csv(index=False).encode("utf-8"),
            file_name="ip_geolocation_results.csv",
            mime="text/csv"
        )

        if not successful_df.empty:
            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.subheader("🌍 IPs by Country")
                country_counts = (
                    successful_df["country"]
                    .fillna("Unknown")
                    .value_counts()
                )
                st.bar_chart(country_counts, color="#1769AA")

            with chart_col2:
                st.subheader("📋 Missing Values")
                missing_counts = successful_df.isna().sum()
                missing_df = pd.DataFrame({
                    "Column": missing_counts.index,
                    "Missing Values": missing_counts.values
                })
                st.bar_chart(
                    missing_df.set_index("Column"),
                    color="#E69F00"
                )

            st.divider()
            st.subheader("📍 Geographic Coordinate Distribution")
            coordinate_df = successful_df.dropna(
                subset=["latitude", "longitude"]
            )

            if not coordinate_df.empty:
                st.scatter_chart(
                    coordinate_df,
                    x="longitude",
                    y="latitude",
                    color="#1769AA",
                    size=100
                )
            else:
                st.info("No geographic coordinates are available to plot.")

        st.caption(
            "Data provider: IPWho.is. Geolocation is approximate. "
            "Check the provider's current terms before publishing data."
        )

# DATABASE RECORDS PAGE
elif page == "🗄️ Database Records":
    st.title("🗄️ All Stored Database Records")

    try:
        connection = sqlite3.connect("ip_geolocation.db")
        try:
            tables = pd.read_sql_query(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='ip_geolocation'",
                connection
            )

            if not tables.empty:
                stored_df = pd.read_sql_query(
                    "SELECT * FROM ip_geolocation",
                    connection
                )

                st.metric("Total Stored Records", len(stored_df))
                
                   
                styled_df = (
    stored_df.style
    .set_properties(**{
        "background-color": "#E8F1FA",
        "color": "#4D90E1",
        "border-color": "#C5D9EE"
    })
    .set_table_styles([
      
{
    "selector": "th",
    "props": [
        ("background-color", "#B8D8F5"),
        ("color", "#12345A"),
        ("font-weight", "bold"),
        ("font-size", "15px"),
        ("border", "1px solid #9BBFE3"),
        ("padding", "12px")
    ]
},

        {
            "selector": "td",
            "props": [
                ("padding", "10px"),
                ("border", "1px solid #C5D9EE")
            ]
        }
    ])
)

                st.dataframe(styled_df, use_container_width=True)

                if not stored_df.empty:
                    st.download_button(
                        "Download All Stored Records",
                        data=stored_df.to_csv(index=False).encode("utf-8"),
                        file_name="all_ip_geolocation_records.csv",
                        mime="text/csv"
                    )
            else:
                st.info(
                    "No database records yet. Look up an IP or process a CSV first."
                )
        finally:
            connection.close()
    except Exception as error:
        st.error(f"Could not read database: {error}")
