"""
Workflow Step Types Metadata API.

Provides step type schemas for UI dynamic form generation.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/workflow/step-types",
    tags=["workflow-step-types"]
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP TYPE METADATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP_TYPE_SCHEMAS = {
    "calculate_premium": {
        "step_type": "calculate_premium",
        "display_name": "Calculate Premium",
        "description": "Calculate insurance premium using pricing templates",
        "icon": "calculator",
        "category": "pricing",
        "version": "2.0.0",
        "config_schema": {
            "type": "object",
            "properties": {
                "pricing_template_id": {
                    "type": "integer",
                    "title": "Pricing Template",
                    "description": "Select which pricing template to use for calculation",
                    "ui_widget": "pricing_template_selector",
                    "ui_data_source": "/api/v1/products/{product_id}/pricing-templates?is_active=true",
                    "ui_required": True,
                    "ui_display_format": "{name} - {strategy}",
                    "ui_allow_create": True,
                    "ui_create_modal": "/products/{product_id}/pricing-templates/new"
                },
                "service": {
                    "type": "string",
                    "title": "Legacy Service",
                    "description": "Use legacy calculation method (deprecated)",
                    "enum": ["quote_simulation"],
                    "ui_widget": "select",
                    "ui_deprecated": True,
                    "ui_show_when": {"legacy_mode": True}
                }
            },
            "oneOf": [
                {
                    "required": ["pricing_template_id"],
                    "properties": {"pricing_template_id": {}}
                },
                {
                    "required": ["service"],
                    "properties": {"service": {}}
                }
            ]
        },
        "input_requirements": {
            "required_context": [
                "quote_id",
                "product_id",
                "service_id"
            ],
            "required_properties": [
                "payment_frequency"
            ],
            "required_protected_assets": True
        },
        "output_provides": {
            "context_keys": ["rate_base", "pricing_breakdown"],
            "quote_properties": ["rate_base"]
        }
    },
    "fetch_quote": {
        "step_type": "fetch_quote",
        "display_name": "Fetch Quote",
        "description": "Retrieve quote data from Habit platform",
        "icon": "download",
        "category": "data",
        "version": "1.0.0",
        "config_schema": {
            "type": "object",
            "properties": {}
        },
        "input_requirements": {
            "required_context": ["quote_id"]
        },
        "output_provides": {
            "context_keys": ["quote", "distributor_id"]
        }
    },
    "validate_product": {
        "step_type": "validate_product",
        "display_name": "Validate Product",
        "description": "Validate quote against product rules",
        "icon": "check-circle",
        "category": "validation",
        "version": "1.0.0",
        "config_schema": {
            "type": "object",
            "properties": {
                "skip_validation": {
                    "type": "boolean",
                    "title": "Skip Validation",
                    "description": "Skip product validation (testing only)",
                    "ui_widget": "checkbox",
                    "ui_optional": True,
                    "ui_default": False
                }
            }
        },
        "input_requirements": {
            "required_context": ["quote", "product_id"]
        },
        "output_provides": {
            "context_keys": ["validation_result"]
        }
    },
    "execute_business_rule": {
        "step_type": "execute_business_rule",
        "display_name": "Execute Business Rule",
        "description": "Run a business rule to make decisions or calculations",
        "icon": "git-branch",
        "category": "rules",
        "version": "1.0.0",
        "config_schema": {
            "type": "object",
            "required": ["rule_id"],
            "properties": {
                "rule_id": {
                    "type": "integer",
                    "title": "Business Rule",
                    "description": "Select which business rule to execute",
                    "ui_widget": "business_rule_selector",
                    "ui_data_source": "/api/v1/products/{product_id}/business-rules?is_active=true",
                    "ui_required": True,
                    "ui_display_format": "{name}",
                    "ui_allow_create": True,
                    "ui_create_modal": "/products/{product_id}/business-rules/new"
                }
            }
        },
        "input_requirements": {
            "required_context": ["quote"]
        },
        "output_provides": {
            "context_keys": ["rule_result", "rule_decision"]
        }
    },
    "update_quote": {
        "step_type": "update_quote",
        "display_name": "Update Quote",
        "description": "Update quote properties on Habit platform",
        "icon": "edit",
        "category": "data",
        "version": "1.0.0",
        "config_schema": {
            "type": "object",
            "required": ["fields"],
            "properties": {
                "fields": {
                    "type": "object",
                    "title": "Fields to Update",
                    "description": "Map of property namespace to value (supports context variables)",
                    "ui_widget": "key_value_editor",
                    "ui_help": "Use {{context.variable}} for dynamic values",
                    "additionalProperties": True
                }
            }
        },
        "input_requirements": {
            "required_context": ["quote_id"]
        },
        "output_provides": {
            "context_keys": ["updated_properties"]
        }
    }
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/{step_type}/schema")
async def get_step_type_schema(step_type: str) -> Dict[str, Any]:
    """
    Get configuration schema for a workflow step type.
    
    Returns JSON Schema for dynamic form generation in UI.
    Used when configuring workflow boxes.
    """
    if step_type not in STEP_TYPE_SCHEMAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step type '{step_type}' not found"
        )
    
    return STEP_TYPE_SCHEMAS[step_type]


@router.get("")
async def list_step_types() -> Dict[str, Any]:
    """
    List all available workflow step types.
    
    Returns metadata for UI step palette/library.
    """
    step_types = []
    
    for step_type, schema in STEP_TYPE_SCHEMAS.items():
        step_types.append({
            "step_type": schema["step_type"],
            "display_name": schema["display_name"],
            "description": schema["description"],
            "icon": schema["icon"],
            "category": schema["category"],
            "version": schema["version"]
        })
    
    return {"step_types": step_types}
