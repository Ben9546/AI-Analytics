# This file makes 'connectors' a Python sub-package of 'services'.
from typing import Any, Optional, List, Dict # Ensure these are at the top
import asyncio # Keep asyncio import as it's used

# Base Connector (conceptual, can be expanded)
class BaseConnector:
    def __init__(self, config: dict):
        self.config = config
        self.connected = False
        print(f"Initializing connector {self.__class__.__name__} with config: {config.get('name', 'Unknown')}")

    async def connect(self) -> bool:
        print(f"Attempting to connect for {self.config.get('name', self.__class__.__name__)}...")
        # Simulate connection attempt
        await asyncio.sleep(0.1) # Simulate network delay
        self.connected = True # Mock successful connection
        print(f"Successfully connected for {self.config.get('name', self.__class__.__name__)}.")
        return True

    async def disconnect(self):
        print(f"Disconnecting for {self.config.get('name', self.__class__.__name__)}...")
        self.connected = False
        await asyncio.sleep(0.05)
        print(f"Disconnected for {self.config.get('name', self.__class__.__name__)}.")

    async def fetch_data(self, data_type: str, params: Optional[Dict[str, Any]] = None) -> Any: # Use Dict[str, Any] for params
        if not self.connected:
            print(f"Error: Not connected. Cannot fetch {data_type} for {self.config.get('name', self.__class__.__name__)}.")
            return {"error": "Not connected"}

        print(f"Fetching mock {data_type} for {self.config.get('name', self.__class__.__name__)} with params: {params}")
        await asyncio.sleep(0.2) # Simulate data fetching
        return {"mock_data_type": data_type, "source": self.config.get('name', self.__class__.__name__), "data": f"Sample {data_type} data", "params_received": params}

    async def get_status(self) -> Dict[str, Any]: # Use Dict[str, Any] for return type
        return {
            "name": self.config.get('name', self.__class__.__name__),
            "type": self.config.get('type', 'unknown'),
            "connected": self.connected,
            "last_synced": "N/A (mock)" # In real app, track last sync time
        }

# `asyncio`, `Any`, `Optional`, `List`, `Dict` are now imported at the top.
