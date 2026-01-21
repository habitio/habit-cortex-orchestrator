# Docker Image Building & Selection - Implementation Complete ✅

All backend work for Docker image building and image selection has been implemented!

## What Was Implemented

### 1. Database Schema ✅
- **`docker_images` table** - Stores built Docker images
  - Tracks build status (pending → building → success/failed)
  - Stores GitHub repo, tag, commit SHA
  - Stores build logs and errors
- **`products.image_id`** - Foreign key to docker_images
- **`products.image_name`** - Full image name (e.g., "bre-payments:v1.2.3")

### 2. GitHub Integration ✅
**File:** `src/orchestrator/services/github_service.py`

- `list_tags(repo)` - List all tags from a GitHub repository
- `get_commit_details(repo, sha)` - Get commit details (author, date, message)
- `download_tarball(repo, ref)` - Download repository source code

### 3. Docker Build Service ✅
**File:** `src/orchestrator/services/image_build_service.py`

- `build_from_github()` - Build Docker image from GitHub repository tag
  - Downloads repo tarball
  - Extracts to temp directory
  - Runs `docker build`
  - Streams build logs in real-time
  - Cleans up after build
- `list_local_images()` - List images on Docker host
- `remove_image()` - Remove Docker image

### 4. Images API Router ✅
**File:** `src/orchestrator/routers/images.py`

**Endpoints:**
```
GET  /api/v1/images/github-tags?repo=owner/repo  # List GitHub tags
POST /api/v1/images                               # Trigger image build
GET  /api/v1/images                               # List built images
GET  /api/v1/images/{id}                          # Get image details
DELETE /api/v1/images/{id}                        # Delete image record
```

### 5. Background Build System ✅
- Uses Python threading for async builds
- Updates database in real-time with build progress
- Stores complete build logs
- Handles errors gracefully

### 6. Products Integration ✅
**Updated:**
- `ProductCreate` schema - accepts `image_id`
- `ProductUpdate` schema - can change image
- `ProductResponse` schema - returns `image_id` and `image_name`
- `create_product()` - validates image exists and build succeeded
- `update_product()` - validates new image if changed
- `DockerManager.create_service()` - uses `product.image_name` instead of hardcoded

---

## API Usage Examples

### 1. List Available GitHub Tags

```bash
GET /api/v1/images/github-tags?repo=habit-analytics/bre-payments

Response:
{
  "tags": [
    {
      "name": "v1.2.3",
      "commit": {
        "sha": "abc123...",
        "date": "2026-01-20T10:00:00Z",
        "author": "John Doe",
        "message": "Fixed payment processing bug"
      },
      "tarball_url": "https://..."
    },
    ...
  ]
}
```

### 2. Trigger Image Build

```bash
POST /api/v1/images
{
  "repo": "habit-analytics/bre-payments",
  "tag": "v1.2.3",
  "commit_sha": "abc123def456...",
  "image_name": "bre-payments"
}

Response 201:
{
  "id": 1,
  "name": "bre-payments",
  "tag": "v1.2.3",
  "github_repo": "habit-analytics/bre-payments",
  "build_status": "pending",  // Will become "building" → "success"/"failed"
  "build_log": null,
  "created_at": "2026-01-21T15:30:00Z"
}
```

**Build happens in background thread!** Poll for status updates.

### 3. Check Build Status

```bash
GET /api/v1/images/1

Response:
{
  "id": 1,
  "name": "bre-payments",
  "tag": "v1.2.3",
  "build_status": "building",  // or "success"/"failed"
  "build_log": "Step 1/10 : FROM python:3.12\n...",
  "build_error": null,
  "built_at": null
}
```

### 4. List All Built Images

```bash
GET /api/v1/images

Response:
[
  {
    "id": 1,
    "name": "bre-payments",
    "tag": "v1.2.3",
    "build_status": "success",
    "built_at": "2026-01-21T15:35:00Z"
  },
  {
    "id": 2,
    "name": "bre-payments",
    "tag": "v1.2.2",
    "build_status": "success",
    "built_at": "2026-01-20T10:00:00Z"
  }
]
```

### 5. Create Product with Specific Image

```bash
POST /api/v1/products
{
  "name": "Allianz Insurance",
  "slug": "allianz",
  "port": 8001,
  "replicas": 2,
  "image_id": 1,  // Use bre-payments:v1.2.3
  "env_vars": {
    "DATABASE_URL": "postgresql://...",
    "PLATFORM_API_KEY": "secret"
  }
}

Response 201:
{
  "id": 1,
  "name": "Allianz Insurance",
  "slug": "allianz",
  "image_id": 1,
  "image_name": "bre-payments:v1.2.3",  // Resolved from image_id
  "status": "stopped"
}
```

### 6. Deploy Product (Uses Selected Image)

```bash
POST /api/v1/products/1/start

# Docker Swarm will deploy using "bre-payments:v1.2.3"
# (Not the default "bre-payments:latest")
```

---

## Complete Workflow

### Scenario: Deploy New Version of Insurance Product

**Step 1:** Check available versions on GitHub
```bash
GET /api/v1/images/github-tags?repo=habit-analytics/bre-payments
# Shows: v1.2.3, v1.2.2, v1.2.1...
```

**Step 2:** Build v1.2.3
```bash
POST /api/v1/images
{
  "repo": "habit-analytics/bre-payments",
  "tag": "v1.2.3",
  "commit_sha": "abc123...",
  "image_name": "bre-payments"
}
# Response: { "id": 5, "build_status": "pending" }
```

**Step 3:** Monitor build progress
```bash
GET /api/v1/images/5
# Poll every 5 seconds until build_status becomes "success"
```

**Step 4:** Create product using new image
```bash
POST /api/v1/products
{
  "name": "AXA Insurance",
  "slug": "axa",
  "port": 8002,
  "image_id": 5,  // Points to bre-payments:v1.2.3
  "env_vars": {
    "DATABASE_URL": "postgresql://axa_db",
    "PLATFORM_API_KEY": "axa_key"
  }
}
```

**Step 5:** Deploy the product
```bash
POST /api/v1/products/1/start
# Deploys using bre-payments:v1.2.3 with AXA-specific env vars
```

---

## Database Schema

### docker_images Table
```sql
CREATE TABLE docker_images (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,              -- "bre-payments"
    tag VARCHAR(100) NOT NULL,               -- "v1.2.3"
    github_repo VARCHAR(255) NOT NULL,       -- "habit-analytics/bre-payments"
    github_ref VARCHAR(255) NOT NULL,        -- "refs/tags/v1.2.3"
    commit_sha VARCHAR(40) NOT NULL,         -- "abc123def456..."
    build_status VARCHAR(50) NOT NULL,       -- pending/building/success/failed
    build_log TEXT,                          -- Complete build output
    build_error TEXT,                        -- Error message if failed
    built_at TIMESTAMP WITH TIME ZONE,       -- When build completed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, tag)  -- Only one build per image:tag
);
```

### products Table (Updated)
```sql
ALTER TABLE products 
  ADD COLUMN image_id INTEGER REFERENCES docker_images(id),
  ADD COLUMN image_name VARCHAR(255) DEFAULT 'bre-payments:latest';
```

---

## Files Created/Modified

**New Files:**
- `src/orchestrator/services/github_service.py` - GitHub API client
- `src/orchestrator/services/image_build_service.py` - Docker build logic
- `src/orchestrator/routers/images.py` - Images API endpoints

**Modified Files:**
- `src/orchestrator/database/models.py` - Added DockerImage model, updated Product
- `src/orchestrator/routers/products.py` - Added image_id support
- `src/orchestrator/services/docker_manager.py` - Uses product.image_name
- `src/orchestrator/main.py` - Registered images router
- `pyproject.toml` - Added requests dependency

**Database Migrations:**
- Created `docker_images` table
- Added `image_id` and `image_name` columns to `products`

---

## Testing

```bash
# 1. Test GitHub tags listing (using public repo)
curl -s "http://127.0.0.1:8004/api/v1/images/github-tags?repo=fastapi/fastapi" | jq '.tags[:3]'

# 2. List built images (should be empty initially)
curl -s http://127.0.0.1:8004/api/v1/images | jq .

# 3. TODO: Trigger actual build (need valid GitHub repo with Dockerfile)
# POST /api/v1/images with your repo details

# 4. Create product with default image
curl -X POST http://127.0.0.1:8004/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Product",
    "slug": "test",
    "port": 8001,
    "env_vars": {"TEST": "value"}
  }' | jq .
```

---

## Next Steps for UI

The UI can now:

1. **Show GitHub Tags** - Call `GET /api/v1/images/github-tags`
2. **Trigger Builds** - Call `POST /api/v1/images`
3. **Monitor Progress** - Poll `GET /api/v1/images/{id}` every 5s
4. **List Images** - Call `GET /api/v1/images` 
5. **Select Image** - Pass `image_id` when creating products

See `docs/ui-extensions-guide.md` for complete UI implementation details.

---

## Known Limitations

1. **No Queue System** - Builds run in threads, not production-ready
   - For production: Use Celery + Redis
   
2. **No Build Cancellation** - Once started, build runs to completion

3. **No Docker Registry** - Images only stored locally
   - For production: Push to Docker registry after build

4. **No Cleanup** - Failed builds leave temp files
   - Added cleanup in finally block, but may fail on errors

5. **No Authentication** - GitHub API has rate limits
   - Add GitHub token for higher limits

---

## Production Improvements (Future)

- [ ] Use Celery for background builds
- [ ] Add build queue management
- [ ] Push images to Docker registry
- [ ] Add build cancellation
- [ ] Add webhook support (auto-build on GitHub push)
- [ ] Add image scanning for vulnerabilities
- [ ] Add rollback support (deploy previous image)
- [ ] Add blue-green deployments
