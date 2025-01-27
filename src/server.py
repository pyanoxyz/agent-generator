from loguru import logger
from fastapi import FastAPI
from src.deploy import deploy_router
from src.character import character_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.include_router(deploy_router, prefix="/api/v1")
app.include_router(character_router, prefix="/api/v1")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# env = os.getenv("ENV")
# logger.info(f"Env is {env}")

# if env not in ["production", "local"]:    
#     logger.error("env can either be production or local, please edit the .env file")
#     sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    import os
    import sys
    env = os.getenv("ENV")
    print(env)
    if env not in ["production", "local"]:
        logger.error("env can either be production or local, please edit the .env file")
        sys.exit(1)
    logger.info(f"Env is {env}")
    uvicorn.run(app, host="0.0.0.0", port=8000)