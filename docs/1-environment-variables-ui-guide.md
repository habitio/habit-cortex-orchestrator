# Environment Variables Configuration - UI Implementation Guide

## Overview

Each product instance needs custom environment variables (database URLs, API keys, etc.). The backend is **already implemented** and ready to use.

---

## Backend API - Already Working ✅

### Create Product with Environment Variables

```http
POST /api/v1/products
Content-Type: application/json

{
  "name": "Allianz Insurance",
  "slug": "allianz",
  "port": 8001,
  "replicas": 2,
  "env_vars": {
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/allianz_db",
    "MUZZLEY_API_URL": "https://api.habit.io",
    "PLATFORM_API_KEY": "allianz-secret-key-123",
    "MQTT_BROKER": "mqtt://broker.habit.io:1883",
    "REDIS_URL": "redis://localhost:6379/0",
    "LOG_LEVEL": "INFO"
  }
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Allianz Insurance",
  "slug": "allianz",
  "port": 8001,
  "replicas": 2,
  "status": "stopped",
  "env_vars": {
    "DATABASE_URL": "postgresql://user:pass@localhost:5432/allianz_db",
    "MUZZLEY_API_URL": "https://api.habit.io",
    "PLATFORM_API_KEY": "allianz-secret-key-123",
    "MQTT_BROKER": "mqtt://broker.habit.io:1883",
    "REDIS_URL": "redis://localhost:6379/0",
    "LOG_LEVEL": "INFO"
  },
  "image_id": null,
  "image_name": "bre-payments:latest",
  "created_at": "2026-01-21T16:00:00Z"
}
```

### Update Environment Variables

```http
PATCH /api/v1/products/{id}
Content-Type: application/json

{
  "env_vars": {
    "DATABASE_URL": "postgresql://updated-connection-string",
    "NEW_VARIABLE": "new_value"
  }
}
```

**Note:** This **replaces all** environment variables. If you want to update just one, you need to send all existing ones plus the changes.

### Get Product (includes env_vars)

```http
GET /api/v1/products/{id}

Response:
{
  "id": 1,
  "name": "Allianz Insurance",
  "env_vars": {
    "DATABASE_URL": "postgresql://...",
    ...
  }
}
```

---

## UI Components Needed

### 1. Environment Variables Editor Component

**Location:** Product Create/Edit Form (modal or page)

**Component Features:**

#### A. Key-Value Pairs Editor

Create a dynamic list where users can:
- Add new variable (button: "+ Add Variable")
- Remove variable (X button on each row)
- Edit key (uppercase input, underscores/numbers allowed)
- Edit value (text input with show/hide toggle for secrets)

#### B. Visual Design

```
┌─────────────────────────────────────────────────────────────┐
│ Environment Variables                                       │
│ Configure instance-specific settings                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Key                        Value                         🗑️│
│ ┌────────────────────┐    ┌────────────────────────────┐  │
│ │ DATABASE_URL       │    │ postgresql://user:pass@... │ ❌│
│ └────────────────────┘    └────────────────────────────┘  │
│                                                             │
│ ┌────────────────────┐    ┌────────────────────────────┐  │
│ │ PLATFORM_API_KEY   │ 🔒 │ ******************        │ ❌│
│ └────────────────────┘    └────────────────────────────┘  │
│                                                             │
│ ┌────────────────────┐    ┌────────────────────────────┐  │
│ │ MUZZLEY_API_URL    │    │ https://api.habit.io       │ ❌│
│ └────────────────────┘    └────────────────────────────┘  │
│                                                             │
│ [+ Add Variable]                    [📋 Load Template ▼] │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Code Examples

### React/TypeScript Component

```typescript
import React, { useState } from 'react';

interface EnvVar {
  key: string;
  value: string;
  isSecret: boolean;
}

interface EnvVarsEditorProps {
  initialVars?: Record<string, string>;
  onChange: (vars: Record<string, string>) => void;
}

const EnvVarsEditor: React.FC<EnvVarsEditorProps> = ({ 
  initialVars = {}, 
  onChange 
}) => {
  const [envVars, setEnvVars] = useState<EnvVar[]>(() => {
    // Convert initial vars to array format
    return Object.entries(initialVars).map(([key, value]) => ({
      key,
      value,
      isSecret: key.includes('KEY') || key.includes('SECRET') || key.includes('PASSWORD')
    }));
  });

  const [showSecrets, setShowSecrets] = useState<Record<number, boolean>>({});

  // Add new variable
  const handleAdd = () => {
    setEnvVars([...envVars, { key: '', value: '', isSecret: false }]);
  };

  // Remove variable
  const handleRemove = (index: number) => {
    const newVars = envVars.filter((_, i) => i !== index);
    setEnvVars(newVars);
    notifyChange(newVars);
  };

  // Update key
  const handleKeyChange = (index: number, key: string) => {
    // Auto-uppercase and allow only valid characters
    const sanitizedKey = key.toUpperCase().replace(/[^A-Z0-9_]/g, '');
    
    const newVars = [...envVars];
    newVars[index].key = sanitizedKey;
    
    // Auto-detect if it should be secret
    newVars[index].isSecret = 
      sanitizedKey.includes('KEY') || 
      sanitizedKey.includes('SECRET') || 
      sanitizedKey.includes('PASSWORD') ||
      sanitizedKey.includes('TOKEN');
    
    setEnvVars(newVars);
    notifyChange(newVars);
  };

  // Update value
  const handleValueChange = (index: number, value: string) => {
    const newVars = [...envVars];
    newVars[index].value = value;
    setEnvVars(newVars);
    notifyChange(newVars);
  };

  // Convert to API format and notify parent
  const notifyChange = (vars: EnvVar[]) => {
    const apiFormat = vars.reduce((acc, { key, value }) => {
      if (key.trim()) {
        acc[key] = value;
      }
      return acc;
    }, {} as Record<string, string>);
    
    onChange(apiFormat);
  };

  // Load template
  const loadTemplate = (template: 'full' | 'minimal') => {
    const templates = {
      full: {
        DATABASE_URL: 'postgresql://user:password@localhost:5432/db_name',
        MUZZLEY_API_URL: 'https://api.habit.io',
        PLATFORM_API_KEY: '',
        MQTT_BROKER: 'mqtt://broker.habit.io:1883',
        REDIS_URL: 'redis://localhost:6379/0',
        LOG_LEVEL: 'INFO'
      },
      minimal: {
        DATABASE_URL: '',
        PLATFORM_API_KEY: '',
        MUZZLEY_API_URL: 'https://api.habit.io'
      }
    };

    const templateVars = Object.entries(templates[template]).map(([key, value]) => ({
      key,
      value,
      isSecret: key.includes('KEY') || key.includes('SECRET')
    }));

    setEnvVars(templateVars);
    notifyChange(templateVars);
  };

  return (
    <div className="env-vars-editor">
      <div className="header">
        <h3>Environment Variables</h3>
        <p className="subtitle">Configure instance-specific settings</p>
      </div>

      <div className="vars-list">
        {envVars.map((envVar, index) => (
          <div key={index} className="var-row">
            <input
              type="text"
              placeholder="VARIABLE_NAME"
              value={envVar.key}
              onChange={(e) => handleKeyChange(index, e.target.value)}
              className="key-input"
            />
            
            <div className="value-input-wrapper">
              <input
                type={envVar.isSecret && !showSecrets[index] ? 'password' : 'text'}
                placeholder="value"
                value={envVar.value}
                onChange={(e) => handleValueChange(index, e.target.value)}
                className="value-input"
              />
              
              {envVar.isSecret && (
                <button
                  type="button"
                  onClick={() => setShowSecrets({ 
                    ...showSecrets, 
                    [index]: !showSecrets[index] 
                  })}
                  className="toggle-secret"
                >
                  {showSecrets[index] ? '🙈' : '👁️'}
                </button>
              )}
            </div>

            <button
              type="button"
              onClick={() => handleRemove(index)}
              className="remove-btn"
            >
              ❌
            </button>
          </div>
        ))}
      </div>

      <div className="actions">
        <button 
          type="button"
          onClick={handleAdd}
          className="add-btn"
        >
          + Add Variable
        </button>

        <div className="dropdown">
          <button type="button" className="template-btn">
            📋 Load Template ▼
          </button>
          <div className="dropdown-menu">
            <button onClick={() => loadTemplate('full')}>Full Template</button>
            <button onClick={() => loadTemplate('minimal')}>Minimal</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnvVarsEditor;
```

### Usage in Product Form

```typescript
const ProductForm: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    port: 8001,
    replicas: 1,
    env_vars: {} as Record<string, string>,
    image_id: null
  });

  const handleEnvVarsChange = (vars: Record<string, string>) => {
    setFormData({ ...formData, env_vars: vars });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const response = await fetch('/api/v1/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    if (response.ok) {
      const product = await response.json();
      console.log('Product created:', product);
      // Redirect or close modal
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Create Product Instance</h2>

      <label>
        Product Name
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
        />
      </label>

      <label>
        Slug (URL-friendly name)
        <input
          type="text"
          value={formData.slug}
          onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
          required
        />
      </label>

      <label>
        Port
        <input
          type="number"
          value={formData.port}
          onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
          required
        />
      </label>

      <label>
        Replicas
        <input
          type="number"
          value={formData.replicas}
          onChange={(e) => setFormData({ ...formData, replicas: parseInt(e.target.value) })}
          min={1}
          max={10}
          required
        />
      </label>

      {/* Environment Variables Editor */}
      <EnvVarsEditor
        initialVars={formData.env_vars}
        onChange={handleEnvVarsChange}
      />

      <button type="submit">Create Product</button>
    </form>
  );
};
```

---

## Required Environment Variables (Validation)

### Minimum Required Variables

All products **MUST** have these variables:

1. **`DATABASE_URL`** - PostgreSQL connection string
   - Format: `postgresql://user:password@host:port/database`
   - Example: `postgresql://allianz:secret@10.10.141.48:5432/allianz_insurance`

2. **`MUZZLEY_API_URL`** - Habit Platform API URL
   - Usually: `https://api.habit.io`
   - Or: `https://api.platform.integrations.habit.io`

3. **`PLATFORM_API_KEY`** - Authentication key for Habit Platform
   - Unique per product instance
   - Secret value

### Optional But Recommended

4. **`MQTT_BROKER`** - MQTT broker URL
   - Example: `mqtt://broker.habit.io:1883`

5. **`REDIS_URL`** - Redis connection string
   - Example: `redis://localhost:6379/0`

6. **`LOG_LEVEL`** - Logging level
   - Values: `DEBUG`, `INFO`, `WARNING`, `ERROR`
   - Default: `INFO`

### Validation in UI

```typescript
const validateEnvVars = (envVars: Record<string, string>) => {
  const errors: string[] = [];

  // Check required variables
  if (!envVars.DATABASE_URL) {
    errors.push('DATABASE_URL is required');
  } else if (!envVars.DATABASE_URL.startsWith('postgresql://')) {
    errors.push('DATABASE_URL must be a PostgreSQL connection string');
  }

  if (!envVars.MUZZLEY_API_URL) {
    errors.push('MUZZLEY_API_URL is required');
  } else if (!envVars.MUZZLEY_API_URL.startsWith('http')) {
    errors.push('MUZZLEY_API_URL must be a valid URL');
  }

  if (!envVars.PLATFORM_API_KEY) {
    errors.push('PLATFORM_API_KEY is required');
  } else if (envVars.PLATFORM_API_KEY.length < 10) {
    errors.push('PLATFORM_API_KEY seems too short');
  }

  // Check for duplicate keys (case-insensitive)
  const keys = Object.keys(envVars).map(k => k.toUpperCase());
  const duplicates = keys.filter((k, i) => keys.indexOf(k) !== i);
  if (duplicates.length > 0) {
    errors.push(`Duplicate keys: ${duplicates.join(', ')}`);
  }

  return errors;
};
```

---

## Display Environment Variables

### Product Detail View

Show environment variables in a **read-only** view with masked secrets:

```typescript
const ProductDetail: React.FC<{ productId: number }> = ({ productId }) => {
  const [product, setProduct] = useState(null);

  useEffect(() => {
    fetch(`/api/v1/products/${productId}`)
      .then(r => r.json())
      .then(setProduct);
  }, [productId]);

  if (!product) return <div>Loading...</div>;

  return (
    <div className="product-detail">
      <h2>{product.name}</h2>
      
      <section>
        <h3>Environment Variables</h3>
        <table className="env-vars-table">
          <thead>
            <tr>
              <th>Variable</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(product.env_vars || {}).map(([key, value]) => {
              const isSecret = key.includes('KEY') || 
                              key.includes('SECRET') || 
                              key.includes('PASSWORD');
              
              return (
                <tr key={key}>
                  <td><code>{key}</code></td>
                  <td>
                    {isSecret ? (
                      <span className="masked">••••••••••••••••</span>
                    ) : (
                      <code>{value}</code>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <button onClick={() => openEditModal(product)}>
        Edit Configuration
      </button>
    </div>
  );
};
```

---

## Edit Existing Product

### Pre-fill Form with Existing Values

```typescript
const EditProductModal: React.FC<{ product: Product }> = ({ product }) => {
  const [formData, setFormData] = useState({
    name: product.name,
    port: product.port,
    replicas: product.replicas,
    env_vars: product.env_vars || {}
  });

  const handleSubmit = async () => {
    const response = await fetch(`/api/v1/products/${product.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    if (response.ok) {
      const updated = await response.json();
      console.log('Updated:', updated);
      // Close modal and refresh
    }
  };

  return (
    <Modal>
      <h2>Edit {product.name}</h2>
      
      <EnvVarsEditor
        initialVars={formData.env_vars}
        onChange={(vars) => setFormData({ ...formData, env_vars: vars })}
      />

      <button onClick={handleSubmit}>Save Changes</button>
    </Modal>
  );
};
```

---

## CSS Styling Example

```css
.env-vars-editor {
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.env-vars-editor .header {
  margin-bottom: 1rem;
}

.env-vars-editor .subtitle {
  color: #6b7280;
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.var-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 0.75rem;
}

.key-input {
  flex: 0 0 200px;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-family: monospace;
  text-transform: uppercase;
}

.value-input-wrapper {
  flex: 1;
  position: relative;
}

.value-input {
  width: 100%;
  padding: 0.5rem;
  padding-right: 2.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-family: monospace;
}

.toggle-secret {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.remove-btn:hover {
  opacity: 1;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.add-btn {
  padding: 0.5rem 1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.add-btn:hover {
  background: #2563eb;
}

.template-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
}
```

---

## Testing Checklist

- [ ] Can add new environment variable
- [ ] Can remove environment variable
- [ ] Key is auto-uppercased
- [ ] Secret fields are detected automatically (KEY, SECRET, PASSWORD, TOKEN)
- [ ] Can toggle show/hide for secret fields
- [ ] Template buttons work
- [ ] Validation shows errors for missing required variables
- [ ] Validation prevents duplicate keys
- [ ] Can create product with env vars
- [ ] Can edit existing product's env vars
- [ ] Product detail shows env vars (secrets masked)
- [ ] Empty key-value pairs are ignored (not sent to API)

---

## Summary for UI Developer

**What you need to implement:**

1. **EnvVarsEditor component** - Dynamic key-value editor
2. **Add it to Product Create form**
3. **Add it to Product Edit form**
4. **Validation** - Check required variables
5. **Display** - Show env vars in product detail (mask secrets)

**Backend is ready:**
- ✅ `POST /api/v1/products` accepts `env_vars`
- ✅ `PATCH /api/v1/products/{id}` updates `env_vars`
- ✅ `GET /api/v1/products/{id}` returns `env_vars`
- ✅ Stored in database as JSONB
- ✅ Passed to Docker containers when deploying

**Just implement the UI components and wire them to the API!**
