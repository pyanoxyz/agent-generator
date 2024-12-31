

import pytest
import json
import requests
from pathlib import Path
import json

@pytest.fixture
def base_url():
    return "http://localhost:8000/api/v1"

@pytest.fixture
def character_data():
    character_file = Path("character.json")
    with open(character_file) as f:
        return json.load(f)

@pytest.fixture
def signature_data():
   return {'signature': '2f532e98a2ae5e0638dddf9726b8ee7858c69815fc44d7bf05a8193de856f3f507094e90b21f8720aafa0eee32bee4f869b5c7bc96af6825b170437b1b19a6cd1c',
        'address': '0x4cD3DBb6076B8097E3F595882adeafd7D3F0Ed48',
        'message': 'just a test message'}

def test_deploy_character(base_url, character_data, signature_data):
    data = {
        'character': json.dumps(character_data),
        'signature': signature_data["signature"],
        'message': signature_data["message"],
        'client_twitter': json.dumps({'username': 'user', 'password': 'pass'}),
        'client_telegram': 'bot_token'
    }
    
    response = requests.post(f"{base_url}/deploy", data=data)
    assert response.status_code == 200
    
    resp_data = response.json()
    assert "character" in resp_data
    assert "client" in resp_data
    assert "signature" in resp_data
    assert "message" in resp_data

def test_deploy_missing_character(base_url, signature_data):
    data = {
        'signature': signature_data["signature"],
        'message': signature_data["message"]
    }
    
    response = requests.post(f"{base_url}/deploy", data=data)
    assert response.status_code == 400
    assert response.json()["detail"] == "character is required"

def test_deploy_invalid_json(base_url, signature_data):
    data = {
        'character': 'invalid json',
        'signature': signature_data["signature"],
        'message': signature_data["message"]
    }
    
    response = requests.post(f"{base_url}/deploy", data=data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON in character file"