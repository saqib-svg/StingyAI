"""
Cloud Agent Tool Layer.

Provides structured tool functions wrapping REST API requests to the FastAPI backend.
Designed for consumption by future AI agents.

All tools return a consistent response format:
{
    "success": bool,
    "data": Dict | List | None,
    "error": str | None
}
"""

import os
from typing import Dict, List, Any, Optional
import httpx


class CloudApiClient:
    """
    Reusable HTTP Client wrapper for communicating with the FastAPI Cloud API.
    Supports custom base URLs and custom httpx.Client instances (e.g. ASGI transport).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ):
        if base_url is None:
            base_url = os.getenv("CLOUD_API_BASE_URL", "http://127.0.0.1:8000")
        
        self.base_url = base_url.rstrip("/")
        self._custom_client = client

    def _get_client(self) -> httpx.Client:
        if self._custom_client is not None:
            return self._custom_client
        return httpx.Client(base_url=self.base_url, timeout=10.0)

    def _format_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Formats an HTTP response into a standardized agent dictionary."""
        if response.is_success:
            return {
                "success": True,
                "data": response.json(),
                "error": None,
            }
        
        try:
            payload = response.json()
            error_msg = payload.get("detail", response.text)
        except Exception:
            error_msg = response.text or f"HTTP {response.status_code} Error"

        return {
            "success": False,
            "data": None,
            "error": error_msg,
        }

    def get(self, endpoint: str) -> Dict[str, Any]:
        """Performs a GET request to the specified endpoint."""
        url = f"{self.base_url}{endpoint}"
        try:
            client = self._get_client()
            # If using custom client (e.g. TestClient/ASGI), pass relative path or full url
            if self._custom_client:
                res = client.get(endpoint)
            else:
                with client:
                    res = client.get(url)
            return self._format_response(res)
        except httpx.RequestError as e:
            return {
                "success": False,
                "data": None,
                "error": f"API connection failed: {str(e)}",
            }

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Performs a POST request to the specified endpoint."""
        url = f"{self.base_url}{endpoint}"
        try:
            client = self._get_client()
            if self._custom_client:
                res = client.post(endpoint, json=json_data)
            else:
                with client:
                    res = client.post(url, json=json_data)
            return self._format_response(res)
        except httpx.RequestError as e:
            return {
                "success": False,
                "data": None,
                "error": f"API connection failed: {str(e)}",
            }


# Shared default client instance
_default_client: Optional[CloudApiClient] = None


def get_default_client() -> CloudApiClient:
    global _default_client
    if _default_client is None:
        _default_client = CloudApiClient()
    return _default_client


# --- Agent Tools ---

def get_all_services(client: Optional[CloudApiClient] = None) -> Dict[str, Any]:
    """
    Tool: Retrieve state and metrics for all cloud services.
    Calls: GET /services
    """
    api_client = client or get_default_client()
    return api_client.get("/services")


def get_service(service_id: str, client: Optional[CloudApiClient] = None) -> Dict[str, Any]:
    """
    Tool: Retrieve full details for a specific service by ID.
    Calls: GET /services/{service_id}
    """
    api_client = client or get_default_client()
    return api_client.get(f"/services/{service_id}")


def get_service_metrics(service_id: str, client: Optional[CloudApiClient] = None) -> Dict[str, Any]:
    """
    Tool: Retrieve key performance and resource metrics for a service.
    Calls: GET /services/{service_id}/metrics
    """
    api_client = client or get_default_client()
    return api_client.get(f"/services/{service_id}/metrics")


def scale_service(service_id: str, instances: int, client: Optional[CloudApiClient] = None) -> Dict[str, Any]:
    """
    Tool: Request a scaling operation for a service to a target instance count.
    Calls: POST /services/{service_id}/scale
    """
    api_client = client or get_default_client()
    return api_client.post(f"/services/{service_id}/scale", json_data={"instances": instances})


def resize_service(service_id: str, instances: int, client: Optional[CloudApiClient] = None) -> Dict[str, Any]:
    """
    Tool: Request a resource resize operation for a service instance count.
    Calls: POST /services/{service_id}/resize
    """
    api_client = client or get_default_client()
    return api_client.post(f"/services/{service_id}/resize", json_data={"instances": instances})


def stop_service(service_id: str, client: Optional[CloudApiClient] = None) -> Dict[str, Any]:
    """
    Tool: Request stopping a service safely.
    Calls: POST /services/{service_id}/stop
    """
    api_client = client or get_default_client()
    return api_client.post(f"/services/{service_id}/stop")
