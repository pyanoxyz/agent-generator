import os
import re
import io
import uuid
import json
import magic
import boto3
import httpx
import hashlib
import mimetypes
import fitz
from PIL import Image
from web3 import Web3
from web3.auto import w3
from loguru import logger
from pathlib import Path
from  datetime import datetime
from dotenv import load_dotenv
from typing import List, Optional
from typing import Optional, Dict
from fastapi import Form, UploadFile, File
from botocore.exceptions import ClientError
from eth_account.messages import encode_defunct
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ValidationError
from src.get_balance import get_account_balance, get_token_balance
from src.s3_upload import upload_character_to_s3, upload_knowledge_to_s3



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


class SignatureRequest(BaseModel):
    signature: str = Field(..., description="Signature is required")
    message: str = Field(..., description="Message is required")



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

@deploy_router.post("/register")
async def register(request: SignatureRequest):
    """
    Verify a wallet signature and store the address in MongoDB.
    """
    try:
        # Verify the signature and get the address
        address = verify_signature(request.signature, request.message)
        
        # Store in MongoDB
        result = db.users.update_one(
            {"address": address},
            {"$set": {
                "address": address,
                "last_verified": datetime.utcnow()
            }},
            upsert=True
        )
        
        return {"address": address, "verified": True}
    
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
class ClientConfig(BaseModel):
    twitter: Optional[Dict[str, str]]=None
    discord: Optional[Dict[str, str]]=None
    telegram: Optional[Dict[str, str]]=None


# Models
class KnowledgeFile:
    def __init__(self, filename: str, content: Dict, content_type: str):
        self.filename = filename
        self.content = content
        self.content_type = content_type

class DeploymentResponse:
    def __init__(
        self,
        agent_id: str,
        character_url: str,
        client_config: Dict,
        signature: str,
        message: str,
        knowledge_files: List[Dict]
    ):
        self.agent_id = agent_id
        self.character_url = character_url
        self.client_config = client_config
        self.signature = signature
        self.message = message
        self.knowledge_files = knowledge_files

    def dict(self):
        return {
            "agent_id": self.agent_id,
            "character": self.character_url,
            "client": self.client_config,
            "signature": self.signature,
            "message": self.message,
            "knowledge_files": self.knowledge_files
        }

class DeploymentService:
    def __init__(self, db):
        self.db = db

    async def verify_user(self, address: str) -> None:
        """Verify if user exists in database"""
        user = await self.db.users.find_one({"address": address})
        print(user)
        if not user:
            logger.error(f"User {address} must register first")
            raise HTTPException(status_code=400, detail=f"User {address} must register first")
        logger.info(f"User {address} is registered")
        return
    
    async def verify_agent_ownership(self, address: str, agent_id: str) -> None:
        """Verify if user exists in database"""
        
        agent = await self.db.agents.find_one({"agent_id": agent_id})
        if not agent:
            raise HTTPException(status_code=400, detail=f"Agent {agent_id} doesnt exists")
        if address != agent["address"]:
            raise HTTPException(status_code=400, detail=f"{address} doesnt own Agent {agent_id}")
        logger.info(f"Agent {agent_id} with owstop{address} exists")
        return

    async def delete_agent(self, agent_id: str) -> None:
        """Verify if user exists in database"""
        
        agent = await self.db.agents.delete_one({"agent_id": agent_id})
        logger.info(f"Agent {agent_id} has been removed successfully")
        return



    async def verify_character_uniqueness(self, address: str, content_hash: str) -> None:
        """Check if character already exists"""
        if await find_character_json(address, content_hash):
            raise HTTPException(
                status_code=409,
                detail="Agent has already been deployed or deployment in process"
            )

    async def process_character_file(self, character: UploadFile) -> tuple[bytes, str]:
        """Process and validate character file"""
        try:
            content = await character.read()
            content_hash = hashlib.md5(content).hexdigest()
            
            try:
                json.loads(content.decode())
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in character file")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Character file must be UTF-8 encoded JSON")
            
            return content, content_hash
        finally:
            await character.close()

    async def process_knowledge_file(self, file: UploadFile) -> KnowledgeFile:
        """Process a single knowledge file"""
        try:
            content = await file.read()
            
            # Get file type using mimetypes
            file_type, _ = mimetypes.guess_type(file.filename)
            if not file_type:
                file_type = 'application/octet-stream'
            
            json_filename = Path(file.filename).stem + '.json'

            if file_type == 'application/pdf':
                paragraphs = await extract_paragraphs_from_pdf(content)
                file_content = {"documents": paragraphs}
                logger.info(f"Successfully extracted {len(paragraphs)} paragraphs from {file.filename}")
            else:
                # For non-PDF files, store content as is
                file_content = {"documents": [content.decode('utf-8', errors='ignore')]}                
                logger.info(f"Processed file {file.filename} as {file_type}")
            print (file_content)
                
            return KnowledgeFile(
                filename=json_filename,
                content=file_content,
                content_type="application/json"
            )
        finally:
            await file.close()


    def validate_client_data(self, twitter: Optional[str], discord: Optional[str], telegram: Optional[str]) -> Dict:
        """Validate and process client configuration data"""
        client_data = {}
        
        for client_type, client_value in [
            ("twitter", twitter),
            ("discord", discord),
            ("telegram", telegram)
        ]:
            if client_value:
                try:
                   client_data[client_type] = json.loads(client_value)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid JSON in client_{client_type}"
                    )

        try:
            return ClientConfig(**client_data)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid client configuration")

    async def verify_crypto_balance(self, address: str) -> None:
        """Verify crypto balance meets threshold"""
        balance = get_token_balance(address, token_address) if token_address else get_account_balance(address)
        logger.success(f"{address} BALANCE is {balance}")
        
        # Uncomment and modify as needed
        # if balance < float(balance_threshold):
        #     raise HTTPException(status_code=400, detail=f"Insufficient balance: {balance}")


@deploy_router.post("/deploy")
async def deploy(
    character: UploadFile = File(...),
    signature: str = Form(...),
    message: str = Form(...),
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
    agent_id = str(uuid.uuid4())
    logger.info(f"agent_id = {agent_id}")
    
    try:
        # Verify user and signature
        address = verify_signature(signature, message)
        logger.info(f"agent_id = {agent_id} for address {address}")
        await deployment_service.verify_user(address)

        # Process character file
        character_content, character_hash = await deployment_service.process_character_file(character)
        await deployment_service.verify_character_uniqueness(address, character_hash)
        
        # Upload character to S3
        character_url = await upload_character_to_s3(
            address,
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
                    address,
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
        await deployment_service.verify_crypto_balance(address)

        # Update database
        await update_agent(
            address,
            agent_id,
            character_url,
            character_hash,
            knowledge_urls,
            client_config
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
            client_config=client_config.dict(),
            signature=signature,
            message=message,
            knowledge_files=knowledge_urls
        ).dict()

    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



async def update_agent(address: str, agent_id: str, character_s3_url: str, md5_hash: str, s3_url_knowledge_files: List[str], client: ClientConfig):
    result = db.agents.update_one(
            {"agent_id": agent_id},
            {"$set": {
                "created_at": datetime.utcnow(),
                "version": "v1",
                "address": address,
                "character": character_s3_url,
                "character_content_md5_hash": md5_hash,
                "client": client.dict(),
                "knowledge": s3_url_knowledge_files # Add knowledge data to storage
            }},
            upsert=True
        )
    return


async def find_character_json(address: str, md5_hash: str):
    result = await db.agents.find_one({
                "address": address,
                "character_content_md5_hash": md5_hash,
            }
        )
    logger.info(result)
    return result

async def extract_paragraphs_from_pdf(content: bytes) -> List[str]:
    """
    Extract text content from PDF using PyMuPDF (fitz) with decoding support
    
    Args:
        content: PDF file content as bytes
    
    Returns:
        List of paragraphs with cleaned text
    """
    try:
        # Create stream from bytes
        stream = io.BytesIO(content)
        doc = fitz.open(stream=stream, filetype="pdf")
        
        paragraphs = []
        
        for page in doc:
            # Get the blocks of text
            blocks = page.get_text("blocks")
            
            for block in blocks:
                text = block[4].strip()
                
                # Skip short lines and page numbers
                if len(text) < 30 or re.match(r'^\d+$', text):
                    continue
                    
                # Check if text is encoded (common patterns in the cipher text)
                if '_' in text or text.count('r') > text.count('s'):
                    # Skip encoded version, as we have the decoded version
                    continue
                
                # Clean up text
                text = text.replace('\n', ' ')
                text = re.sub(r'\s+', ' ', text)
                
                if text:
                    paragraphs.append(text)
        
        doc.close()
        return paragraphs
        
    except Exception as e:
        print(f"Error extracting PDF content: {str(e)}")
        return []



async def notify_deployment_server(
    agent_id: str,
    character_url: str,
    knowledge_files: List[Dict],
    client_config: Dict
) -> None:
    """
    Notify the deployment server about the new agent deployment.
    
    Args:
        agent_id: UUID of the deployed agent
        character_url: S3 URL of the character file
        knowledge_files: List of knowledge file information
        client_config: Client configuration containing credentials
    """
    # Format knowledge files into expected structure
    knowledge_dict = {
        k["filename"]: k["s3_url"].replace("https", "s3").replace(".s3.amazonaws.com", "")
        for k in knowledge_files
    }

    logger.info(knowledge_dict)
    logger.info(client_config)
    
    # Construct environment variables from client config
    env = {
        "TOGETHER_MODEL_LARGE": os.getenv('TOGETHER_MODEL_LARGE'),
        "TOGETHER_MODEL_MEDIUM": os.getenv("TOGETHER_MODEL_MEDIUM"),
        "TOGETHER_MODEL_SMALL": os.getenv("TOGETHER_MODEL_SMALL"),
        "TOGETHER_API_KEY": os.getenv("TOGETHER_API_KEY")
    }
    logger.info(env)

    # Add client credentials to env if they exist
    if client_config.get("twitter"):
        env["TWITTER_USERNAME"] = client_config["twitter"].get("username", "")
        env["TWITTER_PASSWORD"] = client_config["twitter"].get("password", "")
    
   # Add client credentials to env if they exist
    if client_config.get("discord"):
        env["DISCORD_APPLICATION_ID"] = client_config["discord"].get("discord_application_id", "")
        env["DISCORD_API_TOKEN"] = client_config["discord"].get("discord_api_token", "")
        env["DISCORD_VOICE_CHANNEL_ID"] = client_config["discord"].get("discord_voice_channel_id", "")

   # Add client credentials to env if they exist
    if client_config.get("telegram"):
        env["TELEGRAM_BOT_TOKEN"] = client_config["telegram"].get("telegram_bot_token", "")

    logger.info(env)
    # Prepare the payload
    payload = {
        "id": agent_id,
        "character": character_url.replace("https", "s3").replace(".s3.amazonaws.com", ""),
        "knowledge": knowledge_dict,
        "env": env
    }
    
    logger.info(payload)
    try:
        # Get the deployment server URL from environment variables
        deployment_server_url = os.getenv("MARLIN_SERVER_URL")
        if not deployment_server_url:
            logger.error("MARLIN_SERVER_URL not configured")
            return
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{deployment_server_url}/deploy",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            logger.info(f"Successfully notified deployment server for agent {agent_id}")
            
    except Exception as e:
        logger.error(f"Failed to notify deployment server: {str(e)}")

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
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Define request and response models
class AgentShutdownRequest(BaseModel):
    agent_id: str
    signature: str
    message: str

class AgentShutdownResponse(BaseModel):
    success: bool
    message: str


@deploy_router.post("/agent/shutdown", response_model=LogResponse)
async def shutdown_agent(request: AgentShutdownRequest):
    deployment_service = DeploymentService(db)
    
    address = verify_signature(request.signature, request.message)
    await deployment_service.verify_agent_ownership(address, request.agent_id)
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
            print (response.text)
            response.raise_for_status()
            await deployment_service.delete_agent(request.agent_id)
            return AgentShutdownResponse(
                success=True,
                message="Agent removed successfully"
            )
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))