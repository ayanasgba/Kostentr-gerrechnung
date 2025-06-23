# scripts/import_data.py
import pandas as pd
from sqlalchemy import create_engine

EXCEL_PATH = "data/source.xlsx"
DB_URL = "postgresql+psycopg2://postgres:postgresql@localhost:5433/kostcalc"

def main():
    engine = create_engine(DB_URL)
    xls = pd.ExcelFile(EXCEL_PATH)

    sheets = ["Material", "Maschine", "Auftrag", "Teil", "Arbeitsplan"]
    converters = {
        "teil_id": str,
        "Mat": str,
        "maschine": str,
        "ag_nr": str,
        "auftrag_nr": str,
        "Nr": str,
        "knoten": str,
    }

    for sheet in sheets:
        print(f"📥 Importiere {sheet}...")
        df = xls.parse(sheet, dtype=str, converters=converters)
        df.to_sql(sheet.lower(), engine, if_exists="append", index=False)
        print(f"✅ {len(df)} Zeilen aus '{sheet}' gespeichert.")

    print("🎉 Alle Daten erfolgreich importiert!")

if __name__ == "__main__":
    main()
