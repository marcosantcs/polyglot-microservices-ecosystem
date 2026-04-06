from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    data_path: str = "data/knowledge_base.txt"

    class Config:
        env_file = ".env"

settings = Settings()
