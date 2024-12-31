from fastapi import APIRouter, HTTPException, Depends
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.auto import w3
from pymongo import MongoClient
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Dict
from loguru import logger
from  datetime import datetime
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Form, UploadFile, File
# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Initialize MongoDB client
mongodb_uri = os.getenv('MONGODB_URI')  # Replace with your MongoDB URI
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
async def store_character_data(
    character: str = Form(None),
    signature: str = Form(None),
    message: str = Form(None),
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
    print(character)
    print(signature)
    print(client_twitter)
    try:
        # Parse character JSON
        try:
            character = json.loads(character)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in character file")

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

        print (client_data)
        # Validate client config
        try:
            client = ClientConfig(**client_data)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid client configuration")

        # Store in MongoDB
        result = db.users.update_one(
            {"address": address},
            {"$set": {
                "character": character,
                "client": client.dict()
            }},
            upsert=True
        )


        return {
            "character": character,
            "client": client.dict(),
            "signature": signature,
            "message": message
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))