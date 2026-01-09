# Markdown Knowledge Base

Semantic search for markdown collections using PostgreSQL and pgvector.

## Overview

The Markdown Knowledge Base (md-kb) provides semantic search capabilities for markdown document collections. It indexes markdown files recursively, stores them in PostgreSQL with vector embeddings, and provides both CLI and MCP (Model Context Protocol) interfaces for searching.

## Features

- **Semantic Search**: Find documents by meaning, not just keywords
- **Automatic Indexing**: File system watcher keeps index up to date
- **Checksum-Based**: Only reindexes when files actually change
- **Dual Interface**:
  - CLI: One-shot search with forced refresh
  - MCP Server: Long-lived process for AI agents
- **PostgreSQL + pgvector**: High-performance vector similarity search
- **LM Studio Integration**: Uses OpenAI-compatible embedding API

## Prerequisites

- Python 3.11+
- PostgreSQL with pgvector extension
- LM Studio running with an embedding model

See [POSTGRES_SETUP.md](POSTGRES_SETUP.md) for database setup instructions.

## Installation

```bash
# Clone repository
git clone https://github.com/talimoreno/md-kb.git
cd md-kb

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

Or with uv (recommended):

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

## Configuration

Create a `.env` file in the project directory:

```env
# Markdown directory to index
MDKB_DIR=/path/to/your/markdown/files

# PostgreSQL database
MDKB_DB_HOST=localhost
MDKB_DB_PORT=5432
MDKB_DB_NAME=md_kb
MDKB_DB_USER=mdkb_user
MDKB_DB_PASSWORD=your_password_here

# LM Studio embeddings
EMBEDDING_URL=http://127.0.0.1:1338/v1
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
EMBEDDING_DIMENSION=768

# Logging (MCP server and JSON-RPC server only)
MDKB_LOG_LEVEL=INFO
MDKB_LOG_LEVEL_CONSOLE=WARNING
MDKB_LOG_FILE=mcp.log
MDKB_LOG_MAX_BYTES=10485760
MDKB_LOG_BACKUP_COUNT=10
```

You can also place `.env` in `~/.config/mdkb/.env` for system-wide configuration.

## Usage

### CLI Mode

One-shot search with forced index refresh:

```bash
# Search for documents
mdkb search "python async programming"

# Limit results
mdkb search "machine learning" --limit 5

# Adjust similarity threshold (0.0-2.0, lower = more similar)
mdkb search "docker containers" --max-distance 0.3

# Enable verbose logging
mdkb --verbose search "kubernetes"
```

### MCP Server Mode

Long-lived server with continuous file watching:

```bash
# Start MCP server
mdkb --mcp

# Or with short flag
mdkb -m
```

The MCP server provides these tools:

- `search_markdown`: Semantic search with optional limit and max_distance
- `get_document_count`: Get total indexed document count
- `list_documents`: List all documents with pagination

### Configuration Priority

Configuration is loaded in this order:
1. `~/.config/mdkb/.env`
2. `.env` in current directory
3. Environment variables

## Logging

The MCP server and JSON-RPC server support comprehensive file logging with rotation:

### Log Configuration

Configure logging via environment variables:

- `MDKB_LOG_LEVEL`: File log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) - default: INFO
- `MDKB_LOG_LEVEL_CONSOLE`: Console log level - default: WARNING
- `MDKB_LOG_FILE`: Log file name (stored in `~/.config/mdkb/`) - default: mcp.log
- `MDKB_LOG_MAX_BYTES`: Maximum log file size in bytes before rotation - default: 10485760 (10MB)
- `MDKB_LOG_BACKUP_COUNT`: Number of backup log files to keep - default: 10

### Log Format

File logs include timestamps and caller info:
```
2026-01-08 14:30:45 - md_kb.indexer - INFO - indexer.py:123 - Indexed 5 documents
```

Console logs use a simpler format:
```
INFO: Indexed 5 documents
```

### Log Rotation

Logs automatically rotate when reaching `MDKB_LOG_MAX_BYTES`. Old logs are renamed with `.1`, `.2`, etc., and the oldest beyond `MDKB_LOG_BACKUP_COUNT` are deleted. For example:
- `mcp.log` (current)
- `mcp.log.1` (most recent backup)
- `mcp.log.2` (second most recent backup)
- ...
- `mcp.log.10` (oldest backup)

## How It Works

### Indexing

1. **Initial Scan**: Recursively scans markdown directory for `.md` files
2. **Checksum**: Computes SHA256 checksum for each file
3. **Upsert**: Insert new files or update changed files
4. **Cleanup**: Deletes database records for missing files

### File Watching

MCP server mode includes background file watching:
- Detects additions, modifications, and deletions
- Triggers immediate reindexing of affected files
- Uses FSEvents on macOS for high performance

### Search Flow

1. Generate embedding for search query
2. Use pgvector's IVFFlat index for similarity search
3. Return results with:
   - File path (reference to source)
   - Content snippet (context)
   - Similarity score

## Database Schema

```sql
CREATE TABLE markdown_documents (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    indexed_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_md_docs_embedding 
    ON markdown_documents USING ivfflat (embedding vector_cosine_ops);
```

## Troubleshooting

### Database Connection Failed

Check PostgreSQL is running and credentials are correct:

```bash
# Test connection
psql -h localhost -U mdkb_user -d md_kb -W
```

### Embedding Generation Failed

Ensure LM Studio is running and the correct port:

```bash
# Test LM Studio
curl http://127.0.0.1:1338/v1/models
```

### File Watcher Not Working

On macOS, ensure app has filesystem access permissions:
- System Preferences → Security & Privacy → Full Disk Access
- Add your terminal or Python application

### Large Memory Usage

For large document collections, consider:
- Reducing EMBEDDING_DIMENSION (if model supports it)
- Tuning PostgreSQL memory settings (see POSTGRES_SETUP.md)
- Using SSD for faster I/O

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check md_kb/

# Run type checking
mypy md_kb/

# Run tests
pytest
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please feel free to submit pull requests or open issues.
