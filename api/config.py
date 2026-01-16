from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    kafka_brokers: list = [os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")]
    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql://user:pass@localhost/forex_db" 
    model_dir: str = "api/exported_models"
    cors_origins: list = ["http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()