
import requests
import pandas as pd
import ipaddress
from pydantic import BaseModel, ValidationError
import sqlite3


# 1. Define the structure of a valid result
class IPRecord(BaseModel):
    ip: str
    country: str | None = None
    region: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    isp: str | None = None


# 2. Read IP addresses from the input CSV file
df = pd.read_csv("input_ips.csv")

if "ip" not in df.columns:
    raise ValueError("input_ips.csv must contain a column named 'ip'")

results = []

# 3. Process each IP address
for value in df["ip"].dropna():
    ip = str(value).strip()

    if not ip:
        continue

    print(f"Looking up IP: {ip}")

    # 4. Validate the IP address
    try:
        address = ipaddress.ip_address(ip)

        if not address.is_global:
            print(f"Skipping non-public IP: {ip}")
            continue

    except ValueError:
        print(f"Invalid IP address: {ip}")
        continue

    try:
        # 5. Call IPWho.is without an API key
        url = f"https://ipwho.is/{ip}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data.get("success", False):
            print(f"Lookup failed for {ip}: {data.get('message', 'Unknown error')}")
            continue

        # 6. Extract the fields we need
        connection = data.get("connection") or {}
        timezone_data = data.get("timezone") or {}

        record = {
            "ip": data.get("ip", ip),
            "country": data.get("country"),
            "region": data.get("region"),
            "city": data.get("city"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": timezone_data.get("id"),
            "isp": connection.get("isp")
        }

        # 7. Validate the extracted data with Pydantic
        try:
            validated_record = IPRecord(**record)
            results.append(validated_record.model_dump())
            print(f"Successfully retrieved: {ip}")

        except ValidationError as error:
            print(f"Data validation failed for {ip}: {error}")

    except requests.RequestException as error:
        print(f"Request failed for {ip}: {error}")

# 8. Convert results into a pandas DataFrame
results_df = pd.DataFrame(results)

# 9. Clean the results
if not results_df.empty:
    results_df = results_df.drop_duplicates(subset=["ip"])

# 10. Save results to a CSV file
results_df.to_csv("ip_geolocation.csv", index=False)

# 11. Display the results
print("\nIP Geolocation Results:")
print(results_df.to_string(index=False))

print("\nETL extraction finished.")
print(f"Successful records: {len(results_df)}")

# Save results into an SQLite database
connection = sqlite3.connect("ip_geolocation.db")

results_df.to_sql(
    "ip_geolocation",
    connection,
    if_exists="append",
    index=False
)

connection.close()

print("Results saved to SQLite database.")
