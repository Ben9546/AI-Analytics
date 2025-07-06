# Data Connectors
# This package will contain modules for connecting to various data sources.

# Example structure:
# - quickbooks_connector.py
# - salesforce_connector.py
# - shopify_connector.py
# ... and so on for other integrations.

# Each connector module will typically have:
# - Functions to authenticate with the respective API.
# - Functions to fetch relevant data (e.g., sales, customers, products).
# - Functions to handle pagination and rate limiting.
# - Data transformation logic to a standardized format if needed.

# A base connector class or interface might be defined here to ensure consistency.

class BaseConnector:
    def __init__(self, api_key: str, api_secret: str = None, other_config: dict = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = other_config if other_config else {}
        # Initialize HTTP client or SDK specific to the service

    def connect(self):
        """Establishes a connection or authenticates with the data source."""
        raise NotImplementedError

    def fetch_data(self, endpoint: str, params: dict = None):
        """Fetches data from a specific endpoint of the data source."""
        raise NotImplementedError

    def get_all_data(self, data_type: str):
        """Fetches all relevant data for a given type (e.g., 'orders', 'customers')."""
        raise NotImplementedError

    def close(self):
        """Closes any open connections or resources."""
        pass # Optional, if needed

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
