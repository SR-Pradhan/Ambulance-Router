from app.db import SessionLocal
from app.models.models import Hospital

db = SessionLocal()
hospitals = db.query(Hospital).all()
for h in hospitals:
    print(h.name, h.available_beds)
db.close()