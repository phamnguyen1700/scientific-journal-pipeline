import os

from dotenv import load_dotenv

# Load variables from .env
load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# SQL Server
SQLSERVER_DRIVER = require_env("SQLSERVER_DRIVER")
SQLSERVER_SERVER = require_env("SQLSERVER_SERVER")
SQLSERVER_DATABASE = require_env("SQLSERVER_DATABASE")
SQLSERVER_USERNAME = require_env("SQLSERVER_USERNAME")
SQLSERVER_PASSWORD = require_env("SQLSERVER_PASSWORD")
SQLSERVER_TRUSTED_CONNECTION = require_env("SQLSERVER_TRUSTED_CONNECTION")
SQLSERVER_ENCRYPT = require_env("SQLSERVER_ENCRYPT")
SQLSERVER_TRUST_SERVER_CERTIFICATE = require_env("SQLSERVER_TRUST_SERVER_CERTIFICATE")

# OpenAlex API
OPENALEX_BASE_URL = require_env("OPENALEX_BASE_URL")
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")

# Crossref API
CROSSREF_BASE_URL = os.getenv("CROSSREF_BASE_URL", "https://api.crossref.org")
CROSSREF_MAILTO = os.getenv("CROSSREF_MAILTO")
CROSSREF_USER_AGENT = os.getenv(
    "CROSSREF_USER_AGENT",
    "scientific-journal-pipeline/1.0",
)

# Pipeline defaults
DEFAULT_BATCH_SIZE = 1000
OPENALEX_PAGE_DELAY_SECONDS = float(os.getenv("OPENALEX_PAGE_DELAY_SECONDS", "1"))
OPENALEX_KEYWORD_DELAY_SECONDS = float(os.getenv("OPENALEX_KEYWORD_DELAY_SECONDS", "2"))
CROSSREF_PAGE_DELAY_SECONDS = float(os.getenv("CROSSREF_PAGE_DELAY_SECONDS", "1"))
