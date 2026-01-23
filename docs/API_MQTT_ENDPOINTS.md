# MQTT Configuration API Reference

This document provides the complete API specifications for MQTT configuration management in the Cortex Orchestrator.

---

## Base URL

```
http://localhost:8004/api/v1
```

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products/{id}/mqtt-config` | Get full MQTT configuration |
| PUT | `/products/{id}/mqtt-config` | Create/update MQTT configuration |
| POST | `/products/{id}/mqtt-config/test` | Test MQTT connection |
| GET | `/products/{id}/mqtt-config/subscriptions` | List event subscriptions |
| PUT | `/products/{id}/mqtt-config/subscriptions/{sub_id}` | Update subscription |
| POST | `/products/{id}/mqtt-config/reconnect` | Force reconnect |
| GET | `/products/{id}/mqtt-config/status` | Get connection status |

---

## 1. Get MQTT Configuration

### Request

```http
GET /api/v1/products/{product_id}/mqtt-config
```

### Response (200 OK)

```json
{
  "product_id": 2,
  "mqtt_config": {
    "id": 1,
    "product_id": 2,
    "broker": {
      "host": "api.platform.integrations.habit.io",
      "port": 8889,
      "use_tls": true,
      "verify_cert": false,
      "username": "habit-bre-tyres",
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
    },
    "created_at": "2026-01-23T14:03:25.590525",
    "updated_at": "2026-01-23T14:03:25.590525"
  },
  "subscriptions": [
    {
      "id": 1,
      "name": "payment_marked_as_pending",
      "topic": "/v3/applications/ABC123/business-events",
      "enabled": true,
      "description": "Handles pending payment events",
      "actions": [
        {
          "type": "conditional_email",
          "condition": "payment.status == 'pending'",
          "template": "payment_pending"
        }
      ],
      "stats": {
        "messages_received": 145,
        "last_message_at": "2026-01-23T13:45:22.123456",
        "actions_executed": 145,
        "actions_failed": 0
      },
      "created_at": "2026-01-22T10:00:00.000000",
      "updated_at": "2026-01-23T14:03:25.590525"
    }
  ],
  "status": {
    "product_id": 2,
    "connected": true,
    "last_connected_at": "2026-01-23T14:00:00.000000",
    "last_disconnected_at": null,
    "connection_error": null,
    "messages_received": 1247,
    "last_message_at": "2026-01-23T14:05:30.123456",
    "subscribed_topics_count": 12,
    "client_id": "bre-tyres-instance-2-abc123",
    "broker_info": {
      "version": "5.0",
      "max_qos": 2
    },
    "updated_at": "2026-01-23T14:05:35.000000"
  }
}
```

### Response (when not configured)

```json
{
  "product_id": 2,
  "mqtt_config": null,
  "subscriptions": null,
  "status": null,
  "message": "MQTT not configured for this product"
}
```

---

## 2. Create/Update MQTT Configuration

### Request

```http
PUT /api/v1/products/{product_id}/mqtt-config
Content-Type: application/json
```

### Request Body

```json
{
  "broker": {
    "host": "api.platform.integrations.habit.io",
    "port": 8889,
    "use_tls": true,
    "verify_cert": false,
    "username": "habit-bre-tyres",
    "password": "secure-password-123",
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
}
```

### Field Descriptions

**Broker Configuration:**
- `host` (string, required): MQTT broker hostname or IP
- `port` (integer, required): MQTT broker port (1-65535), default 1883
- `use_tls` (boolean): Enable TLS/SSL encryption, default false
- `verify_cert` (boolean): Verify SSL certificate, default true
- `username` (string, optional): Authentication username
- `password` (string, optional): Authentication password (leave blank to keep existing)
- `client_id` (string, optional): MQTT client ID (null = auto-generate)
- `keep_alive` (integer): Keep-alive interval in seconds, default 60
- `clean_session` (boolean): Start fresh session on connect, default true

**Topics Configuration:**
- `prefix` (string, required): Base topic prefix, default "/v3/applications"
- `pattern` (string, required): Topic pattern with variables, default "{application_id}/business-events"
- `use_shared` (boolean): Enable shared subscriptions (load balancing), default true
- `shared_group` (string): Shared subscription group name, default "bre"
- `qos` (integer): Quality of Service level (0, 1, or 2), default 1

### Response (200 OK)

```json
{
  "status": "success",
  "message": "MQTT configuration updated successfully",
  "requires_restart": true,
  "mqtt_config": {
    "id": 1,
    "product_id": 2,
    "broker": {
      "host": "api.platform.integrations.habit.io",
      "port": 8889,
      "use_tls": true,
      "verify_cert": false,
      "username": "habit-bre-tyres",
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
    },
    "created_at": "2026-01-23T14:03:25.590525",
    "updated_at": "2026-01-23T14:03:25.590525"
  }
}
```

### Response (404 Not Found)

```json
{
  "detail": "Product not found"
}
```

### Response (422 Validation Error)

```json
{
  "detail": [
    {
      "loc": ["body", "broker", "port"],
      "msg": "ensure this value is less than or equal to 65535",
      "type": "value_error.number.not_le"
    }
  ]
}
```

---

## 3. Test MQTT Connection

### Request

```http
POST /api/v1/products/{product_id}/mqtt-config/test
Content-Type: application/json
```

### Request Body

```json
{
  "host": "api.platform.integrations.habit.io",
  "port": 8889,
  "use_tls": true,
  "verify_cert": false,
  "username": "habit-bre-tyres",
  "password": "test-password"
}
```

### Response (Success)

```json
{
  "status": "success",
  "connected": true,
  "latency_ms": 45,
  "error": null,
  "details": "Connected successfully"
}
```

### Response (Failure - Bad Credentials)

```json
{
  "status": "error",
  "connected": false,
  "latency_ms": null,
  "error": "Connection failed with code 4",
  "details": "Bad username or password"
}
```

### Response (Failure - Connection Refused)

```json
{
  "status": "error",
  "connected": false,
  "latency_ms": null,
  "error": "Connection failed with code 5",
  "details": "Not authorized"
}
```

### MQTT Connection Return Codes

| Code | Meaning |
|------|---------|
| 0 | Connection successful |
| 1 | Connection refused - incorrect protocol version |
| 2 | Connection refused - invalid client identifier |
| 3 | Connection refused - server unavailable |
| 4 | Connection refused - bad username or password |
| 5 | Connection refused - not authorized |

---

## 4. Get Event Subscriptions

### Request

```http
GET /api/v1/products/{product_id}/mqtt-config/subscriptions
```

### Response (200 OK)

```json
{
  "subscriptions": [
    {
      "id": 1,
      "name": "distributor_successful_created_policy",
      "topic": "/v3/applications/ABC123/business-events",
      "enabled": true,
      "description": "Triggers when distributor successfully creates a policy",
      "actions": [
        {
          "type": "activate_policy",
          "params": {
            "policy_id": "{{event.policy_id}}"
          }
        },
        {
          "type": "conditional_email",
          "condition": "event.sendEmail == true",
          "template": "policy_activated"
        }
      ],
      "stats": {
        "messages_received": 234,
        "last_message_at": "2026-01-23T14:05:22.123456",
        "actions_executed": 468,
        "actions_failed": 0
      },
      "created_at": "2026-01-22T10:00:00.000000",
      "updated_at": "2026-01-23T14:03:25.590525"
    },
    {
      "id": 2,
      "name": "payment_marked_as_pending",
      "topic": "/v3/applications/ABC123/business-events",
      "enabled": true,
      "description": "Handles pending payment notifications",
      "actions": [
        {
          "type": "conditional_email",
          "condition": "payment.status == 'pending'",
          "template": "payment_pending"
        }
      ],
      "stats": {
        "messages_received": 145,
        "last_message_at": "2026-01-23T13:45:22.123456",
        "actions_executed": 145,
        "actions_failed": 0
      },
      "created_at": "2026-01-22T10:00:00.000000",
      "updated_at": "2026-01-23T14:03:25.590525"
    }
  ]
}
```

---

## 5. Update Subscription

### Request

```http
PUT /api/v1/products/{product_id}/mqtt-config/subscriptions/{subscription_id}
Content-Type: application/json
```

### Request Body (Toggle Enable/Disable)

```json
{
  "enabled": false
}
```

### Request Body (Full Update)

```json
{
  "enabled": true,
  "description": "Updated description for the subscription",
  "actions": [
    {
      "type": "activate_policy",
      "params": {
        "policy_id": "{{event.policy_id}}"
      }
    }
  ]
}
```

### Response (200 OK)

```json
{
  "status": "success",
  "message": "Subscription updated successfully",
  "subscription": {
    "id": 1,
    "name": "distributor_successful_created_policy",
    "topic": "/v3/applications/ABC123/business-events",
    "enabled": false,
    "description": "Triggers when distributor successfully creates a policy",
    "actions": [...],
    "stats": {...},
    "created_at": "2026-01-22T10:00:00.000000",
    "updated_at": "2026-01-23T14:10:25.590525"
  }
}
```

---

## 6. Force Reconnect

Triggers a manual reconnection to the MQTT broker. Useful when configuration has changed or connection is stuck.

### Request

```http
POST /api/v1/products/{product_id}/mqtt-config/reconnect
```

### Response (200 OK)

```json
{
  "status": "success",
  "message": "Reconnection triggered. Check status in a few seconds."
}
```

---

## 7. Get Connection Status

### Request

```http
GET /api/v1/products/{product_id}/mqtt-config/status
```

### Response (200 OK - Connected)

```json
{
  "product_id": 2,
  "connected": true,
  "last_connected_at": "2026-01-23T14:00:00.000000",
  "last_disconnected_at": "2026-01-23T13:59:55.000000",
  "connection_error": null,
  "messages_received": 1247,
  "last_message_at": "2026-01-23T14:05:30.123456",
  "subscribed_topics_count": 12,
  "client_id": "bre-tyres-instance-2-abc123",
  "broker_info": {
    "version": "5.0",
    "max_qos": 2
  },
  "updated_at": "2026-01-23T14:05:35.000000"
}
```

### Response (200 OK - Disconnected)

```json
{
  "product_id": 2,
  "connected": false,
  "last_connected_at": "2026-01-23T14:00:00.000000",
  "last_disconnected_at": "2026-01-23T14:10:00.000000",
  "connection_error": "Connection lost: Broker unreachable",
  "messages_received": 1247,
  "last_message_at": "2026-01-23T14:05:30.123456",
  "subscribed_topics_count": 0,
  "client_id": "bre-tyres-instance-2-abc123",
  "broker_info": null,
  "updated_at": "2026-01-23T14:10:05.000000"
}
```

---

## Error Responses

### 404 Not Found

```json
{
  "detail": "Product not found"
}
```

```json
{
  "detail": "Subscription not found"
}
```

### 422 Unprocessable Entity (Validation Error)

```json
{
  "detail": [
    {
      "loc": ["body", "broker", "host"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## Integration Examples

### JavaScript/TypeScript (Fetch)

```javascript
// Get MQTT configuration
async function getMQTTConfig(productId) {
  const response = await fetch(`/api/v1/products/${productId}/mqtt-config`);
  const data = await response.json();
  return data;
}

// Update MQTT configuration
async function updateMQTTConfig(productId, config) {
  const response = await fetch(`/api/v1/products/${productId}/mqtt-config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  
  if (!response.ok) {
    throw new Error('Failed to update configuration');
  }
  
  return response.json();
}

// Test connection
async function testConnection(productId, credentials) {
  const response = await fetch(
    `/api/v1/products/${productId}/mqtt-config/test`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    }
  );
  
  return response.json();
}

// Toggle subscription
async function toggleSubscription(productId, subId, enabled) {
  const response = await fetch(
    `/api/v1/products/${productId}/mqtt-config/subscriptions/${subId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled })
    }
  );
  
  return response.json();
}
```

### Python (requests)

```python
import requests

BASE_URL = "http://localhost:8004/api/v1"

# Get MQTT configuration
def get_mqtt_config(product_id):
    response = requests.get(f"{BASE_URL}/products/{product_id}/mqtt-config")
    response.raise_for_status()
    return response.json()

# Update MQTT configuration
def update_mqtt_config(product_id, config):
    response = requests.put(
        f"{BASE_URL}/products/{product_id}/mqtt-config",
        json=config
    )
    response.raise_for_status()
    return response.json()

# Test connection
def test_connection(product_id, credentials):
    response = requests.post(
        f"{BASE_URL}/products/{product_id}/mqtt-config/test",
        json=credentials
    )
    return response.json()

# Example usage
config = {
    "broker": {
        "host": "api.platform.integrations.habit.io",
        "port": 8889,
        "use_tls": True,
        "verify_cert": False,
        "username": "habit-bre-tyres",
        "password": "password123",
        "keep_alive": 60,
        "clean_session": True
    },
    "topics": {
        "prefix": "/v3/applications",
        "pattern": "{application_id}/business-events",
        "use_shared": True,
        "shared_group": "bre",
        "qos": 1
    }
}

result = update_mqtt_config(2, config)
print(result)
```

### cURL

```bash
# Get configuration
curl http://localhost:8004/api/v1/products/2/mqtt-config | jq .

# Update configuration
curl -X PUT http://localhost:8004/api/v1/products/2/mqtt-config \
  -H "Content-Type: application/json" \
  -d '{
    "broker": {
      "host": "api.platform.integrations.habit.io",
      "port": 8889,
      "use_tls": true,
      "verify_cert": false,
      "username": "habit-bre-tyres",
      "password": "password123",
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
  }' | jq .

# Test connection
curl -X POST http://localhost:8004/api/v1/products/2/mqtt-config/test \
  -H "Content-Type: application/json" \
  -d '{
    "host": "api.platform.integrations.habit.io",
    "port": 8889,
    "use_tls": true,
    "username": "habit-bre-tyres",
    "password": "password123"
  }' | jq .

# Toggle subscription
curl -X PUT http://localhost:8004/api/v1/products/2/mqtt-config/subscriptions/1 \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}' | jq .

# Force reconnect
curl -X POST http://localhost:8004/api/v1/products/2/mqtt-config/reconnect | jq .

# Get status
curl http://localhost:8004/api/v1/products/2/mqtt-config/status | jq .
```

---

## Notes

1. **Password Security**: Passwords are never returned in plain text. When retrieving configuration, password field shows "***" if set, or null if not set.

2. **Container Restart**: After updating MQTT configuration, the product instance container must be restarted to apply changes. The API response includes `requires_restart: true` flag.

3. **Connection Testing**: The `/test` endpoint performs a real connection attempt to the broker with provided credentials. It does not affect the running instance's connection.

4. **QoS Levels**:
   - 0: At most once (fire and forget)
   - 1: At least once (acknowledged delivery)
   - 2: Exactly once (assured delivery)

5. **Shared Subscriptions**: When enabled, multiple instances can share the same subscription for load balancing. Format: `$share/{group}/{topic}`

6. **Topic Variables**: The `{application_id}` variable in topic patterns is replaced with actual application ID at runtime.
