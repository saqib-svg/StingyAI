import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import app


def run_tests():
    print("=" * 60)
    print("   CLOUD BILL AGENT - FASTAPI API TEST SUITE (STEP 2)")
    print("=" * 60)

    client = TestClient(app)

    # 1. GET /services
    print("\n[1] Testing GET /services ...")
    res = client.get("/services")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    services = res.json()
    assert isinstance(services, list) and len(services) == 2, "Expected 2 services"
    print(f"[OK] Returned {len(services)} services successfully.")

    # 2. GET /services/orders-api
    print("\n[2] Testing GET /services/orders-api ...")
    res = client.get("/services/orders-api")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    orders_api = res.json()
    assert orders_api["service_id"] == "orders-api"
    print(f"[OK] Fetched orders-api successfully (instances={orders_api['instances']}).")

    # 3. GET /services/reports-worker
    print("\n[3] Testing GET /services/reports-worker ...")
    res = client.get("/services/reports-worker")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    reports_worker = res.json()
    assert reports_worker["service_id"] == "reports-worker"
    print(f"[OK] Fetched reports-worker successfully (instances={reports_worker['instances']}).")

    # 4. GET /services/orders-api/metrics
    print("\n[4] Testing GET /services/orders-api/metrics ...")
    res = client.get("/services/orders-api/metrics")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    metrics = res.json()
    required_keys = [
        "service_id", "cpu_percent", "memory_percent", "requests_per_minute",
        "latency_ms", "instances", "cost_per_hour", "healthy", "timestamp"
    ]
    for key in required_keys:
        assert key in metrics, f"Missing metric key: {key}"
    print(f"[OK] Fetched orders-api metrics successfully: {metrics}")

    # 5. POST /services/reports-worker/scale with valid value (instances = 3)
    print("\n[5] Testing POST /services/reports-worker/scale (valid instances = 3) ...")
    res = client.post("/services/reports-worker/scale", json={"instances": 3})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    scaled_service = res.json()
    assert scaled_service["instances"] == 3, f"Expected instances=3, got {scaled_service['instances']}"
    print("[OK] Scaled reports-worker to 3 instances successfully.")

    # 6. POST /services/reports-worker/scale below min_instances (instances = 0, min = 1) -> must fail 400
    print("\n[6] Testing POST /services/reports-worker/scale below min_instances (instances = 0) ...")
    res = client.post("/services/reports-worker/scale", json={"instances": 0})
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    print(f"[OK] Scale operation below min_instances rejected as expected: {res.json()['detail']}")

    # 7. POST /services/reports-worker/scale above max_instances (instances = 10, max = 6) -> must fail 400
    print("\n[7] Testing POST /services/reports-worker/scale above max_instances (instances = 10) ...")
    res = client.post("/services/reports-worker/scale", json={"instances": 10})
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    print(f"[OK] Scale operation above max_instances rejected as expected: {res.json()['detail']}")

    # 8. Invalid service ID -> must return 404
    print("\n[8] Testing GET /services/unknown-service (invalid service_id) ...")
    res = client.get("/services/unknown-service")
    assert res.status_code == 404, f"Expected 404, got {res.status_code}"
    print(f"[OK] Invalid service ID returned 404 as expected: {res.json()['detail']}")

    # 9. Verify state persistence after successful scale operation
    print("\n[9] Testing State Persistence via GET /services/reports-worker ...")
    res = client.get("/services/reports-worker")
    assert res.status_code == 200
    persisted_service = res.json()
    assert persisted_service["instances"] == 3, "State persistence check failed!"
    print(f"[OK] State persistence verified: instances remains {persisted_service['instances']}.")

    # 10. POST /services/orders-api/stop (safety checks should reject due to traffic > 0 and min_instances > 0)
    print("\n[10] Testing POST /services/orders-api/stop (Safety Enforcement) ...")
    res = client.post("/services/orders-api/stop")
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    print(f"[OK] Safety check correctly rejected stopping active orders-api: {res.json()['detail']}")

    # 11. POST /services/reports-worker/stop (Safety Enforcement: min_instances == 1 > 0)
    print("\n[11] Testing POST /services/reports-worker/stop (Safety Enforcement: min_instances > 0) ...")
    res = client.post("/services/reports-worker/stop")
    assert res.status_code == 400, f"Expected 400, got {res.status_code}"
    print(f"[OK] Safety check correctly rejected stopping reports-worker: {res.json()['detail']}")

    print("\n" + "=" * 60)
    print("   STEP 2 API VERIFICATION COMPLETE - ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
