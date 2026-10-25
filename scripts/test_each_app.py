import sys
sys.path.insert(0, ".")
from starlette.testclient import TestClient

from services.gateway.main import app as gateway_app
print("Testing gateway...")
cg = TestClient(gateway_app)
print("Gateway:", cg.get("/healthz").json())

from services.audit.main import app as audit_app
print("Testing audit...")
ca = TestClient(audit_app)
print("Audit:", ca.get("/healthz").json())

from services.ml.main import app as ml_app
print("Testing ml...")
cm = TestClient(ml_app)
print("ML:", cm.get("/healthz").json())

from services.rag.main import app as rag_app
print("Testing rag...")
cr = TestClient(rag_app)
print("RAG:", cr.get("/healthz").json())

from services.api.main import app as api_app
print("Testing api...")
capi = TestClient(api_app)
print("API:", capi.get("/healthz").json())

print("ALL 5 SERVICES WORKED!")
