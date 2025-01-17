
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent
from fastapi import APIRouter, HTTPException
# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Configure logging

def get_native_balance(address: str, url: str) -> float:
    """
    Get ETH balance for an address using Alchemy API
    
    Args:
        address: Ethereum wallet address
        api_key: Alchemy API key
    
    Returns:
        float: Balance in ETH
    """
    
    payload = {
        "jsonrpc": "2.0",
        "method": "getBalance",
        "params": [address],
        "id": 1
    }
    
    headers = {"content-type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print (response)
        print (f"Response from alchemy {response.json()["result"]}")
        balance_wei = int(response.json()["result"]["value"])
        balance_eth = balance_wei / 10**9
        
        return balance_eth
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
                status_code=400,
                detail=f"Failed to get balance {str(e)}"
            )

def get_token_balance(address: str, url: str, token_address: str) -> float:
    """
    Get ERC20 token balance for an address using Alchemy API
    
    Args:
        address: Wallet address
        token_address: ERC20 token contract address
        api_key: Alchemy API key
    
    Returns:
        float: Token balance
    """
    
    # ERC20 balanceOf method ID (0x70a08231)
    data = f"0x70a08231000000000000000000000000{address[2:]}"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{
            "to": token_address,
            "data": data
        }, "latest"],
        "id": 1
    }
    
    headers = {"accept": "application/json", "content-type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Convert result to decimal
        balance_wei = int(response.json()["result"], 16)
        balance = balance_wei / 10**18  # Adjust decimals if token uses different precision
        
        return balance
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get token balance: {str(e)}")
