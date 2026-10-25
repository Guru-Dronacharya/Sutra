import asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from services.common.models import Base, User

eng = create_engine("sqlite:///sutra.db")
Base.metadata.create_all(eng)
Session = sessionmaker(bind=eng)

class AsyncDbWrapper:
    def __init__(self, sync_session):
        self._sync = sync_session
    async def execute(self, stmt):
        return await asyncio.to_thread(self._sync.execute, stmt)
    async def commit(self):
        return await asyncio.to_thread(self._sync.commit)
    async def rollback(self):
        return await asyncio.to_thread(self._sync.rollback)
    async def close(self):
        return await asyncio.to_thread(self._sync.close)
    def add(self, obj):
        self._sync.add(obj)
    async def refresh(self, obj):
        return await asyncio.to_thread(self._sync.refresh, obj)

async def test():
    s = Session()
    db = AsyncDbWrapper(s)
    res = await db.execute(select(User))
    print("Async select result:", res.scalars().all())
    await db.close()

if __name__ == "__main__":
    asyncio.run(test())
    print("FILE EXECUTION SUCCESSFUL!")
