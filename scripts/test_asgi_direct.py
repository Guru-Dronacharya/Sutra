import sys
sys.path.insert(0, ".")
import asyncio
from httpx import AsyncClient, ASGITransport
from services.gateway.main import app as gateway_app

async def test():
    print("Creating AsyncClient...")
    async with AsyncClient(transport=ASGITransport(app=gateway_app), base_url="http://test") as client:
        print("Calling /healthz...")
        resp = await client.get("/healthz")
        print("Response:", resp.json())

if __name__ == "__main__":
    asyncio.run(test())
    print("SUCCESS!")
