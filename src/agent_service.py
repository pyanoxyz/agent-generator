import json
from loguru import logger
from fastapi import HTTPException
from src.types import AgentStatus, ClientConfig
from src.deployment_service import DeploymentService, notify_deployment_server
from pathlib import Path
import os
from dotenv import load_dotenv
# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')


allowed_agents = os.getenv('ALLOWED_AGENTS')
env = os.getenv('ENV')


class AgentService:
    def __init__(self, db):
        self.db = db
        
    async def get_agents(self, address: str) -> None:
        """Verify if user exists in database"""
        cursor = self.db.agents.find({"address": address}, {"_id": 0, "character_content_md5_hash": 0, "client_config": 0})
        agents = []
        
        async for agent in cursor:
            agents.append(agent)

        logger.info(f"Found {len(agents)} agents for address {address}")
        return agents

    async def verify_allowed_agents(self, address: str) -> None:
        """Verify if user exists in database"""
        query = {
            "address": address,
            "status": AgentStatus.RUNNING.value
        }
        count = await self.db.agents.count_documents(query)
        # Uncomment and modify as needed
        if env == "production":
            if count >= int(allowed_agents):
                raise HTTPException(status_code=403, detail=f"Only {allowed_agents} running agents are allowed at this moment")
        return
    

    async def verify_agent_ownership(self, address: str, agent_id: str) -> None:
        """Verify if user exists in database"""
        
        agent = await self.db.agents.find_one({"agent_id": agent_id})
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} doesnt exists")
        if address != agent["address"]:
            raise HTTPException(status_code=403, detail=f"{address} doesnt own Agent {agent_id}")
        logger.info(f"Agent {agent_id} with owstop{address} exists")
        return

    async def stop_agent(self, agent_id: str) -> None:
        """Verify if user exists in database"""
        
        agent = await self.db.agents.update_one({"agent_id": agent_id}, {"$set": {"status": AgentStatus.STOPPED.value}}, upsert=False)
        logger.info(f"Agent {agent_id} has been removed successfully")
        return

    async def start_agent(self, agent_id: str) -> None:
        """Start an agent with the given agent_id and client configurations"""
        agent = await self.db.agents.find_one({"agent_id": agent_id})
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} doesn't exist")

        if agent["status"] == AgentStatus.RUNNING.value:
            raise HTTPException(status_code=409, detail=f"Agent {agent_id} already running")

        # # Validate client configurations
        # try:
        #     client_config = ClientConfig(**client_configs)
        # except Exception as e:
        #     logger.error(f"Error in validating client configurations: {str(e)}")
        #     raise HTTPException(status_code=400, detail="Invalid client configuration")

        # Start the agent (assuming DeploymentService has a method to start an agent)
        # Retrieve character_url and knowledge_urls from the agent document
        character_url = agent.get("character_s3_url")
        knowledge_urls = agent.get("knowledge", [])
        
        deployment_notified = await notify_deployment_server(
            agent_id=agent_id,
            character_url=character_url,
            knowledge_files=knowledge_urls,
            client_config=agent["client_config"]
        )
        if not deployment_notified:
            raise HTTPException(status_code=500, detail="Failed to start agent")
        
        agent = await self.db.agents.update_one({"agent_id": agent_id}, {"$set": {"status": AgentStatus.RUNNING.value}}, upsert=False)
        logger.info(f"Agent {agent_id} has been started successfully")
        # Return response
        return character_url, knowledge_urls
