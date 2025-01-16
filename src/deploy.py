import os
import uuid
import httpx
from pathlib import Path
from web3.auto import w3
from loguru import logger
from  datetime import datetime
from dotenv import load_dotenv
from fastapi import Form, UploadFile, File
from src.agent_service import AgentService
from typing import Optional, Dict, Any, List
from eth_account.messages import encode_defunct
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter, HTTPException, Depends
from src.s3_upload import upload_character_to_s3, upload_knowledge_to_s3
from pydantic import BaseModel, Field, ValidationError, validator, EmailStr
from src.deployment_service import DeploymentService, notify_deployment_server
from src.types import ClientConfig, SignatureRequest, AgentStatus, DeploymentResponse, CheckRegistered
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import RawEncoder
import base58

# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Initialize MongoDB client
mongodb_uri = os.getenv('MONGODB_URI')
token_address = os.getenv('TOKEN_ADDRESS')
balance_threshold = os.getenv('BALANCE_THRESHOLD')

client = AsyncIOMotorClient(mongodb_uri)
db = client.users  # Replace with your database name



deploy_router = APIRouter()

def verify_signature(signature: str, message: str) -> str:
    """
    Verify an Ethereum signature and return the signer's address.
    """
    try:
        # Create the message hash
        message_hash = encode_defunct(text=message)
        
        # Recover the address from the signature
        address = w3.eth.account.recover_message(message_hash, signature=signature)
        
        return address
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        raise HTTPException(status_code=400, message="Invalid signature")


def verify_sol_signature(public_key_base58: str, message: str, signature_base58: str):
    # Decode the base58 public key and signature
    public_key = base58.b58decode(public_key_base58)
    signature = base58.b58decode(signature_base58)

    if len(signature) != 64:
        raise ValueError("The signature must be exactly 64 bytes long.")

    # Create a VerifyKey object from the public key
    verify_key = VerifyKey(public_key, encoder=RawEncoder)

    # Verify the signature
    try:
        verify_key.verify(message.encode(), signature)
        return True
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")



# @deploy_router.post("/register")
# async def register(request: SignatureRequest):
#     """
#     Verify a wallet signature and store the address in MongoDB.
#     """
#     try:
#         # Verify the signature and get the address
#         address = verify_signature(request.signature, request.message)
        
#         # Store in MongoDB
#         result = db.users.update_one(
#             {"address": address},
#             {"$set": {
#                 "address": address,
#                 "last_verified": datetime.utcnow()
#             }},
#             upsert=True
#         )
        
#         return {"address": address, "verified": True}
    
#     except Exception as e:
#         logger.error(f"Error in wallet verification: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))


@deploy_router.post("/register")
async def register(request: SignatureRequest):
    """
    Verify a wallet signature and store the address in MongoDB.
    """
    try:
        # Verify the signature and get the address
        verify_sol_signature(request.public_key, request.message, request.signature)

        # Store in MongoDB
        db.users.update_one(
            {"address": request.public_key},
            {"$set": {
                "address": request.public_key,
                "last_verified": datetime.utcnow()
            }},
            upsert=True
        )
        
        return {"address": request.public_key, "verified": True}
    
    except Exception as e:
        logger.error(f"Error in wallet verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@deploy_router.post("/check_registered")
async def check_registered(request: CheckRegistered):
    """
    Verify a wallet address exists in MongoDB.
    """
    try:
       
        deployment_service = DeploymentService(db)        

        await deployment_service.verify_user(request.public_key)
        
        
        return {"address": request.public_key, "registered": True}
    
    except Exception as e:
        logger.error(f"Error in wallet verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

"""
const formData = new FormData();
formData.append('character_file', jsonFile);  // JSON file
formData.append('signature', signature);
formData.append('message', message);
formData.append('client_twitter', JSON.stringify({ username: 'user', password: 'pass' }));
formData.append('client_discord', JSON.stringify({ username: 'user', password: 'pass' }));
formData.append('client_telegram', 'bot_token');

const response = await fetch('/store_character_data', {
    method: 'POST',
    body: formData
});

"""

@deploy_router.post("/agent/deploy")
async def deploy(
    character: UploadFile = File(...),
    signature: str = Form(...),
    message: str = Form(...),
    public_key: str = Form(...),
    knowledge_files: List[UploadFile] = File(None),
    client_twitter: Optional[str] = Form(None),
    client_discord: Optional[str] = Form(None),
    client_telegram: Optional[str] = Form(None)
) -> Dict:
    """
    Deploy a new agent with character and optional knowledge files.
    
    Args:
        character: Character configuration file
        signature: Signature for verification
        message: Message for verification
        knowledge_files: Optional list of knowledge files
        client_twitter: Optional Twitter client configuration
        client_discord: Optional Discord client configuration
        client_telegram: Optional Telegram client configuration
    
    Returns:
        Dict containing deployment information
    """
    deployment_service = DeploymentService(db)
    agent_service = AgentService(db)
    agent_id = str(uuid.uuid4())
    logger.info(f"agent_id = {agent_id}")
    logger.info(f"signature = {signature}")
    logger.info(f"Message = [{message}]")
    
    try:
        # Verify user and signature
        verify_sol_signature(public_key, message, signature)
        logger.info(f"agent_id = {agent_id} for address {public_key}")
        await deployment_service.verify_user(public_key)
        await agent_service.verify_allowed_agents(public_key)
        # Process character file
        character_content, character_hash, json_content = await deployment_service.process_character_file(character)
        await deployment_service.verify_character_uniqueness(public_key, character_hash)
        await deployment_service.verify_crypto_balance(public_key)
        
        # Upload character to S3
        character_url = await upload_character_to_s3(
            public_key,
            agent_id,
            character_content,
            'application/json'
        )

        # Process knowledge files
        knowledge_urls = []

        if knowledge_files:
            for file in knowledge_files:
                processed_file = await deployment_service.process_knowledge_file(file)
                
                knowledge_url = await upload_knowledge_to_s3(
                    public_key,
                    agent_id,
                    processed_file.content,
                    processed_file.filename,
                    processed_file.content_type
                )
                
                knowledge_urls.append({
                    "filename": processed_file.filename,
                    "content_type": processed_file.content_type,
                    "s3_url": knowledge_url
                })

        # Validate client configuration
        client_config = deployment_service.validate_client_data(
            client_twitter,
            client_discord,
            client_telegram
        )

        # Verify crypto balance

        # Update database
        await update_agent(
            public_key,
            agent_id,
            json_content,
            client_config,
            character_url,
            character_hash,
            knowledge_urls
        )

        await notify_deployment_server(
            agent_id=agent_id,
            character_url=character_url,
            knowledge_files=knowledge_urls,
            client_config=client_config.dict()
        )

        # Return response
        return DeploymentResponse(
            agent_id=agent_id,
            character_url=character_url,
            signature=signature,
            message=message,
            knowledge_files=knowledge_urls
        ).dict()
        
    except HTTPException as he:
        # Re-raise existing HTTP exceptions
        raise he

    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Define request and response models
class AgentStartRequest(BaseModel):
    agent_id: str
    signature: str
    message: str
    public_key: str

@deploy_router.post("/agent/start")
async def start_agent(request: AgentStartRequest):   
    agent_service = AgentService(db)
    deployment_service = DeploymentService(db)
    
    verify_sol_signature(request.public_key, request.message, request.signature)
    await agent_service.verify_agent_ownership(request.public_key, request.agent_id)
    await deployment_service.verify_crypto_balance(request.public_key)
    
    try:
        character_url, knowledge_urls = await agent_service.start_agent(request.agent_id)
         # Return response
        return DeploymentResponse(
            agent_id=request.agent_id,
            character_url=character_url,
            signature=request.signature,
            message=request.message,
            knowledge_files=knowledge_urls
        ).dict()

    except HTTPException as he:
        # Re-raise existing HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Failed to start agent: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


async def update_agent(address: str, agent_id: str, json_content: Any, client_config: ClientConfig, character_s3_url: str, md5_hash: str, s3_url_knowledge_files: List[str]):
    result = db.agents.update_one(
            {"agent_id": agent_id},
            {"$set": {
                "created_at": datetime.utcnow(),
                "character": json_content,
                "version": "v1",
                "bio": json_content["bio"],
                "address": address,
                "client_config": client_config.dict(),
                "character_s3_url": character_s3_url,
                "character_content_md5_hash": md5_hash,                
                "knowledge": s3_url_knowledge_files,
                "status": AgentStatus.RUNNING.value
            }},
            upsert=True
        )
    return


# Define request and response models
class LogRequest(BaseModel):
    agent_id: str

class LogResponse(BaseModel):
    success: bool
    message: str
    logs: str


@deploy_router.post("/agent/logs", response_model=LogResponse)
async def get_logs(request: LogRequest):
    try:
        deployment_server_url = os.getenv("MARLIN_SERVER_URL")
        if not deployment_server_url:
            logger.error("MARLIN_SERVER_URL not configured")
            return
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{deployment_server_url}/logs",
                json={"id": request.agent_id},  # Properly structured payload
                headers={"Content-Type": "application/json"}
            )
            print (response.text)
            response.raise_for_status()
            logger.info(f"Successfully retrieved logs for id {request.agent_id}")
            
            return LogResponse(
                success=True,
                message="Logs retrieved successfully",
                logs=response.text
            )
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to retrieve logs: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# Define request and response models
class AgentShutdownRequest(BaseModel):
    agent_id: str
    signature: str
    message: str
    public_key: str

class AgentShutdownResponse(BaseModel):
    success: bool
    message: str


@deploy_router.post("/agent/shutdown", response_model=AgentShutdownResponse)
async def shutdown_agent(request: AgentShutdownRequest):
    agent_service = AgentService(db)
    
    verify_sol_signature(request.public_key, request.message, request.signature)
    await agent_service.verify_agent_ownership(request.public_key, request.agent_id)
    try:
        deployment_server_url = os.getenv("MARLIN_SERVER_URL")
        if not deployment_server_url:
            logger.error("MARLIN_SERVER_URL not configured")
            return
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{deployment_server_url}/stop",
                json={"id": request.agent_id},  # Properly structured payload
                headers={"Content-Type": "application/json"}
            )
            print(response.status_code)
            response.raise_for_status()
            await agent_service.stop_agent(request.agent_id)
            return AgentShutdownResponse(
                success=True,
                message="Agent removed successfully"
            )

    except HTTPException as he:
        # Re-raise existing HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# Define request and response models
class GetAgentsRequest(BaseModel):
    address: str

# Define request and response models
class GetAgentsResponse(BaseModel):
    address: str
    agents: List[Dict[str, Any]]  # This will accept any object structure


@deploy_router.post("/agent/all", response_model=GetAgentsResponse)
async def get_agents(request: GetAgentsRequest):
    try:
        agent_service = AgentService(db)
        deployment_service = DeploymentService(db)
        await deployment_service.verify_user(request.address)

        agents = await agent_service.get_agents(request.address)
        return GetAgentsResponse(
            address=request.address,
            agents=agents
        )
        
    except HTTPException as he:
        # Re-raise existing HTTP exceptions
        raise he

    except Exception as e:
        logger.error(f"Error retrieving agents: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to retrieve agents: {str(e)}"
        )