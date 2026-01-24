# 3-Template System Implementation - INSTRUCTIONS FOR UI TEAM

## Summary

The backend now supports **3 types of templates**:

1. **Email Templates** (Custom) - `/api/v1/products/{id}/templates/email`
   - Subject + Body HTML editor with {{variables}}
   - Store complete email content in database
   - Send emails WITHOUT ListMonk

2. **ListMonk Templates** - `/api/v1/products/{id}/templates/listmonk`
   - Reference to external ListMonk template IDs
   - ListMonk handles email design
   - We store reference + metadata only

3. **SMS Templates** - `/api/v1/products/{id}/templates/sms`
   - Message content with {{variables}}
   - Character count calculation
   - Already implemented ✅

## What Changed

### Backend Status: ⚠️ IN PROGRESS

**Completed:**
- ✅ EmailTemplate model (custom emails with subject/body_html/body_text)
- ✅ ListMonkTemplate model (renamed from old EmailTemplate)
- ✅ Product relationships updated
- ✅ Database exports updated

**TODO (Backend):**
- ⏳ Complete new templates.py router with all 15 endpoints
- ⏳ Database migration to rename email_templates → listmonk_templates
- ⏳ Create new email_templates table
- ⏳ Test all endpoints
- ⏳ Update UI documentation

## UI Implementation - 3 Tabs

### Tab 1: Email Templates (Custom Builder)

**Route**: `/products/:productId/templates` → "Email" tab

**Purpose**: Create custom emails with HTML editor

**Form Fields:**
```
Template Name *
Subject Line *
Body HTML * (Rich text editor with {{variable}} support)
Body Text (Plain text fallback)
Description
Template Type (dropdown: transactional, marketing, notification, system)
Available Variables (auto-detected chips)
```

**API Endpoints:**
```
GET    /api/v1/products/{id}/templates/email
POST   /api/v1/products/{id}/templates/email
GET    /api/v1/products/{id}/templates/email/{template_id}
PUT    /api/v1/products/{id}/templates/email/{template_id}
DELETE /api/v1/products/{id}/templates/email/{template_id}
```

**Sample Payload:**
```json
{
  "name": "Payment Confirmation",
  "subject": "Payment Received for Policy {{policy_number}}",
  "body_html": "<h1>Thank you {{customer_name}}</h1><p>We received your payment of {{amount}}</p>",
  "body_text": "Thank you {{customer_name}}. We received your payment of {{amount}}",
  "template_type": "transactional",
  "available_variables": ["customer_name", "policy_number", "amount"]
}
```

### Tab 2: ListMonk Templates (External Reference)

**Route**: `/products/:productId/templates` → "ListMonk" tab

**Purpose**: Reference external ListMonk templates

**Form Fields:**
```
Template Name *
ListMonk Template ID * (number input)
Description
Template Type
Available Variables
```

**API Endpoints:**
```
GET    /api/v1/products/{id}/templates/listmonk
POST   /api/v1/products/{id}/templates/listmonk
GET    /api/v1/products/{id}/templates/listmonk/{template_id}
PUT    /api/v1/products/{id}/templates/listmonk/{template_id}
DELETE /api/v1/products/{id}/templates/listmonk/{template_id}
```

**Sample Payload:**
```json
{
  "name": "Payment Confirmation (ListMonk)",
  "listmonk_template_id": 42,
  "description": "Managed in ListMonk dashboard",
  "template_type": "transactional",
  "available_variables": ["customer_name", "policy_number", "amount"]
}
```

### Tab 3: SMS Templates

**Route**: `/products/:productId/templates` → "SMS" tab

**Already implemented** - See existing TEMPLATES_UI_GUIDE.md

## UI Layout

```
┌────────────────────────────────────────────────────────┐
│ Edit Product: BRE Tyres                               │
├────────────────────────────────────────────────────────┤
│ Sidebar         │ Templates                            │
│                 │                                       │
│ ☑ Config        │ ┌───────┬──────────┬──────┐         │
│ ☑ Env Vars      │ │ Email │ ListMonk │ SMS  │         │
│ ☐ Templates ◀─  │ └───────┴──────────┴──────┘         │
│ ☐ Events        │                                       │
│                 │ [+ Add Email Template]                │
│                 │                                       │
│                 │ ┌──────────────────────────────┐     │
│                 │ │ Payment Confirmation         │     │
│                 │ │ Subject: Payment Received... │     │
│                 │ │ Type: Transactional          │     │
│                 │ │ Variables: 3                 │     │
│                 │ │              [Edit] [Delete] │     │
│                 │ └──────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

## Email Builder Requirements

### HTML Editor Features
- Rich text editing (bold, italic, headings, lists)
- Variable insertion button (dropdown with {{variable}} options)
- Preview mode (show with sample data)
- Source code view (for advanced users)
- Image upload support
- Link insertion
- Color picker

### Variable Handling
- Auto-detect {{variables}} from subject and body
- Show variables as colored chips/badges
- Validation: warn if variable in subject but not in list
- Variable quick-insert dropdown in toolbar

### Plain Text Fallback
- Auto-generate from HTML (optional)
- Manual editing support
- Show character count

## Using Templates in Actions

When configuring event subscription actions:

**Custom Email:**
```json
{
  "type": "custom_email",
  "template_id": 1,  // ← Email Template ID
  "recipient_source": "insuree",
  "recipient_property": "email"
}
```

**ListMonk Email:**
```json
{
  "type": "listmonk_email",
  "template_id": 5,  // ← ListMonk Template ID
  "recipient_source": "insuree",
  "recipient_property": "email"
}
```

**SMS:**
```json
{
  "type": "sms",
  "template_id": 10,  // ← SMS Template ID
  "recipient_source": "insuree",
  "recipient_property": "phone"
}
```

## Next Steps

### Backend (Me)
1. Complete templates.py router (in progress)
2. Run database migration
3. Test all 15 endpoints
4. Update documentation
5. Commit everything

### Frontend (You)
1. Wait for backend completion notification
2. Add 3rd tab to Templates screen
3. Implement HTML editor for Email tab
4. Update ListMonk tab (was "Email" before)
5. Update action configuration to show template type

## Questions?

**Q: Which HTML editor library should we use?**
A: Recommend TinyMCE, Quill, or Draft.js - your choice

**Q: Do we need email preview?**
A: Yes! Show preview with sample variable data

**Q: Should we validate HTML?**
A: Basic validation only - check for {{variable}} syntax errors

**Q: Can users switch between HTML and plain text?**
A: Yes - provide tabs or toggle

---

**Status: I'm completing the backend now. You'll get notification when ready!**
