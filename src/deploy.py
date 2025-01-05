import os
import uuid
import json
import boto3
import hashlib
from web3 import Web3
from web3.auto import w3
from loguru import logger
from pathlib import Path
from  datetime import datetime
from dotenv import load_dotenv
from typing import Optional, Dict
from pymongo import MongoClient
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from eth_account.messages import encode_defunct
from pydantic import BaseModel, Field, ValidationError
from fastapi import Form, UploadFile, File
from src.get_balance import get_account_balance, get_token_balance
from src.s3_upload import upload_character_to_s3, upload_knowledge_to_s3
from botocore.exceptions import ClientError



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

client = MongoClient(mongodb_uri)
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
    telegram: Optional[str]=None

@deploy_router.post("/deploy")
async def deploy(
    character: UploadFile = File(...),  # Changed to required File upload
    signature: str = Form(None),
    message: str = Form(None),
    knowledge_files: List[UploadFile] = File(None),
    client_twitter: Optional[str] = Form(None),
    client_discord: Optional[str] = Form(None),
    client_telegram: Optional[str] = Form(None)
):
    # Check required fields
    if not character:
        raise HTTPException(status_code=400, detail="character is required")
    if not signature:
        raise HTTPException(status_code=400, detail="signature is required")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    address = verify_signature(signature, message)
    await if_user_in_db(address)


    print(character)
    print(signature)
    print(client_twitter)
    agent_id = str(uuid.uuid4())

    try:
        # Parse character JSON
        try:
            character_content = await character.read()
            character_content_md5_hash = hashlib.md5(character_content).hexdigest()
            
            character_json = json.loads(character_content.decode())
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in character file")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Character file must be a valid UTF-8 encoded JSON file")
        finally:
            await character.close()
        
        ##check if the same character.json exists in the database already 

        
        # Upload character.json to S3
        if await find_character_json(address, character_content_md5_hash):
            raise HTTPException(status_code=500, detail=f"Agent has already been deployed or deployment in process")


        character_s3_url = await upload_character_to_s3(
            address,
            agent_id,
            character_content,
            'application/json'
        )

        # Process knowledge files
        knowledge_data = []
        if knowledge_files:
            for file in knowledge_files:
                # Read and validate each file
                content = await file.read()
                logger.info(f"Uploading knowledge file {file.filename} ...")
                try:
                    # Try to decode as text first
                    text_content = content.decode()
                    knowledge_data.append({
                        "filename": file.filename,
                        "content": text_content,
                        "content_type": file.content_type
                    })
                except UnicodeDecodeError:
                    # If file is not text, store as binary
                    knowledge_data.append({
                        "filename": file.filename,
                        "content": content,
                        "content_type": file.content_type
                    })
                finally:
                    await file.close()

        s3_url_knowledge_files = []
        for knowledge_file_dict in knowledge_data:
            knowledge_s3_url = await upload_knowledge_to_s3(
                address,
                agent_id,
                knowledge_file_dict["content"],
                knowledge_file_dict["filename"],
                knowledge_file_dict["content_type"],
            )
            s3_url_knowledge_files.append({
                "filename": knowledge_file_dict["filename"],
                "content_type": knowledge_file_dict["filename"],
                "s3_url": knowledge_s3_url})


        # Parse client fields if present
        client_data = {}
        if client_twitter:
            try:
                client_data['twitter'] = json.loads(client_twitter)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in client_twitter")
        
        if client_discord:
            try:
                client_data['discord'] = json.loads(client_discord)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in client_discord")
        
        if client_telegram:
            client_data['telegram'] = client_telegram

        print(client_data)

        # Validate client config
        try:
            client = ClientConfig(**client_data)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid client configuration")

        if token_address:
            crypto_balance = get_token_balance(address, token_address)
        else:
            crypto_balance = get_account_balance(address)

        # if crypto_balance < float(balance_threshold):
        #     raise HTTPException(status_code=500, detail=f"This wallet doesnt have sufficient balance {crypto_balance}")
        
        logger.success(f"{address} BALANCE is {crypto_balance}")

        # Store in MongoDB
        await update_agent(address, agent_id, character_s3_url, character_content_md5_hash, s3_url_knowledge_files, client)

        return {
            "agent_id": agent_id,
            "character": character_s3_url,
            "client": client.dict(),
            "signature": signature,
            "message": message,
            "knowledge_files": s3_url_knowledge_files  # Return list of processed files
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def if_user_in_db(address):
    result = db.users.find_one({"address": address})
    if not result:
        logger.error(f"User {address} must registered first")
        raise HTTPException(status_code=500, detail=f"User {address} must register first")


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
    result = db.agents.find_one({
                "address": address,
                "character_content_md5_hash": md5_hash,
            }
        )
    return result
