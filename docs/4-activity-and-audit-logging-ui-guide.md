# Activity and Audit Logging UI Specification

## Overview

The orchestrator now provides two logging systems to track operational events and compliance:

1. **Activity Log** - User-facing operational events for dashboard display
2. **Audit Log** - Comprehensive security and compliance trail

This specification defines the UI features, API integration, and recommended implementations for both systems.

---

## Part 1: Activity Log (Recent Activity Widget)

### Purpose
Display recent operational events in the dashboard for quick visibility into system activity.

### Use Cases
- Dashboard "Recent Activity" widget showing last 10-20 events
- Product-specific activity timeline
- Error monitoring and alerts

---

### API Endpoint

**GET** `/api/v1/activity`

### Query Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `limit` | integer | No | Max number of events (1-100, default 20) | `10` |
| `product_id` | integer | No | Filter by specific product | `5` |
| `severity` | string | No | Filter by severity (info, warning, error) | `error` |
| `event_type` | string | No | Filter by event type | `product_started` |
| `hours` | integer | No | Only show events from last N hours (1-168) | `24` |

### Response Schema

```json
[
  {
    "id": 1,
    "product_id": 5,
    "product_name": "Pet Insurance",
    "event_type": "product_scaled",
    "message": "Pet Insurance scaled to 3 replicas",
    "severity": "info",
    "metadata": {
      "old_replicas": 1,
      "new_replicas": 3
    },
    "created_at": "2026-01-21T16:00:00Z"
  },
  {
    "id": 2,
    "product_id": 7,
    "product_name": "Gadget Insurance",
    "event_type": "health_check_failed",
    "message": "Gadget Insurance failed health check",
    "severity": "error",
    "metadata": {
      "error": "Connection timeout"
    },
    "created_at": "2026-01-21T15:30:00Z"
  }
]
```

### Event Types

| Event Type | Description | Severity |
|------------|-------------|----------|
| `product_created` | Product instance created | info |
| `product_started` | Product deployed and running | info |
| `product_stopped` | Product stopped | info |
| `product_scaled` | Product scaled to N replicas | info |
| `product_deleted` | Product removed | info |
| `product_start_failed` | Product failed to start | error |
| `health_check_failed` | Health check failure | error |
| `service_restarted` | Service automatically restarted | warning |
| `image_build_completed` | Docker image build finished | info |
| `image_build_failed` | Docker image build failed | error |

---

### UI Component: Recent Activity Widget

#### Design Mockup

```
┌─────────────────────────────────────────────────────────┐
│ Recent Activity                          [View All →]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 🟢 Pet Insurance scaled to 3 replicas                  │
│    2 minutes ago                                        │
│                                                         │
│ 🔴 Gadget Insurance failed health check                │
│    30 minutes ago                                       │
│                                                         │
│ 🔵 Tyre Protection restarted                           │
│    1 hour ago                                           │
│                                                         │
│ ⚪ Travel Insurance stopped                            │
│    3 hours ago                                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Features

**Visual Indicators:**
- 🟢 Green dot for `severity: "info"`
- 🟡 Yellow dot for `severity: "warning"`
- 🔴 Red dot for `severity: "error"`

**Time Display:**
- Use relative time (e.g., "2 minutes ago", "1 hour ago")
- Show absolute time on hover

**Actions:**
- Click event to navigate to product details
- "View All" button to open full activity log page

---

### UI Implementation Example (TypeScript/React)

```typescript
interface ActivityEvent {
  id: number;
  product_id: number | null;
  product_name: string | null;
  event_type: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
  metadata: Record<string, any> | null;
  created_at: string;
}

interface ActivityWidgetProps {
  limit?: number;
  productId?: number;
  refreshInterval?: number; // milliseconds
}

function RecentActivityWidget({ 
  limit = 10, 
  productId, 
  refreshInterval = 30000 
}: ActivityWidgetProps) {
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchActivity = async () => {
      const params = new URLSearchParams({
        limit: limit.toString(),
        ...(productId && { product_id: productId.toString() }),
      });

      const response = await fetch(`/api/v1/activity?${params}`);
      const data = await response.json();
      setActivities(data);
      setLoading(false);
    };

    fetchActivity();
    const interval = setInterval(fetchActivity, refreshInterval);
    return () => clearInterval(interval);
  }, [limit, productId, refreshInterval]);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error': return '🔴';
      case 'warning': return '🟡';
      default: return '🟢';
    }
  };

  const getRelativeTime = (timestamp: string) => {
    const now = new Date();
    const then = new Date(timestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  if (loading) return <div>Loading activity...</div>;

  return (
    <div className="activity-widget">
      <div className="widget-header">
        <h3>Recent Activity</h3>
        <Link to="/activity">View All →</Link>
      </div>
      
      <div className="activity-list">
        {activities.length === 0 ? (
          <p className="no-activity">No recent activity</p>
        ) : (
          activities.map(activity => (
            <div 
              key={activity.id} 
              className="activity-item"
              onClick={() => activity.product_id && navigate(`/products/${activity.product_id}`)}
            >
              <span className="severity-icon">
                {getSeverityIcon(activity.severity)}
              </span>
              <div className="activity-content">
                <p className="activity-message">{activity.message}</p>
                <span className="activity-time" title={activity.created_at}>
                  {getRelativeTime(activity.created_at)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

---

### CSS Styling Example

```css
.activity-widget {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 20px;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid #eee;
  padding-bottom: 12px;
}

.widget-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.widget-header a {
  color: #0066cc;
  text-decoration: none;
  font-size: 14px;
}

.activity-list {
  max-height: 400px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: start;
  padding: 12px 0;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.2s;
}

.activity-item:hover {
  background: #f9f9f9;
  margin: 0 -12px;
  padding: 12px;
}

.severity-icon {
  font-size: 20px;
  margin-right: 12px;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
}

.activity-message {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #333;
}

.activity-time {
  font-size: 12px;
  color: #999;
}

.no-activity {
  text-align: center;
  color: #999;
  padding: 40px 0;
}
```

---

### Full Activity Log Page

#### Features

**Filters:**
- Product dropdown (filter by product)
- Severity dropdown (info, warning, error, all)
- Time range selector (last 1 hour, 24 hours, 7 days, 30 days)
- Event type filter

**Display:**
- Paginated list (20 events per page)
- Export to CSV button
- Real-time updates (polling every 30 seconds)

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ Activity Log                                            │
├─────────────────────────────────────────────────────────┤
│ Filters:                                                │
│ [Product ▼] [Severity ▼] [Time Range ▼] [Export CSV]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 🟢 Pet Insurance scaled to 3 replicas                  │
│    2 minutes ago | Metadata: old=1, new=3               │
│                                                         │
│ 🔴 Gadget Insurance failed health check                │
│    30 minutes ago | Error: Connection timeout           │
│                                                         │
│ ... (18 more events)                                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Page: [1] [2] [3] [4] ... [10]                         │
└─────────────────────────────────────────────────────────┘
```

---

## Part 2: Audit Log (Compliance & Security)

### Purpose
Provide comprehensive audit trail for compliance reports, security investigations, and debugging configuration changes.

### Use Cases
- Compliance audits ("show all changes in January 2026")
- Security investigations ("who changed the GitHub token on Jan 15?")
- Debugging ("what changed on this product before it stopped working?")
- User activity tracking

---

### API Endpoint

**GET** `/api/v1/audit`

### Query Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `limit` | integer | No | Max entries (1-500, default 50) | `100` |
| `resource_type` | string | No | Filter by resource (product, orchestrator_settings, docker_image) | `product` |
| `resource_id` | integer | No | Filter by specific resource ID | `5` |
| `action` | string | No | Filter by action | `update_product` |
| `user_id` | string | No | Filter by user ID | `admin@example.com` |
| `success` | boolean | No | Filter by success/failure | `false` |
| `start_date` | datetime | No | Start date (ISO 8601) | `2026-01-01T00:00:00Z` |
| `end_date` | datetime | No | End date (ISO 8601) | `2026-01-31T23:59:59Z` |
| `days` | integer | No | Only show logs from last N days (1-365) | `7` |

### Response Schema

```json
[
  {
    "id": 1,
    "action": "update_product",
    "resource_type": "product",
    "resource_id": 5,
    "resource_name": "Pet Insurance",
    "changes": {
      "replicas": {"old": 1, "new": 3},
      "env_vars": {"old": {...}, "new": {...}}
    },
    "user_id": "system",
    "ip_address": "10.10.141.48",
    "user_agent": "Mozilla/5.0...",
    "success": true,
    "error_message": null,
    "created_at": "2026-01-21T16:00:00Z"
  },
  {
    "action": "start_product",
    "resource_type": "product",
    "resource_id": 7,
    "resource_name": "Gadget Insurance",
    "changes": {
      "status": {"old": "stopped", "new": "running"}
    },
    "user_id": "admin@example.com",
    "ip_address": "192.168.1.100",
    "success": false,
    "error_message": "Docker service creation failed: port already in use",
    "created_at": "2026-01-21T15:30:00Z"
  }
]
```

### Action Types

| Action | Resource Type | Description |
|--------|---------------|-------------|
| `create_product` | product | Product created |
| `update_product` | product | Product metadata updated |
| `delete_product` | product | Product deleted |
| `start_product` | product | Product deployment started |
| `stop_product` | product | Product stopped |
| `scale_product` | product | Product scaled |
| `update_settings` | orchestrator_settings | Orchestrator settings changed |
| `delete_github_token` | orchestrator_settings | GitHub token removed |
| `build_image` | docker_image | Docker image build triggered |

---

### UI Component: Audit Log Viewer

#### Design Mockup

```
┌─────────────────────────────────────────────────────────────┐
│ Audit Log                                                   │
├─────────────────────────────────────────────────────────────┤
│ Filters:                                                    │
│ [Resource ▼] [Action ▼] [User ▼] [Success/Fail ▼]          │
│ Date Range: [2026-01-01] to [2026-01-31] [Apply]           │
│                                               [Export CSV]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ✅ update_product | Pet Insurance (#5)                     │
│    2026-01-21 16:00:00 | system | 10.10.141.48             │
│    Changes: replicas (1 → 3)                                │
│    [Show Details]                                           │
│                                                             │
│ ❌ start_product | Gadget Insurance (#7)                   │
│    2026-01-21 15:30:00 | admin@example.com | 192.168.1.100 │
│    Error: Docker service creation failed: port in use       │
│    [Show Details]                                           │
│                                                             │
│ ... (48 more entries)                                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Page: [1] [2] [3] ... [10]                                 │
└─────────────────────────────────────────────────────────────┘
```

#### Features

**Filters:**
- Resource type dropdown (product, settings, image)
- Action dropdown (create, update, delete, start, stop, scale)
- User dropdown (populated from unique user_ids)
- Success/failure toggle
- Date range picker
- Quick filters (today, last 7 days, last 30 days)

**Display:**
- Success/failure icon (✅/❌)
- Expandable details showing full changes JSON
- Color coding (green for success, red for failure)
- Highlight changed fields

**Export:**
- CSV export with all columns
- Filter before export

---

### UI Implementation Example (TypeScript/React)

```typescript
interface AuditEntry {
  id: number;
  action: string;
  resource_type: string;
  resource_id: number | null;
  resource_name: string | null;
  changes: Record<string, { old: any; new: any }> | null;
  user_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

interface AuditLogViewerProps {
  productId?: number; // Optional: filter by product
}

function AuditLogViewer({ productId }: AuditLogViewerProps) {
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [filters, setFilters] = useState({
    resource_type: '',
    action: '',
    success: '',
    days: 7,
  });
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    const fetchAuditLogs = async () => {
      const params = new URLSearchParams({
        limit: '50',
        ...(productId && { resource_id: productId.toString(), resource_type: 'product' }),
        ...(filters.resource_type && { resource_type: filters.resource_type }),
        ...(filters.action && { action: filters.action }),
        ...(filters.success !== '' && { success: filters.success }),
        days: filters.days.toString(),
      });

      const response = await fetch(`/api/v1/audit?${params}`);
      const data = await response.json();
      setAuditLogs(data);
    };

    fetchAuditLogs();
  }, [productId, filters]);

  const formatChanges = (changes: Record<string, { old: any; new: any }> | null) => {
    if (!changes) return 'No changes recorded';
    
    return Object.entries(changes).map(([field, { old, new: newVal }]) => (
      <div key={field} className="change-line">
        <strong>{field}:</strong> 
        <span className="old-value">{JSON.stringify(old)}</span>
        <span className="arrow">→</span>
        <span className="new-value">{JSON.stringify(newVal)}</span>
      </div>
    ));
  };

  const exportToCsv = () => {
    const headers = ['ID', 'Timestamp', 'Action', 'Resource', 'User', 'IP', 'Success', 'Changes'];
    const rows = auditLogs.map(log => [
      log.id,
      log.created_at,
      log.action,
      `${log.resource_type}:${log.resource_id}`,
      log.user_id || 'system',
      log.ip_address || 'N/A',
      log.success ? 'Yes' : 'No',
      JSON.stringify(log.changes),
    ]);

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${new Date().toISOString()}.csv`;
    a.click();
  };

  return (
    <div className="audit-log-viewer">
      <div className="filters">
        <select 
          value={filters.resource_type} 
          onChange={e => setFilters({...filters, resource_type: e.target.value})}
        >
          <option value="">All Resources</option>
          <option value="product">Products</option>
          <option value="orchestrator_settings">Settings</option>
          <option value="docker_image">Images</option>
        </select>

        <select 
          value={filters.action} 
          onChange={e => setFilters({...filters, action: e.target.value})}
        >
          <option value="">All Actions</option>
          <option value="create_product">Create</option>
          <option value="update_product">Update</option>
          <option value="delete_product">Delete</option>
          <option value="start_product">Start</option>
          <option value="stop_product">Stop</option>
        </select>

        <select 
          value={filters.success} 
          onChange={e => setFilters({...filters, success: e.target.value})}
        >
          <option value="">All</option>
          <option value="true">Success Only</option>
          <option value="false">Failures Only</option>
        </select>

        <select 
          value={filters.days} 
          onChange={e => setFilters({...filters, days: parseInt(e.target.value)})}
        >
          <option value="1">Last 24 hours</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="365">Last year</option>
        </select>

        <button onClick={exportToCsv}>Export CSV</button>
      </div>

      <div className="audit-list">
        {auditLogs.map(log => (
          <div key={log.id} className={`audit-entry ${log.success ? 'success' : 'failure'}`}>
            <div className="entry-header" onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}>
              <span className="status-icon">{log.success ? '✅' : '❌'}</span>
              <strong>{log.action}</strong>
              <span className="resource">
                {log.resource_name} (#{log.resource_id})
              </span>
              <span className="timestamp">{new Date(log.created_at).toLocaleString()}</span>
              <span className="user">{log.user_id}</span>
              <span className="ip">{log.ip_address}</span>
            </div>

            {expandedId === log.id && (
              <div className="entry-details">
                {log.error_message && (
                  <div className="error-message">
                    <strong>Error:</strong> {log.error_message}
                  </div>
                )}
                <div className="changes">
                  <strong>Changes:</strong>
                  {formatChanges(log.changes)}
                </div>
                {log.user_agent && (
                  <div className="user-agent">
                    <strong>User Agent:</strong> {log.user_agent}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Integration Guide

### Dashboard Implementation

**Recommended Layout:**

```
Dashboard
├── Recent Activity Widget (right sidebar)
│   └── Shows last 10 events with real-time updates
│
├── Product Cards (main area)
│   └── Each card shows product-specific activity count
│
└── Quick Links
    ├── View All Activity
    └── View Audit Log
```

### Product Detail Page

**Add Activity Tab:**

```
Product Details: Pet Insurance
├── Tab: Overview
├── Tab: Configuration
├── Tab: Environment Variables
├── Tab: Activity ← NEW
│   └── Shows activity filtered by this product
└── Tab: Audit Trail ← NEW
    └── Shows audit log filtered by this product
```

### Navigation

**Add menu items:**
- Activity Log (accessible to all users)
- Audit Log (restricted to admin users only)

---

## Security Considerations

### Audit Log Access Control

**Recommendation:** Restrict audit log access to admin users only

```typescript
// Example: Route guard
function AuditLogPage() {
  const { user } = useAuth();
  
  if (!user?.isAdmin) {
    return <Redirect to="/unauthorized" />;
  }
  
  return <AuditLogViewer />;
}
```

### Sensitive Data Masking

**Backend automatically masks:**
- Passwords
- Tokens (GitHub, API keys)
- Secrets

**UI should:**
- Display masked values as "***REDACTED***"
- Show "Value changed" instead of actual values for sensitive fields

---

## Testing Checklist

### Activity Log
- [ ] Widget displays on dashboard
- [ ] Real-time updates work (polling)
- [ ] Severity icons match severity level
- [ ] Relative time updates correctly
- [ ] Click event navigates to product
- [ ] "View All" opens full activity log
- [ ] Filters work correctly
- [ ] Empty state displays properly

### Audit Log
- [ ] Access restricted to admin users
- [ ] All filters work correctly
- [ ] Date range filtering works
- [ ] Export to CSV generates valid file
- [ ] Expandable details show all changes
- [ ] Sensitive values are masked
- [ ] Success/failure indicated clearly
- [ ] Pagination works

### Integration
- [ ] Activity logged when creating product
- [ ] Activity logged when starting product
- [ ] Activity logged when stopping product
- [ ] Activity logged when scaling product
- [ ] Audit logged for all CRUD operations
- [ ] IP address captured correctly
- [ ] User ID populated (when auth implemented)

---

## Summary for UI Developer

**Implement these features:**

1. **Dashboard Widget** - Recent Activity (last 10 events, auto-refresh)
2. **Full Activity Log Page** - With filters and pagination
3. **Audit Log Page** - Admin-only, comprehensive filtering
4. **Product Activity Tab** - Product-specific activity timeline
5. **Product Audit Tab** - Product-specific audit trail

**API Endpoints to use:**
- `GET /api/v1/activity?limit=10` - Recent activity
- `GET /api/v1/audit?resource_id=5&resource_type=product` - Product audit

**Key Features:**
- Real-time updates (polling every 30 seconds)
- Severity-based color coding
- Relative time display
- Expandable details
- CSV export
- Admin-only audit access

**No backend changes needed** - all endpoints are ready to use!
