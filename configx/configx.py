import os

POSTGRES_USER = os.getenv("POSTGRES_USER", "stream")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "stream")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "stream")

HOUR =  os.getenv("HOUR","13")
MINUTE = os.getenv("MINUTE","53")

APP_ID = os.getenv("APP_ID","ic-app-id")
APP_SECRET = os.getenv("APP_SECRET","ICSecret@2025")

API_URL1 = "https://api-aof-dev.icenter.ai/integration-service/v1/calendar-events"
API_URL3 = "https://api-aof-dev.icenter.ai/integration-service/v1/locations"
API_URL2 = "https://api-aof-dev.icenter.ai/integration-service/v1/hik-cameras"
API_STREAM = "http://192.168.0.35:4067/api/ai/v2/stream"
TOKEN_URL = "https://api-aof-dev.icenter.ai/integration-service/v1/auth/token"