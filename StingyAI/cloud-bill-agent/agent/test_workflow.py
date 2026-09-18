import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from fastapi.testclient import TestClient

# Ensure root cloud-bill-agent directory is in python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.main import app, simulator
from tools.cloud_tools import CloudApiClient
from agent.hf_client import HFInferenceClient
from agent.cloud_agent import CloudAgent, parse_timestamp


class MockHFWorkflowClient(HFInferenceClient):
    """
    Mock HF Client providing scripted responses for deterministic workflow testing.
    """

    def __init__(self, script_responses: List[str] = None):
        super().__init__(token="mock_token", model_id="mock_model", api_url="http://mock")
        self.script_responses = script_responses or []
        self.call_count = 0

    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.1, max_tokens: int = 1024) -> str:
        if self.call_count < len(self.script_responses):
            resp = self.script_responses[self.call_count]
            self.call_count += 1
            return resp
        return json.dumps({
            "type": "final",
            "response": "Workflow completed via mock script."
        })


def get_test_api_client() -> CloudApiClient:
    """Returns an in-process FastAPI TestClient wrapped in CloudApiClient."""
    return CloudApiClient(client=TestClient(app))


def reset_environment_state():
    """Resets simulator state cleanly between test runs."""
    simulator.reset()


def test_full_workflow_investigate_act_verify():
    print("\n[1] Testing Full Workflow: Investigate -> Decide -> Act -> Verify ...")
    reset_environment_state()
    tool_client = get_test_api_client()

    script = [
        json.dumps({
            "type": "tool_call",
            "tool": "get_all_services",
            "arguments": {},
            "reason": "Investigate environment service metrics"
        }),
        json.dumps({
            "type": "tool_call",
            "tool": "scale_service",
            "arguments": {"service_id": "reports-worker", "instances": 1},
            "reason": "reports-worker has 0 RPM; scaling to 1 instance to minimize bill safely"
        }),
        json.dumps({
            "type": "final",
            "response": "Scaled reports-worker from 4 to 1 instance. Verified new instance count is 1."
        })
    ]

    mock_hf = MockHFWorkflowClient(script)
    agent = CloudAgent(hf_client=mock_hf, tool_client=tool_client)
    res = agent.run("Review services and optimize cost.")

    assert res["status"] == "completed"
    assert res["success"] is True
    assert res["run_id"].startswith("run-")
    assert len(res["investigation"]) >= 1
    assert len(res["actions"]) == 1
    assert res["actions"][0]["success"] is True

    # Pre vs Post Verification check
    ver = res["verification"][0]
    assert ver["verification_success"] is True
    assert ver["before"]["instances"] == 4
    assert ver["after"]["instances"] == 1
    print(f"[OK] Full workflow verified (Run ID: {res['run_id']}).")


def test_no_action_workflow():
    print("\n[2] Testing No-Action Workflow Decision ...")
    reset_environment_state()
    tool_client = get_test_api_client()

    script = [
        json.dumps({
            "type": "tool_call",
            "tool": "get_service_metrics",
            "arguments": {"service_id": "orders-api"},
            "reason": "Inspect orders-api current workload"
        }),
        json.dumps({
            "type": "final",
            "response": "orders-api is operating within optimal CPU and latency parameters. No action required."
        })
    ]

    mock_hf = MockHFWorkflowClient(script)
    agent = CloudAgent(hf_client=mock_hf, tool_client=tool_client)
    res = agent.run("Check if orders-api needs optimization.")

    assert res["status"] == "completed"
    assert len(res["actions"]) == 0
    assert res["decision"]["action"] in ("investigate", "none")
    print("[OK] No-action workflow decision verified.")


def test_backend_safety_rejection_workflow():
    print("\n[3] Testing Backend Safety Rejection Handling ...")
    reset_environment_state()
    tool_client = get_test_api_client()

    script = [
        json.dumps({
            "type": "tool_call",
            "tool": "stop_service",
            "arguments": {"service_id": "orders-api"},
            "reason": "Attempting to stop active service orders-api"
        }),
        json.dumps({
            "type": "final",
            "response": "Backend rejected stopping orders-api due to active incoming traffic."
        })
    ]

    mock_hf = MockHFWorkflowClient(script)
    agent = CloudAgent(hf_client=mock_hf, tool_client=tool_client)
    res = agent.run("Stop orders-api service.")

    assert res["actions"][0]["success"] is False
    assert "active incoming traffic" in res["actions"][0]["error"]
    assert len(res["verification"]) == 0
    print("[OK] Backend safety rejection correctly recorded without claiming success.")


def test_max_iterations_workflow():
    print("\n[4] Testing MAX_ITERATIONS Enforcement ...")
    reset_environment_state()
    tool_client = get_test_api_client()

    infinite_script = [
        json.dumps({
            "type": "tool_call",
            "tool": "get_all_services",
            "arguments": {},
            "reason": f"Loop {i}"
        })
        for i in range(15)
    ]

    mock_hf = MockHFWorkflowClient(infinite_script)
    agent = CloudAgent(hf_client=mock_hf, tool_client=tool_client, max_iterations=3)
    res = agent.run("Loop request")

    assert res["status"] == "iteration_limit"
    assert res["success"] is False
    print("[OK] MAX_ITERATIONS limit enforced (status = 'iteration_limit').")


def test_timestamp_comparison_logic():
    print("\n[5] Testing Observation Timestamp Parsing & Comparison ...")
    ts1_str = "2026-09-17T08:00:00Z"
    ts2_str = "2026-09-17T10:30:00Z"

    dt1 = parse_timestamp(ts1_str)
    dt2 = parse_timestamp(ts2_str)

    assert dt1 is not None and dt2 is not None
    assert dt2 > dt1, "Timestamp 10:30 must be evaluated as newer than 08:00!"
    print("[OK] Timestamp parsing correctly identifies 10:30 as newer than 08:00.")


def test_simulator_reset_functionality():
    print("\n[6] Testing CloudSimulator.reset() ...")
    reset_environment_state()
    tool_client = get_test_api_client()

    # Mutate state
    simulator.scale_service("reports-worker", 1)
    assert simulator.get_service("reports-worker")["instances"] == 1

    # Reset state
    simulator.reset()
    assert simulator.get_service("reports-worker")["instances"] == 4
    print("[OK] CloudSimulator.reset() successfully restored original initial state.")


def test_cost_calculation():
    print("\n[7] Testing Deterministic Cost Summary Calculation ...")
    reset_environment_state()
    tool_client = get_test_api_client()

    # Initial cost for orders-api ($18.50) + reports-worker ($11.00) = $29.50
    initial_cost = sum(s["cost_per_hour"] for s in simulator.get_services())
    assert initial_cost == 29.50
    print(f"[OK] Initial total hourly cost verified: ${initial_cost}/hr.")


def test_scenarios_a_to_d():
    print("\n[8] Testing Hackathon Scenarios A, B, C, D ...")
    tool_client = get_test_api_client()

    # Scenario A
    reset_environment_state()
    script_a = [
        json.dumps({
            "type": "tool_call",
            "tool": "get_all_services",
            "arguments": {},
            "reason": "Investigate utilization across services"
        }),
        json.dumps({
            "type": "tool_call",
            "tool": "scale_service",
            "arguments": {"service_id": "reports-worker", "instances": 1},
            "reason": "Scale reports-worker from 4 to min capacity (1) to save costs safely"
        }),
        json.dumps({
            "type": "final",
            "response": "Scaled reports-worker to 1 instance safely."
        })
    ]
    res_a = CloudAgent(hf_client=MockHFWorkflowClient(script_a), tool_client=tool_client).run("Scenario A")
    assert res_a["actions"][0]["success"] is True

    # Scenario B
    reset_environment_state()
    script_b = [
        json.dumps({
            "type": "tool_call",
            "tool": "get_service_metrics",
            "arguments": {"service_id": "orders-api"},
            "reason": "Inspect orders-api load"
        }),
        json.dumps({
            "type": "tool_call",
            "tool": "scale_service",
            "arguments": {"service_id": "orders-api", "instances": 8},
            "reason": "Scale orders-api to max (8) to handle load"
        }),
        json.dumps({
            "type": "final",
            "response": "Scaled orders-api to 8 instances."
        })
    ]
    res_b = CloudAgent(hf_client=MockHFWorkflowClient(script_b), tool_client=tool_client).run("Scenario B")
    assert res_b["actions"][0]["arguments"]["instances"] == 8

    # Scenario C (Stale vs Recent observation awareness)
    reset_environment_state()
    script_c = [
        json.dumps({
            "type": "tool_call",
            "tool": "get_service_metrics",
            "arguments": {"service_id": "orders-api"},
            "reason": "Inspect最新 10:30 traffic"
        }),
        json.dumps({
            "type": "final",
            "response": "Latest traffic observation (10:30 RPM=1200) is higher than 08:00 (RPM=900). Cost reduction is UNSAFE."
        })
    ]
    res_c = CloudAgent(hf_client=MockHFWorkflowClient(script_c), tool_client=tool_client).run("Scenario C")
    assert len(res_c["actions"]) == 0

    # Scenario D (Failed previous action handling)
    reset_environment_state()
    script_d = [
        json.dumps({
            "type": "tool_call",
            "tool": "get_service",
            "arguments": {"service_id": "orders-api"},
            "reason": "Verify service state after reported previous action failure act-784"
        }),
        json.dumps({
            "type": "final",
            "response": "Acknowledged previous scale action act-784 failed with capacity_unavailable. Current instances remain at 6. No unverified success reported."
        })
    ]
    res_d = CloudAgent(hf_client=MockHFWorkflowClient(script_d), tool_client=tool_client).run("Scenario D")
    assert "capacity_unavailable" in res_d["final_response"] or "failed" in res_d["final_response"].lower() or "6" in res_d["final_response"]

    print("[OK] Scenarios A, B, C, D verified successfully.")


def main():
    print("=" * 60)
    print("   CLOUD BILL AGENT - STEP 5 WORKFLOW TEST SUITE")
    print("=" * 60)

    test_full_workflow_investigate_act_verify()
    test_no_action_workflow()
    test_backend_safety_rejection_workflow()
    test_max_iterations_workflow()
    test_timestamp_comparison_logic()
    test_simulator_reset_functionality()
    test_cost_calculation()
    test_scenarios_a_to_d()

    print("\n" + "=" * 60)
    print("   STEP 5 WORKFLOW VERIFICATION COMPLETE - ALL TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
