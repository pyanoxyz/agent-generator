In [62]: data = {
    ...:      'character': json.dumps(character),
    ...:     'signature': signature["signature"],
    ...:     'message': signature["message"],
    ...:     'client_twitter': json.dumps({'username': 'user', 'password': 'pass'}),
    ...:     'client_telegram': 'bot_token'
    ...: }

In [63]: r = requests.post("http://localhost:8000/api/v1/deploy", data=data)

In [64]: r.json()
Out[64]: {'detail': "name 'ValidationError' is not defined"}

In [65]: with open(character_file, 'r') as file:
    ...:     character = json.load(file)