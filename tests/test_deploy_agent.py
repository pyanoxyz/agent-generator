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
    url = "http://localhost:8000/api/v1/deploy"

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

    try:
        response = requests.post(url, files=files, data=form_data)
        return response.json()
    finally:
        # Close all opened files
        for _, file_data, _ in files:
            if hasattr(file_data[1], 'close'):
                file_data[1].close()

knowledge_files = [ "/Users/sauravverma/programs/pyano/agent-execution-runtime/src/main.rs", 
                "/Users/sauravverma/programs/pyano/mistral.rs/mistralrs-server/src/interactive_mode.rs" ]
character_file = "/Users/sauravverma/programs/pyano/agent-generator/characters/nelson_mandela.json"
twitter_config = {"username": "example_twitter"}
discord_config = {"server_id": "123456"}
telegram_id = {"telegram_bot_token" : "telegram_bot_token" }
message = "We will make it, trust god"
signature="9a69e6bcf98a5e40ae00cf1c8a2c5ebf1c016d0272b3c57be5e133d59dbc199e28a126b07e5425c8755dd5d3c1123a0f7534455298207a1e67e7547a2ec192a51c"
address="0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A" 