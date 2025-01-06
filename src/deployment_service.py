

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
from src.get_balance import get_account_balance, get_token_balance

# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Initialize MongoDB client
token_address = os.getenv('TOKEN_ADDRESS')



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

    async def process_character_file(self, character: UploadFile) -> tuple[bytes, str]:
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
                        client_data[client_type] = TwitterCredentials(**parsed_value)
                    elif client_type == "discord":
                        client_data[client_type] = DiscordCredentials(**parsed_value)
                    elif client_type == "telegram":
                        client_data[client_type] = TelegramCredentials(**parsed_value)
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
        balance = get_token_balance(address, token_address) if token_address else get_account_balance(address)
        logger.success(f"{address} BALANCE is {balance}")
        
        # Uncomment and modify as needed
        # if balance < float(balance_threshold):
        #     raise HTTPException(status_code=400, detail=f"Insufficient balance: {balance}")
