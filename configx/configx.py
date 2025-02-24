import os

POSTGRES_USER = os.getenv("POSTGRES_USER", "stream")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "stream")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "stream")

HOUR =  os.getenv("HOUR","14")
MINUTE = os.getenv("MINUTE","39")