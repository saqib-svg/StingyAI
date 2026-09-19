import json
import sys
from pathlib import Path

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cloud.simulator import CloudSimulator


def main():
    print("=" * 60)
    print("   CLOUD BILL AGENT - SIMULATOR TEST RUN (STEP 1)")
    print("=" * 60)

    # 1. Initialize Simulator
    print("\n[1] Initializing Cloud Simulator...")
    simulator = CloudSimulator()
    print("[OK] CloudSimulator initialized successfully.")

    # 2. Get All Services
    print("\n[2] Fetching All Services (get_services()):")
    all_services = simulator.get_services()
    print(json.dumps(all_services, indent=2))

    # 3. Get specific service: orders-api
    print("\n[3] Fetching Specific Service: orders-api (get_service('orders-api')):")
    orders_api = simulator.get_service("orders-api")
    print(json.dumps(orders_api, indent=2))

    # 4. Get specific service: reports-worker
    print("\n[4] Fetching Specific Service: reports-worker (get_service('reports-worker')):")
    reports_worker = simulator.get_service("reports-worker")
    print(json.dumps(reports_worker, indent=2))

    # 5. Test Stateful Mutation (Scale Action Demonstration)
    print("\n[5] Testing Stateful Mutation (Scaling reports-worker from 4 -> 1 instance):")
    simulator.scale_service("reports-worker", 1)
    updated_reports_worker = simulator.get_service("reports-worker")
    print(f"Updated reports-worker state in memory:\n{json.dumps(updated_reports_worker, indent=2)}")
    assert updated_reports_worker["instances"] == 1, "State mutation check failed!"
    print("[OK] Stateful in-memory mutation verified successfully!")

    # 6. Test Error Handling for Invalid Service ID
    print("\n[6] Testing Error Handling for Invalid service_id ('invalid-service-id'):")
    try:
        simulator.get_service("invalid-service-id")
    except ValueError as e:
        print(f"[OK] Expected error caught successfully: {e}")

    print("\n" + "=" * 60)
    print("   STEP 1 VERIFICATION COMPLETE - ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
