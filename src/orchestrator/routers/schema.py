"""
Template Schema and Metadata API endpoints.

Provides dynamic schema information for UI to build forms without hardcoding.
Returns available data sources, enrichment options, attachment types, etc.
"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from orchestrator.database.models import UserSession
from orchestrator.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/schema", tags=["schema"])


class DataSourceOption(BaseModel):
    """Data source that can be enriched."""
    id: str = Field(..., description="Unique identifier for data source")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="What this data source provides")
    fields: list[str] = Field(..., description="Available fields from this source")
    requires: list[str] = Field(default=[], description="Required fields in event payload")


class AttachmentTypeOption(BaseModel):
    """Type of attachment that can be added."""
    type: str = Field(..., description="Attachment type identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="What this attachment type does")
    config_fields: dict = Field(..., description="Required configuration fields")


class RecipientLogicOption(BaseModel):
    """Recipient determination logic."""
    id: str = Field(..., description="Logic identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="How recipient is determined")


class ActionTypeSchema(BaseModel):
    """Schema for a specific action type."""
    type: str = Field(..., description="Action type identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="What this action does")
    category: str = Field(..., description="Action category (email, api, system, etc.)")
    config_schema: dict = Field(..., description="JSON schema for action configuration")
    supports_conditions: bool = Field(default=True, description="Whether action supports conditions")
    supports_data_enrichment: bool = Field(default=False, description="Whether action supports data enrichment")


@router.get("/data-sources")
async def get_data_sources() -> list[DataSourceOption]:
    """
    Get available data sources for email template enrichment.
    
    Returns list of data sources that can be fetched to enrich email templates.
    """
    return [
        DataSourceOption(
            id="fetch_quote_details",
            name="Quote Details",
            description="Fetch complete quote information including premium, currency, coverage details",
            fields=[
                "quote.id",
                "quote.premium",
                "quote.currency",
                "quote.coverage_type",
                "quote.start_date",
                "quote.end_date",
                "quote.payment_frequency",
                "quote_premium",  # Flattened for convenience
                "quote_currency"
            ],
            requires=["quote_id"]
        ),
        DataSourceOption(
            id="fetch_policyholder",
            name="Policyholder Information",
            description="Fetch policyholder personal details (name, email, phone, address)",
            fields=[
                "policyholder.id",
                "policyholder.name",
                "policyholder.email",
                "policyholder.phone",
                "policyholder.address",
                "policyholder.tax_id",
                "policyholder_name",  # Flattened
                "policyholder_email"
            ],
            requires=["policyholder_id"]
        ),
        DataSourceOption(
            id="fetch_protected_asset",
            name="Protected Asset Details",
            description="Fetch information about the insured asset (vehicle, property, etc.)",
            fields=[
                "asset.id",
                "asset.type",
                "asset.make",
                "asset.model",
                "asset.year",
                "asset.registration",
                "asset.value",
                "asset_make",  # Flattened
                "asset_model"
            ],
            requires=["protected_asset_id"]
        ),
        DataSourceOption(
            id="fetch_policy_details",
            name="Policy Information",
            description="Fetch active policy details including status, dates, coverage",
            fields=[
                "policy.id",
                "policy.code",
                "policy.status",
                "policy.start_date",
                "policy.end_date",
                "policy.next_billing_date",
                "policy_status",  # Flattened
                "policy_start_date"
            ],
            requires=["policy_id"]
        ),
        DataSourceOption(
            id="fetch_payment_details",
            name="Payment Information",
            description="Fetch payment transaction details",
            fields=[
                "payment.id",
                "payment.amount",
                "payment.currency",
                "payment.method",
                "payment.status",
                "payment.date",
                "payment_amount",  # Flattened
                "payment_method"
            ],
            requires=["payment_id"]
        ),
        DataSourceOption(
            id="fetch_documents",
            name="Documents",
            description="Fetch document download URLs (policy certificate, terms, etc.)",
            fields=[
                "documents.policy_certificate",
                "documents.terms_conditions",
                "documents.payment_receipt"
            ],
            requires=["document_id"]
        )
    ]


@router.get("/attachment-types")
async def get_attachment_types() -> list[AttachmentTypeOption]:
    """
    Get available attachment types for emails.
    
    Returns types of attachments that can be added to emails.
    """
    return [
        AttachmentTypeOption(
            type="document",
            name="Document from Habit Platform",
            description="Attach a document stored in Habit Platform (policy cert, receipt, etc.)",
            config_fields={
                "document_id": {
                    "type": "string",
                    "description": "Document ID or template variable (e.g., {{policy_document_id}})",
                    "required": True
                },
                "filename": {
                    "type": "string",
                    "description": "Filename for attachment (supports variables)",
                    "required": False,
                    "default": "document.pdf"
                }
            }
        ),
        AttachmentTypeOption(
            type="generated",
            name="Generated Document",
            description="Generate a document on-the-fly (invoice PDF, report, etc.)",
            config_fields={
                "generator": {
                    "type": "select",
                    "description": "Document generator type",
                    "required": True,
                    "options": ["invoice_pdf", "policy_summary", "payment_receipt"]
                },
                "data_source": {
                    "type": "string",
                    "description": "Data source for generation (payment_data, policy_data, etc.)",
                    "required": False
                }
            }
        ),
        AttachmentTypeOption(
            type="static",
            name="Static File",
            description="Attach a pre-uploaded static file (logo, brochure, etc.)",
            config_fields={
                "file_id": {
                    "type": "string",
                    "description": "Static file ID from media library",
                    "required": True
                },
                "filename": {
                    "type": "string",
                    "description": "Filename for attachment",
                    "required": False
                }
            }
        )
    ]


@router.get("/recipient-logic")
async def get_recipient_logic_options() -> list[RecipientLogicOption]:
    """
    Get available recipient logic options for email actions.
    
    Returns ways to determine who receives the email.
    """
    return [
        RecipientLogicOption(
            id="production",
            name="Production Email",
            description="Always send to production alert email (from environment config)"
        ),
        RecipientLogicOption(
            id="sandbox_conditional",
            name="Sandbox/Production Conditional",
            description="Send to sandbox email if application is in sandbox mode, otherwise production"
        ),
        RecipientLogicOption(
            id="policyholder",
            name="Policyholder Email",
            description="Send to policyholder's email address (from enriched data)"
        ),
        RecipientLogicOption(
            id="broker",
            name="Broker Email",
            description="Send to broker's email address (requires broker data enrichment)"
        ),
        RecipientLogicOption(
            id="custom",
            name="Custom from Context",
            description="Use email address from template context variable {{recipient_email}}"
        )
    ]


@router.get("/action-types")
async def get_action_types() -> list[ActionTypeSchema]:
    """
    Get available action types and their configuration schemas.
    
    Returns complete schema for each action type so UI can build forms dynamically.
    """
    return [
        ActionTypeSchema(
            type="smtp_email",
            name="SMTP Email",
            description="Send email via SMTP using a template with data enrichment and attachments",
            category="email",
            supports_conditions=True,
            supports_data_enrichment=True,
            config_schema={
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "description": "Email template name",
                        "ui_widget": "template_selector",
                        "template_type": "email"
                    },
                    "recipient_logic": {
                        "type": "string",
                        "description": "How to determine recipient",
                        "ui_widget": "select",
                        "options_endpoint": "/api/v1/schema/recipient-logic",
                        "default": "sandbox_conditional"
                    },
                    "data_enrichment": {
                        "type": "object",
                        "description": "Data sources to fetch and merge into template",
                        "ui_widget": "data_enrichment_builder",
                        "options_endpoint": "/api/v1/schema/data-sources",
                        "properties": {
                            "fetch_quote_details": {"type": "boolean"},
                            "fetch_policyholder": {"type": "boolean"},
                            "fetch_protected_asset": {"type": "boolean"},
                            "fetch_policy_details": {"type": "boolean"},
                            "fetch_payment_details": {"type": "boolean"},
                            "fetch_documents": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Document types to fetch"
                            }
                        }
                    },
                    "attachments": {
                        "type": "array",
                        "description": "Email attachments",
                        "ui_widget": "attachment_builder",
                        "options_endpoint": "/api/v1/schema/attachment-types",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "config": {"type": "object"}
                            }
                        }
                    }
                },
                "required": ["template"]
            }
        ),
        ActionTypeSchema(
            type="conditional_email",
            name="Conditional Email (ListMonk)",
            description="Send email via ListMonk with conditional logic",
            category="email",
            supports_conditions=True,
            supports_data_enrichment=False,
            config_schema={
                "type": "object",
                "properties": {
                    "template": {
                        "type": "string",
                        "description": "ListMonk template name",
                        "ui_widget": "template_selector",
                        "template_type": "listmonk"
                    },
                    "recipient_email": {
                        "type": "string",
                        "description": "Recipient email variable path (e.g., user.email)"
                    }
                },
                "required": ["template", "recipient_email"]
            }
        ),
        ActionTypeSchema(
            type="activate_policy",
            name="Activate Policy",
            description="Activate a policy in Habit Platform",
            category="api",
            supports_conditions=True,
            supports_data_enrichment=False,
            config_schema={
                "type": "object",
                "properties": {},
                "description": "No additional configuration required - uses policy_id from event payload"
            }
        ),
        ActionTypeSchema(
            type="invalidate_smartlinks",
            name="Invalidate Smart Links",
            description="Invalidate all smart links associated with a quote",
            category="api",
            supports_conditions=True,
            supports_data_enrichment=False,
            config_schema={
                "type": "object",
                "properties": {},
                "description": "No additional configuration required - uses quote_id from event payload"
            }
        ),
        ActionTypeSchema(
            type="create_invoice",
            name="Create Invoice",
            description="Create invoice in Moloni system",
            category="integration",
            supports_conditions=True,
            supports_data_enrichment=False,
            config_schema={
                "type": "object",
                "properties": {
                    "invoice_type": {
                        "type": "string",
                        "description": "Type of invoice to create",
                        "enum": ["standard", "proforma", "receipt"]
                    }
                }
            }
        ),
        ActionTypeSchema(
            type="healthcheck_response",
            name="Healthcheck Response",
            description="Respond to MQTT healthcheck events",
            category="system",
            supports_conditions=False,
            supports_data_enrichment=False,
            config_schema={
                "type": "object",
                "properties": {},
                "description": "No configuration required - automatically logs healthcheck reception"
            }
        ),
        ActionTypeSchema(
            type="update_next_billing_date",
            name="Update Next Billing Date",
            description="Calculate and update policy's next billing date based on payment frequency",
            category="api",
            supports_conditions=True,
            supports_data_enrichment=False,
            config_schema={
                "type": "object",
                "properties": {},
                "description": "Automatically calculates next billing date from payment frequency"
            }
        )
    ]


@router.get("/template-variables")
async def get_common_template_variables() -> dict:
    """
    Get commonly available template variables.
    
    Returns variables that are typically available in event payloads.
    """
    return {
        "event_payload": [
            "quote_id",
            "policy_id",
            "payment_id",
            "policyholder_id",
            "protected_asset_id",
            "application_id",
            "distributor_id",
            "insurer_id",
            "policy_code",
            "timestamp",
            "sender",
            "payment_new_state",
            "payment_old_state"
        ],
        "enriched_quote": [
            "quote.premium",
            "quote.currency",
            "quote.coverage_type",
            "quote.start_date",
            "quote.end_date"
        ],
        "enriched_policyholder": [
            "policyholder.name",
            "policyholder.email",
            "policyholder.phone",
            "policyholder.address"
        ],
        "enriched_asset": [
            "asset.make",
            "asset.model",
            "asset.year",
            "asset.registration"
        ],
        "enriched_policy": [
            "policy.code",
            "policy.status",
            "policy.start_date",
            "policy.end_date"
        ],
        "enriched_payment": [
            "payment.amount",
            "payment.method",
            "payment.status",
            "payment.date"
        ],
        "debug_placeholders": [
            "debug.quote",
            "debug.policyholder",
            "debug.asset",
            "debug.policy",
            "debug.payment",
            "debug.all"
        ]
    }


@router.get("/mqtt-action-conditions")
async def get_mqtt_action_conditions(
    _current_user: UserSession = Depends(get_current_user)
) -> dict:
    """
    Get available condition fields for each MQTT action type.
    
    This endpoint provides metadata for the UI to dynamically build
    condition forms for MQTT action configuration.
    
    Returns:
        Dictionary mapping action types to their available condition fields,
        including field types, descriptions, options, and defaults.
    """
    return {
        "conditional_email": {
            "description": "Send email via ListMonk with conditional logic",
            "conditions": {
                "payment_state": {
                    "type": "select",
                    "description": "Payment state (from payment object, not event)",
                    "options": ["pending", "paid", "canceled", "refunded", "ANY"],
                    "default": "ANY"
                },
                "payment_method": {
                    "type": "multiselect",
                    "description": "Payment method(s) allowed",
                    "options": ["multibanco", "credit_card", "sepa_debit", "paypal", "mb_way"],
                    "default": []
                },
                "payment_cdata_path": {
                    "type": "text",
                    "description": "Path to custom data in payment object (e.g., cdata.public.field)",
                    "default": ""
                },
                "payment_cdata_value": {
                    "type": "text",
                    "description": "Expected value at cdata path",
                    "default": ""
                },
                "payment_multibanco_exists": {
                    "type": "boolean",
                    "description": "Check if payment has Multibanco data",
                    "default": False
                },
                "payment_tag": {
                    "type": "text",
                    "description": "Required payment tag (e.g., new_subscription, renewal)",
                    "default": ""
                },
                "policy_new_state": {
                    "type": "select",
                    "description": "Policy new state (from event payload)",
                    "options": ["pending", "active", "inactive", "canceled", "ANY"],
                    "default": "ANY"
                }
            },
            "supports_custom_conditions": False
        },
        "activate_policy": {
            "description": "Mark policy as active in Habit Platform",
            "conditions": {
                "payment_new_state": {
                    "type": "select",
                    "description": "Payment new state from event",
                    "options": ["pending", "paid", "canceled", "refunded", "ANY"],
                    "default": "paid"
                },
                "payment_old_state": {
                    "type": "select",
                    "description": "Payment old state from event",
                    "options": ["pending", "paid", "canceled", "refunded", "ANY"],
                    "default": "ANY"
                },
                "payment_type": {
                    "type": "select",
                    "description": "Payment type from event",
                    "options": ["subscription", "one-time", "renewal", "ANY"],
                    "default": "ANY"
                },
                "policy_new_state": {
                    "type": "select",
                    "description": "Policy new state from event",
                    "options": ["pending", "active", "inactive", "canceled", "ANY"],
                    "default": "ANY"
                },
                "policy_old_state": {
                    "type": "select",
                    "description": "Policy old state from event",
                    "options": ["pending", "active", "inactive", "canceled", "ANY"],
                    "default": "ANY"
                }
            },
            "supports_custom_conditions": True
        },
        "invalidate_smartlinks": {
            "description": "Invalidate smart links for quote",
            "conditions": {
                "payment_new_state": {
                    "type": "select",
                    "description": "Payment new state from event",
                    "options": ["pending", "paid", "canceled", "refunded", "ANY"],
                    "default": "paid"
                },
                "payment_old_state": {
                    "type": "select",
                    "description": "Payment old state from event",
                    "options": ["pending", "paid", "canceled", "refunded", "ANY"],
                    "default": "ANY"
                },
                "payment_type": {
                    "type": "select",
                    "description": "Payment type from event",
                    "options": ["subscription", "one-time", "renewal", "ANY"],
                    "default": "ANY"
                }
            },
            "supports_custom_conditions": True
        },
        "create_invoice": {
            "description": "Create invoice in Moloni system",
            "conditions": {
                "payment_new_state": {
                    "type": "select",
                    "description": "Payment new state from event",
                    "options": ["pending", "paid", "canceled", "refunded", "ANY"],
                    "default": "paid"
                },
                "payment_old_state": {
                    "type": "select",
                    "description": "Payment old state from event",
                    "options": ["pending", "paid", "canceled", "refunded", "ANY"],
                    "default": "ANY"
                },
                "payment_type": {
                    "type": "select",
                    "description": "Payment type from event",
                    "options": ["subscription", "one-time", "renewal", "ANY"],
                    "default": "ANY"
                }
            },
            "supports_custom_conditions": True
        },
        "smtp_email": {
            "description": "Send email via SMTP",
            "conditions": {},
            "supports_custom_conditions": True
        },
        "healthcheck_response": {
            "description": "Respond to MQTT healthcheck",
            "conditions": {},
            "supports_custom_conditions": False
        }
    }
