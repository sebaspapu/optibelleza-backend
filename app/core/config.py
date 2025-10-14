from pydantic_settings import BaseSettings

# Defaults provided so the app can run in a local demo mode without
# requiring a Postgres server or AWS credentials. These values can be
# overridden by creating a `.env` file or setting environment variables.
class Settings(BaseSettings):
    database_hostname: str = "sqlite"  # use 'sqlite' to trigger local sqlite fallback
    database_password: str = ""
    database_name: str = "./test.db"
    database_username: str = ""
    secret_key: str = "demo-secret"
    algorithm: str = "HS256"
    database_port: str = "0"
    aws_secret_key: str = "demo-aws-key"
    class Config:
        env_file = ".env"


settings = Settings()