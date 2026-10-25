import sys
sys.path.insert(0, ".")
from fastapi.testclient import TestClient
from services.api.main import app

print("Creating TestClient...")
with TestClient(app) as client:
    print("Calling /healthz...")
    resp = client.get("/healthz")
    print("Response status:", resp.status_code)
    print("Response data:", resp.json())
