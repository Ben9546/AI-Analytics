from . import BaseConnector
import time

# In a real scenario, you'd use a library like 'ShopifyAPI'
# import shopify

class ShopifyConnector(BaseConnector):
    def __init__(self, shop_url: str, api_key: str, password: str, api_version: str = "2023-10"):
        # shop_url is like 'your-store-name.myshopify.com'
        # api_key and password are from the private app credentials
        super().__init__(api_key=api_key, api_secret=password) # Using password as api_secret
        self.shop_url = shop_url
        self.api_version = api_version
        self.session = None # Placeholder for the Shopify session/client

    def connect(self):
        print(f"Connecting to Shopify store: {self.shop_url} using API version {self.api_version}...")
        try:
            # Example using ShopifyAPI library:
            # shopify.ShopifyResource.set_site(f"https://{self.api_key}:{self.api_secret}@{self.shop_url}/admin/api/{self.api_version}")
            # shopify.ShopifyResource.activate_session(shopify.Session(self.shop_url, self.api_version, self.api_secret)) # Or use access token for public apps
            # self.session = shopify # Or the activated session object
            # print("Successfully connected to Shopify.")

            # Mock connection
            self.session = "mock_shopify_session"
            print("Successfully connected to Shopify (mock).")
            return True
        except Exception as e:
            print(f"Failed to connect to Shopify: {e}")
            self.session = None
            return False

    def fetch_data(self, resource_type: str, params: dict = None):
        if not self.session:
            print("Not connected to Shopify. Call connect() first.")
            return None

        print(f"Fetching {resource_type} from Shopify with params: {params if params else {}}")

        # Mock data based on resource_type
        if resource_type.lower() == "products":
            # In real Shopify API, you'd call: shopify.Product.find(limit=params.get('limit', 50))
            return [{"id": 123, "title": "Awesome T-Shirt", "vendor": "MyBrand", "product_type": "Apparel"},
                    {"id": 124, "title": "Cool Hat", "vendor": "MyBrand", "product_type": "Accessory"}]
        elif resource_type.lower() == "orders":
            # shopify.Order.find(status='any', limit=params.get('limit', 50))
            return [{"id": 456, "order_number": 1001, "total_price": "50.00", "customer": {"first_name": "John", "last_name": "Doe"}},
                    {"id": 457, "order_number": 1002, "total_price": "75.00", "customer": {"first_name": "Jane", "last_name": "Smith"}}]
        elif resource_type.lower() == "customers":
            # shopify.Customer.find(limit=params.get('limit', 50))
            return [{"id": 789, "first_name": "John", "last_name": "Doe", "email": "john.doe@example.com"},
                    {"id": 790, "first_name": "Jane", "last_name": "Smith", "email": "jane.smith@example.com"}]
        else:
            print(f"Resource type '{resource_type}' not mocked yet.")
            return []

    def get_all_data(self, resource_type: str, limit_per_page=50, max_pages=None):
        """
        Fetches all data for a given resource type, handling pagination.
        """
        if not self.session:
            print("Not connected to Shopify. Call connect() first.")
            return None

        print(f"Fetching all {resource_type} from Shopify...")
        all_items = []
        page = 1

        # Mock pagination
        while True:
            print(f"Fetching page {page} for {resource_type}...")
            # params = {'limit': limit_per_page, 'page': page} # Real Shopify uses 'page_info' for cursor-based pagination
            # For mock, we'll just simulate a couple of pages
            if page == 1:
                if resource_type.lower() == "products":
                    items = [{"id": 123, "title": "Awesome T-Shirt"}, {"id": 124, "title": "Cool Hat"}]
                elif resource_type.lower() == "orders":
                     items = [{"id": 456, "order_number": 1001}, {"id": 457, "order_number": 1002}]
                else:
                    items = []
            elif page == 2 and resource_type.lower() == "products": # Simulate more products
                 items = [{"id": 125, "title": "Another T-Shirt"}, {"id": 126, "title": "Another Hat"}]
            else: # No more items for other types or further pages in mock
                items = []

            if not items:
                break

            all_items.extend(items)
            page += 1
            if max_pages and page > max_pages:
                print(f"Reached max_pages limit of {max_pages}.")
                break

            # Simulate API rate limit delay
            # time.sleep(0.5) # Shopify API has rate limits

        print(f"Fetched a total of {len(all_items)} {resource_type}.")
        return all_items

    def close(self):
        print("Closing Shopify connection.")
        if self.session:
            # In real ShopifyAPI: shopify.ShopifyResource.clear_session()
            self.session = None
        pass

# Example Usage:
if __name__ == "__main__":
    SHOPIFY_SHOP_URL = "your-store-name.myshopify.com"
    SHOPIFY_API_KEY = "your_shopify_api_key"
    SHOPIFY_PASSWORD = "your_shopify_app_password" # This is the Admin API access token for private apps

    with ShopifyConnector(shop_url=SHOPIFY_SHOP_URL, api_key=SHOPIFY_API_KEY, password=SHOPIFY_PASSWORD) as shopify_conn:
        products = shopify_conn.fetch_data("products", params={"limit": 2})
        if products:
            print("\nShopify Products (first page/limit 2):")
            for p in products:
                print(p)

        all_orders = shopify_conn.get_all_data("orders", max_pages=1) # Mocking only 1 page of orders
        if all_orders:
            print(f"\nAll Shopify Orders (mocked {len(all_orders)}):")
            for o in all_orders:
                print(o)

        all_products = shopify_conn.get_all_data("products", max_pages=2) # Mocking 2 pages of products
        if all_products:
            print(f"\nAll Shopify Products (mocked {len(all_products)}):")
            for p in all_products:
                print(p)
