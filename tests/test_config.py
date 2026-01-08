"""
Configuration module tests.
"""

import pytest
from pathlib import Path
from md_kb.config import Config, get_config


class TestConfig:
    """Test configuration loading and validation."""

    def test_get_postgres_uri(self, monkeypatch):
        """Test PostgreSQL URI construction."""
        monkeypatch.setenv("MDKB_DB_HOST", "testhost")
        monkeypatch.setenv("MDKB_DB_PORT", "5432")
        monkeypatch.setenv("MDKB_DB_NAME", "testdb")
        monkeypatch.setenv("MDKB_DB_USER", "testuser")
        monkeypatch.setenv("MDKB_DB_PASSWORD", "testpass")

        config = Config()
        uri = config.get_postgres_uri()

        assert "postgresql://testuser:testpass@testhost:5432/testdb" == uri

    def test_get_embedding_config(self, monkeypatch):
        """Test embedding configuration loading."""
        monkeypatch.setenv("EMBEDDING_URL", "http://test-host:1338/v1")
        monkeypatch.setenv("EMBEDDING_MODEL", "test-model")
        monkeypatch.setenv("EMBEDDING_DIMENSION", "512")

        config = Config()
        emb_config = config.get_embedding_config()

        assert emb_config["url"] == "http://test-host:1338/v1"
        assert emb_config["model"] == "test-model"
        assert emb_config["dimension"] == 512

    def test_get_markdown_dir(self, monkeypatch, tmp_path):
        """Test markdown directory path resolution."""
        test_dir = tmp_path / "test_md"
        test_dir.mkdir()
        monkeypatch.setenv("MDKB_DIR", str(test_dir))

        config = Config()
        result = config.get_markdown_dir()

        assert result == test_dir

    def test_get_markdown_dir_not_set(self, monkeypatch):
        """Test error when MDKB_DIR environment variable is not set."""
        monkeypatch.delenv("MDKB_DIR", raising=False)

        config = Config()
        with pytest.raises(ValueError, match="MDKB_DIR environment variable is not set"):
            config.get_markdown_dir()

    def test_get_markdown_dir_not_exists(self, monkeypatch):
        """Test error when MDKB_DIR points to non-existent directory."""
        monkeypatch.setenv("MDKB_DIR", "/nonexistent/path")

        config = Config()
        with pytest.raises(ValueError, match="does not exist"):
            config.get_markdown_dir()

    def test_get_markdown_dir_not_directory(self, monkeypatch, tmp_path):
        """Test error when MDKB_DIR points to a file, not directory."""
        test_file = tmp_path / "test_file.md"
        test_file.write_text("# Test")
        monkeypatch.setenv("MDKB_DIR", str(test_file))

        config = Config()
        with pytest.raises(ValueError, match="is not a directory"):
            config.get_markdown_dir()

    def test_get_config_dir(self):
        """Test config directory path."""
        config = Config()
        config_dir = config.get_config_dir()

        assert config_dir.name == "mdkb"
        assert "config" in str(config_dir).lower()

    def test_get_mcp_server_name(self, monkeypatch):
        """Test MCP server name."""
        monkeypatch.setenv("MDKB_MCP_NAME", "test-server")

        config = Config()
        name = config.get_mcp_server_name()

        assert name == "test-server"

    def test_get_mcp_server_name_default(self, monkeypatch):
        """Test default MCP server name."""
        monkeypatch.delenv("MDKB_MCP_NAME", raising=False)

        config = Config()
        name = config.get_mcp_server_name()

        assert name == "mdkb-server"

    def test_get_mcp_server_version(self, monkeypatch):
        """Test MCP server version."""
        monkeypatch.setenv("MDKB_MCP_VERSION", "2.0.0")

        config = Config()
        version = config.get_mcp_server_version()

        assert version == "2.0.0"

    def test_get_mcp_server_version_default(self, monkeypatch):
        """Test default MCP server version."""
        monkeypatch.delenv("MDKB_MCP_VERSION", raising=False)

        config = Config()
        version = config.get_mcp_server_version()

        assert version == "0.1.0"

    def test_get_log_level(self, monkeypatch):
        """Test log level."""
        monkeypatch.setenv("MDKB_LOG_LEVEL", "DEBUG")

        config = Config()
        log_level = config.get_log_level()

        assert log_level == "DEBUG"

    def test_get_log_level_default(self, monkeypatch):
        """Test default log level."""
        monkeypatch.delenv("MDKB_LOG_LEVEL", raising=False)

        config = Config()
        log_level = config.get_log_level()

        assert log_level == "INFO"

    def test_config_priority_env_overrides_file(self, monkeypatch, tmp_path):
        """Test that environment variables override .env file."""
        # Create .env file with one value
        env_file = tmp_path / ".env"
        env_file.write_text("MDKB_NAME=file-value\n")

        config = Config()
        # Environment variable should override
        monkeypatch.setenv("MDKB_NAME", "env-value")

        assert config.get_mcp_server_name() == "env-value"

    def test_get_config_singleton(self, monkeypatch):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2
