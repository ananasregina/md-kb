"""
Markdown Knowledge Base - Configuration Module

Configuration management for markdown directory, PostgreSQL database, and embeddings.
"""

import os
from pathlib import Path
from typing import Optional
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration for the Markdown Knowledge Base.

    Loads configuration from environment variables and .env files.
    """

    def __init__(self) -> None:
        """Initialize configuration from environment and .env files."""
        # Load .env from current directory first
        load_dotenv()

        # Also try loading from ~/.config/mdkb/.env
        config_dir = self._get_config_dir()
        config_env = config_dir / ".env"
        if config_env.exists():
            load_dotenv(config_env)

        logger.debug("Configuration loaded.")

    def get_postgres_uri(self) -> str:
        """
        Get PostgreSQL connection URI.

        Returns:
            str: PostgreSQL connection URI
        """
        host = os.getenv("MDKB_DB_HOST", "localhost")
        port = os.getenv("MDKB_DB_PORT", "5432")
        dbname = os.getenv("MDKB_DB_NAME", "md_kb")
        user = os.getenv("MDKB_DB_USER", "mdkb_user")
        password = os.getenv("MDKB_DB_PASSWORD", "")

        uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        logger.debug(f"PostgreSQL URI: {uri}")
        return uri

    def get_embedding_config(self) -> dict[str, str | int]:
        """
        Get LM Studio embedding configuration.

        Returns:
            dict: Embedding config with url, model, and dimension
        """
        return {
            "url": os.getenv("EMBEDDING_URL", "http://127.0.0.1:1338/v1"),
            "model": os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5-embedding"),
            "dimension": int(os.getenv("EMBEDDING_DIMENSION", "768")),
        }

    def get_markdown_dir(self) -> Path:
        """
        Get the markdown directory to index.

        Returns:
            Path: The markdown directory path

        Raises:
            ValueError: If MDKB_DIR is not set or doesn't exist
        """
        dir_str = os.getenv("MDKB_DIR")
        if not dir_str:
            raise ValueError("MDKB_DIR environment variable is not set")

        dir_path = Path(dir_str)
        if not dir_path.exists():
            raise ValueError(f"MDKB_DIR does not exist: {dir_path}")

        if not dir_path.is_dir():
            raise ValueError(f"MDKB_DIR is not a directory: {dir_path}")

        logger.debug(f"Markdown directory: {dir_path}")
        return dir_path

    def get_config_dir(self) -> Path:
        """
        Get the mdkb configuration directory.

        Returns:
            Path: The configuration directory path
        """
        return self._get_config_dir()

    @staticmethod
    def _get_config_dir() -> Path:
        """
        Get the config directory for mdkb.

        Uses ~/.config/mdkb on Unix-like systems.

        Returns:
            Path: The config directory path
        """
        # Cross-platform config directory
        config_base = Path.home() / ".config"
        mdkb_config = config_base / "mdkb"

        return mdkb_config

    def get_database_name(self) -> Optional[str]:
        """
        Get the database name for MCP server tool naming.

        Returns:
            Optional[str]: Database name or None if not set
        """
        db_name = os.getenv("DATABASE_NAME")
        if db_name:
            db_name = db_name.strip()
            if db_name:
                logger.debug(f"Database name: {db_name}")
                return db_name
        return None

    def get_mcp_server_name(self) -> str:
        """
        Get the MCP server name.

        Returns:
            str: MCP server name
        """
        return os.getenv("MDKB_MCP_NAME", "mdkb-server")

    def get_mcp_server_version(self) -> str:
        """
        Get the MCP server version.

        Returns:
            str: MCP server version
        """
        return os.getenv("MDKB_MCP_VERSION", "0.1.0")

    def get_log_level(self) -> str:
        """
        Get log level for file logging.

        Returns:
            str: Log level (default: INFO)
        """
        return os.getenv("MDKB_LOG_LEVEL", "INFO")

    def get_log_level_console(self) -> str:
        """
        Get log level for console logging.

        Returns:
            str: Console log level (default: WARNING)
        """
        return os.getenv("MDKB_LOG_LEVEL_CONSOLE", "WARNING")

    def get_jsonrpc_host(self) -> str:
        """
        Get JSON-RPC server host.

        Returns:
            str: JSON-RPC server host (default: 127.0.0.1)
        """
        return os.getenv("MDKB_JSONRPC_HOST", "127.0.0.1")

    def get_jsonrpc_port(self) -> int:
        """
        Get JSON-RPC server port.

        Returns:
            int: JSON-RPC server port (default: 8023)
        """
        return int(os.getenv("MDKB_JSONRPC_PORT", "8023"))

    def get_log_file(self) -> Path:
        """
        Get the log file path.

        Returns:
            Path: The log file path (default: ~/.config/mdkb/mcp.log)
        """
        config_dir = self._get_config_dir()
        log_file = config_dir / os.getenv("MDKB_LOG_FILE", "mcp.log")
        logger.debug(f"Log file: {log_file}")
        return log_file

    def get_log_max_bytes(self) -> int:
        """
        Get maximum log file size before rotation.

        Returns:
            int: Max bytes (default: 10MB = 10 * 1024 * 1024)
        """
        return int(os.getenv("MDKB_LOG_MAX_BYTES", str(10 * 1024 * 1024)))

    def get_log_backup_count(self) -> int:
        """
        Get number of backup log files to keep.

        Returns:
            int: Number of backups (default: 10)
        """
        return int(os.getenv("MDKB_LOG_BACKUP_COUNT", "10"))


# Singleton instance for the whole application
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config: The configuration singleton
    """
    global _config
    if _config is None:
        _config = Config()
        logger.debug("Global configuration initialized.")
    return _config
