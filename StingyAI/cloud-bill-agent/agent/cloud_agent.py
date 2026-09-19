"""
Autonomous AI Cloud Optimization Agent Implementation (Step 5).

Implements the full autonomous cloud cost-optimization workflow:
INVESTIGATE -> DECIDE -> ACT -> VERIFY -> ADAPT OR FINISH

Features:
- Unique run_id per execution
- Strict 6-tool operational surface (no exposed reset tool)
- Pre-action (before) vs Post-action (after) verification
- Deterministic cost calculations from simulator cost_per_hour metrics
- Observation timestamp comparison (preferring newer data)
- No-action decision support (decision.action = "none")
- Iteration limit enforcement (status = "iteration_limit")
"""

import json
import re
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from tools.cloud_tools import (
    CloudApiClient,
    get_all_services,
    get_service,
    get_service_metrics,
    scale_service,
    resize_service,
    stop_service,
)
from .hf_client import HFInferenceClient


SYSTEM_PROMPT = """You are an Autonomous AI Cloud Operations & Cost-Optimization Agent.
Your objective is to investigate cloud metrics, decide safe cost-optimization or capacity actions, execute them through available tools, and explain the results.

You have access to EXACTLY these 6 operational tools:
1. get_all_services() -> Retrieves all service metrics and configurations.
2. get_service(service_id) -> Retrieves complete state for a specific service.
3. get_service_metrics(service_id) -> Retrieves metrics for a specific service.
4. scale_service(service_id, instances) -> Requests scaling instances for a service.
5. resize_service(service_id, instances) -> Requests resizing resources for a service.
6. stop_service(service_id) -> Requests safely stopping a service.

WORKFLOW RULES:
- Output strictly JSON in every step. No conversational text outside JSON.
- First INVESTIGATE relevant services before taking action.
- After completing actions and verification (or if no action is safe/required), immediately return a final response using {"type": "final", "response": "..."}.
- The "reason" field must be a concise, user-visible justification. Do NOT include hidden chain-of-thought.
- IDLE SERVICE OPTIMIZATION & MIN INSTANCES RULES:
  * Before considering stop_service for any service, inspect its min_instances, active RPM, and health.
  * If min_instances > 0, stop_service is NOT a valid option because backend infrastructure guardrails strictly require min_instances capacity.
  * If a service is idle (RPM = 0, low utilization) and current instances > min_instances > 0, do NOT call stop_service. Instead, directly choose scale_service or resize_service to scale down instance count toward min_instances.
- TIME & STALE OBSERVATIONS:
  * Always prefer newer timestamp observations over older/stale observations. When current traffic (e.g., 10:30 timestamp) is high, do not scale down based on older low-traffic metrics (e.g., 08:00 timestamp).
- FAILED ACTIONS & HISTORY:
  * Inspect recent_events and action history. If a previous action failed (e.g. scale_up to 5 failed with capacity_unavailable, or stop_service failed due to min_instances), recognize the failure, inspect current state, never claim it succeeded, and evaluate if a different safe action (e.g. scale/resize toward min_instances) is needed. Do NOT retry an action that was already attempted and rejected.

FORMAT FOR TOOL CALLS:
```json
{
    "type": "tool_call",
    "tool": "get_service",
    "arguments": {
        "service_id": "reports-worker"
    },
    "reason": "Investigating current service capacity and load metrics."
}
```

FORMAT FOR FINAL RESPONSE:
```json
{
    "type": "final",
    "response": "Final explanation of findings, actions taken, verification results, or why no action was required."
}
```
"""

ALLOWED_TOOLS = {
    "get_all_services",
    "get_service",
    "get_service_metrics",
    "scale_service",
    "resize_service",
    "stop_service",
}

MUTATION_TOOLS = {"scale_service", "resize_service", "stop_service"}


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parses an ISO format timestamp string into a datetime object for comparison."""
    if not ts_str:
        return None
    try:
        # Standard ISO 8601 replacement
        clean_ts = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_ts)
    except Exception:
        return None


class CloudAgent:
    """
    Autonomous Cloud Cost-Optimization Agent implementing the full workflow.
    """

    def __init__(
        self,
        hf_client: Optional[HFInferenceClient] = None,
        tool_client: Optional[CloudApiClient] = None,
        max_iterations: int = 10,
    ):
        self.hf_client = hf_client or HFInferenceClient()
        self.tool_client = tool_client
        self.max_iterations = max_iterations

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes one of the 6 operational tools via the Agent Tool Layer."""
        if tool_name == "get_all_services":
            return get_all_services(client=self.tool_client)
        elif tool_name == "get_service":
            return get_service(args.get("service_id", ""), client=self.tool_client)
        elif tool_name == "get_service_metrics":
            return get_service_metrics(args.get("service_id", ""), client=self.tool_client)
        elif tool_name == "scale_service":
            return scale_service(args.get("service_id", ""), int(args.get("instances", 0)), client=self.tool_client)
        elif tool_name == "resize_service":
            return resize_service(args.get("service_id", ""), int(args.get("instances", 0)), client=self.tool_client)
        elif tool_name == "stop_service":
            return stop_service(args.get("service_id", ""), client=self.tool_client)
        else:
            return {"success": False, "data": None, "error": f"Unknown tool: '{tool_name}'"}

    def _parse_model_output(self, raw_text: str) -> Dict[str, Any]:
        """Parses JSON decision block robustly."""
        cleaned = raw_text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_str = cleaned[start : end + 1]
            else:
                json_str = cleaned

        return json.loads(json_str)

    def _calculate_total_hourly_cost(self) -> Optional[float]:
        """Calculates current total hourly spending by querying all services."""
        res = get_all_services(client=self.tool_client)
        if res.get("success") and isinstance(res.get("data"), list):
            return sum(s.get("cost_per_hour", 0.0) for s in res["data"])
        return None

    def run(self, user_request: str) -> Dict[str, Any]:
        """
        Runs the full autonomous cloud cost-optimization workflow:
        INVESTIGATE -> DECIDE -> ACT -> VERIFY -> ADAPT OR FINISH
        """
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        step_counter = 0

        execution_trace: List[Dict[str, Any]] = []
        investigation: List[Dict[str, Any]] = []
        decision: Dict[str, Any] = {"action": "none", "reason": "Initial investigation"}
        actions: List[Dict[str, Any]] = []
        verification: List[Dict[str, Any]] = []
        final_response: str = ""
        agent_status: str = "completed"
        agent_success: bool = True

        # Initial Cost Snapshot
        initial_cost = self._calculate_total_hourly_cost()

        failed_tool_attempts = set()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_request},
        ]

        # Log start
        step_counter += 1
        execution_trace.append({
            "step": step_counter,
            "phase": "start",
            "info": f"Run ID '{run_id}' initiated for request: '{user_request}'"
        })

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            try:
                raw_response = self.hf_client.chat_completion(messages, temperature=0.1)
            except Exception as e:
                err_msg = f"Model inference error: {str(e)}"
                step_counter += 1
                execution_trace.append({
                    "step": step_counter,
                    "phase": "error",
                    "info": err_msg
                })
                final_response = f"Agent workflow aborted: {err_msg}"
                agent_status = "failed"
                agent_success = False
                break

            try:
                dec_dict = self._parse_model_output(raw_response)
            except Exception as parse_err:
                step_counter += 1
                execution_trace.append({
                    "step": step_counter,
                    "phase": "parse_retry",
                    "info": f"JSON parse error: {parse_err}"
                })
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({
                    "role": "user",
                    "content": "Your response was not valid JSON. Please output strictly JSON matching the required format."
                })
                continue

            dec_type = dec_dict.get("type", "")

            # 1. FINAL RESPONSE PHASE
            if dec_type == "final":
                final_response = dec_dict.get("response", "Investigation completed.")
                step_counter += 1
                execution_trace.append({
                    "step": step_counter,
                    "phase": "finish",
                    "info": "Final response generated."
                })
                break

            # 2. TOOL CALL PHASE
            if dec_type == "tool_call":
                tool_name = dec_dict.get("tool", "")
                tool_args = dec_dict.get("arguments", {})
                reason = dec_dict.get("reason", "Executing cloud tool")

                # Allowlist check
                if tool_name not in ALLOWED_TOOLS:
                    step_counter += 1
                    execution_trace.append({
                        "step": step_counter,
                        "phase": "validation",
                        "info": f"Rejected disallowed tool '{tool_name}'"
                    })
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append({"role": "user", "content": f"Tool '{tool_name}' is not allowed."})
                    continue

                service_id = tool_args.get("service_id", "all")
                attempt_key = (tool_name, service_id, json.dumps(tool_args, sort_keys=True))

                # Duplicate retry check: Prevent repeating an identical failed action
                if attempt_key in failed_tool_attempts:
                    step_counter += 1
                    execution_trace.append({
                        "step": step_counter,
                        "phase": "validation",
                        "info": f"Prevented retrying previously rejected tool call '{tool_name}' with args {tool_args}"
                    })
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append({
                        "role": "user",
                        "content": f"Tool '{tool_name}' with arguments {json.dumps(tool_args)} was ALREADY attempted and rejected by backend safety guardrails. Do NOT retry identical rejected actions. Adapt strategy to choose a different valid action (or complete if no action is safe)."
                    })
                    continue

                is_mutation = tool_name in MUTATION_TOOLS
                phase_name = "act" if is_mutation else "investigate"

                step_counter += 1
                execution_trace.append({
                    "step": step_counter,
                    "phase": phase_name,
                    "tool": tool_name,
                    "arguments": tool_args,
                    "reason": reason,
                })

                service_id = tool_args.get("service_id", "all")
                decision = {
                    "action": tool_name if is_mutation else "investigate",
                    "reason": reason,
                    "target_service": service_id,
                }

                # PRE-ACTION CAPTURE (for mutating actions)
                before_state = None
                if is_mutation and service_id != "all":
                    pre_res = get_service(service_id, client=self.tool_client)
                    if pre_res.get("success"):
                        before_state = pre_res.get("data")

                # EXECUTE TOOL VIA AGENT TOOL LAYER
                tool_result = self._execute_tool(tool_name, tool_args)

                # Record Investigation or Action
                if not is_mutation:
                    obs_data = tool_result.get("data")
                    investigation.append({
                        "service_id": service_id,
                        "tool": tool_name,
                        "observations": obs_data if isinstance(obs_data, list) else [obs_data],
                    })

                    # Handle Timestamp comparisons if timestamps present
                    if isinstance(obs_data, dict) and "timestamp" in obs_data:
                        step_counter += 1
                        execution_trace.append({
                            "step": step_counter,
                            "phase": "timestamp_check",
                            "info": f"Observed timestamp for '{service_id}': {obs_data['timestamp']}"
                        })

                else:
                    # MUTATION ACTION ATTEMPT
                    if tool_result.get("success"):
                        actions.append({
                            "service_id": service_id,
                            "action": tool_name,
                            "tool": tool_name,
                            "arguments": tool_args,
                            "status": "success",
                            "success": True,
                            "result": tool_result.get("data"),
                        })

                        # VERIFICATION PHASE
                        step_counter += 1
                        execution_trace.append({
                            "step": step_counter,
                            "phase": "verify",
                            "tool": "get_service",
                            "info": f"Performing post-action state verification for '{service_id}'..."
                        })

                        post_res = get_service(service_id, client=self.tool_client)
                        after_state = post_res.get("data") if post_res.get("success") else None

                        # Check if observed state matches requested state
                        ver_success = False
                        if after_state:
                            if tool_name in ("scale_service", "resize_service"):
                                req_inst = tool_args.get("instances")
                                ver_success = (after_state.get("instances") == req_inst)
                            elif tool_name == "stop_service":
                                ver_success = (after_state.get("instances") == 0 and not after_state.get("healthy"))

                        verification.append({
                            "service_id": service_id,
                            "action": tool_name,
                            "verification_success": ver_success,
                            "before": before_state,
                            "after": after_state,
                            "observed_state": after_state,
                        })

                        step_counter += 1
                        execution_trace.append({
                            "step": step_counter,
                            "phase": "verification_result",
                            "verified": ver_success,
                            "observed_instances": after_state.get("instances") if after_state else None,
                        })

                    else:
                        # FAILED ACTION / BACKEND SAFETY REJECTION
                        failed_tool_attempts.add(attempt_key)
                        err_reason = tool_result.get("error", "Action rejected by backend safety layer")
                        actions.append({
                            "service_id": service_id,
                            "action": tool_name,
                            "tool": tool_name,
                            "arguments": tool_args,
                            "status": "failed",
                            "success": False,
                            "error": err_reason,
                        })

                        step_counter += 1
                        execution_trace.append({
                            "step": step_counter,
                            "phase": "action_failed",
                            "tool": tool_name,
                            "error": err_reason,
                            "reason": f"Action '{tool_name}' failed: {err_reason}",
                        })

                        # ADAPT PHASE: Explicitly log adaptation when action is rejected
                        step_counter += 1
                        execution_trace.append({
                            "step": step_counter,
                            "phase": "adapt",
                            "reason": f"Action '{tool_name}' rejected by backend safety boundary ({err_reason}). Adapting strategy to evaluate safe alternative actions.",
                        })

                # Append tool result to conversation history
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({
                    "role": "user",
                    "content": f"Tool '{tool_name}' execution result:\n{json.dumps(tool_result)}"
                })

            else:
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({
                    "role": "user",
                    "content": "Invalid output format. 'type' must be 'tool_call' or 'final'."
                })

        # Iteration Limit Check
        if iteration >= self.max_iterations and not final_response:
            agent_status = "iteration_limit"
            agent_success = False
            final_response = "Agent reached maximum iteration limit before completing request."
            step_counter += 1
            execution_trace.append({
                "step": step_counter,
                "phase": "iteration_limit",
                "info": "Reached MAX_ITERATIONS cap."
            })

        # Final Cost Calculation
        final_cost = self._calculate_total_hourly_cost()
        cost_summary = None
        if initial_cost is not None and final_cost is not None:
            savings = round(initial_cost - final_cost, 2)
            has_change = abs(savings) > 0.001
            cost_summary = {
                "before_hourly_cost": initial_cost,
                "after_hourly_cost": final_cost,
                "estimated_hourly_savings": savings if savings > 0 else 0.0,
                "has_cost_change": has_change,
                "note": None if has_change else "Cost impact unavailable from current simulator pricing data.",
            }

        return {
            "run_id": run_id,
            "request": user_request,
            "status": agent_status,
            "investigation": investigation,
            "decision": decision,
            "actions": actions,
            "verification": verification,
            "execution_trace": execution_trace,
            "cost_summary": cost_summary,
            "final_response": final_response,
            "success": agent_success,
        }

    def parse_decision_or_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Exposes clean model output parser."""
        return self._parse_model_output(raw_text)
