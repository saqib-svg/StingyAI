import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class CloudSimulator:
    """
    Simulated stateful cloud environment that tracks service configurations,
    workload metrics, resource usage, and cost allocations.

    State is loaded initially from services.json and maintained entirely
    in memory for subsequent reads and state mutations.
    """

    def __init__(self, data_file: Optional[str] = None):
        """
        Initialize the simulator by loading service states into memory.

        :param data_file: Optional custom file path to services.json
        """
        base_dir = Path(__file__).resolve().parent.parent
        self.data_dir = base_dir / "data"

        if data_file is None:
            data_file = str(self.data_dir / "services.json")

        self.data_path = Path(data_file)
        self.current_scenario: str = "a"
        self._services: Dict[str, Dict[str, Any]] = {}
        self._load_initial_state()

    def _load_initial_state(self) -> None:
        """Loads service records from services.json or scenario fixture into memory state."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Services data file not found at: {self.data_path}")

        with open(self.data_path, "r", encoding="utf-8") as f:
            services_list = json.load(f)

        for service in services_list:
            service_id = service.get("service_id")
            if service_id:
                # Deep copy dict to isolate runtime state mutations
                self._services[service_id] = json.loads(json.dumps(service))

    def load_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        Loads state from a specific scenario fixture (a, b, c, or d).
        """
        clean_key = scenario_id.strip().lower()
        if clean_key.startswith("scenario"):
            clean_key = clean_key.replace("scenario", "").strip().lower()

        target_file = self.data_dir / f"services_{clean_key}.json"
        if not target_file.exists():
            target_file = self.data_dir / "services.json"

        self.data_path = target_file
        self.current_scenario = clean_key
        self.reset()
        return self.get_services()

    def get_services(self) -> List[Dict[str, Any]]:
        """
        Returns a list of current metrics and states for all managed cloud services.
        """
        return list(self._services.values())

    def get_service(self, service_id: str) -> Dict[str, Any]:
        """
        Returns state for a specific service by service_id.
        Raises ValueError if service_id is invalid or missing.
        """
        if service_id not in self._services:
            raise ValueError(f"Service with id '{service_id}' not found in cloud environment.")
        return self._services[service_id]

    # --- Future Action Methods (Prepared for upcoming agent tools) ---

    def scale_service(self, service_id: str, target_instances: int) -> Dict[str, Any]:
        """
        Scales service instances up or down within min/max boundaries.
        State is updated in memory immediately.
        """
        service = self.get_service(service_id)

        min_i = service.get("min_instances", 1)
        max_i = service.get("max_instances", 10)

        if not (min_i <= target_instances <= max_i):
            raise ValueError(
                f"Cannot scale '{service_id}' to {target_instances} instances. "
                f"Allowed bounds: [{min_i}, {max_i}]."
            )

        service["instances"] = target_instances
        return service

    def resize_service(
        self,
        service_id: str,
        cpu_percent: Optional[float] = None,
        memory_percent: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Updates resource utilization parameters for a service in memory state.
        """
        service = self.get_service(service_id)
        if cpu_percent is not None:
            service["cpu_percent"] = cpu_percent
        if memory_percent is not None:
            service["memory_percent"] = memory_percent
        return service

    def stop_service(self, service_id: str) -> Dict[str, Any]:
        """
        Stops a service by setting instances to 0 and healthy status to False.
        """
        service = self.get_service(service_id)
        service["instances"] = 0
        service["healthy"] = False
        return service

    def reset(self, scenario_id: Optional[str] = None) -> None:
        """
        Resets the in-memory cloud simulator state back to initial values loaded from services.json or scenario fixture.
        Used exclusively for controlled test fixtures and demo resets.
        """
        if scenario_id:
            clean_key = scenario_id.strip().lower()
            if clean_key.startswith("scenario"):
                clean_key = clean_key.replace("scenario", "").strip().lower()
            target_file = self.data_dir / f"services_{clean_key}.json"
            if target_file.exists():
                self.data_path = target_file
                self.current_scenario = clean_key

        self._services.clear()
        self._load_initial_state()

