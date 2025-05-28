import pandas as pd
from sqlalchemy import create_engine

EXCEL_PATH = 'data/source.xlsx'
# URL в формате: postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>
DB_URL = 'postgresql+psycopg2://admin:admin123@localhost:5432/kostcalc'

def main():
    engine = create_engine(DB_URL)
    xls = pd.ExcelFile(EXCEL_PATH)
    sheets = ['Material', 'Struktur', 'Arbeitsplan', 'Maschine', 'Teil', 'Auftrag']
    for sheet in sheets:
        df = xls.parse(sheet)
        df.to_sql(sheet.lower(), engine, if_exists='replace', index=False)
        print(f'Imported {len(df)} raws from sheet "{sheet}" to table "{sheet.lower()}"')
    print('Import has ended!')

if __name__ == '__main__':
    main()
