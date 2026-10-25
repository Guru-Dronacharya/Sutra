import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from services.common.models import Base, User, UserRole
from services.common.security import hash_password

eng = create_engine("sqlite:///:memory:")
Base.metadata.create_all(eng)
SyncSessionLocal = sessionmaker(bind=eng)

class TransparentAsyncSession:
    def __init__(self, sync_session):
        self._s = sync_session
    async def execute(self, stmt, *args, **kwargs):
        return self._s.execute(stmt, *args, **kwargs)
    async def commit(self):
        return self._s.commit()
    async def rollback(self):
        return self._s.rollback()
    async def close(self):
        return self._s.close()
    def add(self, instance):
        return self._s.add(instance)
    async def refresh(self, instance):
        return self._s.refresh(instance)
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.close()

async def run_test():
    s = SyncSessionLocal()
    db = TransparentAsyncSession(s)
    
    # Insert user
    user = User(email="test@sutra.ai", password_hash=hash_password("pass123"), role=UserRole.ADMIN)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    print("User created with ID:", user.id)
    
    # Query user
    stmt = select(User).where(User.email == "test@sutra.ai")
    res = await db.execute(stmt)
    found = res.scalar_one_or_none()
    print("Found user:", found.email, found.role)
    await db.close()

if __name__ == "__main__":
    asyncio.run(run_test())
    print("TRANSPARENT ASYNC SESSION WORKS 100% PERFECTLY!")
