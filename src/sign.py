from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import secrets

def sign_message(private_key: str, message: str):
    """
    Sign a message using a private key
    
    Args:
        private_key (str): Ethereum private key (with or without '0x' prefix)
        message (str): Message to sign
        
    Returns:
        dict: Contains signature, address, and original message
    """
    try:
        # Add '0x' prefix if not present
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
            
        # Create account from private key
        account = Account.from_key(private_key)
        
        # Get the address
        address = account.address
        
        # Create the message hash
        message_hash = encode_defunct(text=message)
        
        # Sign the message
        signed_message = Account.sign_message(message_hash, private_key)
        
        return {
            "signature": signed_message.signature.hex(),
            "address": address,
            "message": message
        }
    except Exception as e:
        raise Exception(f"Error signing message: {str(e)}")

def generate_random_private_key():
    """
    Generate a new random private key
    
    Returns:
        tuple: (private_key, address)
    """
    # Generate random private key
    private_key = '0x' + secrets.token_hex(32)
    account = Account.from_key(private_key)
    
    return private_key, account.address

# Example usage
if __name__ == "__main__":
    # Example 1: Using existing private key
    private_key = "your_private_key_here"  # Replace with actual private key
    message = "Hello, this is a test message!"
    
    try:
        result = sign_message(private_key, message)
        print("Signature:", result["signature"])
        print("Address:", result["address"])
        print("Message:", result["message"])
    except Exception as e:
        print("Error:", e)
    
    # Example 2: Generate new private key and sign
    try:
        new_private_key, new_address = generate_random_private_key()
        print("\nGenerated new wallet:")
        print("Private Key:", new_private_key)
        print("Address:", new_address)
        
        result = sign_message(new_private_key, message)
        print("\nSigned with new wallet:")
        print("Signature:", result["signature"])
    except Exception as e:
        print("Error:", e)
