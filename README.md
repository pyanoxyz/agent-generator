

#### How to deploy an Agent
refer to tests/test_deploy_agent.py file

#### How to get the logs of a running agent
```
r = requests.post("http://localhost:8000/api/v1/logs", json={"agent_id": "b0790868-6d47-46db-9c7e-fa1e2f7dd51"})
```

#### How to shutdown a running agent
```
r = requests.post("http://localhost:8000/api/v1/agent/shutdown", json={"agent_id": "b0790868-6d47-46db-9c7e-fa1e2f7ddd51", "message": message, "signature": signature})
```

#### how to get all the agents running/stopped fopr an address

```
r = requests.post("http://localhost:8000/api/v1/agent/all", json={"address": "0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A"})

OUTPUT
{'address': '0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A',
 'agents': [{'agent_id': '4ccdc93a-e7cd-40f7-a6ea-23ce89a18b74',
   'address': '0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A',
   'bio': ['Nelson Mandela was a South African anti-apartheid revolutionary and politician who served as President of South Africa from 1994 to 1999.',
    'He was a key figure in the fight against apartheid and spent 27 years in prison for his activism.',
    "After his release from prison, he played a crucial role in the transition to democracy in South Africa and became the country's first black president.",
    'Mandela was known for his wisdom, compassion, and commitment to justice and equality.'],
   'character': 'https://pyano-agents-config.s3.amazonaws.com/0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A/4ccdc93a-e7cd-40f7-a6ea-23ce89a18b74/character.json',
   'created_at': '2025-01-06T07:48:21.932000',
   'knowledge': [{'filename': 'main.json',
     'content_type': 'application/json',
     's3_url': 'https://pyano-agents-config.s3.amazonaws.com/0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A/4ccdc93a-e7cd-40f7-a6ea-23ce89a18b74/knowledge/main.json'},
    {'filename': 'interactive_mode.json',
     'content_type': 'application/json',
     's3_url': 'https://pyano-agents-config.s3.amazonaws.com/0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A/4ccdc93a-e7cd-40f7-a6ea-23ce89a18b74/knowledge/interactive_mode.json'}],
   'status': 'running',
   'version': 'v1'}]}
```