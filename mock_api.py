from fastapi import FastAPI
import pandas as pd

app = FastAPI(title="Synthetic Funeral Services API")
EXCEL_PATH = "BI_Manager_Case_Study.xlsx"

@app.get("/api/v1/locations")
def get_locations():
    return pd.read_excel(EXCEL_PATH, sheet_name="Location Master").to_dict(orient="records")

@app.get("/api/v1/netsuite")
def get_netsuite():
    df = pd.read_excel(EXCEL_PATH, sheet_name="NetSuite Financials")
    df["Month"] = df["Month"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")

@app.get("/api/v1/adp")
def get_adp():
    df = pd.read_excel(EXCEL_PATH, sheet_name="ADP Labor")
    df["Month"] = df["Month"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")

@app.get("/api/v1/passare")
def get_passare():
    df = pd.read_excel(EXCEL_PATH, sheet_name="Passare Cases")
    df["Month"] = df["Month"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")
