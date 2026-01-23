# MQTT Configuration Management - Complete Implementation

## Overview
This implementation allows MQTT broker configuration, event subscriptions, and connection monitoring to be managed via UI instead of hardcoded config files.

---

## Database Schema

### Tables Created

#### 1. `mqtt_configs`
Stores MQTT broker connection configuration for each product.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| product_id | Integer | FK to products (unique) |
| broker_host | String(255) | MQTT broker hostname |
| broker_port | Integer | Broker port (default: 1883) |
| use_tls | Boolean | Enable TLS/SSL |
| verify_cert | Boolean | Verify SSL certificate |
| username | String(255) | MQTT username |
| password | String(512) | MQTT password (encrypted) |
| client_id | String(255) | MQTT client ID (null = auto) |
| keep_alive | Integer | Keep-alive interval (seconds) |
| clean_session | Boolean | Clean session flag |
| topic_prefix | String(255) | Topic prefix pattern |
| topic_pattern | String(255) | Topic pattern with placeholders |
| use_shared_subscriptions | Boolean | Enable shared subscriptions |
| shared_group | String(100) | Shared group name |
| qos | Integer | Quality of Service (0-2) |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

#### 2. `mqtt_subscriptions`
Event subscriptions and actions configuration.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| mqtt_config_id | Integer | FK to mqtt_configs |
| name | String(255) | Subscription name |
| topic | String(512) | Full topic path |
| enabled | Boolean | Enable/disable subscription |
| description | Text | Human-readable description |
| actions | JSON | Array of action configurations |
| messages_received | Integer | Message counter |
| last_message_at | DateTime | Last message timestamp |
| actions_executed | Integer | Successful actions counter |
| actions_failed | Integer | Failed actions counter |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

#### 3. `mqtt_connection_status`
Real-time connection status tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| product_id | Integer | FK to products (unique) |
| connected | Boolean | Current connection state |
| last_connected_at | DateTime | Last successful connection |
| last_disconnected_at | DateTime | Last disconnection |
| connection_error | Text | Last error message |
| messages_received | Integer | Total messages received |
| last_message_at | DateTime | Last message timestamp |
| subscribed_topics_count | Integer | Active subscriptions |
| client_id | String(255) | Active client ID |
| broker_info | JSON | Broker metadata |
| updated_at | DateTime | Last status update |

---

## API Endpoints

### Base Path: `/api/v1/products/{product_id}/mqtt-config`

#### GET `/api/v1/products/{product_id}/mqtt-config`
Get complete MQTT configuration including subscriptions and status.

**Response:**
```json
{
  "product_id": 2,
  "mqtt_config": {
    "broker": {...},
    "topics": {...}
  },
  "subscriptions": [...],
  "status": {...}
}
```

#### PUT `/api/v1/products/{product_id}/mqtt-config`
Update MQTT configuration (requires container restart).

**Request:**
```json
{
  "broker": {
    "host": "api.platform.integrations.habit.io",
    "port": 8889,
    "use_tls": true,
    "verify_cert": false,
    "username": "app-id",
    "password": "secret",
    "keep_alive": 60
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

#### POST `/api/v1/products/{product_id}/mqtt-config/test`
Test connection with provided credentials.

**Request:**
```json
{
  "host": "broker.example.com",
  "port": 8889,
  "use_tls": true,
  "username": "test",
  "password": "test123"
}
```

**Response:**
```json
{
  "status": "success",
  "connected": true,
  "latency_ms": 45,
  "broker_info": {...}
}
```

#### GET `/api/v1/products/{product_id}/mqtt-config/subscriptions`
List all event subscriptions.

#### PUT `/api/v1/products/{product_id}/mqtt-config/subscriptions/{sub_id}`
Update a specific subscription (enable/disable, description).

#### POST `/api/v1/products/{product_id}/mqtt-config/reconnect`
Force MQTT client reconnection.

#### GET `/api/v1/products/{product_id}/mqtt-config/status`
Get real-time connection status only.

---

## Migration Steps

### 1. Create Database Tables
```bash
cd /home/djsb/development/bre-tyres-01/cortex-orchestrator
source venv/bin/activate
python -m orchestrator.database.migrations.add_mqtt_config
```

### 2. Restart Orchestrator
```bash
pkill -f "uvicorn orchestrator"
cd src
uvicorn orchestrator.main:app --host 0.0.0.0 --port 8004 --reload
```

### 3. Initialize MQTT Config for Existing Products
Use API or create initialization script to populate mqtt_configs table with current .env values.

---

## Instance Integration

### Modified Files in cortex-instance:

#### 1. Update `config.py` to read from environment OR database
Add fallback logic to check database first, then fall back to env vars:

```python
def get_mqtt_config():
    """Get MQTT config from database or environment variables."""
    # Try database first (orchestrator-managed)
    db_config = fetch_mqtt_config_from_orchestrator_api()
    if db_config:
        return db_config
    
    # Fallback to environment variables
    settings = get_settings()
    return {
        "host": settings.mqtt_host,
        "port": settings.mqtt_port,
        ...
    }
```

#### 2. Update `mqtt_listener.py`
Replace hardcoded config file reads with API calls:

```python
class MQTTListener:
    def __init__(self):
        self.mqtt_config = get_mqtt_config()  # From DB via API
        self.subscriptions = get_mqtt_subscriptions()  # From DB
```

#### 3. Add Health Check Endpoint
Create endpoint in instance to report MQTT status back to orchestrator:

```python
@router.post("/internal/mqtt-status")
async def update_mqtt_status(status: MQTTStatus):
    """Receive status updates from MQTT listener."""
    # Forward to orchestrator API
    await update_orchestrator_mqtt_status(status)
```

---

## UI Integration Guide

### For UI Team:

#### 1. MQTT Configuration Page
Create route: `/products/{id}/mqtt-config`

Components needed:
- BrokerConnectionForm (host, port, auth, TLS settings)
- TopicConfigForm (prefix, pattern, shared subscriptions)
- SubscriptionsList (enable/disable, view actions)
- ConnectionStatus (live status indicator)
- TestConnectionButton

#### 2. API Calls
```javascript
// Fetch config
const config = await fetch(`/api/v1/products/${productId}/mqtt-config`);

// Update config
await fetch(`/api/v1/products/${productId}/mqtt-config`, {
  method: 'PUT',
  body: JSON.stringify(mqttConfig)
});

// Test connection
const testResult = await fetch(
  `/api/v1/products/${productId}/mqtt-config/test`,
  { method: 'POST', body: JSON.stringify(testCredentials) }
);
```

#### 3. Real-time Status
Poll `/api/v1/products/{id}/mqtt-config/status` every 5-10 seconds for live connection status.

---

## Security Considerations

### 1. Password Encryption
**TODO**: Implement encryption for `mqtt_configs.password` field.

Recommended approach:
```python
from cryptography.fernet import Fernet

# Store key in environment variable
ENCRYPTION_KEY = os.getenv("MQTT_PASSWORD_ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY)

# Encrypt before storing
encrypted = cipher.encrypt(password.encode())

# Decrypt when using
decrypted = cipher.decrypt(encrypted).decode()
```

### 2. API Authentication
All MQTT config endpoints should require admin/orchestrator authentication.

### 3. Audit Logging
All config changes should be logged to `audit_logs` table.

---

## Testing

### 1. Test MQTT Connection
```bash
curl -X POST http://localhost:8004/api/v1/products/2/mqtt-config/test \
  -H "Content-Type: application/json" \
  -d '{
    "host": "api.platform.integrations.habit.io",
    "port": 8889,
    "use_tls": true,
    "username": "app-id",
    "password": "secret"
  }'
```

### 2. Update Configuration
```bash
curl -X PUT http://localhost:8004/api/v1/products/2/mqtt-config \
  -H "Content-Type: application/json" \
  -d @mqtt_config.json
```

### 3. Get Current Config
```bash
curl http://localhost:8004/api/v1/products/2/mqtt-config | jq .
```

---

## Rollback Plan

If issues occur:

1. Revert database changes:
```sql
DROP TABLE mqtt_connection_status;
DROP TABLE mqtt_subscriptions;
DROP TABLE mqtt_configs;
```

2. Revert code changes:
```bash
git checkout main -- \
  src/orchestrator/models/mqtt_config.py \
  src/orchestrator/routers/mqtt_config.py \
  src/orchestrator/database/models.py \
  src/orchestrator/main.py
```

3. Instances will continue using `.env` files as before.

---

## Future Enhancements

1. **Event Action Editor**: Visual editor for configuring subscription actions
2. **MQTT Message Browser**: View recent messages in UI
3. **Performance Metrics**: Track message processing latency, throughput
4. **Alert Rules**: Notify on connection failures or high error rates
5. **Multi-Broker Support**: Configure multiple brokers with failover
6. **Message Replay**: Replay missed messages after reconnection

---

## Files Created/Modified

### New Files:
- `/cortex-orchestrator/src/orchestrator/models/mqtt_config.py`
- `/cortex-orchestrator/src/orchestrator/routers/mqtt_config.py`
- `/cortex-orchestrator/src/orchestrator/database/migrations/add_mqtt_config.py`

### Modified Files:
- `/cortex-orchestrator/src/orchestrator/database/models.py` (added relationships)
- `/cortex-orchestrator/src/orchestrator/main.py` (registered router)

### Instance Files to Modify (TODO):
- `/cortex-instance/src/bre_payments/config.py` (add DB fallback)
- `/cortex-instance/src/bre_payments/mqtt_listener.py` (use DB config)
- `/cortex-instance/src/bre_payments/routers/` (add status reporting endpoint)

---

## Support

For issues or questions:
1. Check orchestrator logs: `/tmp/orchestrator.log`
2. Check instance MQTT logs: `/app/logs/mqtt-events.log`
3. Verify database connectivity: `SELECT * FROM mqtt_configs;`
4. Test broker connectivity: Use `/mqtt-config/test` endpoint
