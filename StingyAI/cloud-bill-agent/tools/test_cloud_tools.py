import json
import sys
from pathlib import Path
import httpx
from fastapi.testclient import TestClient

# Ensure root cloud-bill-agent directory is in python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.main import app
from tools.cloud_tools import (
    CloudApiClient,
    get_all_services,
    get_service,
    get_service_metrics,
    scale_service,
    resize_service,
    stop_service,
)


def get_test_client() -> CloudApiClient:
    """
    Returns a CloudApiClient connected to a live running uvicorn server at http://127.0.0.1:8000,
    or falls back to an in-process FastAPI TestClient if no live server is detected.
    """
    live_url = "http://127.0.0.1:8000"
    try:
        res = httpx.get(f"{live_url}/", timeout=1.0)
        if res.is_success:
            print(f"[INFO] Connecting tools test suite to LIVE server at {live_url}")
            return CloudApiClient(base_url=live_url)
    except Exception:
        pass

    print("[INFO] No live server detected on 127.0.0.1:8000. Running tests with in-process TestClient.")
    test_client = TestClient(app)
    return CloudApiClient(client=test_client)


def main():
    print("=" * 60)
    print("   CLOUD BILL AGENT - AGENT TOOL LAYER TEST SUITE (STEP 3)")
    print("=" * 60)

    client = get_test_client()

    # 1. get_all_services()
    print("\n[1] Testing Tool: get_all_services() ...")
    res = get_all_services(client)
    assert res["success"] is True, f"Tool failed: {res}"
    services = res["data"]
    assert isinstance(services, list) and len(services) == 2
    print(f"[OK] Tool returned {len(services)} services successfully.")

    # 2. get_service("orders-api")
    print("\n[2] Testing Tool: get_service('orders-api') ...")
    res = get_service("orders-api", client)
    assert res["success"] is True, f"Tool failed: {res}"
    orders_api = res["data"]
    assert orders_api["service_id"] == "orders-api"
    print(f"[OK] Tool returned orders-api (instances={orders_api['instances']}).")

    # 3. get_service("reports-worker")
    print("\n[3] Testing Tool: get_service('reports-worker') ...")
    res = get_service("reports-worker", client)
    assert res["success"] is True, f"Tool failed: {res}"
    reports_worker = res["data"]
    assert reports_worker["service_id"] == "reports-worker"
    print(f"[OK] Tool returned reports-worker (instances={reports_worker['instances']}).")

    # 4. get_service_metrics("orders-api")
    print("\n[4] Testing Tool: get_service_metrics('orders-api') ...")
    res = get_service_metrics("orders-api", client)
    assert res["success"] is True, f"Tool failed: {res}"
    metrics = res["data"]
    print(f"[OK] Tool returned metrics: {json.dumps(metrics, indent=2)}")

    # 5. scale_service("reports-worker", valid value=2)
    print("\n[5] Testing Tool: scale_service('reports-worker', 2) [Valid] ...")
    res = scale_service("reports-worker", 2, client)
    assert res["success"] is True, f"Tool failed: {res}"
    scaled_data = res["data"]
    assert scaled_data["instances"] == 2
    print("[OK] Tool successfully scaled reports-worker to 2 instances.")

    # 6. scale_service("reports-worker", invalid value=0) -> must return success: False with error detail
    print("\n[6] Testing Tool: scale_service('reports-worker', 0) [Invalid - Below Min] ...")
    res = scale_service("reports-worker", 0, client)
    assert res["success"] is False, "Expected success=False for invalid scale"
    assert res["data"] is None
    assert res["error"] is not None
    print(f"[OK] Tool correctly reported failure: error='{res['error']}'")

    # 7. get_service("invalid-service-id") -> must return success: False with 404 error detail
    print("\n[7] Testing Tool: get_service('invalid-service-id') [Invalid Service ID] ...")
    res = get_service("invalid-service-id", client)
    assert res["success"] is False, "Expected success=False for invalid service ID"
    assert res["data"] is None
    assert res["error"] is not None
    print(f"[OK] Tool correctly reported failure: error='{res['error']}'")

    # 8. Verify state persistence through the tool layer
    print("\n[8] Testing Tool: State Persistence Check via get_service('reports-worker') ...")
    res = get_service("reports-worker", client)
    assert res["success"] is True
    assert res["data"]["instances"] == 2, "State persistence check through tool layer failed!"
    print(f"[OK] Tool state persistence verified: instances remains {res['data']['instances']}.")

    # 9. Test stop_service("orders-api") -> should return success: False due to backend safety check
    print("\n[9] Testing Tool: stop_service('orders-api') [Safety Violation Check] ...")
    res = stop_service("orders-api", client)
    assert res["success"] is False, "Expected success=False when backend rejects unsafe stop"
    assert res["error"] is not None
    print(f"[OK] Tool correctly returned safety rejection: error='{res['error']}'")

    print("\n" + "=" * 60)
    print("   STEP 3 AGENT TOOL LAYER VERIFICATION COMPLETE - ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
