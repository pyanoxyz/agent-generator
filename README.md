


#### How to get the logs of a running agent
```
r = requests.post("http://localhost:8000/api/v1/logs", json={"agent_id": "b0790868-6d47-46db-9c7e-fa1e2f7dd51"})
```

#### How to shutdown a running agent
```
r = requests.post("http://localhost:8000/api/v1/agent/shutdown", json={"agent_id": "b0790868-6d47-46db-9c7e-fa1e2f7ddd51", "message": message, "signature": signature})
```
