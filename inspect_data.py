import pandas as pd

target_file = "BI_Manager_Case_Study.xlsx"

print(f"==========================================")
print(f" EXAMINING: {target_file}")
print(f"==========================================\n")

xl = pd.ExcelFile(target_file)
print("Excel Sheet Names:", xl.sheet_names)

for sheet in xl.sheet_names:
    print(f"\n--- Sheet: '{sheet}' ---")
    df = pd.read_excel(target_file, sheet_name=sheet)
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print("\nFirst 3 rows:")
    print(df.head(3))