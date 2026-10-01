import requests
import sqlite3
import pandas as pd

BASE_URL = "http://127.0.0.1:8000/api/v1"

print("1. Ingesting raw extracts from REST API endpoints...")
locations = pd.DataFrame(requests.get(f"{BASE_URL}/locations").json())
netsuite = pd.DataFrame(requests.get(f"{BASE_URL}/netsuite").json())
adp = pd.DataFrame(requests.get(f"{BASE_URL}/adp").json())
passare = pd.DataFrame(requests.get(f"{BASE_URL}/passare").json())

print("2. Joining multi-system extracts via Location Master crosswalk...")
merged = netsuite.merge(locations, on="NetSuite Location ID", how="inner")
merged = merged.merge(adp, on=["ADP Company Code", "Month"], how="left", suffixes=("", "_adp"))
final_model = merged.merge(passare, on=["Passare Location ID", "Month"], how="left", suffixes=("", "_passare"))

print("3. Executing data quality validation & labor audit...")
final_model["Payroll_Variance"] = final_model["Actual Payroll + Benefits ($)"] - final_model["Total Labor Cost ($)"]
final_model["Labor_Audit_Flag"] = final_model["Payroll_Variance"].apply(
    lambda x: "RECONCILED" if abs(x) < 1.00 else "MISMATCH"
)

conn = sqlite3.connect("central_warehouse.db")
final_model.to_sql("fct_monthly_location_performance", conn, if_exists="replace", index=False)
conn.close()

print("Pipeline execution complete! Model written to central_warehouse.db.")
