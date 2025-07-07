from . import BaseConnector, asyncio, Any, Optional

class ShopifyConnector(BaseConnector):
    def __init__(self, config: dict):
        super().__init__(config)
        self.connector_type = "Shopify"

    async def fetch_products(self, collection_id: Optional[str] = None) -> dict:
        if not self.connected:
            return {"error": "Shopify not connected"}
        await asyncio.sleep(0.1)
        return {
            "source": self.connector_type,
            "data_type": "Products",
            "filter_collection_id": collection_id,
            "products": [
                {"id": f"sh_prod_{random.randint(10000,99999)}", "title": f"Awesome T-Shirt {random.choice(['Red', 'Blue', 'Green'])}", "vendor": "MyBrand", "price": f"{random.uniform(19.99, 49.99):.2f}"},
                {"id": f"sh_prod_{random.randint(10000,99999)}", "title": f"Cool Hat {random.choice(['Snapback', 'Beanie'])}", "vendor": "TheirBrand", "price": f"{random.uniform(15.00, 30.00):.2f}"}
            ]
        }

    async def fetch_orders(self, status: str = "any", limit: int = 10) -> dict:
        if not self.connected:
            return {"error": "Shopify not connected"}
        await asyncio.sleep(0.15)
        orders = []
        for _ in range(limit):
            orders.append({
                "id": f"sh_ord_{random.randint(100000,999999)}",
                "order_number": random.randint(1001, 5001),
                "total_price": f"{random.uniform(20.00, 500.00):.2f}",
                "status": random.choice(["fulfilled", "pending", "partially_fulfilled", "cancelled"]),
                "customer_name": f"Customer {random.randint(1,100)}"
            })
        return {
            "source": self.connector_type,
            "data_type": "Orders",
            "filter_status": status,
            "limit": limit,
            "orders": orders
        }

    async def fetch_data(self, data_type: str, params: Optional[dict] = None) -> Any:
        if not self.connected:
            return {"error": f"{self.connector_type} not connected"}

        print(f"Shopify: Fetching mock {data_type} with params: {params}")
        params = params or {}
        if data_type == "products":
            return await self.fetch_products(collection_id=params.get("collection_id"))
        elif data_type == "orders":
            return await self.fetch_orders(status=params.get("status", "any"), limit=params.get("limit", 10))
        else:
            return await super().fetch_data(data_type, params)

import random # For mock data generation
