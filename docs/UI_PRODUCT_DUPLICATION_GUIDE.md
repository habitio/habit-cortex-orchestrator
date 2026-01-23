# UI Guide: Product Duplication Feature

## Overview

The Product Duplication feature allows users to create a copy of an existing product instance with all its configuration, avoiding manual recreation of environment variables, MQTT settings, and subscriptions.

---

## User Flow

1. User navigates to a product detail page
2. User clicks "Duplicate Product" button
3. Modal/form appears requesting:
   - New Product Name
   - New Product Slug
   - New Port Number
4. User submits the form
5. System validates inputs and creates duplicate
6. User is redirected to the new product or shown success message

---

## API Endpoint

### Duplicate Product

**Method:** `POST`

**URL:** `/api/v1/products/{product_id}/duplicate`

**Path Parameters:**
- `product_id` (integer, required) - The ID of the product to duplicate

**Query Parameters:**
- `new_name` (string, required) - Name for the new product (e.g., "BRE Tyres Test")
- `new_slug` (string, required) - Unique slug identifier (e.g., "bre-tyres-test")
- `new_port` (integer, required) - Unique port number for the product (e.g., 8001)

**Example Request:**
```
POST /api/v1/products/2/duplicate?new_name=BRE%20Tyres%20Test&new_slug=bre-tyres-test&new_port=8001
```

---

## Request Details

### URL Encoding
All query parameters must be URL-encoded:
- Spaces become `%20`
- Special characters must be properly encoded

### Validation Rules

**new_name:**
- Must not be empty
- Can contain spaces and special characters
- Recommended: 3-100 characters

**new_slug:**
- Must be unique across all products
- Recommended format: lowercase with hyphens (e.g., "my-product-name")
- No spaces allowed
- Recommended: alphanumeric and hyphens only

**new_port:**
- Must be unique across all products
- Valid port range: 1024-65535
- Reserved ports (8004) should be avoided

---

## Success Response

**Status Code:** `200 OK`

**Response Body:**
```json
{
  "id": 5,
  "name": "BRE Tyres Test",
  "slug": "bre-tyres-test",
  "port": 8001,
  "replicas": 1,
  "status": "stopped",
  "image_name": "bre-cortex:v0.0.7",
  "env_vars": {
    "ENV": "development",
    "DEBUG": "true",
    "API_HOST": "0.0.0.0",
    ...
  },
  "created_at": "2026-01-23T15:20:18.252182+00:00",
  "source_product_id": 2,
  "source_product_name": "Invoice Protection",
  "mqtt_config_copied": true,
  "subscriptions_copied": 10
}
```

### Response Fields

**Core Product Information:**
- `id` - New product ID (integer)
- `name` - Product name as provided (string)
- `slug` - Product slug as provided (string)
- `port` - Port number as provided (integer)
- `replicas` - Number of replicas copied from source (integer)
- `status` - Always "stopped" for new products (string)
- `image_name` - Docker image copied from source (string)
- `created_at` - Timestamp of creation (ISO 8601 string)

**Environment Variables:**
- `env_vars` - Complete dictionary of all environment variables copied from source (object)

**Duplication Metadata:**
- `source_product_id` - ID of the original product (integer)
- `source_product_name` - Name of the original product (string)
- `mqtt_config_copied` - Whether MQTT configuration was copied (boolean)
- `subscriptions_copied` - Number of MQTT subscriptions copied (integer)

---

## Error Responses

### 404 Not Found
**Scenario:** Source product does not exist

**Status Code:** `404`

**Response Body:**
```json
{
  "detail": "Source product 999 not found"
}
```

**UI Action:**
- Display error message: "The product you're trying to duplicate no longer exists"
- Return to products list

---

### 409 Conflict - Duplicate Slug
**Scenario:** The provided slug already exists

**Status Code:** `409`

**Response Body:**
```json
{
  "detail": "Product with slug 'bre-tyres-test' already exists"
}
```

**UI Action:**
- Highlight the slug input field
- Display error message: "This slug is already in use. Please choose a different one."
- Allow user to modify slug and retry

---

### 409 Conflict - Port In Use
**Scenario:** The provided port is already in use

**Status Code:** `409`

**Response Body:**
```json
{
  "detail": "Port 8001 is already in use by product 'BRE Tyres Test'"
}
```

**UI Action:**
- Highlight the port input field
- Display error message with the product name using the port
- Suggest next available port (optional feature)
- Allow user to modify port and retry

---

### 422 Unprocessable Entity
**Scenario:** Invalid input parameters (wrong type, missing required field)

**Status Code:** `422`

**Response Body:**
```json
{
  "detail": [
    {
      "loc": ["query", "new_port"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

**UI Action:**
- Validate inputs client-side before submission
- Display field-specific error messages
- Highlight invalid fields

---

## What Gets Copied

The duplication process copies the following from the source product:

**✅ Copied:**
- All environment variables (complete key-value dictionary)
- MQTT broker configuration (host, port, TLS settings, credentials)
- MQTT topic configuration (prefix, pattern, QoS, shared subscriptions)
- All MQTT subscriptions (name, topic, enabled status, description)
- All actions within each subscription (conditions, configurations)
- Number of replicas
- Docker image reference

**❌ NOT Copied:**
- Shared key (new product will need to generate its own)
- Running state (new product always starts as "stopped")
- Service ID (assigned when product is deployed)
- Deployment timestamp
- Activity logs
- Statistics (messages received, actions executed, etc.)

---

## UI Recommendations

### Form Design

**Modal/Dialog with 3 Fields:**

1. **Product Name**
   - Type: Text input
   - Placeholder: "Enter new product name"
   - Default: `{source_product_name} (Copy)`
   - Required: Yes

2. **Product Slug**
   - Type: Text input
   - Placeholder: "enter-slug-here"
   - Default: `{source_slug}-copy` or suggest based on name
   - Required: Yes
   - Pattern: Lowercase, hyphens, no spaces
   - Real-time validation: Check uniqueness

3. **Port Number**
   - Type: Number input
   - Placeholder: "8001"
   - Default: Suggest next available port
   - Required: Yes
   - Min: 1024, Max: 65535
   - Real-time validation: Check availability

### Button States

**Before Submission:**
- Primary button: "Duplicate Product"
- Secondary button: "Cancel"

**During Submission:**
- Show loading spinner
- Disable form inputs
- Button text: "Duplicating..."

**After Success:**
- Show success message: "Product duplicated successfully!"
- Option 1: Redirect to new product detail page
- Option 2: Show new product ID and option to view
- Close modal automatically after 2 seconds

**After Error:**
- Keep modal open
- Display error message above form
- Re-enable form for corrections
- Button text returns to "Duplicate Product"

### Confirmation

For products with complex configurations:
- Show summary before duplication:
  - "This will copy 44 environment variables"
  - "This will copy MQTT configuration with 10 subscriptions"
  - "Total actions: 14"
- Confirm button: "Yes, Duplicate"

### Success Actions

After successful duplication, provide quick actions:
- "View New Product" - Navigate to product detail
- "Start Product" - Immediately deploy the duplicate
- "Edit Configuration" - Modify before deployment
- "Duplicate Another" - Create another copy

---

## Pre-flight Validation (Recommended)

Before showing the duplication form, the UI can optionally fetch available resources:

**Check Available Ports:**
```
GET /api/v1/products
```
Extract used ports from response and suggest next available port.

**Suggest Slug:**
Based on source product slug:
- If source is "invoice-protection", suggest "invoice-protection-2"
- If "invoice-protection-2" exists, suggest "invoice-protection-3"
- Or use timestamp: "invoice-protection-2026-01-23"

---

## Complete Workflow Example

### Step 1: User Clicks "Duplicate"
- Source Product ID: 2
- Source Product Name: "Invoice Protection"
- Source Product Slug: "invoice-protection"
- Source Product Port: 8000

### Step 2: Form Shows Pre-filled Values
- Name: "Invoice Protection (Copy)"
- Slug: "invoice-protection-copy"
- Port: 8001 (auto-suggested)

### Step 3: User Modifies Values
- Name: "BRE Tyres Test"
- Slug: "bre-tyres-test"
- Port: 8001

### Step 4: UI Validates
- Check slug uniqueness (client-side check against cached product list)
- Check port availability
- Both valid → Enable submit button

### Step 5: Submit Request
```
POST /api/v1/products/2/duplicate?new_name=BRE%20Tyres%20Test&new_slug=bre-tyres-test&new_port=8001
```

### Step 6: Handle Response
- Status 200 → Show success, redirect to new product
- Status 409 → Show specific error, allow correction
- Status 404 → Show error, close modal
- Status 422 → Highlight invalid fields

### Step 7: Post-Duplication
- Navigate to new product detail page (ID: 5)
- Show toast notification: "Product duplicated successfully! 44 environment variables and 10 MQTT subscriptions copied."
- New product is in "stopped" state, ready for configuration review or deployment

---

## Testing Checklist

### Successful Duplication
- [ ] Duplicate with all unique values succeeds
- [ ] All environment variables are present in new product
- [ ] MQTT configuration matches source
- [ ] All subscriptions are copied
- [ ] All actions within subscriptions are copied
- [ ] New product status is "stopped"

### Error Handling
- [ ] Duplicate with existing slug shows error
- [ ] Duplicate with existing port shows error
- [ ] Duplicate of non-existent product shows error
- [ ] Invalid port number shows validation error
- [ ] Empty required fields show validation error

### User Experience
- [ ] Form pre-fills with suggested values
- [ ] Loading state shows during API call
- [ ] Success message appears after completion
- [ ] Redirect works correctly
- [ ] Error messages are clear and actionable

---

## Integration Notes

### State Management
After successful duplication:
- Refresh products list if cached
- Add new product to local state
- Update port availability list
- Clear duplication form

### Permissions
If implementing user roles:
- Check "create_product" permission before showing button
- Handle 403 Forbidden response if unauthorized

### Analytics
Track duplication events:
- Event: "product_duplicated"
- Properties: source_product_id, new_product_id, env_vars_count, subscriptions_count

---

## Summary

**Endpoint:** `POST /api/v1/products/{product_id}/duplicate`

**Required Parameters:** new_name, new_slug, new_port

**Success Response:** Complete product object with duplication metadata

**Key Validations:** Unique slug, unique port, valid product_id

**Copies:** Environment variables, MQTT config, subscriptions, actions, replicas, image

**Does Not Copy:** Shared key, running state, service ID, logs, statistics

---

## Related Endpoints

### View MQTT Configuration
After duplicating a product, the UI can view the copied MQTT configuration:

**Method:** `GET`

**URL:** `/api/v1/products/{product_id}/mqtt-config`

**Authentication:** None required (public endpoint for UI access)

**Example:**
```
GET /api/v1/products/6/mqtt-config
```

**Response:**
```json
{
  "product_id": 6,
  "mqtt_config": {
    "id": 3,
    "broker": {
      "host": "api.platform.integrations.habit.io",
      "port": 8889,
      "use_tls": true,
      "verify_cert": true,
      "username": "ab6a53ba-cba1-4e88-90ba-43da8a296490",
      "password": "***",
      "client_id": null,
      "keep_alive": 60,
      "clean_session": true
    },
    "topics": {
      "prefix": "/v3/applications",
      "pattern": "{application_id}/business-events",
      "use_shared": true,
      "shared_group": "bre",
      "qos": 1
    }
  },
  "subscriptions": [
    {
      "id": 123,
      "name": "payment_change_state",
      "topic": "/v3/applications/ab6a53ba-cba1-4e88-90ba-43da8a296490/business-events",
      "enabled": true,
      "description": "Handle payment state changes",
      "actions": [...]
    }
  ],
  "status": {
    "connected": false,
    "last_connected_at": null
  }
}
```

### Edit MQTT Configuration
The UI can edit the duplicated product's MQTT settings:

**Method:** `PUT`

**URL:** `/api/v1/products/{product_id}/mqtt-config`

**Authentication:** None required

**Request Body:**
```json
{
  "broker": {
    "host": "api.platform.integrations.habit.io",
    "port": 8889,
    "use_tls": true,
    "verify_cert": true,
    "username": "new-username",
    "password": "new-password",
    "keep_alive": 60,
    "clean_session": true
  },
  "topics": {
    "prefix": "/v3/applications",
    "pattern": "{application_id}/business-events",
    "use_shared": true,
    "shared_group": "bre",
    "qos": 1
  }
}
```

**Note:** Changes require product restart to take effect.

---

## Important UI/UX Considerations

### MQTT Broker Settings vs Environment Variables

**Question:** Do MQTT broker settings overlap with environment variables?

**Answer:** Yes, they overlap by design. Here's the architecture:

**Data Flow:**
```
MQTT Configuration UI → Database (mqtt_configs table) → Environment Variables → Product Instance
```

**How It Works:**
1. **Single Source of Truth:** The MQTT Configuration screen (Broker & Topics tab) is the primary interface for editing MQTT settings
2. **Automatic Sync:** When you save via MQTT Configuration UI, it updates the database `mqtt_configs` table
3. **Deployment:** When the product starts/restarts, the orchestrator automatically populates environment variables from the database MQTT config
4. **Instance Reads:** The running product instance reads MQTT settings from environment variables

**Overlapping Fields:**

| MQTT Config Field | Environment Variable | Note |
|------------------|---------------------|------|
| `broker.host` | `MQTT_HOST` | Auto-synced |
| `broker.port` | `MQTT_PORT` | Auto-synced |
| `broker.use_tls` | `MQTT_USE_TLS` | Auto-synced |
| `broker.username` | `MQTT_USERNAME` | Auto-synced |
| `broker.password` | `MQTT_PASSWORD` | Auto-synced |
| `topics.prefix` | `MQTT_TOPIC_PREFIX` | Auto-synced |
| `topics.shared_group` | `MQTT_SHARED_GROUP` | Auto-synced |

**UI Recommendations:**

1. **Hide MQTT env vars from Environment Variables screen** - Users should not manually edit these
2. **Show read-only notice** - If you display them, mark as "Managed by MQTT Configuration" with a link to the MQTT tab
3. **Prevent manual editing** - Make MQTT-related env vars read-only or hidden in the Environment Variables UI
4. **Single edit location** - Users should only edit MQTT settings via the "MQTT Configuration" screen

**Why This Design:**
- Prevents configuration drift between UI and env vars
- Provides structured validation for MQTT settings
- Allows testing connection before deployment
- Simplifies user experience (one place to configure MQTT)

---

### Event Subscriptions: Actions Configuration Missing

**Critical Issue:** The current UI shows subscriptions but does **NOT** provide a way to configure actions for each subscription.

**What's Missing:**

Looking at your Event Subscriptions screenshot, each subscription shows "0 actions" but there's no interface to:
- View existing actions
- Add new actions
- Edit action configurations
- Delete actions
- Reorder actions (execution_order)

**Required Functionality:**

Each subscription can have multiple actions that execute sequentially. The UI needs to provide:

#### 1. Subscription Detail View

When clicking on a subscription row (the `>` arrow), show a detail panel/modal with:

**Subscription Header:**
- Name (e.g., "payment_change_state")
- Description
- Topic (full MQTT topic path)
- Enabled toggle
- Statistics (messages received, actions executed, failures)

**Actions List:**
- Show all actions for this subscription
- Display action name, type, description
- Show enabled/disabled status
- Show execution order (1, 2, 3...)
- Allow drag-to-reorder
- "Add Action" button

#### 2. Action Editor

For each action, provide form fields based on action type:

**Common Fields (All Action Types):**
- **Name** - Identifier (e.g., "activate_policy")
- **Type** - Dropdown with action types (see below)
- **Description** - What this action does
- **Enabled** - Toggle to enable/disable
- **Execution Order** - Number (1 = first)
- **Conditions** - JSON editor or structured form for filtering

**Action Types & Their Specific Fields:**

| Action Type | Required Config Fields |
|------------|----------------------|
| `activate_policy` | No additional fields |
| `smtp_email` | `email.provider`, `email.template`, `email.recipient_logic` |
| `listmonk_email` | `listmonk.template_id`, `listmonk.recipient_logic` |
| `invalidate_smartlinks` | No additional fields |
| `create_invoice` | No additional fields |
| `http_webhook` | `webhook.url`, `webhook.method`, `webhook.headers`, `webhook.body_template` |
| `custom_api_call` | `api.endpoint`, `api.method`, `api.payload_template` |

**Example Action Configuration:**

```json
{
  "name": "alert_habit",
  "type": "smtp_email",
  "description": "Send email alert to Habit team about payment status change",
  "enabled": true,
  "execution_order": 2,
  "conditions": {
    "payment_new_state": "paid"
  },
  "email": {
    "provider": "smtp",
    "template": "payment_alert",
    "recipient_logic": "sandbox_conditional"
  }
}
```

#### 3. Missing API Endpoints

**Current State:**
- ✅ `GET /mqtt-config/subscriptions` - List all subscriptions
- ✅ `PUT /mqtt-config/subscriptions/{id}` - Update subscription (enabled, description only)
- ❌ **NO endpoints to manage actions**

**What Needs to Be Built:**

The orchestrator needs these additional endpoints:

```
GET    /api/v1/products/{product_id}/mqtt-config/subscriptions/{subscription_id}/actions
POST   /api/v1/products/{product_id}/mqtt-config/subscriptions/{subscription_id}/actions
PUT    /api/v1/products/{product_id}/mqtt-config/subscriptions/{subscription_id}/actions/{action_index}
DELETE /api/v1/products/{product_id}/mqtt-config/subscriptions/{subscription_id}/actions/{action_index}
POST   /api/v1/products/{product_id}/mqtt-config/subscriptions/{subscription_id}/actions/reorder
```

**Current Limitation:**
Actions are stored as a JSON array in the `MQTTSubscription.actions` column. To edit them, you currently need to:
1. GET the full subscription
2. Modify the entire `actions` JSON array client-side
3. PUT the entire subscription back with the updated actions array

This is fragile and error-prone. The UI should either:
- **Option A:** Request backend endpoints to manage individual actions
- **Option B:** Implement a client-side actions editor that modifies the JSON array and sends the full update

#### 4. Can You Replicate mqtt-events.json?

**Answer:** Almost, but with missing features.

**What's Supported ✅:**
- Broker configuration (host, port, TLS, auth)
- Topic configuration (prefix, pattern, QoS, shared subscriptions)
- Multiple event subscriptions
- Actions stored in JSON format
- All action types from mqtt-events.json

**What's Missing ❌:**
- **UI to configure actions** - No interface to add/edit/delete actions for subscriptions
- **Actions API endpoints** - No REST API to manage actions separately
- **Conditions editor** - No UI for setting action execution conditions
- **Action templates** - No templates/examples for common action types
- **Testing actions** - No way to test an action without triggering it from a real MQTT message
- **Action logs** - No way to see execution history of specific actions

**Migration Path from mqtt-events.json:**

To fully migrate from the old `mqtt-events.json` format, the UI needs:

1. **Import Wizard** - Upload mqtt-events.json and automatically create subscriptions + actions
2. **Visual Action Builder** - Drag-and-drop interface for building action chains
3. **Conditions Editor** - Form-based editor for action conditions (no raw JSON editing)
4. **Template Library** - Pre-built action configurations for common scenarios
5. **Test Mode** - Simulate MQTT messages to test action chains

**Recommendation:**

Tell the UI team they need to build:
1. **Subscription Detail View** - Click a subscription to see/edit its actions
2. **Actions Management Interface** - Add/edit/delete/reorder actions
3. **Request Backend Support** - Ask for dedicated actions API endpoints
4. **Conditions Form Builder** - Structured editor for action conditions (payment_new_state, etc.)

**Temporary Workaround:**

Until actions UI is built, users can:
1. Use the existing mqtt-events.json file in the running instance
2. Manually edit subscription actions via database or API (PUT full subscription with actions array)
3. Duplicate products to copy working configurations

---

**Summary:**

1. **MQTT Broker Settings:** Remove from Environment Variables UI - managed automatically via MQTT Configuration screen
2. **Actions Configuration:** Currently missing from UI - needs dedicated interface to add/edit actions per subscription
3. **Full Feature Parity:** Not yet possible - UI needs actions management to fully replace mqtt-events.json
