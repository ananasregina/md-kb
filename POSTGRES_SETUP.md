# PostgreSQL + pgvector Setup Guide for Markdown Knowledge Base

The markdown knowledge base needs a proper home. This guide helps you set up PostgreSQL with pgvector extension for semantic search.

## Prerequisites

- macOS with Homebrew **OR** Linux with package manager
- LM Studio running with an embedding model
- Python 3.11+ (for markdown knowledge base)

---

## Installation

### macOS (Homebrew - Recommended)

1. **Install PostgreSQL**
    ```bash
    brew install postgresql@17
    brew services start postgresql@17
    ```

2. **Install pgvector extension**
    ```bash
    brew install pgvector
    ```

3. **Create database and user**
    ```bash
    # Create database
    psql postgres -c "CREATE DATABASE md_kb;"
    
    # Create user with password
    psql postgres -c "CREATE USER mdkb_user WITH PASSWORD 'your_secure_password';"
    
    # Grant privileges
    psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE md_kb TO mdkb_user;"
    psql postgres -c "ALTER USER mdkb_user CREATEDB;"
    
    # Grant schema privileges
    psql md_kb -c "GRANT ALL PRIVILEGES ON SCHEMA public TO mdkb_user;"
    psql md_kb -c "GRANT USAGE ON SCHEMA public TO mdkb_user;"
    ```

4. **Enable pgvector extension**
    ```bash
    psql md_kb -c "CREATE EXTENSION IF NOT EXISTS vector;"
    ```

5. **Verify installation**
    ```bash
    # Check if vector extension is loaded
    psql md_kb -c "\dx"
    
    # Should show something like:
    # Name    | Version |   Schema   |           Description
    # ---------+---------+------------+-----------------------------------
    # vector   | 0.5.1   | public     | vector data type and ivfflat/hnsw access methods
    ```

### Linux (apt/deb-based)

1. **Install PostgreSQL and development headers**
    ```bash
    sudo apt-get update
    sudo apt-get install postgresql postgresql-contrib libpq-dev
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    ```

2. **Install pgvector from source**
    ```bash
    # Clone pgvector repository
    git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
    cd pgvector
    
    # Build and install
    make
    sudo make install
    
    # Restart PostgreSQL
    sudo systemctl restart postgresql
    ```

3. **Create database and user**
    ```bash
    # Switch to postgres user
    sudo -u postgres psql
    
    # In psql shell:
    CREATE DATABASE md_kb;
    CREATE USER mdkb_user WITH PASSWORD 'your_secure_password';
    GRANT ALL PRIVILEGES ON DATABASE md_kb TO mdkb_user;
    ALTER USER mdkb_user CREATEDB;
    
    # Enable vector extension
    \c md_kb
    CREATE EXTENSION vector;
    
    # Grant schema privileges
    GRANT ALL PRIVILEGES ON SCHEMA public TO mdkb_user;
    GRANT USAGE ON SCHEMA public TO mdkb_user;
    
    # Exit
    \q
    ```

4. **Verify installation**
    ```bash
    sudo -u postgres psql -d md_kb -c "\dx"
    ```

### Linux (dnf/rpm-based)

1. **Install PostgreSQL and development headers**
    ```bash
    sudo dnf install postgresql postgresql-server postgresql-devel
    sudo postgresql-setup initdb
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    ```

2. **Install pgvector from source**
    ```bash
    # Same as apt-based (see above)
    git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
    cd pgvector
    make
    sudo make install
    sudo systemctl restart postgresql
    ```

3. **Create database and user**
    ```bash
    # Switch to postgres user
    sudo -u postgres psql
    
    # In psql shell (same as apt-based):
    CREATE DATABASE md_kb;
    CREATE USER mdkb_user WITH PASSWORD 'your_secure_password';
    GRANT ALL PRIVILEGES ON DATABASE md_kb TO mdkb_user;
    ALTER USER mdkb_user CREATEDB;
    \c md_kb
    CREATE EXTENSION vector;
    GRANT ALL PRIVILEGES ON SCHEMA public TO mdkb_user;
    GRANT USAGE ON SCHEMA public TO mdkb_user;
    \q
    ```

---

## Testing Configuration

### Test PostgreSQL Connection

```bash
# Test connection
psql -h localhost -U mdkb_user -d md_kb -W

# You should see psql prompt:
# md_kb=#
```

### Test pgvector Extension

```bash
psql md_kb -c "
SELECT 
    typname as type, 
    typlen as length 
FROM pg_type 
WHERE typname = 'vector';
"

# Should show:
#  type  | length
# -------+--------
#  vector |     16
```

---

## Environment Configuration

Add these variables to your `.env` file:

```bash
# PostgreSQL Database Configuration
MDKB_DB_HOST=localhost
MDKB_DB_PORT=5432
MDKB_DB_NAME=md_kb
MDKB_DB_USER=mdkb_user
MDKB_DB_PASSWORD=your_secure_password

# LM Studio Embeddings (for semantic search)
EMBEDDING_URL=http://127.0.0.1:1338/v1
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5-embedding
EMBEDDING_DIMENSION=768
```

### Important Security Note

- **Never commit `.env` to version control**
- Use strong, unique passwords
- Consider using a password manager
- If deploying, use environment variables instead of `.env`

---

## Creating a Test Database

For development and testing, create a separate test database:

```bash
# Create test database
psql postgres -c "CREATE DATABASE test_md_kb;"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE test_md_kb TO mdkb_user;"

# Enable vector extension on test database
psql test_md_kb -c "CREATE EXTENSION vector;"

# Grant schema privileges on test database
psql test_md_kb -c "GRANT ALL PRIVILEGES ON SCHEMA public TO mdkb_user;"
psql test_md_kb -c "GRANT USAGE ON SCHEMA public TO mdkb_user;"

# Update your .env for testing:
# MDKB_DB_NAME=test_md_kb
```

---

## Troubleshooting

### pgvector Extension Not Found

**Error**: `could not open extension control file "vector"`

**Solution**:
1. Verify pgvector is installed:
    ```bash
    brew list | grep pgvector  # macOS
    # or
    dpkg -l | grep pgvector  # Linux
    ```

2. Check PostgreSQL version compatibility:
    ```bash
    psql --version
    # pgvector 0.5.1 supports PostgreSQL 12-17
    ```

3. Reinstall pgvector:
    ```bash
    brew reinstall pgvector  # macOS
    # or
    cd pgvector && make clean && make && sudo make install  # Linux source
    ```

### Connection Refused

**Error**: `connection refused` or `could not connect to server`

**Solution**:
```bash
# Check PostgreSQL is running
brew services list | grep postgresql  # macOS
sudo systemctl status postgresql  # Linux

# Check logs
tail -f /usr/local/var/log/postgresql@17.log  # macOS
sudo journalctl -u postgresql  # Linux
```

### Permission Denied

**Error**: `permission denied for database md_kb` or `permission denied for schema public`

**Solution**:
```bash
# Grant database privileges
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE md_kb TO mdkb_user;"

# Grant schema privileges
psql md_kb -c "GRANT ALL PRIVILEGES ON SCHEMA public TO mdkb_user;"
psql md_kb -c "GRANT USAGE ON SCHEMA public TO mdkb_user;"
psql md_kb -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mdkb_user;"
psql md_kb -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mdkb_user;"
```

---

## Advanced Configuration (Optional)

### Tune PostgreSQL for Vector Workloads

For better performance with vector similarity search:

```bash
psql md_kb -c "
-- Increase work memory for index creation
ALTER SYSTEM SET maintenance_work_mem = '256MB';

-- Increase shared buffers for caching
ALTER SYSTEM SET shared_buffers = '512MB';

-- Reload configuration
SELECT pg_reload_conf();
"
```

### Enable Connection Pooling

For production deployments, consider using a connection pooler like PgBouncer:

```bash
# Install PgBouncer
brew install pgbouncer  # macOS
sudo apt-get install pgbouncer  # Linux

# Configure pgbouncer.ini
[databases]
md_kb = host=localhost port=5432 dbname=md_kb

[pgbouncer]
pool_mode = transaction
max_client_conn = 100
default_pool_size = 25
```

---

## Verification

Once PostgreSQL is set up, verify everything works:

```bash
# 1. Test database connection
python -c "
from md_kb.config import get_config
config = get_config()
print(f'Database URI: {config.get_postgres_uri()}')
"

# 2. Test embedding generation
python -c "
import asyncio
from md_kb.embeddings import EmbeddingService
async def test():
    service = EmbeddingService()
    emb = await service.generate_embedding('test markdown')
    print(f'Embedding dimension: {len(emb) if emb else \"Failed\"}')
asyncio.run(test())
"

# 3. Test database initialization
python -c "
import asyncio
from md_kb.database import init_db
asyncio.run(init_db())
print('Database initialized successfully!')
"
```

---

## Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgvector GitHub Repository](https://github.com/pgvector/pgvector)
- [LM Studio Documentation](https://lmstudio.ai/docs/developer)
- [Markdown Knowledge Base README](README.md)
