import logging

from fastapi import FastAPI
from src.adapters.api import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(root_path="/appointment-service")
app.include_router(router)
