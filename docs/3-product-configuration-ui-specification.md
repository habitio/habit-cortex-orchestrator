# Product Configuration UI Specification

## Overview

The product creation/editing interface is organized into **6 logical sections** to clearly separate different types of configuration. This specification defines the scope, features, API wiring, and data flow for each section.

---

## UI Structure & Navigation

### Multi-Step Form Approach (Recommended)

**Visual Structure:**
```
┌─────────────────────────────────────────────────────────┐
│ Create Product: Allianz Insurance                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ① Instance   ② Env Vars   ③ Database   ④ Events      │
│     Config                    Config      & Actions     │
│                                                         │
│  ⑤ Validation   ⑥ Advanced                            │
│     Rules         Settings                              │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│         [Current section content here]                  │
│                                                         │
│                                                         │
│         [Section-specific forms and inputs]             │
│                                                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                    [← Back]    [Next →]    [Save]      │
└─────────────────────────────────────────────────────────┘
```

### Alternative: Accordion/Expandable Sections

```
▼ 1. Instance Configuration
  └─ [Instance details form]

▼ 2. Environment Variables
  └─ [Env vars editor]

▶ 3. Database Configuration (click to expand)

▶ 4. Events & Actions

▶ 5. Product Validation Rules

▶ 6. Advanced Settings
```

### Navigation States

**Creating New Product:**
- All sections start collapsed/hidden
- User progresses through sections sequentially
- Can jump to any section via navigation
- Must complete required sections before final save

**Editing Existing Product:**
- All sections pre-populated with current values
- User can directly navigate to any section
- Changes are saved per-section or globally
- Show "unsaved changes" indicator

---

## Section 1: Instance Configuration

### Purpose
Basic Docker deployment settings for the product instance.

### Fields

#### 1.1 Product Name
- **Type:** Text input
- **Required:** Yes
- **Validation:** 3-100 characters, alphanumeric + spaces
- **Example:** "Allianz Insurance", "AXA Protection"

#### 1.2 Slug
- **Type:** Text input (auto-generated from name)
- **Required:** Yes
- **Validation:** Lowercase, alphanumeric + hyphens, unique across products
- **Example:** "allianz-insurance", "axa-protection"
- **Behavior:** Auto-fills from Product Name (user can override)

#### 1.3 Port
- **Type:** Number input
- **Required:** Yes
- **Validation:** 1024-65535, unique across products
- **Default:** Auto-suggest next available port (8001, 8002, etc.)
- **Example:** 8001

#### 1.4 Replicas
- **Type:** Number input with stepper (+ / - buttons)
- **Required:** Yes
- **Validation:** 1-10
- **Default:** 1
- **Example:** 2
- **Help Text:** "Number of identical instances for high availability"

#### 1.5 Docker Image Version
- **Type:** Dropdown/Select
- **Required:** No (defaults to latest)
- **Options:** Fetched from `GET /api/v1/images?status_filter=success`
- **Display:** "bre-payments:v1.2.3 (Built 2 hours ago)"
- **Default:** Latest or "Use default image"

### API Wiring

**Endpoint:** `POST /api/v1/products` (Create) or `PATCH /api/v1/products/{id}` (Update)

**Request Payload:**
```json
{
  "name": "Allianz Insurance",
  "slug": "allianz-insurance",
  "port": 8001,
  "replicas": 2,
  "image_id": 5
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Allianz Insurance",
  "slug": "allianz-insurance",
  "port": 8001,
  "replicas": 2,
  "image_id": 5,
  "image_name": "bre-payments:v1.2.3",
  "status": "stopped",
  "created_at": "2026-01-21T16:00:00Z"
}
```

### Validation Rules

- **Name:** Cannot be empty, must be unique
- **Slug:** Must match pattern `^[a-z0-9-]+$`, must be unique
- **Port:** Must be available (not used by another product)
- **Image:** If specified, must exist and have `build_status=success`

### User Flow

1. User enters product name
2. Slug auto-generates (editable)
3. System suggests next available port
4. User sets replicas (or keeps default)
5. User optionally selects Docker image version
6. Click "Next" to proceed to Environment Variables

---

## Section 2: Environment Variables

### Purpose
Configure instance-specific environment variables (DATABASE_URL, API keys, etc.)

### Fields

#### 2.1 Environment Variables Editor
- **Type:** Dynamic key-value list
- **Features:**
  - Add new variable
  - Remove variable
  - Auto-uppercase keys
  - Show/hide toggle for secrets (KEY, PASSWORD, SECRET, TOKEN)
  - Template loader (pre-fill common variables)

#### 2.2 Required Variables
- `DATABASE_URL` - PostgreSQL connection
- `MUZZLEY_API_URL` - Habit Platform API
- `PLATFORM_API_KEY` - Authentication key
- `MQTT_BROKER` - IoT broker URL
- `REDIS_URL` - Redis connection
- `LOG_LEVEL` - Logging verbosity

### API Wiring

**Endpoint:** `PATCH /api/v1/products/{id}`

**Request Payload:**
```json
{
  "env_vars": {
    "DATABASE_URL": "postgresql://user:pass@10.10.141.48:5432/allianz_db",
    "MUZZLEY_API_URL": "https://api.habit.io",
    "PLATFORM_API_KEY": "prod-allianz-abc123",
    "MQTT_BROKER": "mqtt://broker.habit.io:1883",
    "REDIS_URL": "redis://10.10.141.48:6379/0",
    "LOG_LEVEL": "INFO"
  }
}
```

**Response:**
```json
{
  "id": 1,
  "env_vars": {
    "DATABASE_URL": "postgresql://user:pass@10.10.141.48:5432/allianz_db",
    "MUZZLEY_API_URL": "https://api.habit.io",
    "PLATFORM_API_KEY": "prod-allianz-abc123",
    "MQTT_BROKER": "mqtt://broker.habit.io:1883",
    "REDIS_URL": "redis://10.10.141.48:6379/0",
    "LOG_LEVEL": "INFO"
  },
  "updated_at": "2026-01-21T16:05:00Z"
}
```

### Validation Rules

- All 6 required variables must be present
- `DATABASE_URL` must start with `postgresql://`
- `MUZZLEY_API_URL` must be valid HTTP/HTTPS URL
- `PLATFORM_API_KEY` minimum 10 characters
- `MQTT_BROKER` must start with `mqtt://` or `mqtts://`
- `REDIS_URL` must start with `redis://` or `rediss://`
- `LOG_LEVEL` must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL

### User Flow

1. Section shows template with all required variables
2. User fills in instance-specific values (database name, API key, etc.)
3. User can add optional variables
4. System validates all required fields
5. Shows warning if secrets are exposed (not masked)
6. Click "Next" to proceed to Database Configuration

---

## Section 3: Database Configuration

### Purpose
Business logic configuration stored in the product instance's database. This is separate from env vars and contains insurance-product-specific settings.

### Subsections

#### 3.1 Product Settings
- **Product Code** - Insurance product identifier
- **Product Name** - Display name in customer apps
- **Currency** - ISO currency code (EUR, GBP, USD)
- **Market** - Country/region code (PT, ES, UK)

#### 3.2 Coverage Settings
- **Default Coverage Amount** - Monetary value
- **Coverage Type** - Dropdown (Comprehensive, Third Party, etc.)
- **Premium Calculation Method** - Dropdown (Fixed, Usage-based, Hybrid)

#### 3.3 Integration Settings
- **Provider ID** - Insurance provider identifier
- **Policy Template ID** - Template reference
- **External System ID** - Third-party system reference

### API Wiring

**Note:** This data is NOT stored in orchestrator database. It's configuration that the deployed instance will use in its own database.

**Approach 1: Store as JSON in orchestrator**

**Endpoint:** `PATCH /api/v1/products/{id}`

**Request Payload:**
```json
{
  "database_config": {
    "product_code": "ALLIANZ_AUTO_2024",
    "product_name": "Allianz Auto Protection",
    "currency": "EUR",
    "market": "PT",
    "default_coverage_amount": 50000,
    "coverage_type": "comprehensive",
    "premium_method": "usage_based",
    "provider_id": "ALLIANZ_PT",
    "policy_template_id": "AUTO_V1",
    "external_system_id": "SAP_12345"
  }
}
```

**Approach 2: Initialize via API call to deployed instance**

After instance is deployed, UI calls the instance's API to configure:

**Endpoint:** `POST http://{instance_url}:{port}/api/v1/admin/initial-config`

**Request Payload:**
```json
{
  "product_settings": {
    "product_code": "ALLIANZ_AUTO_2024",
    "product_name": "Allianz Auto Protection",
    "currency": "EUR",
    "market": "PT"
  },
  "coverage_settings": {
    "default_amount": 50000,
    "type": "comprehensive",
    "premium_method": "usage_based"
  },
  "integration_settings": {
    "provider_id": "ALLIANZ_PT",
    "policy_template_id": "AUTO_V1",
    "external_system_id": "SAP_12345"
  }
}
```

### User Flow

1. User enters product-specific business settings
2. System validates data types and ranges
3. Configuration is stored (either in orchestrator or passed to instance)
4. Shows preview of configuration
5. Click "Next" to proceed to Events & Actions

---

## Section 4: Events & Actions Configuration

### Purpose
Configure event-driven automation, MQTT topics, webhooks, and action triggers.

### Subsections

#### 4.1 MQTT Topics
Configure which MQTT topics this instance subscribes to and publishes on.

**Fields:**
- **Incoming Topics** - List of topics to subscribe to
  - Device events (e.g., `devices/+/telemetry`)
  - Customer actions (e.g., `customers/+/actions`)
  - Platform notifications (e.g., `platform/notifications`)

- **Outgoing Topics** - List of topics to publish to
  - Policy updates (e.g., `policies/+/updates`)
  - Claims processing (e.g., `claims/+/status`)
  - Billing events (e.g., `billing/+/events`)

#### 4.2 Event Handlers
Configure which events trigger which actions.

**Event Types:**
- Device telemetry received
- Customer action detected
- Policy threshold exceeded
- Claim submitted
- Payment received

**Action Types:**
- Send notification
- Update policy
- Calculate premium
- Trigger workflow
- Call external API

#### 4.3 Webhooks
Configure external webhook endpoints for events.

**Fields:**
- **Webhook URL** - External endpoint
- **Event Type** - Which event triggers this webhook
- **Authentication** - Header-based auth (optional)
- **Retry Policy** - Number of retries on failure

### API Wiring

**Endpoint:** `PATCH /api/v1/products/{id}`

**Request Payload:**
```json
{
  "events_config": {
    "mqtt": {
      "subscribe_topics": [
        "devices/+/telemetry",
        "customers/+/actions",
        "platform/notifications"
      ],
      "publish_topics": [
        "policies/+/updates",
        "claims/+/status",
        "billing/+/events"
      ]
    },
    "event_handlers": [
      {
        "event": "device_telemetry",
        "action": "calculate_premium",
        "enabled": true
      },
      {
        "event": "claim_submitted",
        "action": "send_notification",
        "enabled": true
      }
    ],
    "webhooks": [
      {
        "url": "https://allianz.com/api/webhooks/policy-updates",
        "event": "policy_updated",
        "auth_header": "Bearer allianz-webhook-token",
        "retry_count": 3
      }
    ]
  }
}
```

**Response:**
```json
{
  "id": 1,
  "events_config": {
    "mqtt": { ... },
    "event_handlers": [ ... ],
    "webhooks": [ ... ]
  },
  "updated_at": "2026-01-21T16:10:00Z"
}
```

### User Flow

1. User configures MQTT topics (or uses defaults)
2. User maps events to actions
3. User adds webhook endpoints (optional)
4. System validates URLs and topic patterns
5. Shows summary of configured automations
6. Click "Next" to proceed to Validation Rules

---

## Section 5: Product Validation Rules

### Purpose
Define business rules for validating policies, claims, and customer data specific to this insurance product.

### Subsections

#### 5.1 Policy Validation Rules
Rules that must be satisfied for a policy to be created/updated.

**Rule Types:**
- **Age Range** - Min/max customer age
- **Coverage Limits** - Min/max coverage amounts
- **Geographic Restrictions** - Allowed regions/countries
- **Vehicle Requirements** - (for auto insurance) Age, type, value
- **Eligibility Criteria** - Custom conditions

#### 5.2 Claim Validation Rules
Rules for validating claims submissions.

**Rule Types:**
- **Claim Amount Limits** - Max claim amount vs coverage
- **Time Restrictions** - Claims must be filed within N days
- **Evidence Requirements** - Photos, documents required
- **Approval Workflow** - Auto-approve under threshold

#### 5.3 Pricing Rules
Rules for calculating premiums and discounts.

**Rule Types:**
- **Base Premium** - Starting price
- **Risk Multipliers** - Based on customer profile
- **Discounts** - Safe driver, bundling, loyalty
- **Dynamic Pricing** - Usage-based adjustments

### API Wiring

**Endpoint:** `PATCH /api/v1/products/{id}`

**Request Payload:**
```json
{
  "validation_rules": {
    "policy": {
      "min_customer_age": 18,
      "max_customer_age": 75,
      "min_coverage": 10000,
      "max_coverage": 500000,
      "allowed_regions": ["PT", "ES"],
      "vehicle_max_age": 15
    },
    "claims": {
      "max_claim_amount_ratio": 1.0,
      "filing_deadline_days": 30,
      "auto_approve_threshold": 500,
      "evidence_required": ["photos", "police_report"]
    },
    "pricing": {
      "base_premium": 300,
      "risk_multipliers": {
        "age_under_25": 1.5,
        "high_mileage": 1.2,
        "urban_area": 1.1
      },
      "discounts": {
        "safe_driver": 0.15,
        "bundled": 0.10,
        "loyalty_3_years": 0.05
      }
    }
  }
}
```

**Response:**
```json
{
  "id": 1,
  "validation_rules": { ... },
  "updated_at": "2026-01-21T16:15:00Z"
}
```

### User Flow

1. User defines policy validation criteria
2. User sets claim approval rules
3. User configures pricing formulas
4. System validates rule logic (no conflicts)
5. Shows summary of all rules
6. Click "Next" to proceed to Advanced Settings

---

## Section 6: Advanced Settings

### Purpose
Miscellaneous settings and optional configurations.

### Subsections

#### 6.1 Performance Settings
- **Connection Pool Size** - Database connection pool
- **Cache TTL** - Redis cache time-to-live (seconds)
- **Request Timeout** - HTTP request timeout (seconds)
- **Max Concurrent Requests** - Rate limiting

#### 6.2 Feature Flags
Enable/disable specific features for this instance.

**Flags:**
- **Enable Telematics** - GPS tracking for usage-based insurance
- **Enable Claims Portal** - Customer self-service claims
- **Enable Auto-Renewal** - Automatic policy renewals
- **Enable Payment Plans** - Installment payments

#### 6.3 Monitoring & Alerts
- **Health Check Interval** - How often to ping instance
- **Alert Email** - Email for critical alerts
- **Slack Webhook** - Slack notifications (optional)
- **Error Threshold** - Error rate before alert (%)

#### 6.4 Backup & Recovery
- **Backup Schedule** - Daily/Weekly/Monthly
- **Retention Period** - Days to keep backups
- **Auto-Recovery** - Restart on failure

### API Wiring

**Endpoint:** `PATCH /api/v1/products/{id}`

**Request Payload:**
```json
{
  "advanced_settings": {
    "performance": {
      "db_pool_size": 20,
      "cache_ttl": 3600,
      "request_timeout": 30,
      "max_concurrent_requests": 100
    },
    "feature_flags": {
      "telematics_enabled": true,
      "claims_portal_enabled": true,
      "auto_renewal_enabled": false,
      "payment_plans_enabled": true
    },
    "monitoring": {
      "health_check_interval": 60,
      "alert_email": "ops@allianz.com",
      "slack_webhook": "https://hooks.slack.com/...",
      "error_threshold_percent": 5
    },
    "backup": {
      "schedule": "daily",
      "retention_days": 30,
      "auto_recovery": true
    }
  }
}
```

**Response:**
```json
{
  "id": 1,
  "advanced_settings": { ... },
  "updated_at": "2026-01-21T16:20:00Z"
}
```

### User Flow

1. User reviews default performance settings (or customizes)
2. User toggles feature flags based on product needs
3. User configures monitoring contacts
4. User sets backup policies
5. Shows summary of all settings
6. Click "Save & Deploy" to complete configuration

---

## Complete API Flow

### Creating New Product (Complete Flow)

**Step 1: Create Product (Section 1)**
```http
POST /api/v1/products
{
  "name": "Allianz Insurance",
  "slug": "allianz-insurance",
  "port": 8001,
  "replicas": 2,
  "image_id": 5
}

Response: { "id": 1, ... }
```

**Step 2: Update Environment Variables (Section 2)**
```http
PATCH /api/v1/products/1
{
  "env_vars": { ... }
}
```

**Step 3: Update Database Config (Section 3)**
```http
PATCH /api/v1/products/1
{
  "database_config": { ... }
}
```

**Step 4: Update Events Config (Section 4)**
```http
PATCH /api/v1/products/1
{
  "events_config": { ... }
}
```

**Step 5: Update Validation Rules (Section 5)**
```http
PATCH /api/v1/products/1
{
  "validation_rules": { ... }
}
```

**Step 6: Update Advanced Settings (Section 6)**
```http
PATCH /api/v1/products/1
{
  "advanced_settings": { ... }
}
```

**Step 7: Deploy Product**
```http
POST /api/v1/products/1/start

Response: { "status": "starting", "service_id": "abc123" }
```

### Editing Existing Product

**Load Product Data:**
```http
GET /api/v1/products/1

Response:
{
  "id": 1,
  "name": "Allianz Insurance",
  "env_vars": { ... },
  "database_config": { ... },
  "events_config": { ... },
  "validation_rules": { ... },
  "advanced_settings": { ... },
  "status": "running"
}
```

**Update Any Section:**
```http
PATCH /api/v1/products/1
{
  "validation_rules": { ... }  // Only update what changed
}
```

---

## Data Persistence Strategy

### Option 1: Single Endpoint (All-in-One)
Store all configuration sections as JSON fields in products table.

**Pros:**
- Simple API
- One request to get all data
- Easy to version control

**Cons:**
- Large payloads
- Harder to validate specific sections

### Option 2: Separate Endpoints per Section
Create dedicated endpoints for each configuration section.

**Endpoints:**
- `PATCH /api/v1/products/{id}/instance`
- `PATCH /api/v1/products/{id}/env-vars`
- `PATCH /api/v1/products/{id}/database-config`
- `PATCH /api/v1/products/{id}/events`
- `PATCH /api/v1/products/{id}/validation-rules`
- `PATCH /api/v1/products/{id}/advanced`

**Pros:**
- Granular updates
- Better validation per section
- Clearer API

**Cons:**
- More API calls
- Need to coordinate multiple requests

### Recommended: Hybrid Approach
Use single endpoint for updates, but support partial payloads.

```http
PATCH /api/v1/products/1
{
  "events_config": { ... }  // Only update this section
}
```

Backend merges with existing data, only updating provided fields.

---

## Validation Summary

### Section-Specific Validation

**Section 1 (Instance):**
- ❌ Duplicate slug
- ❌ Duplicate port
- ❌ Invalid image_id

**Section 2 (Env Vars):**
- ❌ Missing required variables
- ❌ Invalid URL formats
- ❌ Too-short secrets

**Section 3 (Database):**
- ❌ Invalid currency code
- ❌ Negative coverage amounts
- ❌ Missing required fields

**Section 4 (Events):**
- ❌ Invalid MQTT topic patterns
- ❌ Invalid webhook URLs
- ❌ Conflicting event mappings

**Section 5 (Validation Rules):**
- ❌ Min > Max contradictions
- ❌ Invalid percentage values
- ❌ Circular rule dependencies

**Section 6 (Advanced):**
- ❌ Invalid email format
- ❌ Out-of-range values
- ❌ Invalid cron expressions

### Global Validation

Before allowing deployment:
- ✅ All required sections completed
- ✅ No validation errors
- ✅ All interdependent values are consistent
- ✅ Product is in "stopped" status (for first deployment)

---

## UI/UX Recommendations

### Visual Indicators

**Section Completion:**
```
✅ 1. Instance Configuration    (Complete)
✅ 2. Environment Variables      (Complete)
⚠️  3. Database Configuration    (Missing required fields)
⏳ 4. Events & Actions           (In Progress)
⭕ 5. Validation Rules           (Not Started)
⭕ 6. Advanced Settings          (Not Started)
```

### Progress Bar
```
[████████████░░░░░░░░░░░░] 50% Complete
4 of 6 sections configured
```

### Save Behavior

**Auto-Save:**
- Save each section when user clicks "Next"
- Show "Saving..." indicator
- Confirm save with checkmark

**Manual Save:**
- "Save Draft" button saves current state
- "Save & Deploy" validates all sections and starts deployment

### Error Handling

**Inline Errors:**
- Show errors next to problematic fields
- Highlight invalid sections in navigation

**Summary Modal:**
- Before deployment, show validation summary
- List all errors grouped by section
- Allow user to jump to error location

---

## Summary for UI Developer

**Implement 6 configuration sections:**

1. **Instance** - Basic Docker settings (name, slug, port, replicas, image)
2. **Env Variables** - Required environment variables (DATABASE_URL, API keys, etc.)
3. **Database Config** - Business settings (product codes, coverage, pricing)
4. **Events & Actions** - MQTT topics, webhooks, event handlers
5. **Validation Rules** - Policy/claim/pricing rules
6. **Advanced** - Performance, feature flags, monitoring, backups

**API Integration:**
- Single `PATCH /api/v1/products/{id}` endpoint
- Supports partial updates (send only changed sections)
- Each section has its own JSON object in payload

**User Experience:**
- Clear navigation between sections
- Visual progress indicators
- Section-specific validation
- Auto-save on navigation
- Final validation before deployment

**No backend code needed from UI team** - all endpoints already implemented and ready to use!
