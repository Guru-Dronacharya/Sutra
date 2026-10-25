import asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from services.common.models import Base, User

eng = create_engine("sqlite:///sutra.db")
Base.metadata.create_all(eng)
SessionLocal = sessionmaker(bind=eng)

async def test():
    s = SessionLocal()
    users = s.scalars(select(User)).all()
    print("Users successfully retrieved in async def:", users)
    s.close()

if __name__ == "__main__":
    asyncio.run(test())
    print("WORKS INSTANTLY!")
