"""
Interactive CLI Demonstration Script for Cloud Bill Agent (Step 5).

Demonstrates the complete autonomous cloud cost-optimization workflow:
INVESTIGATE -> DECIDE -> ACT -> VERIFY -> ADAPT OR FINISH
"""

import json
import sys
from pathlib import Path
import httpx

# Ensure root cloud-bill-agent directory is in python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.main import simulator, app
from fastapi.testclient import TestClient
from tools.cloud_tools import CloudApiClient
from agent.hf_client import HFInferenceClient
from agent.cloud_agent import CloudAgent


def get_demo_client() -> tuple[CloudApiClient, str]:
    """Detects live server or falls back to TestClient."""
    live_url = "http://127.0.0.1:8000"
    try:
        res = httpx.get(f"{live_url}/", timeout=1.0)
        if res.is_success:
            return CloudApiClient(base_url=live_url), "LIVE Server (http://127.0.0.1:8000)"
    except Exception:
        pass
    return CloudApiClient(client=TestClient(app)), "In-Process TestClient"


def main():
    print("=" * 70)
    print("   'THE CLOUD BILL THAT WOULDN'T STOP GROWING'")
    print("   Autonomous Cloud Cost-Optimization Agent Demonstration (Step 5)")
    print("=" * 70)

    # Reset environment state cleanly for demo run
    simulator.reset()
    print("\n[RESET] CloudSimulator state reset to initial services.json metrics.")

    tool_client, client_type = get_demo_client()
    print(f"[CLIENT] Connected via: {client_type}")

    hf_client = HFInferenceClient()
    if hf_client.is_configured():
        print(f"[LLM] Using Hugging Face Hosted Inference API (Model: {hf_client.model_id})")
    else:
        print("[LLM] HF_API_TOKEN not configured in .env. (Set token in .env for live LLM inference).")

    # Prompt user or use default
    default_request = "Review current services and reduce unnecessary cost without breaking latency or availability requirements."
    print(f"\nDefault Request: '{default_request}'")
    
    if sys.stdin.isatty():
        try:
            user_input = input("\nEnter your cloud optimization request (Press Enter for default): ").strip()
            if user_input:
                user_request = user_input
            else:
                user_request = default_request
        except EOFError:
            user_request = default_request
    else:
        user_request = default_request

    print(f"\n>>> Running Autonomous Agent for: '{user_request}'\n")

    agent = CloudAgent(hf_client=hf_client, tool_client=tool_client, max_iterations=10)
    result = agent.run(user_request)

    print("=" * 70)
    print(f" EXECUTION TRACE (Run ID: {result['run_id']})")
    print("=" * 70)

    for entry in result["execution_trace"]:
        phase = entry.get("phase", "").upper()
        if phase == "START":
            print(f"\n[START] {entry.get('info')}")
        elif phase == "INVESTIGATE":
            print(f"\n[INVESTIGATE] {entry.get('reason')}")
            print(f"  [TOOL] {entry.get('tool')}({json.dumps(entry.get('arguments', {}))})")
        elif phase == "ACT":
            print(f"\n[ACTION] {entry.get('reason')}")
            print(f"  [TOOL] {entry.get('tool')}({json.dumps(entry.get('arguments', {}))})")
        elif phase == "VERIFY":
            print(f"\n[VERIFY] {entry.get('info')}")
        elif phase == "VERIFICATION_RESULT":
            status_str = "SUCCESS" if entry.get("verified") else "FAILED"
            print(f"  [VERIFICATION] State Verified: {status_str} (Observed instances: {entry.get('observed_instances')})")
        elif phase == "ACTION_FAILED":
            print(f"  [REJECTED/FAILED] {entry.get('error')}")
        elif phase == "FINISH":
            print(f"\n[FINISH] {entry.get('info')}")

    print("\n" + "=" * 70)
    print(" STRUCTURED RESULT SUMMARY")
    print("=" * 70)

    print(f"Status       : {result['status'].upper()}")
    print(f"Success      : {result['success']}")
    print(f"Run ID       : {result['run_id']}")
    
    if result.get("cost_summary"):
        cs = result["cost_summary"]
        print(f"Initial Cost : ${cs['before_hourly_cost']:.2f}/hr")
        print(f"Final Cost   : ${cs['after_hourly_cost']:.2f}/hr")
        print(f"Est Savings  : ${cs['estimated_hourly_savings']:.2f}/hr")

    print("\nFinal Agent Explanation:")
    print("-" * 50)
    print(result["final_response"])
    print("-" * 50)

    print("\n[DEMO COMPLETE]")


if __name__ == "__main__":
    main()
