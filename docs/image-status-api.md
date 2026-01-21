# Image Status & Build Tracking API

Complete API reference for tracking Docker image builds in the UI.

## Build Status Lifecycle

```
POST /api/v1/images
    ↓
[pending] → Image record created, build queued
    ↓
[building] → Background worker started, logs streaming
    ↓
[success] ✅ Build completed, image ready to use
    OR
[failed] ❌ Build error, check build_error field
```

---

## API Endpoints for UI

### 1. List All Images with Status

```http
GET /api/v1/images
GET /api/v1/images?status_filter=success
GET /api/v1/images?status_filter=building
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "bre-payments",
    "tag": "v1.2.3",
    "github_repo": "habit-analytics/bre-payments",
    "github_ref": "refs/tags/v1.2.3",
    "commit_sha": "abc123def456...",
    "build_status": "success",
    "build_log": null,
    "build_error": null,
    "built_at": "2026-01-21T15:45:00Z",
    "created_at": "2026-01-21T15:30:00Z"
  },
  {
    "id": 2,
    "name": "bre-payments",
    "tag": "v1.2.2",
    "github_repo": "habit-analytics/bre-payments",
    "github_ref": "refs/tags/v1.2.2",
    "commit_sha": "def456abc789...",
    "build_status": "building",
    "build_log": "Step 5/12 : RUN pip install...",
    "build_error": null,
    "built_at": null,
    "created_at": "2026-01-21T16:00:00Z"
  },
  {
    "id": 3,
    "name": "bre-payments",
    "tag": "v1.2.1",
    "github_repo": "habit-analytics/bre-payments",
    "github_ref": "refs/tags/v1.2.1",
    "commit_sha": "789abc012def...",
    "build_status": "failed",
    "build_log": "Step 3/12 : RUN pip install...\nERROR: ...",
    "build_error": "Docker build failed: exit code 1",
    "built_at": null,
    "created_at": "2026-01-20T10:00:00Z"
  }
]
```

**Query Parameters:**
- `status_filter` - Filter by build status (pending, building, success, failed)

**Use Cases:**
- Dashboard showing all built images
- Filter to only show successful builds for product selection
- Show currently building images with progress indicator

---

### 2. Get Single Image with Full Details

```http
GET /api/v1/images/{id}
```

**Response:**
```json
{
  "id": 2,
  "name": "bre-payments",
  "tag": "v1.2.2",
  "github_repo": "habit-analytics/bre-payments",
  "github_ref": "refs/tags/v1.2.2",
  "commit_sha": "def456abc789...",
  "build_status": "building",
  "build_log": "Sending build context to Docker daemon...\nStep 1/12 : FROM python:3.12-slim\n ---> abc123def456\nStep 2/12 : WORKDIR /app\n ---> Running in xyz789...\n ---> def456abc123\nStep 3/12 : COPY requirements.txt .\n ---> 123abc456def\nStep 4/12 : RUN pip install --no-cache-dir -r requirements.txt\nCollecting fastapi...\nCollecting uvicorn...\n[... continuing build output ...]\n",
  "build_error": null,
  "built_at": null,
  "created_at": "2026-01-21T16:00:00Z"
}
```

**Use Cases:**
- Poll this endpoint every 3-5 seconds while build_status is "building"
- Display real-time build logs in terminal viewer
- Show error details if build fails

---

### 3. Trigger New Build

```http
POST /api/v1/images
Content-Type: application/json

{
  "repo": "habit-analytics/bre-payments",
  "tag": "v1.2.3",
  "commit_sha": "abc123def456...",
  "image_name": "bre-payments"
}
```

**Response (201 Created):**
```json
{
  "id": 4,
  "name": "bre-payments",
  "tag": "v1.2.3",
  "github_repo": "habit-analytics/bre-payments",
  "github_ref": "refs/tags/v1.2.3",
  "commit_sha": "abc123def456...",
  "build_status": "pending",
  "build_log": null,
  "build_error": null,
  "built_at": null,
  "created_at": "2026-01-21T16:05:00Z"
}
```

**Note:** Build status changes from "pending" → "building" within 1-2 seconds as the background worker picks it up.

---

### 4. List GitHub Tags (Before Building)

```http
GET /api/v1/images/github-tags?repo=habit-analytics/bre-payments
```

**Response:**
```json
{
  "tags": [
    {
      "name": "v1.2.3",
      "commit": {
        "sha": "abc123def456...",
        "url": "https://api.github.com/repos/habit-analytics/bre-payments/git/commits/abc123...",
        "date": "2026-01-20T10:00:00Z",
        "author": "John Doe",
        "message": "Fix payment processing bug"
      },
      "zipball_url": "https://api.github.com/repos/habit-analytics/bre-payments/zipball/v1.2.3",
      "tarball_url": "https://api.github.com/repos/habit-analytics/bre-payments/tarball/v1.2.3"
    },
    {
      "name": "v1.2.2",
      "commit": {
        "sha": "def456abc789...",
        "url": "https://api.github.com/repos/habit-analytics/bre-payments/git/commits/def456...",
        "date": "2026-01-15T14:30:00Z",
        "author": "Jane Smith",
        "message": "Add new payment provider"
      },
      "zipball_url": "https://api.github.com/repos/habit-analytics/bre-payments/zipball/v1.2.2",
      "tarball_url": "https://api.github.com/repos/habit-analytics/bre-payments/tarball/v1.2.2"
    }
  ]
}
```

**Use Cases:**
- Populate dropdown in "Build New Image" modal
- Show commit details (author, date, message) to help user select version
- Display commit SHA short form (first 7 chars)

---

### 5. Delete Image Record

```http
DELETE /api/v1/images/{id}
```

**Response (204 No Content):**
```
(empty response)
```

**Note:** Only deletes the database record, not the actual Docker image. Use for cleanup of failed builds or old entries.

---

## UI Implementation Examples

### Real-Time Build Monitor Component

```typescript
const BuildMonitor: React.FC<{ imageId: number }> = ({ imageId }) => {
  const [image, setImage] = useState(null);
  const [isPolling, setIsPolling] = useState(true);
  
  useEffect(() => {
    if (!isPolling) return;
    
    const fetchStatus = async () => {
      const response = await fetch(`/api/v1/images/${imageId}`);
      const data = await response.json();
      setImage(data);
      
      // Stop polling when build finishes
      if (data.build_status === 'success' || data.build_status === 'failed') {
        setIsPolling(false);
      }
    };
    
    fetchStatus(); // Initial fetch
    const interval = setInterval(fetchStatus, 3000); // Poll every 3 seconds
    
    return () => clearInterval(interval);
  }, [imageId, isPolling]);
  
  if (!image) return <div>Loading...</div>;
  
  return (
    <div className="build-monitor">
      <div className="status">
        Status: {image.build_status === 'building' && '🔄 Building...'}
        {image.build_status === 'success' && '✅ Success'}
        {image.build_status === 'failed' && '❌ Failed'}
      </div>
      
      <div className="log-viewer">
        <pre>{image.build_log || 'Waiting for build to start...'}</pre>
      </div>
      
      {image.build_error && (
        <div className="error">
          <strong>Error:</strong> {image.build_error}
        </div>
      )}
    </div>
  );
};
```

### Docker Images Dashboard

```typescript
const ImagesDashboard: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  
  const { data: images, isLoading } = useQuery({
    queryKey: ['images', statusFilter],
    queryFn: () => {
      const url = statusFilter 
        ? `/api/v1/images?status_filter=${statusFilter}`
        : '/api/v1/images';
      return fetch(url).then(r => r.json());
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });
  
  return (
    <div className="images-dashboard">
      <div className="filters">
        <button onClick={() => setStatusFilter(null)}>All</button>
        <button onClick={() => setStatusFilter('success')}>Successful</button>
        <button onClick={() => setStatusFilter('building')}>Building</button>
        <button onClick={() => setStatusFilter('failed')}>Failed</button>
      </div>
      
      <table>
        <thead>
          <tr>
            <th>Image</th>
            <th>Tag</th>
            <th>Status</th>
            <th>Built</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {images?.map(img => (
            <tr key={img.id}>
              <td>{img.name}</td>
              <td>
                {img.tag}
                <br />
                <small>{img.commit_sha.slice(0, 7)}</small>
              </td>
              <td>
                <StatusBadge status={img.build_status} />
              </td>
              <td>
                {img.built_at ? formatDate(img.built_at) : '-'}
              </td>
              <td>
                <button onClick={() => viewLogs(img.id)}>View Logs</button>
                {img.build_status === 'failed' && (
                  <button onClick={() => retryBuild(img)}>Retry</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

### Image Selector in Product Form

```typescript
const ProductForm: React.FC = () => {
  const [selectedImageId, setSelectedImageId] = useState<number | null>(null);
  
  // Only show successfully built images
  const { data: images } = useQuery({
    queryKey: ['images', 'success'],
    queryFn: () => fetch('/api/v1/images?status_filter=success').then(r => r.json()),
  });
  
  return (
    <form>
      {/* ... other fields ... */}
      
      <div className="form-field">
        <label>Docker Image Version</label>
        <select 
          value={selectedImageId || ''} 
          onChange={(e) => setSelectedImageId(Number(e.target.value))}
        >
          <option value="">Default (latest)</option>
          {images?.map(img => (
            <option key={img.id} value={img.id}>
              {img.name}:{img.tag} - Built {formatTimeAgo(img.built_at)}
            </option>
          ))}
        </select>
        <small>
          Select a specific version or use the default latest image
        </small>
      </div>
      
      {/* ... env vars, etc ... */}
    </form>
  );
};
```

---

## Status Field Values

| Status | Meaning | UI Display | Actions Available |
|--------|---------|------------|-------------------|
| `pending` | Build queued, not started yet | 🟡 Pending | Cancel, View Details |
| `building` | Build in progress | 🔵 Building... (spinner) | View Live Logs, Cancel |
| `success` | Build completed successfully | ✅ Success | View Logs, Use in Product, Delete |
| `failed` | Build encountered error | ❌ Failed | View Error, Retry, Delete |

---

## Polling Best Practices

1. **When to poll:**
   - Only poll when build_status is "pending" or "building"
   - Stop polling when status becomes "success" or "failed"

2. **Polling interval:**
   - Every 3-5 seconds for individual image
   - Every 5-10 seconds for images list
   - Use exponential backoff if build takes very long (rare)

3. **Memory/performance:**
   - Limit log display to last 500 lines in UI
   - Provide "Download Full Log" button for complete output
   - Use React Query or similar for automatic cache management

---

## Complete Workflow Example

**User wants to deploy version v1.2.3 of bre-payments:**

```typescript
async function buildAndDeployVersion() {
  // Step 1: List available tags
  const tagsResponse = await fetch(
    '/api/v1/images/github-tags?repo=habit-analytics/bre-payments'
  );
  const { tags } = await tagsResponse.json();
  
  // User selects v1.2.3
  const selectedTag = tags.find(t => t.name === 'v1.2.3');
  
  // Step 2: Trigger build
  const buildResponse = await fetch('/api/v1/images', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      repo: 'habit-analytics/bre-payments',
      tag: 'v1.2.3',
      commit_sha: selectedTag.commit.sha,
      image_name: 'bre-payments'
    })
  });
  const newImage = await buildResponse.json();
  
  // Step 3: Poll for build completion
  let buildComplete = false;
  while (!buildComplete) {
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    const statusResponse = await fetch(`/api/v1/images/${newImage.id}`);
    const imageStatus = await statusResponse.json();
    
    console.log('Build status:', imageStatus.build_status);
    console.log('Latest log:', imageStatus.build_log?.split('\n').slice(-5).join('\n'));
    
    if (imageStatus.build_status === 'success') {
      buildComplete = true;
      console.log('✅ Build successful!');
    } else if (imageStatus.build_status === 'failed') {
      buildComplete = true;
      console.error('❌ Build failed:', imageStatus.build_error);
      throw new Error('Build failed');
    }
  }
  
  // Step 4: Create product using the built image
  const productResponse = await fetch('/api/v1/products', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: 'Allianz Insurance',
      slug: 'allianz',
      port: 8001,
      replicas: 2,
      image_id: newImage.id,  // Reference the built image
      env_vars: {
        DATABASE_URL: 'postgresql://...',
        PLATFORM_API_KEY: 'secret'
      }
    })
  });
  const product = await productResponse.json();
  
  // Step 5: Deploy the product
  await fetch(`/api/v1/products/${product.id}/start`, { method: 'POST' });
  
  console.log('✅ Product deployed with version v1.2.3!');
}
```

---

## Testing the API

```bash
# List all images
curl http://127.0.0.1:8004/api/v1/images | jq .

# Filter successful builds only
curl "http://127.0.0.1:8004/api/v1/images?status_filter=success" | jq .

# Get specific image details
curl http://127.0.0.1:8004/api/v1/images/1 | jq .

# List GitHub tags
curl "http://127.0.0.1:8004/api/v1/images/github-tags?repo=fastapi/fastapi" | jq '.tags[:3]'

# Trigger build (replace with your repo)
curl -X POST http://127.0.0.1:8004/api/v1/images \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "habit-analytics/bre-payments",
    "tag": "v1.0.0",
    "commit_sha": "abc123def456...",
    "image_name": "bre-payments"
  }' | jq .

# Poll build status
watch -n 3 'curl -s http://127.0.0.1:8004/api/v1/images/1 | jq ".build_status, .build_log"'
```
