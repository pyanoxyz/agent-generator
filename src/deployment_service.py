

from fastapi import Form, UploadFile, File, HTTPException
from src.types import KnowledgeFile, TwitterCredentials, DiscordCredentials, TelegramCredentials, ClientConfig
from pydantic import BaseModel, Field, ValidationError, validator, EmailStr
from typing import Optional, Dict, List
import json
from loguru import logger
import hashlib
import mimetypes
from pathlib import Path
from src.utils.extract_pdf import extract_paragraphs_from_pdf
from dotenv import load_dotenv
import os
from src.get_balance import get_native_balance
import httpx
import requests
from twikit import Client
from telegram import Bot
from discord import Client as DiscordClient
# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Initialize MongoDB client
token_address = os.getenv('TOKEN_ADDRESS')
balance_threshold = os.getenv('BALANCE_THRESHOLD')
token_threshold = os.getenv('TOKEN_THRESHOLD')

SOL_URL = os.getenv("SOL_URL")
# BASE_URL = os.getenv("BASE_URL")

env = os.getenv('ENV')



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
    

    async def verify_character_uniqueness(self, address: str, content_hash: str) -> None:
        """Check if character already exists"""
        async def find_character_json(address: str, md5_hash: str):
            result = await self.db.agents.find_one({
                "address": address,
                "character_content_md5_hash": md5_hash,
            }
            )
            logger.info(result)
            return result

        if await find_character_json(address, content_hash):
            raise HTTPException(
                status_code=409,
                detail="Agent has already been deployed or deployment in process"
            )

    @staticmethod
    async def process_character_file(character: UploadFile) -> tuple[bytes, str]:
        """Process and validate character file"""
        try:
            content = await character.read()
            content_hash = hashlib.md5(content).hexdigest()
            
            try:
                json_content = json.loads(content.decode())
                if 'bio' not in json_content:
                    raise HTTPException(status_code=400, detail="Missing 'bio' field in character file")
                
                if not isinstance(json_content['bio'], list):
                    raise HTTPException(status_code=400, detail="'bio' field must be a list")
                
                return content, content_hash, json_content

            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in character file")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Character file must be UTF-8 encoded JSON")
            
        finally:
            await character.close()

    async def process_knowledge_file(self, file: UploadFile) -> KnowledgeFile:
        """Process a single knowledge file"""
        try:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="File content is empty")            
            # Get file type using mimetypes
            file_type, _ = mimetypes.guess_type(file.filename)
            if not file_type:
                file_type = 'application/octet-stream'
            
            json_filename = Path(file.filename).stem + '.json'

            if file_type == 'application/pdf':
                paragraphs = extract_paragraphs_from_pdf(content)
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


    async def validate_client_data(self, twitter: Optional[str], discord: Optional[str], telegram: Optional[str]) -> ClientConfig:
        """Validate and process client configuration data"""
        client_data = {
            "twitter": None,
            "discord": None,
            "telegram": None
        }
        
        for client_type, client_value in [
            ("twitter", twitter),
            ("discord", discord),
            ("telegram", telegram)
        ]:
            if client_value:
                try:
                    parsed_value = json.loads(client_value)
                    if client_type == "twitter":
                        creds = TwitterCredentials(**parsed_value)
                        client = Client('en-US')
                        try:
                            await client.login(
                                auth_info_1=creds.username,
                                auth_info_2=creds.email,
                                password=creds.password,
                            )
                        except Exception as e:
                            logger.error(f"Failed to authenticate with Twitter: {str(e)}")
                            raise HTTPException(
                                status_code=400,
                                detail=f"Failed to authenticate with Twitter: {str(e)}"
                            )
                        client_data[client_type] = creds
                    elif client_type == "discord":
                        creds = DiscordCredentials(**parsed_value)
                        client = DiscordClient(intents=discord.Intents.default())
                        try:
                             await client.login(creds.discord_api_token)
                             await client.close()
                        except Exception as e:
                            logger.error(f"Failed to authenticate with Discord: {str(e)}")
                            raise HTTPException(
                                status_code=400,
                                detail=f"Failed to authenticate with Discord: {str(e)}"
                            )
                        client_data[client_type] = creds
                    elif client_type == "telegram":
                        creds = TelegramCredentials(**parsed_value)
                        try:
                            bot = Bot(token=creds.telegram_bot_token)
                            await bot.get_me()
                        except Exception as e:
                            logger.error(f"Failed to authenticate with Telegram: {str(e)}")
                            raise HTTPException(
                                status_code=400,
                                detail=f"Failed to authenticate with Telegram: {str(e)}"
                            )
                        client_data[client_type] = creds
                    else:
                        raise HTTPException(
                        status_code=400,
                        detail=f"Client not supported yet"
                        )                    
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid JSON in client_{client_type}"
                    )

        try:
            return ClientConfig(**client_data)
        except ValidationError as e:
            logger.error(f"Error in validating client {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid client configuration")

    async def verify_crypto_balance(self, address: str) -> None:
        """Verify crypto balance meets threshold"""
        ##First check balance on Eth
        if env == "production":
            sol_balance = get_native_balance(address, SOL_URL)
            if sol_balance < float(balance_threshold):
                # logger.error(f"Address=[{address}] doesnt have suiffcient eth balance on ETH, Balance=[{eth_balance}]")
                # token_balance = get_token_balance(address, ETH_URL, token_address)
                # if token_balance < float(token_threshold):
                #     logger.error(f"Address=[{address}] doesnt have suiffcient virtuals balance on ETH, Balance=[{token_balance}]")
                #     base_balance = get_native_balance(address, BASE_URL)
                #     if base_balance < float(balance_threshold):
                #         logger.error(f"Address=[{address}] doesnt have suiffcient balance on BASE, Balance=[{base_balance}]")
                raise HTTPException(status_code=400, detail=f"Insufficient balance on Solana blockchain for Sol: Required {balance_threshold}")

        return



async def notify_deployment_server(
    agent_id: str,
    character_url: str,
    knowledge_files: List[Dict],
    client_config: Dict
) -> bool:
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

    knowledge_filenames = ','.join(f"{k['filename']}" for k in knowledge_files)
    logger.info(knowledge_dict)
    logger.info(client_config)
    logger.info(knowledge_filenames)
    
    # Construct environment variables from client config
    env = {
        "TOGETHER_MODEL_LARGE": os.getenv('TOGETHER_MODEL_LARGE'),
        "TOGETHER_MODEL_MEDIUM": os.getenv("TOGETHER_MODEL_MEDIUM"),
        "TOGETHER_MODEL_SMALL": os.getenv("TOGETHER_MODEL_SMALL"),
        "TOGETHER_API_KEY": os.getenv("TOGETHER_API_KEY"),
        "USE_TOGETHER_EMBEDDING": "true",
        "KNOWLEDGE_DIR": "/app/knowledge/", 
        "KNOWLEDGE_FILES": knowledge_filenames
    }
    logger.info(env)

    # Add client credentials to env if they exist
    if client_config.get("twitter"):
        env["TWITTER_USERNAME"] = client_config["twitter"].get("username", "")
        env["TWITTER_PASSWORD"] = client_config["twitter"].get("password", "")
        env["TWITTER_EMAIL"] = client_config["twitter"].get("email", "")
    
   # Add client credentials to env if they exist
    if client_config.get("discord"):
        env["DISCORD_APPLICATION_ID"] = client_config["discord"].get("discord_application_id", "")
        env["DISCORD_API_TOKEN"] = client_config["discord"].get("discord_api_token", "")
        if client_config["discord"].get("discord_voice_channel_id"):
            env["DISCORD_VOICE_CHANNEL_ID"] = client_config["discord"].get("discord_voice_channel_id")

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
    
    logger.info(json.dumps(payload))
    try:
        # Get the deployment server URL from environment variables
        deployment_server_url = os.getenv("MARLIN_SERVER_URL")
        if not deployment_server_url:
            logger.error("MARLIN_SERVER_URL not configured")
            return False
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{deployment_server_url}/deploy",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print (response)
            logger.info(f"Successfully notified deployment server for agent {agent_id}")
    except Exception as e:
        logger.error(f"Failed to notify deployment server: {str(e)}")
        raise HTTPException(status_code=400, detail="Couldnt deploy the agent, Please email us for quick resolution")

    return True
