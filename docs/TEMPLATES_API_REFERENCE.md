# Template API Quick Reference

## Base URL
```
http://localhost:8004/api/v1/products/{product_id}/templates
```

## Email Templates

### List All
```bash
GET /email
```

### Create
```bash
POST /email
{
  "name": "Payment Confirmation",
  "listmonk_template_id": 42,
  "description": "Sent when payment is paid",
  "template_type": "transactional",
  "available_variables": ["customer_name", "policy_number", "amount"]
}
```

### Get Single
```bash
GET /email/{template_id}
```

### Update
```bash
PUT /email/{template_id}
{
  "description": "Updated description",
  "available_variables": ["customer_name", "policy_number"]
}
```

### Delete
```bash
DELETE /email/{template_id}
# Returns: 204 No Content
```

---

## SMS Templates

### List All
```bash
GET /sms
```

### Create
```bash
POST /sms
{
  "name": "Policy Reminder",
  "message": "Your policy {{policy_number}} expires on {{expiry_date}}",
  "description": "7-day reminder",
  "template_type": "notification",
  "available_variables": ["policy_number", "expiry_date"]
}
```

### Get Single
```bash
GET /sms/{template_id}
```

### Update
```bash
PUT /sms/{template_id}
{
  "message": "UPDATED: Policy {{policy_number}} expires {{expiry_date}}"
}
```

### Delete
```bash
DELETE /sms/{template_id}
# Returns: 204 No Content
```

---

## Template Types
- `transactional` - Transaction confirmations, receipts
- `marketing` - Promotional content
- `notification` - Reminders, alerts
- `system` - System-generated messages

---

## SMS Character Limits
- 1-160 chars = 1 SMS
- 161-306 chars = 2 SMS  
- 307-459 chars = 3 SMS

---

## Error Codes
- `401` - Unauthorized (missing/invalid session)
- `404` - Template not found
- `409` - Duplicate template name for product

---

## Usage in Event Actions

```json
{
  "type": "conditional_email",
  "email": {
    "provider": "listmonk",
    "template_id": 1  // ← Email Template ID
  }
}
```

```json
{
  "type": "sms_notification",
  "sms": {
    "template_id": 1  // ← SMS Template ID
  }
}
```
