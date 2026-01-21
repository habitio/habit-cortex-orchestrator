# GitHub Authentication Setup Guide

## Why Do You Need a GitHub Token?

The orchestrator needs to access the **private** repository `habitio/bre-cortex` to:
1. **List available tags/versions** - Show UI which versions can be built
2. **Download source code** - Clone specific tag for Docker image building

### Without Token (Public Repos Only):
- ✅ Can access public repos like `fastapi/fastapi`
- ❌ Cannot access private repos like `habitio/bre-cortex`
- ⚠️  Rate limited to 60 requests/hour

### With Token:
- ✅ Can access private repos
- ✅ Rate limit increased to 5,000 requests/hour
- ✅ Full control over authentication

---

## Setup Instructions

### Step 1: Generate GitHub Personal Access Token

#### Option A: Fine-Grained Token (Recommended - More Secure)

1. Go to: https://github.com/settings/tokens?type=beta
2. Click **"Generate new token"**
3. Fill in:
   - **Token name**: `Cortex Orchestrator`
   - **Expiration**: 90 days (or custom)
   - **Repository access**: 
     - Select: **"Only select repositories"**
     - Choose: `habitio/bre-cortex`
   - **Permissions**:
     - ✅ **Contents**: Read-only
     - ✅ **Metadata**: Read-only
4. Click **"Generate token"**
5. **Copy the token** (starts with `github_pat_...`)

#### Option B: Classic Token (Simpler)

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Fill in:
   - **Note**: `Cortex Orchestrator`
   - **Expiration**: 90 days
   - **Scopes**: 
     - ✅ `repo` (Full control of private repositories)
4. Click **"Generate token"**
5. **Copy the token** (starts with `ghp_...`)

⚠️ **Important**: Copy the token now! You won't see it again.

---

### Step 2: Add Token to Environment

Edit the `.env` file:

```bash
cd /home/djsb/development/bre-tyres-01/cortex-orchestrator
nano .env
```

Add your token at the bottom:

```bash
# GitHub Integration (for private repos like habitio/bre-cortex)
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Replace** `ghp_xxxx...` with your actual token.

---

### Step 3: Restart Orchestrator

```bash
cd /home/djsb/development/bre-tyres-01/cortex-orchestrator
pkill -f orchestrator.main
./start.sh
```

Or manually:
```bash
source venv/bin/activate
python -m orchestrator.main
```

---

### Step 4: Test Authentication

#### Test 1: List Tags from Private Repo

```bash
curl "http://127.0.0.1:8004/api/v1/images/github-tags?repo=habitio/bre-cortex" | jq .
```

**Expected:** List of tags with commit details

**Without token:** 
```json
{
  "detail": "Failed to fetch GitHub tags: 404 Not Found"
}
```

**With token:**
```json
{
  "tags": [
    {
      "name": "v1.0.0",
      "commit": {
        "sha": "abc123...",
        "date": "2026-01-15T10:00:00Z",
        "author": "Your Name",
        "message": "Initial release"
      },
      "tarball_url": "https://..."
    }
  ]
}
```

#### Test 2: Check Health Endpoint

```bash
curl http://127.0.0.1:8004/health | jq .
```

Response should still show service running (Docker Swarm disconnection is separate issue).

---

## How It Works

### 1. Configuration Loading

File: `src/orchestrator/config.py`

```python
class Settings(BaseSettings):
    # ...
    github_token: str | None = Field(
        default=None,
        description="GitHub personal access token for private repo access",
    )
```

Loaded from `.env` file automatically.

### 2. GitHub Service Authentication

File: `src/orchestrator/services/github_service.py`

```python
class GitHubService:
    def __init__(self, token: str | None = None):
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
```

Token added to HTTP `Authorization` header for all GitHub API calls.

### 3. Usage in Endpoints

File: `src/orchestrator/routers/images.py`

```python
# List GitHub tags
@router.get("/github-tags")
def list_github_tags(repo: str = "habitio/bre-cortex"):
    github_service = GitHubService(token=settings.github_token)
    tags = github_service.list_tags(repo)
    ...

# Build image (background worker)
def build_worker():
    build_service = ImageBuildService(github_token=settings.github_token)
    build_service.build_from_github(...)
```

---

## Security Best Practices

### ✅ DO:
- Store token in `.env` file (gitignored)
- Use fine-grained tokens with minimal permissions
- Set token expiration (90 days max)
- Rotate tokens regularly
- Revoke old tokens when creating new ones

### ❌ DON'T:
- Commit token to git
- Share token in chat/email
- Use tokens with `admin` or `delete` permissions
- Use tokens without expiration
- Reuse tokens across multiple services

---

## Troubleshooting

### Problem: "404 Not Found" when listing tags

**Cause**: No token or invalid token for private repo

**Solution**:
1. Check `.env` has `GITHUB_TOKEN=...`
2. Verify token is valid: https://github.com/settings/tokens
3. Check token has `repo` or `contents:read` permission
4. Restart orchestrator after adding token

### Problem: "403 API rate limit exceeded"

**Cause**: Token not being used, or expired

**Solution**:
1. Add valid token to `.env`
2. Check token hasn't expired
3. Restart orchestrator

### Problem: Token not loading

**Solution**:
```bash
cd /home/djsb/development/bre-tyres-01/cortex-orchestrator
source venv/bin/activate
python -c "from orchestrator.config import settings; print(settings.github_token)"
```

Should print your token (not `None`).

---

## Example: Full Workflow with Private Repo

```bash
# 1. Set up token
echo 'GITHUB_TOKEN=ghp_xxxYourTokenHerexxx' >> .env

# 2. Restart orchestrator
./start.sh

# 3. List available versions
curl "http://127.0.0.1:8004/api/v1/images/github-tags?repo=habitio/bre-cortex" | jq '.tags[0:3]'

# 4. Trigger build of specific version
curl -X POST http://127.0.0.1:8004/api/v1/images \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "habitio/bre-cortex",
    "tag": "v1.0.0",
    "commit_sha": "abc123def456...",
    "image_name": "bre-cortex"
  }' | jq .

# 5. Monitor build progress
curl http://127.0.0.1:8004/api/v1/images/1 | jq '.build_status, .build_log'

# 6. Create product with built image
curl -X POST http://127.0.0.1:8004/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Allianz Insurance",
    "slug": "allianz",
    "port": 8001,
    "image_id": 1,
    "env_vars": {
      "DATABASE_URL": "postgresql://...",
      "PLATFORM_API_KEY": "secret"
    }
  }' | jq .
```

---

## Token Permissions Reference

### Minimum Permissions Required:

**For Fine-Grained Token:**
- Repository: `habitio/bre-cortex` (only)
- Permissions:
  - Contents: **Read** (to download source code)
  - Metadata: **Read** (to list tags, get commit info)

**For Classic Token:**
- Scope: `repo` (full private repo access)

### What Each Permission Enables:

| Permission | Allows |
|-----------|--------|
| **Contents: Read** | Download tarballs, read files |
| **Metadata: Read** | List tags, get commit details, repo info |
| ❌ **Write/Admin** | NOT needed (orchestrator is read-only) |

---

## Environment Variable Reference

```bash
# .env file format

# Required for private repo access
GITHUB_TOKEN=ghp_yourTokenHere

# Optional: Override default repo in UI
DEFAULT_GITHUB_REPO=habitio/bre-cortex
```

---

## Next Steps

After setting up authentication:

1. ✅ **Verify token works**: Test listing tags from private repo
2. ⬜ **Initialize Docker Swarm**: `docker swarm init` (separate issue)
3. ⬜ **Build first image**: Trigger build from UI or API
4. ⬜ **Deploy product**: Create product using built image

---

## Summary

✅ **Implementation Complete:**
- GitHub token configuration added to `config.py`
- Token passed to `GitHubService` in all endpoints
- Token used for authentication in API requests
- Works for both private and public repositories

🔐 **Security:**
- Token stored in `.env` file (gitignored)
- Fine-grained permissions supported
- Read-only access to repositories
- Token expiration recommended

📝 **Usage:**
- Add `GITHUB_TOKEN=xxx` to `.env`
- Restart orchestrator
- Test with `habitio/bre-cortex` repository
