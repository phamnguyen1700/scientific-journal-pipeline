import pyodbc

from src.config.settings import (
    SQLSERVER_DATABASE,
    SQLSERVER_DRIVER,
    SQLSERVER_ENCRYPT,
    SQLSERVER_PASSWORD,
    SQLSERVER_SERVER,
    SQLSERVER_TRUST_SERVER_CERTIFICATE,
    SQLSERVER_TRUSTED_CONNECTION,
    SQLSERVER_USERNAME,
)


def build_connection_string() -> str:
    parts = [
        f"DRIVER={{{SQLSERVER_DRIVER}}}",
        f"SERVER={SQLSERVER_SERVER}",
        f"DATABASE={SQLSERVER_DATABASE}",
        f"Encrypt={SQLSERVER_ENCRYPT}",
        f"TrustServerCertificate={SQLSERVER_TRUST_SERVER_CERTIFICATE}",
    ]

    if SQLSERVER_TRUSTED_CONNECTION.lower() in {"yes", "true", "1"}:
        parts.append("Trusted_Connection=yes")
    else:
        parts.extend(
            [
                f"UID={SQLSERVER_USERNAME}",
                f"PWD={SQLSERVER_PASSWORD}",
            ]
        )

    return ";".join(parts)


def get_connection() -> pyodbc.Connection:
    return pyodbc.connect(build_connection_string())
