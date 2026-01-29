"""
Step configuration schemas - defines the configuration interface for each step type.
This tells the UI how to render configuration panels dynamically.
"""
from typing import Any, Optional
from pydantic import BaseModel


class ConfigFieldSchema(BaseModel):
    """Schema for a single configuration field."""
    name: str
    type: str  # string, number, boolean, object, array, date, select, multiselect
    label: str
    description: Optional[str] = None
    required: bool = False
    default: Any = None
    options: Optional[list[dict]] = None  # For select/multiselect
    placeholder: Optional[str] = None
    validation: Optional[dict] = None  # Validation rules
    depends_on: Optional[dict] = None  # Conditional visibility
    group: Optional[str] = None  # Group fields together
    ui_component: Optional[str] = None  # Specific UI component to use


class ConfigSectionSchema(BaseModel):
    """Schema for a configuration section (group of fields)."""
    name: str
    label: str
    description: Optional[str] = None
    fields: list[ConfigFieldSchema]
    collapsible: bool = False
    default_expanded: bool = True


class StepConfigSchema(BaseModel):
    """Complete configuration schema for a step type."""
    step_type: str
    label: str
    description: str
    sections: list[ConfigSectionSchema]
    examples: Optional[list[dict]] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP CONFIGURATION SCHEMAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UPDATE_QUOTE_SCHEMA = StepConfigSchema(
    step_type="update_quote",
    label="Update Quote",
    description="Update quote properties with static values, contextual values, or calculated values",
    sections=[
        ConfigSectionSchema(
            name="fields",
            label="Quote Fields",
            description="Select which quote fields to update and specify their values",
            fields=[
                ConfigFieldSchema(
                    name="field_selector",
                    type="quote_field_multiselect",
                    label="Select Fields to Update",
                    description="Choose which quote properties to update",
                    required=True,
                    ui_component="QuoteFieldSelector"
                ),
                ConfigFieldSchema(
                    name="field_values",
                    type="field_value_map",
                    label="Field Values",
                    description="For each selected field, specify static value or context variable",
                    required=True,
                    ui_component="FieldValueEditor"
                )
            ],
            collapsible=False,
            default_expanded=True
        ),
        ConfigSectionSchema(
            name="date_calculations",
            label="Date Calculations",
            description="Configure automatic date calculations for date fields",
            fields=[
                ConfigFieldSchema(
                    name="enabled_fields",
                    type="multiselect",
                    label="Enable Date Calculations For",
                    description="Select which date fields should be automatically calculated",
                    options=[
                        {"value": "policy_start_date", "label": "Policy Start Date"},
                        {"value": "policy_end_date", "label": "Policy End Date"},
                        {"value": "policy_expiry_date", "label": "Policy Expiry Date"},
                        {"value": "coverage_start_date", "label": "Coverage Start Date"}
                    ]
                ),
                ConfigFieldSchema(
                    name="calculations",
                    type="date_calculation_map",
                    label="Calculation Rules",
                    description="Define how each date should be calculated",
                    ui_component="DateCalculationEditor",
                    validation={
                        "schema": {
                            "source": {
                                "type": "select",
                                "options": ["current_date", "quote_created", "static", "<other_date_field>"],
                                "required": True
                            },
                            "static_value": {
                                "type": "date",
                                "required_if": "source=static"
                            },
                            "offset_days": {"type": "number", "default": 0},
                            "offset_months": {"type": "number", "default": 0},
                            "offset_years": {"type": "number", "default": 0},
                            "from_spec": {
                                "type": "select",
                                "description": "Read offset from quote spec (overrides offset value)",
                                "options": ["<quote_specs>"]
                            }
                        }
                    }
                )
            ],
            collapsible=True,
            default_expanded=False
        ),
        ConfigSectionSchema(
            name="payment_gateway_mapping",
            label="Payment Gateway Auto-Selection",
            description="Automatically select payment gateway based on payment method",
            fields=[
                ConfigFieldSchema(
                    name="enabled",
                    type="boolean",
                    label="Enable Auto-Selection",
                    description="Automatically set payment_gateway based on payment_method",
                    default=False
                ),
                ConfigFieldSchema(
                    name="rules",
                    type="key_value_map",
                    label="Mapping Rules",
                    description="Map payment methods to gateway keys",
                    placeholder="payment_method → gateway_key",
                    depends_on={"enabled": True},
                    ui_component="KeyValueEditor"
                ),
                ConfigFieldSchema(
                    name="gateway_options_lookup",
                    type="boolean",
                    label="Search Gateway Options",
                    description="Find gateway from payment_gateway.options by matching key/label",
                    default=True,
                    depends_on={"enabled": True}
                )
            ],
            collapsible=True,
            default_expanded=False
        )
    ],
    examples=[
        {
            "name": "Basic Update",
            "description": "Update state and rate_base",
            "config": {
                "fields": {
                    "state": "simulated",
                    "rate_base": "{{rate_base}}"
                }
            }
        },
        {
            "name": "With Date Calculations",
            "description": "Update with calculated policy dates",
            "config": {
                "fields": {
                    "state": "simulated",
                    "rate_base": "{{rate_base}}",
                    "policy_start_date": "{{policy_start_date}}",
                    "policy_end_date": "{{policy_end_date}}"
                },
                "date_calculations": {
                    "policy_start_date": {
                        "source": "current_date"
                    },
                    "policy_end_date": {
                        "source": "policy_start_date",
                        "offset_months": 12,
                        "from_spec": "policy_validity"
                    }
                }
            }
        },
        {
            "name": "With Payment Gateway Auto-Selection",
            "description": "Auto-select gateway based on payment method",
            "config": {
                "fields": {
                    "payment_gateway": "{{payment_gateway}}"
                },
                "payment_gateway_mapping": {
                    "enabled": True,
                    "rules": {
                        "mb": "stripe",
                        "cc": "stripe",
                        "mbway": "eupago"
                    },
                    "gateway_options_lookup": True
                }
            }
        }
    ]
)


# Registry of all step configuration schemas
STEP_CONFIG_SCHEMAS = {
    "update_quote": UPDATE_QUOTE_SCHEMA,
    # Add more step types here as they get enhanced
}


def get_step_config_schema(step_type: str) -> Optional[StepConfigSchema]:
    """Get the configuration schema for a step type."""
    return STEP_CONFIG_SCHEMAS.get(step_type)


def list_step_config_schemas() -> dict[str, StepConfigSchema]:
    """List all available step configuration schemas."""
    return STEP_CONFIG_SCHEMAS
