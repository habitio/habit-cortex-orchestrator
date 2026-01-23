# MQTT Configuration UI Specification

## Overview

This specification defines how to implement the MQTT Configuration UI within the Product Edit screen. The UI manages MQTT broker connections, event subscriptions, and action configurations for product instances.

**Base API URL:** `http://orchestrator-host:8004/api/v1`

**Authentication:** These endpoints do NOT require the `X-Cortex-Shared-Key` header (orchestrator UI endpoints are public).

---

## Environment Variables Management

**Note:** Environment variables for the product are managed through the main Product API, not through MQTT-specific endpoints.

### API Endpoint: Get Product (includes env_vars)

**Endpoint:** `GET /products/{product_id}`

**Response includes env_vars field:**
```json
{
  "id": 2,
  "name": "BRE Tyres",
  "env_vars": {
    "PRODUCT_ID": "2",
    "CORTEX_API_BASE_URL": "http://10.10.141.48:8004",
    "CORTEX_API_SHARED_KEY": "67af2b36b3b547d54c80bf026286d197c528f35de0e5fd27867a77b98f1cfa02df34d1dc0834bb63d2455d68d826bf4ffe0c5c9c6aea949108b16d8eda8bfd5e",
    "APPLICATION_ID": "ab6a53ba-cba1-4e88-90ba-43da8a296490",
    "MUZZLEY_API_URL": "https://api.platform.integrations.habit.io",
    "LISTMONK_URL": "https://list-management.develop.habit.io/",
    "LISTMONK_USERNAME": "habit",
    "LISTMONK_PASSWORD": "Krq7p44EO1yJyaT8HYfDBoVoa0iPfG5f",
    ...
  },
  ...
}
```

### API Endpoint: Update Environment Variables

**Endpoint:** `PATCH /products/{product_id}`

**Request:**
```http
PATCH /api/v1/products/2 HTTP/1.1
Content-Type: application/json

{
  "env_vars": {
    "PRODUCT_ID": "2",
    "APPLICATION_ID": "ab6a53ba-cba1-4e88-90ba-43da8a296490",
    "NEW_VARIABLE": "new_value",
    ...
  }
}
```

**Important:** When updating `env_vars`, you must send the **complete** object with all variables. Partial updates will **replace** the entire env_vars object, not merge.

**UI Behavior:**
1. Load existing env_vars from `GET /products/{id}`
2. User edits/adds/removes variables in UI
3. Send complete updated env_vars object via `PATCH /products/{id}`
4. Never send partial env_vars - always send full object

**Recommended UI:**
- Key-value pair editor (dynamic form)
- "Add Variable" button to add new key-value pairs
- Delete button for each variable
- Validate keys (no spaces, alphanumeric + underscore)
- Mark sensitive variables (PASSWORD, SECRET, KEY) with password input field

---

## Page Structure

**Route:** `/products/:productId/mqtt-configuration`

**Layout:** Three-section interface
1. **Broker & Topics** - Connection settings and topic configuration
2. **Event Subscriptions** - List of MQTT event subscriptions
3. **Subscription Detail** - Actions associated with selected subscription

---

## Section 1: Broker & Topic Configuration

---

## Section 1: Broker & Topic Configuration

### API Endpoint: Get MQTT Configuration

**Purpose:** Load complete MQTT configuration on page mount

**Endpoint:** `GET /products/{product_id}/mqtt-config`

**Request:**
```http
GET /api/v1/products/2/mqtt-config HTTP/1.1
```

**Response (200 OK):**
```json
{
  "mqtt_config": {
    "id": 1,
    "product_id": 2,
    "broker": {
      "host": "api.platform.integrations.habit.io",
      "port": 8889,
      "use_tls": true,
      "verify_cert": false,
      "username": "ab6a53ba-cba1-4e88-90ba-43da8a296490",
      "password": "••••••••",
      "client_id": "",
      "keep_alive": 60,
      "clean_session": true
    },
    "topics": {
      "prefix": "/v3/applications",
      "pattern": "{application_id}/business-events",
      "use_shared": true,
      "shared_group": "bre",
      "qos": 1
    },
    "created_at": "2026-01-22T10:30:00Z",
    "updated_at": "2026-01-23T14:20:00Z"
  },
  "subscriptions": [...],
  "connection_status": {
    "is_connected": true,
    "last_connected_at": "2026-01-23T14:15:32Z",
    "last_error": null,
    "connection_uptime_seconds": 3600
  }
}
```

**UI Behavior:**
- Call this endpoint when page loads
- Populate all form fields with `mqtt_config.broker` and `mqtt_config.topics`
- Display connection status in header/status bar
- If `mqtt_config` is null, show default values (host: "", port: 1883, clean_session: true)

---

### API Endpoint: Update Broker & Topic Configuration

**Purpose:** Save broker connection settings and topic configuration

**Endpoint:** `PUT /products/{product_id}/mqtt-config`

**Request:**
```http
PUT /api/v1/products/2/mqtt-config HTTP/1.1
Content-Type: application/json

{
  "broker": {
    "host": "api.platform.integrations.habit.io",
    "port": 8889,
    "use_tls": true,
    "verify_cert": false,
    "username": "ab6a53ba-cba1-4e88-90ba-43da8a296490",
    "password": "new_password_here",
    "client_id": "",
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

**Response (200 OK):**
```json
{
  "id": 1,
  "product_id": 2,
  "broker": {
    "host": "api.platform.integrations.habit.io",
    "port": 8889,
    "use_tls": true,
    "verify_cert": false,
    "username": "ab6a53ba-cba1-4e88-90ba-43da8a296490",
    "password": "new_password_here",
    "client_id": "",
    "keep_alive": 60,
    "clean_session": true
  },
  "topics": {
    "prefix": "/v3/applications",
    "pattern": "{application_id}/business-events",
    "use_shared": true,
    "shared_group": "bre",
    "qos": 1
  },
  "updated_at": "2026-01-23T15:00:00Z"
}
```

**UI Behavior:**
- Call when "Save Configuration" button clicked
- Show loading state on button during save
- On success: Show toast "Configuration saved successfully"
- Update form with returned data
- On error: Show validation errors below respective fields

**Field Validations:**
- `host`: Required, max 255 chars
- `port`: Required, integer 1-65535
- `username`: Optional, max 255 chars
- `password`: Optional, max 512 chars (if empty, password unchanged)
- `client_id`: Optional, max 255 chars (empty = auto-generate)
- `keep_alive`: Required, integer 10-3600
- `clean_session`: Required, boolean
- `topics.prefix`: Required, max 255 chars
- `topics.pattern`: Required, max 255 chars
- `topics.shared_group`: Required if `use_shared = true`, max 100 chars
- `topics.qos`: Required, must be 0, 1, or 2

---

### API Endpoint: Test MQTT Connection

**Purpose:** Validate broker credentials before saving

**Endpoint:** `POST /products/{product_id}/mqtt-config/test-connection`

**Request:**
```http
POST /api/v1/products/2/mqtt-config/test-connection HTTP/1.1
Content-Type: application/json

{
  "host": "api.platform.integrations.habit.io",
  "port": 8889,
  "use_tls": true,
  "username": "test_user",
  "password": "test_password"
}
```

**Response (200 OK - Success):**
```json
{
  "success": true,
  "message": "Successfully connected to MQTT broker",
  "latency_ms": 45,
  "broker_info": {
    "version": "5.0",
    "max_qos": 2
  }
}
```

**Response (200 OK - Failure):**
```json
{
  "success": false,
  "message": "Connection refused: Authentication failed",
  "error_code": "AUTH_FAILED"
}
```

**UI Behavior:**
- "Test Connection" button triggers this endpoint
- Show loading spinner on button during test
- On success: Show green alert "Connected in {latency_ms}ms"
- On failure: Show red alert with error message
- Test does NOT save configuration

---

### UI Form Fields

**Broker Configuration:**
- Host (text input, required)
- Port (number input, required, default: 1883)
- Use TLS (toggle/checkbox, default: false)
- Verify Certificate (toggle, only show if TLS enabled, default: true)
- Username (text input, optional)
- Password (password input, optional, placeholder: "Leave blank to keep existing")
- Client ID (text input, optional, placeholder: "Auto-generated if empty")
- Keep Alive (number input, required, default: 60, suffix: "seconds")
- Clean Session (toggle, default: true)

**Topic Configuration:**
- Topic Prefix (text input, required, default: "/v3/applications")
- Topic Pattern (text input, required, default: "{application_id}/business-events")
- Use Shared Subscriptions (toggle, default: true)
- Shared Group Name (text input, conditional: only show if shared enabled, default: "bre")
- QoS (select/dropdown, required, options: 0, 1, 2, default: 1)

**QoS Options:**
- 0: "At most once (fire and forget)"
- 1: "At least once (acknowledged)" ← Default
- 2: "Exactly once (assured delivery)"

---

## Section 2: Event Subscriptions List

### API Endpoint: List Subscriptions

**Purpose:** Display all event subscriptions for the product

**Endpoint:** `GET /products/{product_id}/mqtt-config/subscriptions`

**Request:**
```http
GET /api/v1/products/2/mqtt-config/subscriptions HTTP/1.1
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "event_name": "payment_change_state",
    "topic": "/v3/applications/{application_id}/business-events/payment-change-state",
    "description": "Triggered when payment state changes",
    "enabled": true,
    "action_count": 4
  },
  {
    "id": 2,
    "event_name": "payment_marked_as_pending",
    "topic": "/v3/applications/{application_id}/business-events/payment-marked-as-pending",
    "description": "Triggered when payment is marked as pending",
    "enabled": true,
    "action_count": 2
  },
  {
    "id": 3,
    "event_name": "quote_updated",
    "topic": "/v3/applications/{application_id}/business-events/quote-updated",
    "description": "Triggered when quote properties are updated",
    "enabled": false,
    "action_count": 0
  }
]
```

**UI Behavior:**
- Load this when page mounts (can use data from initial GET if available)
- Display as table or card list
- Show: event name, description, topic (truncated/collapsible), action count, enabled toggle
- Clicking a row opens subscription detail view

**Table Columns:**
1. Event Name (bold/primary text)
2. Description (secondary/muted text, under event name)
3. Topic (code/monospace, truncated, tooltip shows full)
4. Actions (badge showing count)
5. Enabled (toggle switch)

---

### API Endpoint: Create Subscription

**Purpose:** Add a new event subscription

**Endpoint:** `POST /products/{product_id}/mqtt-config/subscriptions`

**Request:**
```http
POST /api/v1/products/2/mqtt-config/subscriptions HTTP/1.1
Content-Type: application/json

{
  "event_name": "policy_created",
  "topic": "/v3/applications/{application_id}/business-events/policy-created",
  "description": "Triggered when a new policy is created",
  "enabled": true
}
```

**Response (201 Created):**
```json
{
  "id": 15,
  "product_id": 2,
  "event_name": "policy_created",
  "topic": "/v3/applications/{application_id}/business-events/policy-created",
  "description": "Triggered when a new policy is created",
  "enabled": true,
  "created_at": "2026-01-23T15:00:00Z",
  "updated_at": "2026-01-23T15:00:00Z"
}
```

**UI Behavior:**
- "Add Subscription" button opens modal/form
- Form fields: event_name, topic, description, enabled toggle
- On success: Close modal, refresh subscription list, show toast
- On error: Show validation errors in modal

---

### API Endpoint: Update Subscription

**Purpose:** Modify subscription metadata or toggle enabled state

**Endpoint:** `PATCH /products/{product_id}/mqtt-config/subscriptions/{subscription_id}`

**Request (Toggle Enabled):**
```http
PATCH /api/v1/products/2/mqtt-config/subscriptions/1 HTTP/1.1
Content-Type: application/json

{
  "enabled": false
}
```

**Request (Update Description):**
```http
PATCH /api/v1/products/2/mqtt-config/subscriptions/1 HTTP/1.1
Content-Type: application/json

{
  "description": "Updated description text"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "product_id": 2,
  "event_name": "payment_change_state",
  "topic": "/v3/applications/{application_id}/business-events/payment-change-state",
  "description": "Updated description text",
  "enabled": false,
  "updated_at": "2026-01-23T15:05:00Z"
}
```

**UI Behavior:**
- Toggle switch in table row calls this immediately (optimistic UI update)
- Edit button opens modal with pre-filled form
- On success: Update list item, show toast
- On error (toggle): Revert toggle state, show error toast

---

### API Endpoint: Delete Subscription

**Purpose:** Remove subscription and all its actions

**Endpoint:** `DELETE /products/{product_id}/mqtt-config/subscriptions/{subscription_id}`

**Request:**
```http
DELETE /api/v1/products/2/mqtt-config/subscriptions/3 HTTP/1.1
```

**Response (204 No Content):**
```
(Empty body)
```

**UI Behavior:**
- Delete button/icon in table row
- Show confirmation dialog: "Delete subscription '{event_name}'? This will also delete all {action_count} associated actions."
- On confirm: Call endpoint
- On success: Remove from list, show toast "Subscription deleted"
- On error: Show error toast

---

## Section 3: Subscription Detail & Actions

### API Endpoint: Get Subscription with Actions

**Purpose:** Load detailed subscription info including all actions

**Endpoint:** `GET /products/{product_id}/mqtt-config/subscriptions/{subscription_id}`

**Request:**
```http
GET /api/v1/products/2/mqtt-config/subscriptions/1 HTTP/1.1
```

**Response (200 OK):**
```json
{
  "id": 1,
  "product_id": 2,
  "event_name": "payment_change_state",
  "topic": "/v3/applications/{application_id}/business-events/payment-change-state",
  "description": "Triggered when payment state changes",
  "enabled": true,
  "created_at": "2026-01-22T10:30:00Z",
  "updated_at": "2026-01-23T12:00:00Z",
  "actions": [
    {
      "id": 1,
      "subscription_id": 1,
      "name": "activate_policy",
      "action_type": "activate_policy",
      "description": "Activate policy when payment is marked as paid",
      "conditions": {
        "payment_new_state": "paid"
      },
      "config": {},
      "execution_order": 1,
      "enabled": true,
      "created_at": "2026-01-22T10:30:00Z",
      "updated_at": "2026-01-22T10:30:00Z"
    },
    {
      "id": 2,
      "subscription_id": 1,
      "name": "alert_habit",
      "action_type": "smtp_email",
      "description": "Send email alert to Habit team",
      "conditions": {
        "payment_new_state": "paid"
      },
      "config": {
        "provider": "smtp",
        "template": "payment_alert",
        "recipient_logic": "sandbox_conditional"
      },
      "execution_order": 2,
      "enabled": true,
      "created_at": "2026-01-22T10:30:00Z",
      "updated_at": "2026-01-22T10:30:00Z"
    }
  ]
}
```

**UI Behavior:**
- Call when user clicks subscription row or "View Details" button
- Display in modal, side panel, or dedicated detail view
- Show subscription info at top
- List actions below with their details
- Actions should be ordered by `execution_order` ascending

---

### API Endpoint: Create Action

**Purpose:** Add new action to a subscription

**Endpoint:** `POST /products/{product_id}/mqtt-config/subscriptions/{subscription_id}/actions`

**Request Example 1 (Email Action):**
```http
POST /api/v1/products/2/mqtt-config/subscriptions/1/actions HTTP/1.1
Content-Type: application/json

{
  "name": "send_confirmation_email",
  "action_type": "conditional_email",
  "description": "Send confirmation email to customer",
  "conditions": {
    "payment_new_state": "paid",
    "payment_method": ["credit_card", "debit_card"]
  },
  "config": {
    "provider": "listmonk",
    "template_ref": "payment_confirmation",
    "recipient_source": "insuree",
    "recipient_property": "email"
  },
  "execution_order": 3,
  "enabled": true
}
```

**Request Example 2 (Policy Action):**
```http
POST /api/v1/products/2/mqtt-config/subscriptions/1/actions HTTP/1.1
Content-Type: application/json

{
  "name": "activate_policy",
  "action_type": "activate_policy",
  "description": "Activate policy when payment is confirmed",
  "conditions": {
    "payment_new_state": "paid"
  },
  "config": {},
  "execution_order": 1,
  "enabled": true
}
```

**Response (201 Created):**
```json
{
  "id": 25,
  "subscription_id": 1,
  "name": "send_confirmation_email",
  "action_type": "conditional_email",
  "description": "Send confirmation email to customer",
  "conditions": {
    "payment_new_state": "paid",
    "payment_method": ["credit_card", "debit_card"]
  },
  "config": {
    "provider": "listmonk",
    "template_ref": "payment_confirmation",
    "recipient_source": "insuree",
    "recipient_property": "email"
  },
  "execution_order": 3,
  "enabled": true,
  "created_at": "2026-01-23T15:10:00Z",
  "updated_at": "2026-01-23T15:10:00Z"
}
```

**UI Behavior:**
- "Add Action" button opens modal/form
- Form includes: name, action_type (dropdown), description, conditions (JSON editor), config (JSON editor), execution_order, enabled
- Auto-suggest next execution_order based on existing actions
- On success: Close modal, refresh action list, show toast
- On error: Show validation errors in modal

**Action Type Options:**
- `activate_policy` - Activates insurance policy
- `conditional_email` - Sends email via Listmonk
- `smtp_email` - Sends email via SMTP
- `invalidate_smartlinks` - Invalidates quote smartlinks
- `create_invoice` - Creates invoice in Moloni
- `healthcheck_response` - Responds to MQTT ping
- `http_webhook` - Calls external HTTP endpoint

---

### API Endpoint: Update Action

**Purpose:** Modify existing action

**Endpoint:** `PATCH /products/{product_id}/mqtt-config/subscriptions/{subscription_id}/actions/{action_id}`

**Request:**
```http
PATCH /api/v1/products/2/mqtt-config/subscriptions/1/actions/1 HTTP/1.1
Content-Type: application/json

{
  "description": "Updated action description",
  "conditions": {
    "payment_new_state": "paid",
    "payment_amount_min": 100
  },
  "enabled": false
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "subscription_id": 1,
  "name": "activate_policy",
  "action_type": "activate_policy",
  "description": "Updated action description",
  "conditions": {
    "payment_new_state": "paid",
    "payment_amount_min": 100
  },
  "config": {},
  "execution_order": 1,
  "enabled": false,
  "updated_at": "2026-01-23T15:15:00Z"
}
```

**UI Behavior:**
- Edit button opens modal with pre-filled form
- Toggle switch for enabled calls this immediately
- On success: Update action in list, show toast
- On error: Show validation errors or revert toggle

---

### API Endpoint: Delete Action

**Purpose:** Remove action from subscription

**Endpoint:** `DELETE /products/{product_id}/mqtt-config/subscriptions/{subscription_id}/actions/{action_id}`

**Request:**
```http
DELETE /api/v1/products/2/mqtt-config/subscriptions/1/actions/2 HTTP/1.1
```

**Response (204 No Content):**
```
(Empty body)
```

**UI Behavior:**
- Delete button/icon on action item
- Show confirmation: "Delete action '{name}'?"
- On success: Remove from list, show toast
- On error: Show error toast

---

## Action Configuration Reference

### Action Type: conditional_email

**Required `config` fields:**
```json
{
  "provider": "listmonk",
  "template_ref": "payment_confirmation",
  "recipient_source": "insuree",
  "recipient_property": "email"
}
```

**Field Descriptions:**
- `provider`: Email provider ("listmonk")
- `template_ref`: Listmonk template ID/name
- `recipient_source`: Data source for recipient ("insuree", "policy", "payment")
- `recipient_property`: Property containing email address

---

### Action Type: smtp_email

**Required `config` fields:**
```json
{
  "provider": "smtp",
  "template": "payment_alert",
  "recipient_logic": "sandbox_conditional"
}
```

**Field Descriptions:**
- `provider`: Always "smtp"
- `template`: Email template name
- `recipient_logic`: Logic for determining recipients

---

### Action Type: http_webhook

**Required `config` fields:**
```json
{
  "url": "https://example.com/webhook",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer token123",
    "Content-Type": "application/json"
  },
  "timeout_seconds": 30
}
```

**Field Descriptions:**
- `url`: Webhook endpoint URL
- `method`: HTTP method (GET, POST, PUT, PATCH, DELETE)
- `headers`: HTTP headers object
- `timeout_seconds`: Request timeout

---

### Action Types with No Config

These action types do not require `config` fields (use empty object `{}`):
- `activate_policy`
- `invalidate_smartlinks`
- `create_invoice`
- `healthcheck_response`

---

## Migration Guide: mqtt_events.json → UI Forms

This section shows how to translate the legacy `mqtt_events.json` format into the orchestrator UI/API format.

### Key Structural Differences

| mqtt_events.json | Orchestrator API | Notes |
|------------------|------------------|-------|
| `events[]` | `subscriptions[]` | Top-level events become subscriptions |
| `events[].name` | `subscription.event_name` | Event identifier |
| `events[].actions[]` | `actions[]` | Nested under subscription |
| `actions[].type` | `actions[].action_type` | Field name changed |
| `actions[].email` | `actions[].config` | Email config moved to generic config object |
| N/A | `actions[].execution_order` | New field - defines action sequence |
| `configuration.qos` | `mqtt_config.topics.qos` | Moved to topics configuration |
| `configuration.clean_session` | `mqtt_config.broker.clean_session` | Moved to broker configuration |
| `configuration.shared_subscription` | `mqtt_config.topics.use_shared` | Renamed and moved |
| `configuration.shared_group_prefix` | `mqtt_config.topics.shared_group` | Simplified (remove prefix syntax) |

---

### Example 1: Subscription with conditional_email Action

**mqtt_events.json format:**
```json
{
  "name": "distributor_successful_created_policy",
  "description": "Triggered when a policy is successfully created by a distributor",
  "topic": "/v3/applications/{application_id}/business-events/distributor-successful-created-policy",
  "enabled": true,
  "actions": [
    {
      "name": "send_mb_reference_email",
      "type": "conditional_email",
      "description": "Send MB reference email if payment is pending and method is MB or SEPA",
      "conditions": {
        "payment_state": "pending",
        "payment_method": ["mb", "sepa_debit"]
      },
      "email": {
        "provider": "listmonk",
        "template_ref": "mbreference",
        "recipient_source": "insuree",
        "recipient_property": "email"
      }
    }
  ]
}
```

**UI Steps:**

1. **Create Subscription:**
   - Click "Add Subscription" button
   - Fill form:
     - Event Name: `distributor_successful_created_policy`
     - Topic: `/v3/applications/{application_id}/business-events/distributor-successful-created-policy`
     - Description: `Triggered when a policy is successfully created by a distributor`
     - Enabled: ✓ (checked)
   - Click "Save"

2. **Add Action to Subscription:**
   - In subscription detail view, click "Add Action"
   - Fill form:
     - Name: `send_mb_reference_email`
     - Action Type: `conditional_email` (select from dropdown)
     - Description: `Send MB reference email if payment is pending and method is MB or SEPA`
     - Conditions (JSON editor):
       ```json
       {
         "payment_state": "pending",
         "payment_method": ["mb", "sepa_debit"]
       }
       ```
     - Config (JSON editor):
       ```json
       {
         "provider": "listmonk",
         "template_ref": "mbreference",
         "recipient_source": "insuree",
         "recipient_property": "email"
       }
       ```
     - Execution Order: `1`
     - Enabled: ✓ (checked)
   - Click "Save"

**API Calls:**

```bash
# Step 1: Create subscription
curl -X POST http://localhost:8004/api/v1/products/2/mqtt-config/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "distributor_successful_created_policy",
    "topic": "/v3/applications/{application_id}/business-events/distributor-successful-created-policy",
    "description": "Triggered when a policy is successfully created by a distributor",
    "enabled": true
  }'

# Response: {"id": 1, ...}

# Step 2: Create action
curl -X POST http://localhost:8004/api/v1/products/2/mqtt-config/subscriptions/1/actions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "send_mb_reference_email",
    "action_type": "conditional_email",
    "description": "Send MB reference email if payment is pending and method is MB or SEPA",
    "conditions": {
      "payment_state": "pending",
      "payment_method": ["mb", "sepa_debit"]
    },
    "config": {
      "provider": "listmonk",
      "template_ref": "mbreference",
      "recipient_source": "insuree",
      "recipient_property": "email"
    },
    "execution_order": 1,
    "enabled": true
  }'
```

---

### Example 2: Subscription with Multiple Actions (payment_change_state)

**mqtt_events.json format:**
```json
{
  "name": "payment_change_state",
  "description": "Triggered when payment state changes",
  "topic": "/v3/applications/{application_id}/business-events/payment-change-state",
  "enabled": true,
  "actions": [
    {
      "name": "activate_policy",
      "type": "activate_policy",
      "description": "Activate policy when payment is marked as paid",
      "conditions": {
        "payment_new_state": "paid"
      }
    },
    {
      "name": "alert_habit",
      "type": "smtp_email",
      "description": "Send email alert to Habit team about payment status change",
      "conditions": {
        "payment_new_state": "paid"
      },
      "email": {
        "provider": "smtp",
        "template": "payment_alert",
        "recipient_logic": "sandbox_conditional"
      }
    },
    {
      "name": "invalidate_smartlinks",
      "type": "invalidate_smartlinks",
      "description": "Invalidate all smart links for the quote",
      "conditions": {
        "payment_new_state": "paid"
      }
    },
    {
      "name": "create_invoice",
      "type": "create_invoice",
      "description": "Create invoice in Moloni system",
      "conditions": {
        "payment_new_state": "paid"
      }
    }
  ]
}
```

**UI Steps:**

1. **Create Subscription** (same as Example 1)

2. **Add Action 1 - activate_policy:**
   - Name: `activate_policy`
   - Action Type: `activate_policy`
   - Description: `Activate policy when payment is marked as paid`
   - Conditions: `{"payment_new_state": "paid"}`
   - Config: `{}` (empty object)
   - Execution Order: `1`
   - Enabled: ✓

3. **Add Action 2 - alert_habit:**
   - Name: `alert_habit`
   - Action Type: `smtp_email`
   - Description: `Send email alert to Habit team about payment status change`
   - Conditions: `{"payment_new_state": "paid"}`
   - Config:
     ```json
     {
       "provider": "smtp",
       "template": "payment_alert",
       "recipient_logic": "sandbox_conditional"
     }
     ```
   - Execution Order: `2`
   - Enabled: ✓

4. **Add Action 3 - invalidate_smartlinks:**
   - Name: `invalidate_smartlinks`
   - Action Type: `invalidate_smartlinks`
   - Description: `Invalidate all smart links for the quote`
   - Conditions: `{"payment_new_state": "paid"}`
   - Config: `{}`
   - Execution Order: `3`
   - Enabled: ✓

5. **Add Action 4 - create_invoice:**
   - Name: `create_invoice`
   - Action Type: `create_invoice`
   - Description: `Create invoice in Moloni system`
   - Conditions: `{"payment_new_state": "paid"}`
   - Config: `{}`
   - Execution Order: `4`
   - Enabled: ✓

---

### Example 3: smtp_email Action Type

**mqtt_events.json format:**
```json
{
  "name": "alert_habit_canceled",
  "type": "smtp_email",
  "description": "Alert Habit operations about payment cancellation",
  "conditions": {},
  "email": {
    "provider": "smtp",
    "template": "payment_alert",
    "recipient_logic": "sandbox_conditional"
  }
}
```

**Orchestrator API format:**
```json
{
  "name": "alert_habit_canceled",
  "action_type": "smtp_email",
  "description": "Alert Habit operations about payment cancellation",
  "conditions": {},
  "config": {
    "provider": "smtp",
    "template": "payment_alert",
    "recipient_logic": "sandbox_conditional"
  },
  "execution_order": 1,
  "enabled": true
}
```

**Mapping:**
- `type` → `action_type`
- `email` object → `config` object (content unchanged)
- Add `execution_order` field
- Add `enabled` field (default: true)

---

### Example 4: Complex Conditions (payment_marked_as_pending)

**mqtt_events.json format:**
```json
{
  "name": "send_mb_initial_email",
  "type": "conditional_email",
  "description": "Send MB reference email if payment method is multibanco",
  "conditions": {
    "payment_state": "pending",
    "payment_cdata_path": "cdata.public.last_payment_method",
    "payment_cdata_value": "multibanco",
    "payment_multibanco_exists": true
  },
  "email": {
    "provider": "listmonk",
    "template_ref": "mbreference",
    "recipient_source": "insuree",
    "recipient_property": "email"
  }
}
```

**UI Config Field (JSON editor):**
```json
{
  "payment_state": "pending",
  "payment_cdata_path": "cdata.public.last_payment_method",
  "payment_cdata_value": "multibanco",
  "payment_multibanco_exists": true
}
```

**Notes:**
- Complex condition objects are copied as-is into the conditions field
- No transformation needed - the instance logic understands these conditions
- All custom condition keys are preserved

---

### Example 5: Actions with No Config (activate_policy, invalidate_smartlinks, etc.)

**mqtt_events.json format:**
```json
{
  "name": "activate_policy",
  "type": "activate_policy",
  "description": "Activate policy when payment is marked as paid",
  "conditions": {
    "payment_new_state": "paid"
  }
}
```

**UI Form:**
- Config field: Enter `{}` (empty JSON object)
- All other action types without email/webhook config also use `{}`

**Action types requiring empty config:**
- `activate_policy`
- `invalidate_smartlinks`
- `create_invoice`
- `healthcheck_response`

---

### Example 6: Global Configuration Translation

**mqtt_events.json format:**
```json
{
  "configuration": {
    "qos": 1,
    "clean_session": false,
    "shared_subscription": false,
    "shared_group_prefix": "$share/bre/"
  }
}
```

**UI Form (Broker & Topic Configuration tab):**

**Broker Settings:**
- Clean Session: ☐ (unchecked - maps to `false`)

**Topic Settings:**
- QoS: `1` (select from dropdown)
- Use Shared Subscriptions: ☐ (unchecked - maps to `shared_subscription: false`)
- Shared Group Name: `bre` (remove `$share/` prefix and trailing `/`)

**API Call:**
```bash
curl -X PUT http://localhost:8004/api/v1/products/2/mqtt-config \
  -H "Content-Type: application/json" \
  -d '{
    "broker": {
      "host": "api.platform.integrations.habit.io",
      "port": 8889,
      "use_tls": true,
      "verify_cert": false,
      "username": "ab6a53ba-cba1-4e88-90ba-43da8a296490",
      "password": "your_password",
      "client_id": "",
      "keep_alive": 60,
      "clean_session": false
    },
    "topics": {
      "prefix": "/v3/applications",
      "pattern": "{application_id}/business-events",
      "use_shared": false,
      "shared_group": "bre",
      "qos": 1
    }
  }'
```

---

### Complete Migration Workflow

**To migrate entire mqtt_events.json file:**

1. **Extract broker configuration:**
   - Use existing broker settings from instance environment
   - Map `configuration.clean_session` to `broker.clean_session`

2. **Extract topic configuration:**
   - Parse topic pattern from first event (e.g., `/v3/applications/{application_id}/business-events/...`)
   - Extract prefix: `/v3/applications`
   - Extract pattern: `{application_id}/business-events`
   - Map `configuration.qos` to `topics.qos`
   - Map `configuration.shared_subscription` to `topics.use_shared`
   - Map `configuration.shared_group_prefix` to `topics.shared_group` (remove `$share/` and `/`)

3. **Create subscriptions:**
   - For each event in `events[]`:
     - Create subscription with `event_name`, `topic`, `description`, `enabled`
     - Store subscription ID from response

4. **Create actions:**
   - For each action in `events[].actions[]`:
     - Transform `type` → `action_type`
     - Transform `email` → `config` (if exists)
     - Add `execution_order` (sequential: 1, 2, 3...)
     - Add `enabled: true`
     - Create action under parent subscription

---

### Action Type Mapping Reference

| JSON type | API action_type | Config Structure |
|-----------|----------------|------------------|
| `conditional_email` | `conditional_email` | `{provider, template_ref, recipient_source, recipient_property}` |
| `smtp_email` | `smtp_email` | `{provider, template, recipient_logic}` |
| `activate_policy` | `activate_policy` | `{}` (empty) |
| `invalidate_smartlinks` | `invalidate_smartlinks` | `{}` (empty) |
| `create_invoice` | `create_invoice` | `{}` (empty) |
| `healthcheck_response` | `healthcheck_response` | `{}` (empty) |
| `http_webhook` | `http_webhook` | `{url, method, headers, timeout_seconds}` |

---

### Common Pitfalls

1. **Forgetting execution_order:** Always assign sequential order (1, 2, 3...) when creating actions
2. **Empty config vs missing config:** Use `{}` for actions that don't need config, never omit the field
3. **Shared group prefix:** Remove `$share/` and trailing `/` from group name
4. **Type vs action_type:** Use `action_type` in API, not `type`
5. **Email object location:** Email config goes in `config` object, not separate `email` field
6. **Empty conditions:** Use `{}` for actions without conditions, never omit the field

---

### Validation Before Migration

**Check mqtt_events.json for:**
- [ ] All events have unique names (no duplicates)
- [ ] All actions within subscription have unique names
- [ ] All action types are supported (see Action Type Mapping Reference)
- [ ] Email objects have required fields (provider, template_ref/template, recipient_source/logic, recipient_property)
- [ ] Conditions are valid JSON objects
- [ ] Topics follow consistent pattern

**After migration, verify:**
- [ ] Subscription count matches event count (excluding disabled)
- [ ] Total action count matches (count all actions across all events)
- [ ] Broker connection settings work (test connection)
- [ ] Instance can fetch configuration successfully
- [ ] First MQTT message triggers correct actions

---

## Validation Rules

### Subscription Fields

| Field | Required | Type | Max Length | Rules |
|-------|----------|------|------------|-------|
| event_name | Yes | string | 100 | Unique per product, lowercase with underscores |
| topic | Yes | string | 512 | Valid MQTT topic pattern |
| description | No | string | 1000 | - |
| enabled | Yes | boolean | - | - |

### Action Fields

| Field | Required | Type | Max Length | Rules |
|-------|----------|------|------------|-------|
| name | Yes | string | 100 | Unique per subscription, lowercase with underscores |
| action_type | Yes | string | - | Must be valid action type |
| description | No | string | 500 | - |
| conditions | Yes | object | - | Valid JSON object |
| config | Yes | object | - | Valid JSON object |
| execution_order | Yes | integer | - | >= 1, unique per subscription recommended |
| enabled | Yes | boolean | - | - |

---

## Error Responses

### Format
```json
{
  "detail": "Error message"
}
```

### With Validation Errors
```json
{
  "detail": "Validation failed",
  "errors": [
    {
      "field": "broker.port",
      "message": "Port must be between 1 and 65535"
    },
    {
      "field": "topics.qos",
      "message": "QoS must be 0, 1, or 2"
    }
  ]
}
```

### HTTP Status Codes

| Code | Meaning | UI Action |
|------|---------|-----------|
| 200 | Success | Show success toast |
| 201 | Created | Show success toast, refresh list |
| 204 | Deleted | Remove from list, show toast |
| 400 | Bad Request | Show validation errors below fields |
| 404 | Not Found | Show "Resource not found" error |
| 409 | Conflict | Show "Name already exists" error |
| 500 | Server Error | Show "Server error, please try again" |

---

## User Workflows

### Workflow 1: Initial MQTT Setup

1. Navigate to Product → MQTT Configuration
2. Page loads → `GET /products/2/mqtt-config`
3. Fill in broker settings (host, port, username, password, TLS settings)
4. Click "Test Connection" → `POST /products/2/mqtt-config/test-connection`
5. If successful, fill in topic configuration
6. Click "Save Configuration" → `PUT /products/2/mqtt-config`
7. Success toast shown, form updated with saved data

### Workflow 2: Add Subscription with Actions

1. In subscriptions section, click "Add Subscription"
2. Modal opens with form
3. Fill: event_name, topic, description
4. Click "Save" → `POST /products/2/mqtt-config/subscriptions`
5. Success → Modal shows "Add actions to this subscription?" or closes and opens detail view
6. In detail view, click "Add Action"
7. Fill: name, action_type, description, conditions (JSON), config (JSON), execution_order
8. Click "Save" → `POST /products/2/mqtt-config/subscriptions/15/actions`
9. Success → Action appears in list
10. Repeat steps 6-9 for additional actions

### Workflow 3: Disable Subscription

1. In subscriptions list, toggle enabled switch to OFF
2. UI optimistically updates toggle state
3. Call `PATCH /products/2/mqtt-config/subscriptions/1` with `{"enabled": false}`
4. On success: Show toast "Subscription disabled"
5. On error: Revert toggle, show error toast

### Workflow 4: Edit Action

1. In subscription detail view, click "Edit" on an action
2. Modal opens with form pre-filled
3. Modify fields (description, conditions, config, etc.)
4. Click "Save" → `PATCH /products/2/mqtt-config/subscriptions/1/actions/5`
5. On success: Close modal, update action in list, show toast
6. On error: Show validation errors in modal

### Workflow 5: Delete Action

1. Click delete icon on action
2. Confirmation dialog: "Delete action 'send_email'?"
3. Click "Delete" → `DELETE /products/2/mqtt-config/subscriptions/1/actions/5`
4. On success (204): Remove from list, show toast "Action deleted"
5. On error: Show error toast

---

## UI State Management

### Required State Variables

**Page Level:**
- `mqttConfig` - Broker and topic configuration object
- `subscriptions` - Array of subscription objects
- `selectedSubscription` - Currently selected subscription (for detail view)
- `connectionStatus` - MQTT connection status object
- `loading` - Boolean for initial page load
- `saving` - Boolean for save operations
- `testing` - Boolean for connection test

**Form State:**
- `brokerForm` - Broker configuration form values
- `topicForm` - Topic configuration form values
- `subscriptionForm` - Subscription create/edit form
- `actionForm` - Action create/edit form

### Data Flow

1. **Page Mount:**
   - Set `loading = true`
   - Call `GET /products/{id}/mqtt-config`
   - Set `mqttConfig`, `subscriptions`, `connectionStatus`
   - Set `loading = false`

2. **Save Broker Config:**
   - Set `saving = true`
   - Call `PUT /products/{id}/mqtt-config` with form data
   - Update `mqttConfig` with response
   - Set `saving = false`
   - Show success toast

3. **Select Subscription:**
   - User clicks subscription row
   - Call `GET /products/{id}/mqtt-config/subscriptions/{sub_id}`
   - Set `selectedSubscription` with response (includes actions)
   - Open detail view/modal

4. **Toggle Subscription:**
   - User clicks toggle
   - Optimistically update `subscriptions` array
   - Call `PATCH /products/{id}/mqtt-config/subscriptions/{id}` with new enabled value
   - On error: Revert `subscriptions` array, show error

---

## Recommended UI Components

### Form Fields

**Broker Configuration:**
- Text input: host
- Number input: port, keep_alive
- Toggle/Switch: use_tls, verify_cert, clean_session
- Text input: username
- Password input: password (with show/hide toggle)
- Text input: client_id (with placeholder text)

**Topic Configuration:**
- Text input: prefix, pattern
- Toggle: use_shared
- Text input: shared_group (conditional display)
- Select/Dropdown: qos (3 options)

**Subscription Form:**
- Text input: event_name
- Text input: topic
- Textarea: description
- Toggle: enabled

**Action Form:**
- Text input: name
- Select: action_type (dropdown with 7 options)
- Textarea: description
- JSON Editor: conditions (Monaco, CodeMirror, or textarea with validation)
- JSON Editor: config (Monaco, CodeMirror, or textarea with validation)
- Number input: execution_order
- Toggle: enabled

### Lists & Tables

**Subscriptions List:**
- Option 1: Table with columns (Event Name, Topic, Actions, Enabled)
- Option 2: Card list with subscription cards showing all info

**Actions List:**
- Ordered list (numbered by execution_order)
- Each item shows: name, action_type, description, enabled toggle, edit/delete buttons
- Drag-and-drop for reordering (updates execution_order)

### Modals & Panels

- Create/Edit Subscription: Modal dialog
- Create/Edit Action: Modal dialog
- Subscription Detail: Side panel or modal (showing actions list)
- Delete Confirmation: Alert/confirmation dialog

---

## Testing Checklist

**Broker Configuration:**
- [ ] Load existing config on mount
- [ ] Save broker settings
- [ ] Test connection with valid credentials
- [ ] Test connection with invalid credentials
- [ ] Handle empty password (keeps existing)
- [ ] Validate port range (1-65535)
- [ ] Toggle TLS shows/hides verify_cert
- [ ] Save topic configuration
- [ ] Validate QoS selection

**Subscriptions:**
- [ ] List all subscriptions
- [ ] Create new subscription
- [ ] Edit subscription description
- [ ] Toggle subscription enabled/disabled
- [ ] Delete subscription (with confirmation)
- [ ] Handle duplicate event_name error (409)
- [ ] Select subscription to view details

**Actions:**
- [ ] List actions for subscription
- [ ] Create new action
- [ ] Edit existing action
- [ ] Toggle action enabled/disabled
- [ ] Delete action (with confirmation)
- [ ] Validate JSON in conditions field
- [ ] Validate JSON in config field
- [ ] Handle action type change (show appropriate config fields)
- [ ] Reorder actions (if drag-drop implemented)

**Error Handling:**
- [ ] Show field validation errors
- [ ] Show network errors
- [ ] Show 404 errors gracefully
- [ ] Show 500 errors with retry option
- [ ] Handle concurrent edits (optimistic UI rollback)

**UX:**
- [ ] Loading states on buttons
- [ ] Loading states on page/section load
- [ ] Success toasts after save operations
- [ ] Error toasts on failures
- [ ] Confirmation dialogs before delete
- [ ] Disabled state on form submit
- [ ] Form reset after modal close

---

## Connection Status Polling

### API Endpoint: Get Connection Status

**Endpoint:** `GET /products/{product_id}/mqtt-config/status`

**Response:**
```json
{
  "is_connected": true,
  "last_connected_at": "2026-01-23T14:15:32Z",
  "last_error": null,
  "connection_uptime_seconds": 3600,
  "messages_received": 1247,
  "last_message_at": "2026-01-23T14:45:10Z"
}
```

**UI Behavior:**
- Poll this endpoint every 10-15 seconds
- Update status indicator in header
- If status changes, update UI (connected/disconnected badge)
- Don't poll if page not visible (use Page Visibility API)

---

## Notes

1. **JSON Editing:** Use a proper JSON editor component with syntax highlighting and validation for `conditions` and `config` fields. Libraries: Monaco Editor, CodeMirror, react-json-editor.

2. **Password Handling:** When editing broker config, show password field empty with placeholder "Leave blank to keep existing password". Only include password in request if user enters new value.

3. **Execution Order:** When creating action, auto-suggest next order number (max + 1). Allow manual override. Consider drag-and-drop reordering.

4. **Optimistic Updates:** For toggle operations (enabled/disabled), update UI immediately and revert on error.

5. **Action Type Templates:** Consider providing config templates for each action type to help users fill in required fields correctly.

6. **Validation:** Validate JSON syntax client-side before submitting. Show helpful error messages.

7. **Empty States:** When no subscriptions exist, show empty state with "Add your first subscription" message and button.

8. **Confirmation Dialogs:** Always confirm destructive actions (delete subscription, delete action).

9. **Mobile Responsive:** Ensure forms work on mobile (stack fields vertically, use mobile-friendly modals).

10. **Accessibility:** Use proper labels, ARIA attributes, keyboard navigation support.
