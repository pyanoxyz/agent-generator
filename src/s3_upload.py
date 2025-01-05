
import os
import boto3
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from loguru import logger


# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Initialize MongoDB client
mongodb_uri = os.getenv('AWS_ACCESS_KEY_ID')
token_address = os.getenv('AWS_SECRET_ACCESS_KEY')
balance_threshold = os.getenv('AWS_REGION')


# S3 client configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)
BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')

async def upload_character_to_s3(address: str, agent_id: str, file_content: bytes, content_type: str = None) -> str:
    """
    Upload a file to S3 with timestamp metadata and return its URL
    
    Args:
        agent_id: The ID of the agent
        file_content: The file content in bytes
        content_type: MIME type of the file
    
    Returns:
        str: The S3 URL of the uploaded file
    """
    try:
        # Generate a unique file path
        s3_path = f"{address}/{agent_id}/character.json"
        
        # Generate timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Prepare metadata and content type arguments
        metadata = {
            'timestamp': timestamp,
            'agent_id': agent_id
        }
        
        extra_args = {
            'Metadata': metadata,
            **(({'ContentType': content_type} if content_type else {}))
        }
        
        # Upload to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_path,
            Body=file_content,
            **extra_args
        )
        
        # Generate URL
        url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_path}"
        
        logger.info(f"Uploaded character.json for agent {agent_id} with timestamp {timestamp}")
        return url
        
    except ClientError as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file to S3")


async def upload_knowledge_to_s3(address: str, agent_id: str, file_content: bytes, file_name: str, content_type: str = None) -> str:
    """
    Upload a file to S3 with timestamp metadata and return its URL
    
    Args:
        agent_id: The ID of the agent
        file_content: The file content in bytes
        content_type: MIME type of the file
    
    Returns:
        str: The S3 URL of the uploaded file
    """
    try:
        # Generate a unique file path
        s3_path = f"{address}/{agent_id}/knowledge/{file_name}"
        
        # Generate timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Prepare metadata and content type arguments
        metadata = {
            'timestamp': timestamp,
            'agent_id': agent_id
        }
        
        extra_args = {
            'Metadata': metadata,
            **(({'ContentType': content_type} if content_type else {}))
        }
        
        # Upload to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_path,
            Body=file_content,
            **extra_args
        )
        
        # Generate URL
        url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_path}"
        
        logger.info(f"Uploaded knowledge file {file_name} for agent {agent_id} with timestamp {timestamp}")
        return url
        
    except ClientError as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file to S3")