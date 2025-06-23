import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.database import Base, engine
from scripts import models

Base.metadata.create_all(engine)
from sqlalchemy import text
from scripts.database import engine
from scripts.models import Base

with engine.connect() as conn:
    print("🧹 Entferne alte Tabellen...")
    conn.execute(text("DROP TABLE IF EXISTS arbeitsplan, teil, auftrag, material, maschine CASCADE;"))
    conn.commit()

print("🛠️ Erstelle neue Tabellen...")
Base.metadata.create_all(bind=engine)
print("✅ Tabellen erfolgreich erstellt.")
