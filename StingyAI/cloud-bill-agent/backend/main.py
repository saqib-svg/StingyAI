"""
FastAPI Backend Cloud API Layer & Dashboard Host for 'The Cloud Bill That Wouldn't Stop Growing'.

Exposes HTTP REST endpoints for inspecting simulated cloud service states,
reading metrics, scaling instances, resizing resources, safely stopping services,
and executing the autonomous CloudAgent workflow.

Enforces strict deterministic infrastructure safety constraints at the backend level.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from backend.cloud.simulator import CloudSimulator
except ImportError:
    from cloud.simulator import CloudSimulator

try:
    from agent.cloud_agent import CloudAgent
    from tools.cloud_tools import CloudApiClient
except ImportError:
    try:
        from backend.agent.cloud_agent import CloudAgent
        from tools.cloud_tools import CloudApiClient
    except ImportError:
        CloudAgent = None
        CloudApiClient = None

# Initialize FastAPI application
app = FastAPI(
    title="Cloud Bill Agent API & Dashboard",
    description="Backend API and web dashboard for stateful cloud environment metrics and autonomous optimization.",
    version="1.0.0",
)

# Add CORS Middleware for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global singleton instance of CloudSimulator (in-memory state)
simulator = CloudSimulator()


# --- Pydantic Request Models ---

class ScaleRequest(BaseModel):
    instances: int = Field(..., description="Target instance count for scaling", ge=0)


class ResizeRequest(BaseModel):
    instances: int = Field(..., description="Target instance count for resizing", ge=0)


class AgentRunRequest(BaseModel):
    request: str = Field(..., description="Natural language optimization request for CloudAgent")


# --- API Endpoints ---

@app.get("/services", tags=["Services"])
def get_all_services() -> List[Dict[str, Any]]:
    """
    1. GET /services
    Returns state and metrics for all cloud services.
    """
    return simulator.get_services()


@app.get("/services/{service_id}", tags=["Services"])
def get_service_by_id(service_id: str) -> Dict[str, Any]:
    """
    2. GET /services/{service_id}
    Returns detailed state for a specific service by ID.
    Returns HTTP 404 if the service does not exist.
    """
    try:
        return simulator.get_service(service_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@app.get("/services/{service_id}/metrics", tags=["Services"])
def get_service_metrics(service_id: str) -> Dict[str, Any]:
    """
    3. GET /services/{service_id}/metrics
    Returns current workload and health metrics for a specific service.
    Returns HTTP 404 if the service does not exist.
    """
    try:
        service = simulator.get_service(service_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    res = {
        "service_id": service.get("service_id"),
        "cpu_percent": service.get("cpu_percent"),
        "memory_percent": service.get("memory_percent"),
        "requests_per_minute": service.get("requests_per_minute"),
        "latency_ms": service.get("latency_ms"),
        "instances": service.get("instances"),
        "cost_per_hour": service.get("cost_per_hour"),
        "healthy": service.get("healthy"),
        "timestamp": service.get("timestamp"),
    }
    if "history" in service:
        res["history"] = service["history"]
    if "previous_requests_per_minute" in service:
        res["previous_requests_per_minute"] = service["previous_requests_per_minute"]
    if "recent_events" in service:
        res["recent_events"] = service["recent_events"]
    return res


@app.post("/services/{service_id}/scale", tags=["Infrastructure Operations"])
def scale_service(service_id: str, request: ScaleRequest) -> Dict[str, Any]:
    """
    4. POST /services/{service_id}/scale
    Scales a service to target instance count.
    Enforces min_instances <= requested <= max_instances.
    """
    try:
        service = simulator.get_service(service_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    target_instances = request.instances
    min_instances = service.get("min_instances", 1)
    max_instances = service.get("max_instances", 10)

    if target_instances < min_instances:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Scale operation rejected: requested instances ({target_instances}) "
                f"is below minimum allowed capacity limit ({min_instances}) for service '{service_id}'."
            ),
        )

    if target_instances > max_instances:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Scale operation rejected: requested instances ({target_instances}) "
                f"exceeds maximum allowed capacity limit ({max_instances}) for service '{service_id}'."
            ),
        )

    return simulator.scale_service(service_id, target_instances)


@app.post("/services/{service_id}/resize", tags=["Infrastructure Operations"])
def resize_service(service_id: str, request: ResizeRequest) -> Dict[str, Any]:
    """
    5. POST /services/{service_id}/resize
    Resizes a service instance allocation.
    """
    try:
        service = simulator.get_service(service_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    target_instances = request.instances
    min_instances = service.get("min_instances", 1)
    max_instances = service.get("max_instances", 10)

    if target_instances < min_instances:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Resize operation rejected: requested instances ({target_instances}) "
                f"is below minimum allowed capacity limit ({min_instances}) for service '{service_id}'."
            ),
        )

    if target_instances > max_instances:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Resize operation rejected: requested instances ({target_instances}) "
                f"exceeds maximum allowed capacity limit ({max_instances}) for service '{service_id}'."
            ),
        )

    return simulator.scale_service(service_id, target_instances)


@app.post("/services/{service_id}/stop", tags=["Infrastructure Operations"])
def stop_service(service_id: str) -> Dict[str, Any]:
    """
    6. POST /services/{service_id}/stop
    Stops a service safely with deterministic backend checks.
    """
    try:
        service = simulator.get_service(service_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    if not service.get("healthy", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stop operation rejected: service '{service_id}' is currently unhealthy.",
        )

    rpm = service.get("requests_per_minute", 0)
    if rpm > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Stop operation rejected: service '{service_id}' has active incoming traffic "
                f"({rpm} requests per minute)."
            ),
        )

    min_instances = service.get("min_instances", 0)
    if min_instances > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Stop operation rejected: stopping service '{service_id}' would violate "
                f"minimum capacity requirement (min_instances={min_instances})."
            ),
        )

    return simulator.stop_service(service_id)


@app.post("/agent/run", tags=["Agent Operations"])
def run_agent_workflow(body: AgentRunRequest) -> Dict[str, Any]:
    """
    POST /agent/run
    Executes the autonomous CloudAgent workflow for a natural-language request.
    The tool client is explicitly pointed at the same host/port as this server,
    preventing the agent from defaulting to a hardcoded 8000 port when running
    on a different port (e.g. 8001 during testing).
    Returns the complete structured workflow result.
    """
    if CloudAgent is None:
        raise HTTPException(status_code=500, detail="CloudAgent module not available.")

    # Resolve the correct base URL for the agent tool calls:
    # 1. Prefer CLOUD_API_BASE_URL env var (set by caller / CI)
    # 2. Fall back to the port this process is listening on (from SERVER_PORT env var)
    # 3. Final fallback: 8000
    server_port = os.getenv("SERVER_PORT", os.getenv("PORT", "8000"))
    base_url = os.getenv("CLOUD_API_BASE_URL", f"http://127.0.0.1:{server_port}")
    tool_client = CloudApiClient(base_url=base_url) if CloudApiClient else None

    agent = CloudAgent(tool_client=tool_client)
    return agent.run(body.request)


@app.post("/demo/scenario/{scenario_id}", tags=["Demo Controls"])
def load_demo_scenario(scenario_id: str) -> Dict[str, Any]:
    """
    POST /demo/scenario/{scenario_id}
    Loads one of the exact hackathon test scenarios (A, B, C, or D).
    """
    services = simulator.load_scenario(scenario_id)
    return {
        "status": "ok",
        "scenario": scenario_id.upper(),
        "services": services,
    }


@app.post("/demo/reset", tags=["Demo Controls"])
def reset_demo_environment(scenario: Optional[str] = None) -> Dict[str, str]:
    """
    POST /demo/reset
    Controlled demo reset endpoint to restore initial services.json metrics state or current scenario.
    """
    simulator.reset(scenario_id=scenario)
    return {"status": "ok", "message": f"Simulated cloud environment reset to scenario {simulator.current_scenario.upper()} state"}


# --- Static Frontend Serving ---

frontend_path = Path(__file__).resolve().parent.parent / "frontend"

if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/", tags=["Dashboard"])
    def serve_dashboard():
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"status": "ok", "message": "Cloud Simulator API is running"}
else:
    @app.get("/", tags=["Health"])
    def root() -> Dict[str, str]:
        return {"status": "ok", "message": "Cloud Simulator API is running"}
