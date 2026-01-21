# Required Environment Variables - Mandatory Configuration

## Overview

**All environment variables listed below are MANDATORY** for a product instance to start successfully. The backend will pass these to the Docker container, and the application will fail to start if any are missing.

---

## Mandatory Environment Variables

### 1. DATABASE_URL ⚠️ REQUIRED

**Purpose:** PostgreSQL database connection string for the product instance

**Format:**
```
postgresql://username:password@host:port/database_name
```

**Example:**
```
postgresql://allianz_user:secret_password@10.10.141.48:5432/allianz_insurance
```

**Validation Rules:**
- Must start with `postgresql://`
- Must include username and password
- Must include host and port
- Must include database name

**What happens if missing:**
- Application fails to start
- Error: `DATABASE_URL environment variable not set`

**Notes:**
- Each product instance should have its own dedicated database
- Database must be created before deploying the instance
- Use strong passwords in production

---

### 2. MUZZLEY_API_URL ⚠️ REQUIRED

**Purpose:** Habit Platform API base URL for IoT device integration

**Format:**
```
https://api.domain.com
```

**Common Values:**
```
https://api.habit.io
https://api.platform.integrations.habit.io
```

**Validation Rules:**
- Must start with `http://` or `https://`
- Must be a valid URL
- Should not end with a trailing slash

**What happens if missing:**
- Application fails to start
- IoT device communication will not work
- Error: `MUZZLEY_API_URL not configured`

**Notes:**
- Usually the same for all instances (production environment)
- May differ in staging/development environments

---

### 3. PLATFORM_API_KEY ⚠️ REQUIRED

**Purpose:** Authentication key for Habit Platform API

**Format:**
```
String (typically 32-64 characters)
```

**Example:**
```
prod-allianz-a3f8b9c2d4e5f6a7b8c9d0e1f2a3b4c5
```

**Validation Rules:**
- Minimum length: 10 characters
- Cannot be empty
- Should be unique per product instance

**What happens if missing:**
- Application fails to authenticate with platform
- API calls will be rejected (401 Unauthorized)
- Error: `PLATFORM_API_KEY not configured`

**Notes:**
- **HIGHLY SENSITIVE** - treat as a secret
- Different for each product instance
- Should be stored securely (never commit to git)
- Rotate regularly for security

---

### 4. MQTT_BROKER ⚠️ REQUIRED

**Purpose:** MQTT broker URL for IoT device communication

**Format:**
```
mqtt://host:port
```

**Example:**
```
mqtt://broker.habit.io:1883
mqtt://10.10.141.50:1883
```

**Validation Rules:**
- Must start with `mqtt://` or `mqtts://` (secure)
- Must include host
- Port is optional (defaults to 1883)

**What happens if missing:**
- Application cannot connect to IoT devices
- Real-time device events will not work
- Error: `MQTT_BROKER not configured`

**Notes:**
- Usually shared across all instances (same broker)
- Use `mqtts://` for production (TLS encryption)
- Default port: 1883 (non-TLS), 8883 (TLS)

---

### 5. REDIS_URL ⚠️ REQUIRED

**Purpose:** Redis connection string for caching and session storage

**Format:**
```
redis://host:port/database_number
```

**Example:**
```
redis://localhost:6379/0
redis://10.10.141.48:6379/1
```

**Validation Rules:**
- Must start with `redis://` or `rediss://` (secure)
- Must include host and port
- Database number is optional (defaults to 0)

**What happens if missing:**
- Application caching will not work
- Session management may fail
- Performance degradation
- Error: `REDIS_URL not configured`

**Notes:**
- Can be shared across instances (use different database numbers)
- Each instance should use a different database number (0-15)
- Example: Allianz uses `/0`, AXA uses `/1`, etc.

---

### 6. LOG_LEVEL ⚠️ REQUIRED

**Purpose:** Application logging verbosity level

**Format:**
```
DEBUG | INFO | WARNING | ERROR | CRITICAL
```

**Recommended:**
```
INFO (production)
DEBUG (development/troubleshooting)
```

**Validation Rules:**
- Must be one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- Case-insensitive

**What happens if missing:**
- Application may default to a suboptimal level
- Recommended to explicitly set

**Notes:**
- `INFO` is recommended for production
- `DEBUG` generates more logs (useful for troubleshooting)
- `ERROR` only logs errors (not recommended)

---

## Summary Table

| Variable | Type | Example | Unique Per Instance? |
|----------|------|---------|---------------------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` | ✅ Yes |
| `MUZZLEY_API_URL` | HTTP URL | `https://api.habit.io` | ❌ No (shared) |
| `PLATFORM_API_KEY` | Secret string | `prod-allianz-abc123...` | ✅ Yes |
| `MQTT_BROKER` | MQTT URL | `mqtt://broker.habit.io:1883` | ❌ No (shared) |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` | ⚠️ Shared host, unique DB number |
| `LOG_LEVEL` | Enum | `INFO` | ❌ No (can be same) |

---

## UI Validation Requirements

### Pre-Deployment Validation

The UI **must validate** all required variables before allowing product creation:

```typescript
interface ValidationError {
  field: string;
  message: string;
}

const validateRequiredEnvVars = (envVars: Record<string, string>): ValidationError[] => {
  const errors: ValidationError[] = [];

  // 1. DATABASE_URL
  if (!envVars.DATABASE_URL) {
    errors.push({
      field: 'DATABASE_URL',
      message: 'Database URL is required'
    });
  } else if (!envVars.DATABASE_URL.startsWith('postgresql://')) {
    errors.push({
      field: 'DATABASE_URL',
      message: 'Must be a PostgreSQL connection string (postgresql://...)'
    });
  }

  // 2. MUZZLEY_API_URL
  if (!envVars.MUZZLEY_API_URL) {
    errors.push({
      field: 'MUZZLEY_API_URL',
      message: 'Muzzley API URL is required'
    });
  } else if (!envVars.MUZZLEY_API_URL.startsWith('http')) {
    errors.push({
      field: 'MUZZLEY_API_URL',
      message: 'Must be a valid HTTP/HTTPS URL'
    });
  }

  // 3. PLATFORM_API_KEY
  if (!envVars.PLATFORM_API_KEY) {
    errors.push({
      field: 'PLATFORM_API_KEY',
      message: 'Platform API Key is required'
    });
  } else if (envVars.PLATFORM_API_KEY.length < 10) {
    errors.push({
      field: 'PLATFORM_API_KEY',
      message: 'API Key seems too short (minimum 10 characters)'
    });
  }

  // 4. MQTT_BROKER
  if (!envVars.MQTT_BROKER) {
    errors.push({
      field: 'MQTT_BROKER',
      message: 'MQTT Broker URL is required'
    });
  } else if (!envVars.MQTT_BROKER.startsWith('mqtt://') && 
             !envVars.MQTT_BROKER.startsWith('mqtts://')) {
    errors.push({
      field: 'MQTT_BROKER',
      message: 'Must start with mqtt:// or mqtts://'
    });
  }

  // 5. REDIS_URL
  if (!envVars.REDIS_URL) {
    errors.push({
      field: 'REDIS_URL',
      message: 'Redis URL is required'
    });
  } else if (!envVars.REDIS_URL.startsWith('redis://') && 
             !envVars.REDIS_URL.startsWith('rediss://')) {
    errors.push({
      field: 'REDIS_URL',
      message: 'Must start with redis:// or rediss://'
    });
  }

  // 6. LOG_LEVEL
  if (!envVars.LOG_LEVEL) {
    errors.push({
      field: 'LOG_LEVEL',
      message: 'Log Level is required'
    });
  } else {
    const validLevels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
    if (!validLevels.includes(envVars.LOG_LEVEL.toUpperCase())) {
      errors.push({
        field: 'LOG_LEVEL',
        message: `Must be one of: ${validLevels.join(', ')}`
      });
    }
  }

  return errors;
};

// Usage in form
const handleSubmit = () => {
  const errors = validateRequiredEnvVars(formData.env_vars);
  
  if (errors.length > 0) {
    // Show error messages in UI
    setValidationErrors(errors);
    return; // Don't submit
  }

  // All valid, proceed with API call
  createProduct(formData);
};
```

### UI Template

Pre-fill the "Load Template" with all required variables:

```typescript
const REQUIRED_TEMPLATE = {
  // Database
  DATABASE_URL: 'postgresql://username:password@10.10.141.48:5432/database_name',
  
  // Habit Platform
  MUZZLEY_API_URL: 'https://api.habit.io',
  PLATFORM_API_KEY: '', // Must be filled by user
  
  // Infrastructure
  MQTT_BROKER: 'mqtt://broker.habit.io:1883',
  REDIS_URL: 'redis://10.10.141.48:6379/0',
  
  // Configuration
  LOG_LEVEL: 'INFO'
};
```

---

## UI Error Messages

### Visual Indicators

**Before submission:**
- Show red border on fields with empty required variables
- Show warning icon next to missing fields
- Display inline error message below each field

**On submission attempt:**
- Show modal/alert with all validation errors
- Prevent API call until all required fields are filled
- Highlight problematic fields

### Example Error Display

```
❌ Cannot create product - Missing required configuration:

• DATABASE_URL is required
• PLATFORM_API_KEY is required

Please fill in all required environment variables.
```

---

## Default Values (For Template)

When user clicks "Load Template" or "Add New Product", pre-populate with:

```json
{
  "DATABASE_URL": "postgresql://",
  "MUZZLEY_API_URL": "https://api.habit.io",
  "PLATFORM_API_KEY": "",
  "MQTT_BROKER": "mqtt://broker.habit.io:1883",
  "REDIS_URL": "redis://localhost:6379/0",
  "LOG_LEVEL": "INFO"
}
```

**User must customize:**
- `DATABASE_URL` - username, password, database name
- `PLATFORM_API_KEY` - unique key for this instance
- `REDIS_URL` - database number (0-15)

---

## Backend Behavior

### What Backend Does

1. **On Product Create/Update:**
   - Accepts `env_vars` as JSON object
   - Stores in database as JSONB
   - Does NOT validate content (UI responsibility)

2. **On Product Deploy (Start):**
   - Reads `env_vars` from database
   - Passes to Docker container as environment variables
   - Docker container starts with these variables

3. **Application Startup:**
   - Application reads environment variables
   - **Fails immediately** if required variables are missing
   - Shows error in logs: `GET /products/{id}/logs`

### Current Backend Validation

⚠️ **Important:** Backend does NOT currently validate required variables. This is the **UI's responsibility**.

If you create a product without required variables:
- ✅ Backend accepts it
- ✅ Product is created in database
- ✅ You can click "Start"
- ❌ Docker container starts but application crashes
- ❌ Status becomes "failed"
- ❌ Logs show: "Missing required environment variable: DATABASE_URL"

**Therefore: UI MUST validate before submission!**

---

## Testing Checklist for UI

- [ ] Cannot submit form without `DATABASE_URL`
- [ ] Cannot submit form without `MUZZLEY_API_URL`
- [ ] Cannot submit form without `PLATFORM_API_KEY`
- [ ] Cannot submit form without `MQTT_BROKER`
- [ ] Cannot submit form without `REDIS_URL`
- [ ] Cannot submit form without `LOG_LEVEL`
- [ ] Shows clear error messages for each missing field
- [ ] Template button fills all 6 required variables
- [ ] Edit form shows validation errors if required vars are missing
- [ ] Can save product only when all required vars are valid

---

## Example: Complete Valid Configuration

```json
{
  "name": "Allianz Insurance",
  "slug": "allianz",
  "port": 8001,
  "replicas": 2,
  "env_vars": {
    "DATABASE_URL": "postgresql://allianz_user:secure_password@10.10.141.48:5432/allianz_db",
    "MUZZLEY_API_URL": "https://api.habit.io",
    "PLATFORM_API_KEY": "prod-allianz-d8f7e6c5b4a3",
    "MQTT_BROKER": "mqtt://broker.habit.io:1883",
    "REDIS_URL": "redis://10.10.141.48:6379/0",
    "LOG_LEVEL": "INFO"
  }
}
```

This configuration will:
- ✅ Pass UI validation
- ✅ Be accepted by backend
- ✅ Deploy successfully
- ✅ Application starts without errors

---

## Summary for UI Developer

**All 6 variables are MANDATORY:**

1. `DATABASE_URL` - PostgreSQL connection
2. `MUZZLEY_API_URL` - Habit API URL
3. `PLATFORM_API_KEY` - Authentication key
4. `MQTT_BROKER` - IoT broker URL
5. `REDIS_URL` - Redis connection
6. `LOG_LEVEL` - Logging level

**Your responsibilities:**

✅ Pre-fill template with all 6 variables
✅ Mark all as required in the form
✅ Validate before submission
✅ Show clear error messages
✅ Prevent API call if validation fails
✅ Guide user to fill in missing values

**Backend will NOT validate** - it's your job to ensure all required variables are present and valid before allowing product creation.
