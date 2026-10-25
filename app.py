
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import ipaddress
import sqlite3

st.set_page_config(
    page_title="IP Geolocation Explorer",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 IP Geolocation Explorer")
st.write("Look up an IP address or upload a CSV file containing IP addresses.")

API_URL = "https://ipwho.is/"


def lookup_ip(ip):
    """Get geolocation information for one public IP address."""

    try:
        ip = str(ip).strip()

        # Check whether the IP address is valid
        address = ipaddress.ip_address(ip)

        if not address.is_global:
            return {"ip": ip, "success": False,
                    "error": "Enter a public IP address."}

        response = requests.get(
            API_URL + ip,
            timeout=15
        )

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


# -------------------------------
# SECTION 1: Single IP lookup
# -------------------------------

st.header("1. Look Up One IP Address")

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
            
# Save the searched IP to the database
            connection = sqlite3.connect("ip_geolocation.db")

            record_df = pd.DataFrame([result])

            record_df.to_sql(
            "ip_geolocation",
             connection,
            if_exists="append",
            index=False
             )

            connection.close()

            st.success("IP result saved to database!")


            details = {
                key: value
                for key, value in result.items()
                if key not in ("success", "ip")
            }

            col1, col2 = st.columns(2)

            with col1:
                st.metric("IP Address", result["ip"])
                st.write("**Country:**", result["country"])
                st.write("**Region:**", result["region"])
                st.write("**City:**", result["city"])
                st.write("**Continent:**", result["continent"])

            with col2:
                st.write("**Latitude:**", result["latitude"])
                st.write("**Longitude:**", result["longitude"])
                st.write("**ISP:**", result["isp"])
                st.write("**Organization:**", result["organization"])
                st.write("**Timezone:**", result["timezone"])

            if result["latitude"] is not None and result["longitude"] is not None:
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


# -------------------------------
# SECTION 2: CSV upload
# -------------------------------

st.divider()
st.header("2. Upload a CSV File")

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
                                                       # Save CSV lookup results to SQLite

                    connection = sqlite3.connect("ip_geolocation.db")

                    results_df.to_sql(
                    "ip_geolocation",
                     connection,
                    if_exists="append",
                      index=False
                    )

                    connection.close()

                    st.success("Results saved to SQLite database!")

                    status.write("Processing complete.")

    except Exception as error:
        st.error(f"Could not read the CSV file: {error}")


# -------------------------------
# SECTION 3: Results and EDA
# -------------------------------

if "results_df" in st.session_state:
    results_df = st.session_state["results_df"]

    st.divider()
    st.header("3. Results and Exploratory Data Analysis")

    successful_df = results_df[
        results_df["success"] == True
    ].copy()

    total = len(results_df)
    successful = len(successful_df)
    failed = total - successful

    col1, col2, col3 = st.columns(3)
    col1.metric("Total IPs", total)
    col2.metric("Successful Lookups", successful)
    col3.metric("Failed Lookups", failed)

    st.subheader("Lookup Results")
    st.dataframe(results_df, use_container_width=True)

    # Download results
    csv_data = results_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Results as CSV",
        data=csv_data,
        file_name="ip_geolocation_results.csv",
        mime="text/csv"
    )

    if not successful_df.empty:
        st.subheader("Country Frequency")

        country_counts = (
            successful_df["country"]
            .fillna("Unknown")
            .value_counts()
        )

        st.bar_chart(country_counts)

        st.subheader("Missing Values")

        missing_counts = successful_df.isna().sum()

        missing_df = pd.DataFrame({
            "Column": missing_counts.index,
            "Missing Values": missing_counts.values
        })

        st.bar_chart(
            missing_df.set_index("Column")["Missing Values"]
        )

        st.subheader("Coordinate Distribution")

        coordinate_df = successful_df.dropna(
            subset=["latitude", "longitude"]
        )

        if not coordinate_df.empty:
            st.scatter_chart(
                coordinate_df,
                x="longitude",
                y="latitude"
            )

st.caption(
    "Data provider: IPWho.is. Check its current terms and attribution "
    "requirements before publishing or redistributing lookup data."
)

# SECTION 4: All Stored Database Records

st.divider()
st.header("4. All Stored Database Records")

try:
    connection = sqlite3.connect("ip_geolocation.db")

    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ip_geolocation'",
        connection
    )

    if not tables.empty:
        stored_df = pd.read_sql_query(
            "SELECT * FROM ip_geolocation",
            connection
        )

        st.metric("Total Stored Records", len(stored_df))
        st.dataframe(stored_df, use_container_width=True)

        if not stored_df.empty:
            st.download_button(
                "Download All Stored Records",
                data=stored_df.to_csv(index=False).encode("utf-8"),
                file_name="all_ip_geolocation_records.csv",
                mime="text/csv"
            )
    else:
        st.info("No database records yet. Upload and process a CSV first.")

    connection.close()

except Exception as error:
    st.error(f"Could not read database: {error}")


