from app.database import SessionLocal
from app.models.jeweller import Jeweller
from app.core.encryption import encrypt_token
from app.config import settings

db = SessionLocal()
j = db.query(Jeweller).first()

j.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
j.access_token = encrypt_token(settings.WHATSAPP_ACCESS_TOKEN)

db.commit()
print(f"Updated jeweller #{j.id} with platform WhatsApp credentials")
db.close()