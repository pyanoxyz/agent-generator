from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Any, Dict, List
from enum import Enum
from fastapi import Form, UploadFile, File, HTTPException

class CharacterEditResponse(BaseModel):
    update: Dict[str, Any]

class CharacterRequest(BaseModel):
    prompt: str

class CharacterResponse(BaseModel):
    character_json: dict

class AgentStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"

class TwitterCredentials(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=3)
    email: EmailStr

class DiscordCredentials(BaseModel):
    discord_application_id: str = Field(..., min_length=1)
    discord_api_token: str = Field(..., min_length=1)
    discord_voice_channel_id: Optional[str] = None

class TelegramCredentials(BaseModel):
    telegram_bot_token: str = Field(..., min_length=1)


class SignatureRequest(BaseModel):
    signature: str = Field(..., description="Signature is required")
    message: str = Field(..., description="Message is required")
    public_key: str = Field(..., description="public_key is required")
    

class CheckRegistered(BaseModel):
    public_key: str = Field(..., description="Address is required")

# Update the ClientConfig to use DiscordCredentials
class ClientConfig(BaseModel):
    twitter: Optional[TwitterCredentials]
    discord: Optional[DiscordCredentials]
    telegram: Optional[TelegramCredentials]

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
        signature: str,
        message: str,
        knowledge_files: List[Dict]
    ):
        self.agent_id = agent_id
        self.character_url = character_url
        self.signature = signature
        self.message = message
        self.knowledge_files = knowledge_files

    def dict(self):
        return {
            "agent_id": self.agent_id,
            "character": self.character_url,
            "signature": self.signature,
            "message": self.message,
            "knowledge_files": self.knowledge_files
        }
