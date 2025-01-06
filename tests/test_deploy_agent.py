def deploy_character(
    character_file_path: str,
    knowledge_file_paths: list,
    signature: str,
    message: str,
    client_twitter: dict = None,
    client_discord: dict = None,
    client_telegram: dict = None
):
    import mimetypes
    url = "http://localhost:8000/api/v1/agent/deploy"

    # Initialize files with character file
    files = []
    files.append(
        ('character', ('character.json', open(character_file_path, 'r'), 'application/json'))
    )

    # Add multiple knowledge files with automatically detected mime type
    for file_path in knowledge_file_paths:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        original_filename = Path(file_path).name
        # Append each file with the same key 'knowledge_files'
        files.append(
            ('knowledge_files', (original_filename, open(file_path, 'rb'), mime_type))
        )

    form_data = {
        'signature': signature,
        'message': message
    }

    if client_twitter:
        form_data['client_twitter'] = json.dumps(client_twitter)
    if client_discord:
        form_data['client_discord'] = json.dumps(client_discord)
    if client_telegram:
        form_data['client_telegram'] = json.dumps(client_telegram)

    response = requests.post(url, files=files, data=form_data)
    return response.json()


knowledge_files = [ "/Users/sauravverma/programs/pyano/agent-execution-runtime/src/main.rs", 
                "/Users/sauravverma/programs/pyano/mistral.rs/mistralrs-server/src/interactive_mode.rs" ]
character_file = "/Users/sauravverma/programs/pyano/agent-generator/characters/nelson_mandela.json"
twitter_config = {"username": "example_twitter", "password": "password", "email": "test@gmail.com"}
discord_config = {"discord_application_id": "123456", "discord_api_token": "sewerwerwr"}
telegram_id = {"telegram_bot_token": "telegram_bot_token"}
message = "Welcome to pyano network, Sign this message for server authentication"
signature="8fbbf5b11fc4c75407def62092bd57cd21b7e9da3918d6bd0e6c72573a532b83043bcafdd1b32901d16e4a669065053fc943ffd8369115bd75a9fb621a145a831c"
address="0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A"

result = deploy_character(
        character_file,
        knowledge_files,
        signature,
        message,
        client_twitter=twitter_config,
        client_discord=discord_config,
        client_telegram=telegram_config
    )

