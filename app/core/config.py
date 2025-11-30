from pydantic_settings import BaseSettings

# Defaults provided so the app can run in a local demo mode without
# requiring a Postgres server or AWS credentials. These values can be
# overridden by creating a `.env` file or setting environment variables.
class Settings(BaseSettings):
    database_hostname: str = "sqlite"  # use 'sqlite' to trigger local sqlite fallback
    database_password: str = ""
    database_name: str = "./test2.db"
    database_username: str = ""
    secret_key: str = "demo-secret"
    algorithm: str = "HS256"
    database_port: str = "0"
    aws_secret_key: str = "demo-aws-key"
    stripe_secret_key: str = "sk_test_51SMhR3Romhy3CPSI8i2b6uJJGQRekrJ93Ux4h7PiKebXz8SL5tBz1TMDC8wHTl0Wu71PkKg0s5J27PhZUgtJgSMM00gEdk1RX6"
    stripe_webhook_secret: str = "whsec_JI97WplSECDuzjAp8c6QBYc3OkkGefAc"
    stripe_publishable_key: str = "pk_test_51SMhR3Romhy3CPSIknU2QhVPXiQVzqCy9Y20zFAJKmuDmfYKHRufSFoh0STIOAWUyCzDGHS7PiEgxIHRTUrqqlg700vKkKiuqC"
    
    class Config:
        env_file = ".env"


settings = Settings()