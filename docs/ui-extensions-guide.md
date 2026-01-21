# UI Extensions Guide - Phase 2 Features

This document outlines the extensions needed for the UI to support:
1. Environment variables configuration
2. Log viewing for deployed instances
3. Docker image building from GitHub tags
4. Image selection when creating products

---

## 1. Environment Variables Configuration

### ✅ Backend Status: IMPLEMENTED

**Database:**
- `products.env_vars` - JSONB column storing key-value pairs

**API Endpoints:**
```typescript
// Create product with environment variables
POST /api/v1/products
{
  "name": "Allianz Insurance",
  "slug": "allianz",
  "port": 8001,
  "replicas": 2,
  "env_vars": {
    "DATABASE_URL": "postgresql://user:pass@host:5432/allianz",
    "MUZZLEY_API_URL": "https://api.habit.io",
    "PLATFORM_API_KEY": "secret-key-123",
    "MQTT_BROKER": "mqtt://broker.habit.io:1883",
    "REDIS_URL": "redis://localhost:6379/0"
  }
}

// Update environment variables
PATCH /api/v1/products/{id}
{
  "env_vars": {
    "DATABASE_URL": "postgresql://updated-connection"
  }
}

// Get product (includes env_vars)
GET /api/v1/products/{id}
{
  "id": 1,
  "name": "Allianz Insurance",
  "slug": "allianz",
  "port": 8001,
  "env_vars": {
    "DATABASE_URL": "postgresql://...",
    ...
  },
  ...
}
```

### UI Implementation Needed:

**1. Product Form Component** (Create/Edit screens)

Add a **Key-Value Editor** component:

```typescript
interface EnvVarField {
  key: string;
  value: string;
  isSecret?: boolean; // For password/API key fields
}

// Component state
const [envVars, setEnvVars] = useState<EnvVarField[]>([
  { key: '', value: '', isSecret: false }
]);

// Convert to API format
const apiEnvVars = envVars.reduce((acc, { key, value }) => {
  if (key.trim()) acc[key] = value;
  return acc;
}, {} as Record<string, string>);
```

**Component Features:**
- Add/Remove row buttons
- Key input (uppercase, underscores, numbers only)
- Value input with toggle for password visibility
- Validation:
  - No duplicate keys
  - Required keys: `DATABASE_URL`, `MUZZLEY_API_URL`, `PLATFORM_API_KEY`
- Template button to auto-fill common variables

**UI Mockup:**
```
┌─────────────────────────────────────────────────┐
│ Environment Variables                           │
├─────────────────────────────────────────────────┤
│ Key                  Value                   📋 │
│ ┌─────────────┐     ┌──────────────────┐   ❌  │
│ │DATABASE_URL │     │postgresql://...  │       │
│ └─────────────┘     └──────────────────┘       │
│ ┌─────────────┐     ┌──────────────────┐   ❌  │
│ │PLATFORM_KEY │  🔒 │*************     │       │
│ └─────────────┘     └──────────────────┘       │
│                                                 │
│ [+ Add Variable]  [Load Template ▼]            │
└─────────────────────────────────────────────────┘
```

---

## 2. Log Viewing for Deployed Instances

### ✅ Backend Status: IMPLEMENTED

**API Endpoint:**
```typescript
GET /api/v1/products/{id}/logs?tail=100

Response:
{
  "product_id": 1,
  "product_name": "Allianz Insurance",
  "service_id": "abc123...",
  "logs": "2026-01-21 15:30:00 INFO: Starting application...\n2026-01-21 15:30:01 INFO: Connected to database\n...",
  "lines": 100
}
```

**Query Parameters:**
- `tail` - Number of lines from end (default: 100, max: 1000)

### UI Implementation Needed:

**1. Add "View Logs" button** to Product List screen (for running products)

**2. Create "Product Logs" modal/screen:**

```typescript
interface LogViewerProps {
  productId: number;
  onClose: () => void;
}

const LogViewer: React.FC<LogViewerProps> = ({ productId, onClose }) => {
  const [tail, setTail] = useState(100);
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // Fetch logs every 5 seconds if autoRefresh is on
  const { data, isLoading } = useQuery({
    queryKey: ['product-logs', productId, tail],
    queryFn: () => api.get(`/api/v1/products/${productId}/logs?tail=${tail}`),
    refetchInterval: autoRefresh ? 5000 : false,
  });
  
  return (
    <div className="log-viewer">
      <div className="controls">
        <select value={tail} onChange={(e) => setTail(Number(e.target.value))}>
          <option value={50}>Last 50 lines</option>
          <option value={100}>Last 100 lines</option>
          <option value={500}>Last 500 lines</option>
          <option value={1000}>Last 1000 lines</option>
        </select>
        <label>
          <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
          Auto-refresh
        </label>
        <button onClick={() => window.open(`/api/v1/products/${productId}/logs?tail=10000`, '_blank')}>
          Download Full Log
        </button>
      </div>
      <pre className="log-content">
        {data?.logs || 'Loading...'}
      </pre>
    </div>
  );
};
```

**Features:**
- Monospace font, dark theme
- Auto-scroll to bottom
- Auto-refresh toggle (5s interval)
- Line count selector
- Color-coded log levels (INFO=blue, WARN=yellow, ERROR=red)
- Download full log button

---

## 3. Docker Image Building from GitHub

### ✅ Backend Status: FULLY IMPLEMENTED

**Database Schema:**

```sql
-- New table to track Docker images
CREATE TABLE docker_images (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,           -- e.g., "bre-payments"
    tag VARCHAR(100) NOT NULL,            -- e.g., "v1.2.3", "main-abc123"
    github_repo VARCHAR(255) NOT NULL,    -- e.g., "myorg/bre-payments"
    github_ref VARCHAR(255) NOT NULL,     -- e.g., "refs/tags/v1.2.3"
    commit_sha VARCHAR(40) NOT NULL,      -- Git commit hash
    build_status VARCHAR(50) NOT NULL,    -- building, success, failed
    build_log TEXT,                       -- Build output
    built_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, tag)
);

-- ✅ Products table already updated
ALTER TABLE products 
  ADD COLUMN image_id INTEGER REFERENCES docker_images(id),
  ADD COLUMN image_name VARCHAR(255) DEFAULT 'bre-payments:latest';
```

**✅ API Endpoints Available:**

```typescript
// 1. List available GitHub tags (TESTED ✅)
GET /api/v1/images/github-tags?repo=myorg/bre-payments
Response: {
  "tags": [
    {
      "name": "v1.2.3",
      "commit": { "sha": "abc123...", "date": "2026-01-15T10:00:00Z" },
      "url": "https://github.com/myorg/bre-payments/tree/v1.2.3"
    },
    { "name": "v1.2.2", ... },
    { "name": "v1.2.1", ... }
  ]
}

// 2. Trigger image build (BACKGROUND WORKER ✅)
POST /api/v1/images
{
  "repo": "myorg/bre-payments",
  "tag": "v1.2.3",
  "commit_sha": "abc123...",
  "image_name": "bre-payments"
}
Response 201: {
  "id": 5,
  "name": "bre-payments",
  "tag": "v1.2.3",
  "github_repo": "myorg/bre-payments",
  "github_ref": "refs/tags/v1.2.3",
  "commit_sha": "abc123...",
  "build_status": "pending",  // Immediately becomes "building" in background
  "build_log": null,
  "build_error": null,
  "created_at": "2026-01-21T15:30:00Z"
}

// 3. Get build status/logs (POLL THIS FOR PROGRESS ✅)
GET /api/v1/images/{id}
Response: {
  "id": 5,
  "name": "bre-payments",
  "tag": "v1.2.3",
  "build_status": "success",
  "build_log": "Step 1/10 : FROM python:3.12...\n...",
  "built_at": "2026-01-21T15:45:00Z"
}

// 4. List all images with status filter (TESTED ✅)
GET /api/v1/images?status_filter=success
Response: [
  {
    "id": 5,
    "name": "bre-payments",
    "tag": "v1.2.3",
    "github_repo": "myorg/bre-payments",
    "build_status": "success",  // Can be: pending, building, success, failed
    "built_at": "2026-01-21T15:45:00Z",
    "created_at": "2026-01-21T15:30:00Z"
  }
]

// 5. Delete image record
DELETE /api/v1/images/{id}
Response 204: No content

```

**✅ Backend Implementation Complete:**

1. ✅ Created `docker_images` table and DockerImage model
2. ✅ GitHub API integration (`services/github_service.py`)
3. ✅ Docker build service (`services/image_build_service.py`)
4. ✅ Background workers using Python threading
5. ✅ Real-time build log streaming to database
6. ✅ Complete REST API (`routers/images.py`)

**Key Build Status Values:**
- `pending` - Build queued, not started yet
- `building` - Build in progress (check build_log for live output)
- `success` - Build completed successfully
- `failed` - Build failed (check build_error for details)

### UI Implementation Needed:

**1. New "Docker Images" Screen:**

```
┌────────────────────────────────────────────────────────┐
│ Docker Images                        [+ Build New Image]│
├────────────────────────────────────────────────────────┤
│ Image              Tag      Status    Built             │
│ bre-payments       v1.2.3   ✅ Success  2 hours ago     │
│ bre-payments       v1.2.2   ✅ Success  1 day ago       │
│ bre-payments       v1.2.1   ❌ Failed    3 days ago     │
│ bre-payments       main     🔄 Building  Just now       │
└────────────────────────────────────────────────────────┘
```

**2. "Build Image" Modal:**

```typescript
const BuildImageModal = () => {
  const [selectedTag, setSelectedTag] = useState('');
  
  // Fetch available tags from GitHub
  const { data: tags } = useQuery({
    queryKey: ['github-tags'],
    queryFn: () => api.get('/api/v1/images/github-tags?repo=myorg/bre-payments'),
  });
  
  const buildMutation = useMutation({
    mutationFn: (tag: string) => api.post('/api/v1/images/build', {
      repo: 'myorg/bre-payments',
      tag: tag,
      commit_sha: tags.find(t => t.name === tag)?.commit.sha
    }),
  });
  
  return (
    <Modal>
      <h2>Build New Docker Image</h2>
      <select value={selectedTag} onChange={(e) => setSelectedTag(e.target.value)}>
        <option value="">Select GitHub Tag...</option>
        {tags?.tags.map(tag => (
          <option key={tag.name} value={tag.name}>
            {tag.name} - {tag.commit.sha.slice(0, 7)} ({formatDate(tag.commit.date)})
          </option>
        ))}
      </select>
      <button onClick={() => buildMutation.mutate(selectedTag)}>
        Build Image
      </button>
    </Modal>
  );
};
```

**3. Build Progress/Log Viewer:**

- Real-time build status updates (polling or WebSocket)
- Show build log in terminal-style viewer
- Cancel build button
- Retry build button

---

## 4. Image Selection When Creating Product

### ✅ Backend Status: FULLY IMPLEMENTED

**Implementation Details:**

1. **Update Product model:**
```python
# Add to Product model
image_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('docker_images.id'), nullable=True)
image_name: Mapped[str] = mapped_column(String(255), default='bre-payments:latest', nullable=False)

# Add relationship
image: Mapped[Optional["DockerImage"]] = relationship("DockerImage", back_populates="products")
```

2. **✅ ProductCreate/Update schemas updated:**
```python
class ProductCreate(BaseModel):
    name: str
    slug: str
    port: int
    replicas: int = 1
    env_vars: dict[str, str] | None = None
    image_id: int | None = None  # NEW: Reference to built image
    image_name: str = "bre-payments:latest"  # NEW: Fallback to default
```

3. **✅ DockerManager.create_service updated:**
```python
def create_service(self, product: Product) -> str:
    # Now uses product's image instead of hardcoded
    image = product.image_name if product.image_name else settings.instance_image
    
    service = self.client.services.create(
        image=image,  # Changed from settings.instance_image
        ...
    )
```

### UI Implementation Needed:

**Update Product Form:**

Add image selector after basic fields:

```typescript
interface ProductFormData {
  name: string;
  slug: string;
  port: number;
  replicas: number;
  image_id: number | null;
  env_vars: Record<string, string>;
}

const ProductForm = () => {
  const [formData, setFormData] = useState<ProductFormData>({...});
  
  // Fetch available images
  const { data: images } = useQuery({
    queryKey: ['images'],
    queryFn: () => api.get('/api/v1/images'),
  });
  
  return (
    <form>
      <input name="name" placeholder="Product Name" />
      <input name="slug" placeholder="slug" />
      <input name="port" type="number" />
      
      {/* NEW: Image Selector */}
      <div className="form-field">
        <label>Docker Image</label>
        <select 
          value={formData.image_id || ''} 
          onChange={(e) => setFormData({
            ...formData, 
            image_id: Number(e.target.value)
          })}
        >
          <option value="">Latest (default)</option>
          {images?.images
            .filter(img => img.build_status === 'success')
            .map(img => (
              <option key={img.id} value={img.id}>
                {img.name}:{img.tag} - Built {formatDate(img.built_at)}
              </option>
            ))
          }
        </select>
        <small>Select which version of the application to deploy</small>
      </div>
      
      {/* Environment Variables Editor */}
      <EnvVarsEditor ... />
      
      <button type="submit">Create Product</button>
    </form>
  );
};
```

---

## Summary: Implementation Checklist

### ✅ Backend Complete (All Features Working):
- [x] Environment variables storage (database)
- [x] Environment variables API (create/update/read)
- [x] Service logs endpoint
- [x] `docker_images` table and model
- [x] GitHub API integration (list tags, get commits, download repos)
- [x] Docker image build service with real-time logging
- [x] Background worker system for async builds
- [x] Product model with image_id reference
- [x] DockerManager uses product-specific images
- [x] Complete Images REST API (5 endpoints)

### 🎨 UI TODO (Backend Ready for All):
- [ ] Environment variables key-value editor component ✅ API ready
- [ ] Log viewer modal with auto-refresh ✅ API ready
- [ ] Docker Images management screen ✅ API ready
- [ ] Build image modal with GitHub tag selection ✅ API ready
- [ ] Image selector in product form ✅ API ready
- [ ] Build progress/log viewer (poll GET /images/{id}) ✅ API ready

---

## Quick Start for UI Developer:

1. **Environment Variables** - Ready to use:
   - Add key-value editor to product form
   - Send as `env_vars` object in POST/PATCH requests
   - Display in product detail view

2. **Logs Viewer** - Ready to use:
   - Call `GET /api/v1/products/{id}/logs?tail=100`
   - Display in terminal-style component
   - Add auto-refresh every 5 seconds

3. **Image Building** - ✅ Ready to use:
   - List GitHub tags: `GET /api/v1/images/github-tags?repo=owner/repo`
   - Trigger build: `POST /api/v1/images` (returns immediately, builds in background)
   - Poll status: `GET /api/v1/images/{id}` every 3-5 seconds
   - List images: `GET /api/v1/images?status_filter=success`
   - Use in products: Pass `image_id` when creating product

---

## Example: Complete Product Creation Flow

```typescript
const createProduct = async (formData: ProductFormData) => {
  const response = await api.post('/api/v1/products', {
    name: "Allianz Insurance",
    slug: "allianz",
    port: 8001,
    replicas: 2,
    image_id: 5,  // bre-payments:v1.2.3
    env_vars: {
      DATABASE_URL: "postgresql://user:pass@host:5432/allianz",
      MUZZLEY_API_URL: "https://api.habit.io",
      PLATFORM_API_KEY: "secret-key-123",
      MQTT_BROKER: "mqtt://broker.habit.io:1883",
      REDIS_URL: "redis://localhost:6379/0"
    }
  });
  
  // Product created with ID
  const productId = response.data.id;
  
  // Start the product (deploy to Docker Swarm)
  await api.post(`/api/v1/products/${productId}/start`);
  
  // View logs after deployment
  const logs = await api.get(`/api/v1/products/${productId}/logs?tail=100`);
  console.log(logs.data.logs);
};
```
