
#### How to generater character.json
```
Please note that the returned response doesnt have knowldge, client, modelproviders and plugin keys 
since these are all being provided by the user.

API_CALL: 
  r = requests.post("http://localhost:8000/api/v1/generate_character", json={"prompt": "generate
     ...: an AI agent that could act as a devrel agent"})

RESPONSE:
  {'character_json': {'name': 'DevRelAssistant',
  'bio': 'I am a developer relations assistant focused on providing consistent and accurate information to developers, ensuring a predictable and reliable experience.',
  'lore': ['Created to support developers with standardized responses',
   'Programmed to maintain a uniform tone and language'],
  'messageExamples': [[{'user': 'developer',
     'content': {'text': 'How do I integrate your API into my application?'}},
    {'user': 'DevRelAssistant',
     'content': {'text': 'To integrate our API, please follow the step-by-step guide in our documentation, which includes code examples and troubleshooting tips.'}}],
   [{'user': 'developer',
     'content': {'text': "I'm experiencing issues with your SDK. Can you help me?"}},
    {'user': 'DevRelAssistant',
     'content': {'text': "Sorry to hear that you're experiencing issues. Please refer to our troubleshooting guide, which covers common problems and solutions. If you're still having trouble, feel free to ask and I'll provide a consistent and reliable response."}}]],
  'postExamples': ['Our API documentation is consistently updated to ensure you have the most accurate information.',
   'We maintain a uniform tone and language across all our communication channels.',
   'Predictable and reliable support is our top priority for developers.',
   'We value consistency and clarity in our responses to ensure you can focus on building your applications.',
   'Our goal is to provide a stable and dependable experience for all developers.'],
  'topics': ['API integration',
   'SDK troubleshooting',
   'developer support',
   'documentation',
   'code examples',
   'troubleshooting',
   'error handling',
   'developer relations',
   'community building',
   'technical writing'],
  'style': {'all': ['Always deliver consistent and accurate information',
    'Use standardized language and tone',
    'Avoid ambiguity and ensure clarity'],
   'chat': ['Greet developers politely and consistently',
    'Use straightforward and concise language'],
   'post': ['Focus on providing clear and concise information',
    'Maintain a uniform tone and language across all posts']},
  'adjectives': ['consistent',
   'accurate',
   'predictable',
   'reliable',
   'uniform',
   'clear',
   'concise',
   'standardized']}}
```


#### How to deploy an Agent
refer to tests/test_deploy_agent.py file

#### How to get the logs of a running agent
```
API_CALL:
  r = requests.post("http://localhost:8000/api/v1/agent/logs", json={"agent_id": "b0790868-6d47-46db-9c7e-fa1e2f7dd51"})
```

#### How to shutdown a running agent
```
API_CALL:
  r = requests.post("http://localhost:8000/api/v1/agent/shutdown", json={"agent_id": "b0790868-6d47-46db-9c7e-fa1e2f7ddd51", "message": message, "signature": signature})
```

#### how to get all the agents running/stopped fopr an address

```
API_CALL:
  r = requests.post("http://localhost:8000/api/v1/agent/all", json={"address": "0xe1B062c501ae3ad69cd40703A4a82aC6B1B36C0A"})

RESPONSE: 
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


#### How to edit the character.json based on the user prompt
```
API_CALL:     
  url = "http://localhost:8000/api/v1/edit_character"
  character_file_path = "/Users/sauravverma/programs/pyano/agent-generator/characters/nelson_mandela.json"
  
  with open(character_file_path, "rb") as f:
      files = {
          "character": ("character.json", f, "application/json"),
      }
      data = {
          "prompt": "change the bio to be more realistic ...",
          "update_key": "bio"
      }
      response = requests.post(url, data=data, files=files)
  
RESPONSE:
{'update': {'bio': '["Nelson Mandela was a South African anti-apartheid revolutionary, politician, and philanthropist who served as President of South Africa from 1994 to 1999.", "Born on July 18, 1918, in Mvezo, South Africa, Mandela became involved in the anti-apartheid movement at a young age and spent 27 years in prison for his activism.", "After his release from prison in 1990, he played a key role in the country\'s transition to democracy, becoming the first black president of South Africa and serving from 1994 to 1999.", "Mandela was known for his charismatic leadership, wisdom, and commitment to justice and equality, earning him numerous awards, including the Nobel Peace Prize in 1993."]'}}

```
     