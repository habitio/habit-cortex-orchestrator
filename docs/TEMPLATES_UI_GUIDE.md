# Templates UI Implementation Guide

## Overview

This guide provides complete specifications for implementing Email and SMS template management in the product configuration UI.

**Key Concepts:**
- **Email Templates**: References to ListMonk templates (store ListMonk template ID only)
- **SMS Templates**: Direct message storage with variable placeholders
- **NO Trigger Events**: Templates are pure content, triggers are defined in Event Subscriptions
- **Product-Specific**: Each product has its own templates

---

## Architecture

### Template → Action Flow

```
1. Create Template (content library)
   └─> Email: "Payment Confirmation" → ListMonk Template #42
   └─> SMS: "Policy Reminder" → Message: "Your policy {{policy_number}} expires {{expiry_date}}"

2. Create Event Subscription (trigger logic)
   └─> Event: "payment_change_state"
       └─> Action: IF payment_new_state='paid' THEN
           └─> Send Email Template #1 (Payment Confirmation)
           └─> Send SMS Template #3 (Policy Reminder)
```

### Why This Design?

✅ **Separation of Concerns**: Content vs. Logic  
✅ **Reusability**: Same template for multiple events  
✅ **Flexibility**: Change trigger without editing template  
✅ **Centralized Content**: ListMonk manages email design

---

## UI Structure

### Page Location

**Route**: `/products/:productId/templates`

**Navigation**: 
- Product Edit Screen → Sidebar → "Templates"
- Same level as "Events & Actions"

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Edit Product: BRE Tyres                                      │
├──────────────────────────────────────────────────────────────┤
│ Sidebar              │ Templates                             │
│                      │                                        │
│ ☑ Instance Config    │ ┌──────────────┬──────────────┐      │
│ ☑ Environment Vars   │ │ 📧 Email     │ 📱 SMS       │      │
│ ☐ Templates  ◀─────  │ └──────────────┴──────────────┘      │
│ ☐ Events & Actions   │                                        │
│ ☐ Validation Rules   │ Configure email and SMS templates.    │
│                      │ Reference templates from actions.      │
│                      │                                        │
│                      │ [+ Add Email Template]                 │
│                      │                                        │
│                      │ ┌────────────────────────────────┐    │
│                      │ │ ✅ Payment Confirmation        │    │
│                      │ │ ListMonk ID: 42                │    │
│                      │ │ Type: Transactional            │    │
│                      │ │ Used: 156 times                │    │
│                      │ │                    [Edit] [🗑] │    │
│                      │ └────────────────────────────────┘    │
│                      │                                        │
│                      │ ┌────────────────────────────────┐    │
│                      │ │ ✅ MB Reference Email          │    │
│                      │ │ ListMonk ID: 38                │    │
│                      │ │ Type: Transactional            │    │
│                      │ │ Used: 89 times                 │    │
│                      │ │                    [Edit] [🗑] │    │
│                      │ └────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## Email Templates Tab

### List View

**API Endpoint**: `GET /api/v1/products/{product_id}/templates/email`

**Response**:
```json
[
  {
    "id": 1,
    "product_id": 2,
    "name": "Payment Confirmation",
    "listmonk_template_id": 42,
    "description": "Sent when payment is marked as paid",
    "template_type": "transactional",
    "available_variables": [
      "customer_name",
      "policy_number",
      "premium_amount",
      "effective_date"
    ],
    "stats": {
      "times_used": 156,
      "last_used_at": "2026-01-23T14:30:00Z"
    },
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-01-20T16:45:00Z"
  },
  {
    "id": 2,
    "product_id": 2,
    "name": "MB Reference Email",
    "listmonk_template_id": 38,
    "description": "MB payment reference for pending payments",
    "template_type": "transactional",
    "available_variables": [
      "customer_name",
      "mb_entity",
      "mb_reference",
      "amount"
    ],
    "stats": {
      "times_used": 89,
      "last_used_at": "2026-01-22T11:20:00Z"
    },
    "created_at": "2026-01-15T10:05:00Z",
    "updated_at": "2026-01-15T10:05:00Z"
  }
]
```

**UI Components**:
- **Card per template** with:
  - ✅ Enabled indicator (always enabled, no toggle)
  - Template name (h3, bold)
  - ListMonk Template ID (small, gray text)
  - Template type badge (pill/badge)
  - Description (2 lines max, truncated)
  - Usage stats ("Used 156 times")
  - Actions: Edit button, Delete button

### Create/Edit Modal

**Trigger**: Click "+ Add Email Template" or "Edit" button

**API Endpoints**:
- **Create**: `POST /api/v1/products/{product_id}/templates/email`
- **Update**: `PUT /api/v1/products/{product_id}/templates/email/{template_id}`
- **Get Single**: `GET /api/v1/products/{product_id}/templates/email/{template_id}`

**Form Fields**:

```
┌─────────────────────────────────────────────────┐
│ Add Email Template                              │
├─────────────────────────────────────────────────┤
│                                                 │
│ Template Name *                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ e.g., Payment Confirmation              │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ ListMonk Template ID *                          │
│ ┌─────────────────────────────────────────┐   │
│ │ 42                                      │   │
│ └─────────────────────────────────────────┘   │
│ ℹ️ Get this ID from ListMonk dashboard        │
│                                                 │
│ Description                                     │
│ ┌─────────────────────────────────────────┐   │
│ │ Sent when payment is marked as paid     │   │
│ │                                         │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ Template Type                                   │
│ ┌─────────────────────────────────────────┐   │
│ │ Transactional            ▼             │   │
│ └─────────────────────────────────────────┘   │
│ Options: Transactional, Marketing,              │
│          Notification, System                   │
│                                                 │
│ Available Variables (comma-separated)           │
│ ┌─────────────────────────────────────────┐   │
│ │ customer_name, policy_number, amount    │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ [Cancel]                        [Save Template] │
└─────────────────────────────────────────────────┘
```

**Create Request Payload**:
```json
{
  "name": "Payment Confirmation",
  "listmonk_template_id": 42,
  "description": "Sent when payment is marked as paid",
  "template_type": "transactional",
  "available_variables": [
    "customer_name",
    "policy_number",
    "premium_amount",
    "effective_date"
  ]
}
```

**Create Response** (201 Created):
```json
{
  "id": 3,
  "product_id": 2,
  "name": "Payment Confirmation",
  "listmonk_template_id": 42,
  "description": "Sent when payment is marked as paid",
  "template_type": "transactional",
  "available_variables": [
    "customer_name",
    "policy_number",
    "premium_amount",
    "effective_date"
  ],
  "stats": {
    "times_used": 0,
    "last_used_at": null
  },
  "created_at": "2026-01-23T15:30:00Z",
  "updated_at": "2026-01-23T15:30:00Z"
}
```

**Update Request Payload** (partial update supported):
```json
{
  "description": "Updated description",
  "available_variables": [
    "customer_name",
    "policy_number",
    "premium_amount"
  ]
}
```

**Validation Rules**:
- ✅ Template name: Required, max 255 chars, unique per product
- ✅ ListMonk Template ID: Required, positive integer
- ✅ Template type: Must be one of: transactional, marketing, notification, system
- ✅ Available variables: Array of strings (can be empty)

**Error Responses**:
```json
// 409 Conflict - Duplicate name
{
  "detail": "Email template 'Payment Confirmation' already exists for this product"
}

// 404 Not Found
{
  "detail": "Email template 3 not found"
}
```

### Delete Template

**API Endpoint**: `DELETE /api/v1/products/{product_id}/templates/email/{template_id}`

**Response**: 204 No Content

**UI Behavior**:
- Show confirmation dialog: "Delete template 'Payment Confirmation'? This cannot be undone."
- ⚠️ **Warning**: "This template may be referenced in event subscription actions"
- On success: Remove from list, show toast "Template deleted"

---

## SMS Templates Tab

### List View

**API Endpoint**: `GET /api/v1/products/{product_id}/templates/sms`

**Response**:
```json
[
  {
    "id": 10,
    "product_id": 2,
    "name": "Policy Reminder",
    "message": "Your policy {{policy_number}} expires on {{expiry_date}}. Renew now at {{renewal_link}}",
    "description": "7-day reminder before policy expiry",
    "template_type": "notification",
    "available_variables": [
      "policy_number",
      "expiry_date",
      "renewal_link"
    ],
    "char_count": 98,
    "stats": {
      "times_used": 234,
      "last_used_at": "2026-01-23T09:15:00Z"
    },
    "created_at": "2026-01-10T14:00:00Z",
    "updated_at": "2026-01-18T11:30:00Z"
  }
]
```

**UI Components**:
- **Card per template** with:
  - Template name (h3, bold)
  - Message preview (truncated, 2 lines)
  - Character count badge ("98 chars, ~1 SMS")
  - Template type badge
  - Description
  - Usage stats
  - Actions: Edit, Delete

**SMS Character Count Info**:
- 1-160 chars = 1 SMS
- 161-306 chars = 2 SMS
- 307-459 chars = 3 SMS
- Show: "98 chars, ~1 SMS" or "234 chars, ~2 SMS"

### Create/Edit Modal

**API Endpoints**:
- **Create**: `POST /api/v1/products/{product_id}/templates/sms`
- **Update**: `PUT /api/v1/products/{product_id}/templates/sms/{template_id}`
- **Get Single**: `GET /api/v1/products/{product_id}/templates/sms/{template_id}`

**Form Fields**:

```
┌─────────────────────────────────────────────────┐
│ Add SMS Template                                │
├─────────────────────────────────────────────────┤
│                                                 │
│ Template Name *                                 │
│ ┌─────────────────────────────────────────┐   │
│ │ Policy Reminder                         │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ Message Content *                      98/160  │
│ ┌─────────────────────────────────────────┐   │
│ │ Your policy {{policy_number}} expires  │   │
│ │ on {{expiry_date}}. Renew now at       │   │
│ │ {{renewal_link}}                       │   │
│ └─────────────────────────────────────────┘   │
│ ℹ️ Use {{variable}} for placeholders          │
│ 📊 ~1 SMS                                      │
│                                                 │
│ Description                                     │
│ ┌─────────────────────────────────────────┐   │
│ │ 7-day reminder before policy expiry     │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ Template Type                                   │
│ ┌─────────────────────────────────────────┐   │
│ │ Notification             ▼             │   │
│ └─────────────────────────────────────────┘   │
│                                                 │
│ Available Variables (detected)                  │
│ 🏷️ policy_number  🏷️ expiry_date             │
│ 🏷️ renewal_link                               │
│ [+ Add Variable]                                │
│                                                 │
│ [Cancel]                        [Save Template] │
└─────────────────────────────────────────────────┘
```

**Create Request Payload**:
```json
{
  "name": "Policy Reminder",
  "message": "Your policy {{policy_number}} expires on {{expiry_date}}. Renew now at {{renewal_link}}",
  "description": "7-day reminder before policy expiry",
  "template_type": "notification",
  "available_variables": [
    "policy_number",
    "expiry_date",
    "renewal_link"
  ]
}
```

**Create Response** (201 Created):
```json
{
  "id": 11,
  "product_id": 2,
  "name": "Policy Reminder",
  "message": "Your policy {{policy_number}} expires on {{expiry_date}}. Renew now at {{renewal_link}}",
  "description": "7-day reminder before policy expiry",
  "template_type": "notification",
  "available_variables": [
    "policy_number",
    "expiry_date",
    "renewal_link"
  ],
  "char_count": 98,
  "stats": {
    "times_used": 0,
    "last_used_at": null
  },
  "created_at": "2026-01-23T15:45:00Z",
  "updated_at": "2026-01-23T15:45:00Z"
}
```

**UI Features**:
- **Live character counter**: Update as user types
- **SMS count calculator**: Show "~1 SMS", "~2 SMS", etc.
- **Variable detection**: Auto-detect {{variables}} in message
- **Variable chips**: Show detected variables as chips/badges
- **Add variable button**: Insert common variables at cursor position

**Validation Rules**:
- ✅ Template name: Required, max 255 chars, unique per product
- ✅ Message: Required, min 1 char
- ⚠️ Message length warning: Show yellow if >160 chars, red if >306 chars
- ✅ Template type: Must be one of: transactional, marketing, notification, system

---

## Integration with Events & Actions

### Using Templates in Actions

When configuring an action in Event Subscriptions, templates can be selected by ID:

**Email Action Example**:
```json
{
  "type": "conditional_email",
  "description": "Send payment confirmation",
  "conditions": {
    "payment_new_state": "paid"
  },
  "email": {
    "provider": "listmonk",
    "template_id": 1,  // ← Email Template ID
    "recipient_source": "insuree",
    "recipient_property": "email"
  }
}
```

**SMS Action Example**:
```json
{
  "type": "sms_notification",
  "description": "Send policy reminder",
  "conditions": {
    "days_to_expiry": 7
  },
  "sms": {
    "template_id": 10,  // ← SMS Template ID
    "recipient_source": "insuree",
    "recipient_property": "phone"
  }
}
```

### Template Selector UI

When configuring actions, show template dropdown:

```
Action Configuration
┌─────────────────────────────────────────┐
│ Action Type: Email                      │
│ ┌───────────────────────────────────┐  │
│ │ Conditional Email    ▼           │  │
│ └───────────────────────────────────┘  │
│                                         │
│ Email Template *                        │
│ ┌───────────────────────────────────┐  │
│ │ Payment Confirmation  ▼          │  │
│ └───────────────────────────────────┘  │
│ Options:                                │
│   - Payment Confirmation (ID: 1)        │
│   - MB Reference Email (ID: 2)          │
│   - Policy Created (ID: 5)              │
│                                         │
│ Recipient                               │
│ ┌───────────────────────────────────┐  │
│ │ Insuree Email       ▼            │  │
│ └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Load templates for dropdown**:
```javascript
// Fetch templates when action modal opens
const response = await fetch(`/api/v1/products/${productId}/templates/email`);
const templates = await response.json();

// Populate dropdown
const options = templates.map(t => ({
  value: t.id,
  label: `${t.name} (ID: ${t.id})`
}));
```

---

## UX Considerations

### Best Practices

1. **Template First, Actions Second**
   - Guide users to create templates before configuring actions
   - Show hint in Events & Actions: "📧 Create templates first in Templates tab"

2. **Template Preview**
   - Email: Show "View in ListMonk" link (opens ListMonk template editor)
   - SMS: Show message preview with variables highlighted

3. **Variable Consistency**
   - Show which variables are available when selecting template in action
   - Validate that action can provide required variables

4. **Usage Tracking**
   - Show warning when deleting template with usage > 0
   - "This template is used in 3 actions. Delete anyway?"

5. **Template Types**
   - Use color-coded badges:
     - Transactional: Blue
     - Marketing: Green
     - Notification: Yellow
     - System: Gray

### Empty States

**No Email Templates**:
```
┌───────────────────────────────────────┐
│          📧                           │
│   No Email Templates Yet              │
│                                       │
│   Email templates reference ListMonk  │
│   templates for professional emails.  │
│                                       │
│   [+ Create First Template]           │
└───────────────────────────────────────┘
```

**No SMS Templates**:
```
┌───────────────────────────────────────┐
│          📱                           │
│   No SMS Templates Yet                │
│                                       │
│   SMS templates store message content │
│   with variable placeholders.         │
│                                       │
│   [+ Create First Template]           │
└───────────────────────────────────────┘
```

---

## API Reference Summary

### Email Templates

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/products/{id}/templates/email` | List all email templates |
| POST | `/api/v1/products/{id}/templates/email` | Create email template |
| GET | `/api/v1/products/{id}/templates/email/{template_id}` | Get single template |
| PUT | `/api/v1/products/{id}/templates/email/{template_id}` | Update template |
| DELETE | `/api/v1/products/{id}/templates/email/{template_id}` | Delete template |

### SMS Templates

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/products/{id}/templates/sms` | List all SMS templates |
| POST | `/api/v1/products/{id}/templates/sms` | Create SMS template |
| GET | `/api/v1/products/{id}/templates/sms/{template_id}` | Get single template |
| PUT | `/api/v1/products/{id}/templates/sms/{template_id}` | Update template |
| DELETE | `/api/v1/products/{id}/templates/sms/{template_id}` | Delete template |

**Authentication**: All endpoints require user session (login via Habit Platform)

---

## Implementation Checklist

### Backend ✅ Complete
- [x] Database models (EmailTemplate, SMSTemplate)
- [x] API router with CRUD endpoints
- [x] Product relationships
- [x] Validation logic
- [x] Error handling

### Frontend TODO
- [ ] Templates navigation menu item
- [ ] Email templates tab
- [ ] SMS templates tab
- [ ] Create/Edit modal for email templates
- [ ] Create/Edit modal for SMS templates
- [ ] Delete confirmation dialogs
- [ ] Template selector in action configuration
- [ ] Character counter for SMS
- [ ] Variable detection and chips
- [ ] Usage statistics display
- [ ] Empty states

---

## Next Steps

1. **Create database migration** to add `email_templates` and `sms_templates` tables
2. **Test API endpoints** with Postman/curl
3. **Implement UI** following this specification
4. **Update Events & Actions screen** to reference templates by ID
5. **Document instance-side** template usage (how instance fetches and uses templates)

---

**Questions or Need Clarification?**

This specification provides complete backend support and detailed UI requirements. Review and confirm before starting frontend implementation!
