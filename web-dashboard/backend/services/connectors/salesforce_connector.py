from . import BaseConnector, asyncio, Any, Optional

class SalesforceConnector(BaseConnector):
    def __init__(self, config: dict):
        super().__init__(config)
        self.connector_type = "Salesforce"

    async def fetch_opportunities(self, stage: str = "any") -> dict:
        if not self.connected:
            return {"error": "Salesforce not connected"}
        await asyncio.sleep(0.1)
        return {
            "source": self.connector_type,
            "data_type": "Opportunities",
            "filter_stage": stage,
            "opportunities": [
                {"id": f"sf_opp_{random.randint(1000,9999)}", "name": f"Big Deal {random.randint(1,100)}", "stage": random.choice(["Prospecting", "Qualification", "Proposal", "Closed Won", "Closed Lost"]), "amount": round(random.uniform(10000, 100000),2)},
                {"id": f"sf_opp_{random.randint(1000,9999)}", "name": f"Small Project {random.randint(1,100)}", "stage": random.choice(["Prospecting", "Qualification", "Proposal", "Closed Won", "Closed Lost"]), "amount": round(random.uniform(1000, 20000),2)}
            ]
        }

    async def fetch_accounts(self, account_type: str = "all") -> dict:
        if not self.connected:
            return {"error": "Salesforce not connected"}
        await asyncio.sleep(0.15)
        return {
            "source": self.connector_type,
            "data_type": "Accounts",
            "filter_type": account_type,
            "accounts": [
                {"id": f"sf_acc_{random.randint(100,999)}", "name": f"Global Corp {random.randint(1,10)}", "type": random.choice(["Customer", "Partner", "Prospect"])},
                {"id": f"sf_acc_{random.randint(100,999)}", "name": f"Local Biz {random.randint(1,10)}", "type": random.choice(["Customer", "Partner", "Prospect"])}
            ]
        }

    async def fetch_data(self, data_type: str, params: Optional[dict] = None) -> Any:
        if not self.connected:
            return {"error": f"{self.connector_type} not connected"}

        print(f"Salesforce: Fetching mock {data_type} with params: {params}")
        if data_type == "opportunities":
            return await self.fetch_opportunities(stage=params.get("stage", "any") if params else "any")
        elif data_type == "accounts":
            return await self.fetch_accounts(account_type=params.get("type", "all") if params else "all")
        else:
            return await super().fetch_data(data_type, params)

import random # For mock data generation
