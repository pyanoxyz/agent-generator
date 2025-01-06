
import json
from loguru import logger


class AgentService:
    def __init__(self, db):
        self.db = db
        
    async def get_agents(self, address: str) -> None:
        """Verify if user exists in database"""
        cursor = self.db.agents.find({"address": address}, {"_id": 0, "character_content_md5_hash": 0, "client": 0})
        agents = []
        
        async for agent in cursor:
            agents.append(agent)
            
        if not agents:
            logger.error(f"User {address} must register first")
            raise HTTPException(status_code=400, detail=f"User {address} must register first")
            
        logger.info(f"Found {len(agents)} agents for address {address}")
        return agents

    async def verify_agent_ownership(self, address: str, agent_id: str) -> None:
        """Verify if user exists in database"""
        
        agent = await self.db.agents.find_one({"agent_id": agent_id})
        if not agent:
            raise HTTPException(status_code=400, detail=f"Agent {agent_id} doesnt exists")
        if address != agent["address"]:
            raise HTTPException(status_code=400, detail=f"{address} doesnt own Agent {agent_id}")
        logger.info(f"Agent {agent_id} with owstop{address} exists")
        return

    async def stop_agent(self, agent_id: str) -> None:
        """Verify if user exists in database"""
        
        agent = await self.db.agents.update_one({"agent_id": agent_id}, {"$set": {"status": AgentStatus.STOPPED}}, upsert=False)
        logger.info(f"Agent {agent_id} has been removed successfully")
        return