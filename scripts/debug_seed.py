import sys
sys.path.insert(0, ".")
from services.common.database import SyncSessionLocal, init_db
from services.common.models import User, UserRole, GuardrailPolicy, RiskTier, PIIAction, InjectionAction
from services.common.security import hash_password
from sqlalchemy import select

print("Step 1: init_db")
init_db()

print("Step 2: SyncSessionLocal")
db = SyncSessionLocal()

print("Step 3: query User")
u = db.execute(select(User).limit(1)).scalar_one_or_none()
print("User is:", u)

if not u:
    print("Step 4: hashing passwords and adding users")
    for email, pwd, role in [("admin@sutra.ai", "admin123", UserRole.ADMIN)]:
        user = User(email=email, password_hash=hash_password(pwd), role=role)
        db.add(user)

print("Step 5: committing")
db.commit()
print("Step 6: committed successfully!")
db.close()
