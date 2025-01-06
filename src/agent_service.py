import json
from loguru import logger
from fastapi import HTTPException
from src.types import AgentStatus, ClientConfig, DeploymentResponse
from src.deployment_service import DeploymentService, notify_deployment_server

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
            logger.error(f"{address} havent deployed any agents")
            raise HTTPException(status_code=404, detail=f"User {address} must deploy agents first")
            
        logger.info(f"Found {len(agents)} agents for address {address}")
        return agents

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

    async def start_agent(self, address:str, message:str, signature:str, agent_id: str, client_configs: dict) -> None:
        """Start an agent with the given agent_id and client configurations"""
        agent = await self.db.agents.find_one({"agent_id": agent_id})
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} doesn't exist")


        # Validate client configurations
        try:
            client_config = ClientConfig(**client_configs)
        except Exception as e:
            logger.error(f"Error in validating client configurations: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid client configuration")

        # Start the agent (assuming DeploymentService has a method to start an agent)
        deployment_service = DeploymentService(self.db)
        

        logger.info(f"Agent {agent_id} has been started successfully")
        
        # Retrieve character_url and knowledge_urls from the agent document
        character_url = agent.get("character_s3_url")
        knowledge_urls = agent.get("knowledge", [])
        
        deployment_notified = await notify_deployment_server(
            agent_id=agent_id,
            character_url=character_url,
            knowledge_files=knowledge_urls,
            client_config=client_config.dict()
        )
        if not deployment_notified:
            raise HTTPException(status_code=500, detail="Failed to start agent")
        
        agent = await self.db.agents.update_one({"agent_id": agent_id}, {"$set": {"status": AgentStatus.RUNNING.value}}, upsert=False)
        logger.info(f"Agent {agent_id} has been started successfully")
        # Return response
        return DeploymentResponse(
            agent_id=agent_id,
            character_url=character_url,
            signature=signature,
            message=message,
            knowledge_files=knowledge_urls
        ).dict()
