from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import RawEncoder
import base58

# Function to generate a new keypair
def generate_keypair():
    signing_key = SigningKey.generate()
    private_key = signing_key.encode()  # Private key in bytes
    public_key = signing_key.verify_key.encode()  # Public key in bytes

    # Format the keys as base58 strings
    private_key_base58 = base58.b58encode(private_key).decode()
    public_key_base58 = base58.b58encode(public_key).decode()

    return private_key_base58, public_key_base58

# Function to sign a message
def sign_message(private_key_base58: str, message: str):
    # Decode the base58 private key into raw bytes
    private_key = base58.b58decode(private_key_base58)
    signing_key = SigningKey(private_key, encoder=RawEncoder)

    # Sign the message and retrieve only the signature (64 bytes)
    signature = signing_key.sign(message.encode()).signature

    # Encode the signature into base58 format
    signature_base58 = base58.b58encode(signature).decode()
    return signature_base58

# Function to verify a signature using the public key
def verify_signature(public_key_base58: str, message: str, signature_base58: str):
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
        raise ValueError(f"Signature verification failed: {e}")

# Example Usage
if __name__ == "__main__":
    # Generate keypair
    private_key, public_key = generate_keypair()
    print("Private Key (Base58):", private_key)
    print("Public Key (Base58):", public_key)

    # Sign a message
    message = "Hello, Solana!"
    signature = sign_message(private_key, message)
    print("Signature (Base58):", signature)

    # Verify the signature
    try:
        is_valid = verify_signature(public_key, message, signature)
        print("Signature is valid:", is_valid)
    except ValueError as e:
        print(e)