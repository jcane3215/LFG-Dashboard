import requests
import pandas as pd
from sqlalchemy import create_engine, text
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
DB_PATH = "local_data.db"           # Path to your existing SQLite database
TABLE_NAME = "api_records"          # Main table name in SQLite
PRIMARY_KEY = "id"                  # Unique record ID field to deduplicate on
API_URL = "http://127.0.0.1:8000/api/v1/records"  # Your mock_api endpoint

# ==========================================
# 2. REFRESH & DEDUPLICATE FUNCTION
# ==========================================
def refresh_and_deduplicate():
    print(f"Connecting to API endpoint: {API_URL}...")
    
    try:
        # 1. Fetch fresh payload from mock_api
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        payload = response.json()
        
        records = payload.get("data", payload) if isinstance(payload, dict) else payload
        
        if not records:
            print("No records returned from API.")
            return

        # 2. Transform payload to Pandas DataFrame
        df = pd.json_normalize(records)
        df["_extracted_at"] = pd.Timestamp.utcnow().isoformat()

        # Check that primary key exists in incoming payload
        if PRIMARY_KEY not in df.columns:
            raise KeyError(f"Primary key '{PRIMARY_KEY}' not found in API records.")

        engine = create_engine(f"sqlite:///{DB_PATH}")

        with engine.begin() as conn:
            # 3. Create main table if it doesn't exist yet
            df.head(0).to_sql(TABLE_NAME, con=conn, if_exists="append", index=False)

            # 4. Write incoming records to a temporary staging table
            staging_table = f"stg_{TABLE_NAME}"
            df.to_sql(staging_table, con=conn, if_exists="replace", index=False)

            # 5. Insert ONLY records from staging that don't exist in the main table
            columns = [f'"{col}"' for col in df.columns]
            cols_str = ", ".join(columns)

            dedup_sql = text(f"""
                INSERT INTO {TABLE_NAME} ({cols_str})
                SELECT {cols_str}
                FROM {staging_table}
                WHERE {PRIMARY_KEY} NOT IN (
                    SELECT DISTINCT {PRIMARY_KEY} 
                    FROM {TABLE_NAME} 
                    WHERE {PRIMARY_KEY} IS NOT NULL
                );
            """)
            
            result = conn.execute(dedup_sql)
            inserted_count = result.rowcount

            # 6. Clean up temporary staging table
            conn.execute(text(f"DROP TABLE IF EXISTS {staging_table};"))

        print(f"Refresh Complete! {inserted_count} new unique records inserted into '{TABLE_NAME}'.")

    except requests.exceptions.RequestException as e:
        print(f"API Error: Failed to reach {API_URL}. Details: {e}")
    except Exception as e:
        print(f"Pipeline Error: {e}")

# ==========================================
# 3. EXECUTION
# ==========================================
if __name__ == "__main__":
    refresh_and_deduplicate()