"""
Pricing Strategies Metadata API.

Provides strategy information for UI dynamic form generation.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/pricing-strategies",
    tags=["pricing-strategies"]
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STRATEGY METADATA REGISTRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# This mirrors the strategies in the instance but provides metadata for UI
# In production, this could be auto-generated from instance strategy classes
STRATEGY_METADATA = {
    "simple_percentage": {
        "name": "simple_percentage",
        "version": "1.0.0",
        "display_name": "Simple Percentage",
        "description": "Calculate premium as a percentage of coverage amount",
        "icon": "percentage",
        "category": "percentage_based",
        "complexity": "simple",
        "config_schema": {
            "type": "object",
            "required": ["percentage"],
            "properties": {
                "percentage": {
                    "type": "number",
                    "title": "Percentage Rate",
                    "description": "Percentage of coverage amount (0.05 = 5%)",
                    "minimum": 0,
                    "maximum": 1,
                    "ui_widget": "percentage_input",
                    "ui_placeholder": "0.05",
                    "ui_help": "Enter as decimal (e.g., 0.05 for 5%)"
                },
                "min_premium": {
                    "type": "number",
                    "title": "Minimum Premium",
                    "description": "Minimum premium amount in currency",
                    "minimum": 0,
                    "ui_widget": "currency_input",
                    "ui_placeholder": "10.00",
                    "ui_optional": True
                },
                "max_premium": {
                    "type": "number",
                    "title": "Maximum Premium",
                    "description": "Maximum premium amount in currency",
                    "minimum": 0,
                    "ui_widget": "currency_input",
                    "ui_placeholder": "1000.00",
                    "ui_optional": True
                }
            }
        },
        "examples": [
            {
                "name": "Standard 5%",
                "description": "5% of coverage with €10-€1000 bounds",
                "config": {
                    "percentage": 0.05,
                    "min_premium": 10.00,
                    "max_premium": 1000.00
                }
            },
            {
                "name": "Premium 3%",
                "description": "Lower rate for higher coverage",
                "config": {
                    "percentage": 0.03,
                    "min_premium": 25.00
                }
            }
        ]
    },
    "interval_based": {
        "name": "interval_based",
        "version": "1.0.0",
        "display_name": "Interval-Based Pricing",
        "description": "Fixed premium for coverage amount ranges",
        "icon": "layers",
        "category": "interval_based",
        "complexity": "simple",
        "config_schema": {
            "type": "object",
            "required": ["intervals"],
            "properties": {
                "intervals": {
                    "type": "array",
                    "title": "Coverage Intervals",
                    "description": "Define premium for each coverage range",
                    "items": {
                        "type": "object",
                        "required": ["premium"],
                        "properties": {
                            "min": {
                                "type": "number",
                                "title": "Minimum Coverage",
                                "minimum": 0,
                                "ui_widget": "currency_input",
                                "ui_default": 0
                            },
                            "max": {
                                "type": "number",
                                "title": "Maximum Coverage",
                                "minimum": 0,
                                "ui_widget": "currency_input",
                                "ui_nullable": True,
                                "ui_help": "Leave empty for unlimited"
                            },
                            "premium": {
                                "type": "number",
                                "title": "Fixed Premium",
                                "minimum": 0,
                                "ui_widget": "currency_input",
                                "ui_required": True
                            }
                        }
                    },
                    "ui_widget": "interval_builder",
                    "ui_min_items": 1
                },
                "payment_frequency_adjustments": {
                    "type": "object",
                    "title": "Payment Frequency Multipliers",
                    "description": "Optional multipliers for different payment frequencies",
                    "properties": {
                        "monthly": {"type": "number", "minimum": 0, "ui_default": 1.1},
                        "quarterly": {"type": "number", "minimum": 0, "ui_default": 1.05},
                        "annual": {"type": "number", "minimum": 0, "ui_default": 1.0}
                    },
                    "ui_widget": "frequency_multipliers",
                    "ui_optional": True,
                    "ui_collapsed": True
                }
            }
        },
        "examples": [
            {
                "name": "Tiered Coverage",
                "description": "Fixed premiums per coverage bracket",
                "config": {
                    "intervals": [
                        {"min": 0, "max": 500, "premium": 15.00},
                        {"min": 500, "max": 2000, "premium": 30.00},
                        {"min": 2000, "max": None, "premium": 50.00}
                    ]
                }
            }
        ]
    },
    "tiered_percentage": {
        "name": "tiered_percentage",
        "version": "1.0.0",
        "display_name": "Tiered Percentage",
        "description": "Progressive percentage rates by coverage tier",
        "icon": "trending-up",
        "category": "percentage_based",
        "complexity": "advanced",
        "config_schema": {
            "type": "object",
            "required": ["tiers"],
            "properties": {
                "tiers": {
                    "type": "array",
                    "title": "Percentage Tiers",
                    "description": "Define percentage rate for each coverage tier",
                    "items": {
                        "type": "object",
                        "required": ["percentage"],
                        "properties": {
                            "min": {
                                "type": "number",
                                "title": "Tier Start",
                                "minimum": 0,
                                "ui_widget": "currency_input",
                                "ui_default": 0
                            },
                            "max": {
                                "type": "number",
                                "title": "Tier End",
                                "minimum": 0,
                                "ui_widget": "currency_input",
                                "ui_nullable": True,
                                "ui_help": "Leave empty for unlimited"
                            },
                            "percentage": {
                                "type": "number",
                                "title": "Percentage Rate",
                                "minimum": 0,
                                "maximum": 1,
                                "ui_widget": "percentage_input",
                                "ui_required": True
                            }
                        }
                    },
                    "ui_widget": "tier_builder",
                    "ui_min_items": 1
                },
                "min_premium": {
                    "type": "number",
                    "title": "Minimum Premium",
                    "minimum": 0,
                    "ui_widget": "currency_input",
                    "ui_optional": True
                },
                "max_premium": {
                    "type": "number",
                    "title": "Maximum Premium",
                    "minimum": 0,
                    "ui_widget": "currency_input",
                    "ui_optional": True
                }
            }
        },
        "examples": [
            {
                "name": "Progressive Rates",
                "description": "Higher coverage = lower percentage",
                "config": {
                    "tiers": [
                        {"min": 0, "max": 500, "percentage": 0.06},
                        {"min": 500, "max": 2000, "percentage": 0.045},
                        {"min": 2000, "max": None, "percentage": 0.03}
                    ],
                    "min_premium": 15.00,
                    "max_premium": 500.00
                }
            }
        ]
    }
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCalculationRequest(BaseModel):
    """Request for testing pricing calculation."""
    strategy: str
    strategy_config: Dict[str, Any]
    test_inputs: Dict[str, Any]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("")
async def list_pricing_strategies() -> Dict[str, List[Dict[str, Any]]]:
    """
    List all available pricing strategies.
    
    Returns strategy metadata for UI dropdown/selection.
    """
    strategies = []
    
    for strategy_name, metadata in STRATEGY_METADATA.items():
        strategies.append({
            "name": metadata["name"],
            "version": metadata["version"],
            "display_name": metadata["display_name"],
            "description": metadata["description"],
            "icon": metadata["icon"],
            "category": metadata["category"],
            "complexity": metadata["complexity"]
        })
    
    return {"strategies": strategies}


@router.get("/{strategy_name}/schema")
async def get_strategy_schema(strategy_name: str) -> Dict[str, Any]:
    """
    Get configuration schema for a specific pricing strategy.
    
    Returns JSON Schema for dynamic form generation in UI.
    """
    if strategy_name not in STRATEGY_METADATA:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_name}' not found"
        )
    
    metadata = STRATEGY_METADATA[strategy_name]
    
    return {
        "strategy": metadata["name"],
        "version": metadata["version"],
        "display_name": metadata["display_name"],
        "description": metadata["description"],
        "config_schema": metadata["config_schema"],
        "examples": metadata.get("examples", [])
    }


@router.post("/test")
async def test_pricing_calculation(request: TestCalculationRequest) -> Dict[str, Any]:
    """
    Test a pricing calculation without saving.
    
    Allows UI to preview premium calculation with current configuration.
    Note: This endpoint performs basic calculation logic for preview only.
    Actual instance calculations may include additional business logic.
    """
    strategy = request.strategy
    config = request.strategy_config
    inputs = request.test_inputs
    
    if strategy not in STRATEGY_METADATA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown strategy: {strategy}"
        )
    
    # Basic validation and calculation
    coverage_amount = float(inputs.get("coverage_amount", 0))
    payment_frequency = inputs.get("payment_frequency", "annual")
    
    try:
        if strategy == "simple_percentage":
            percentage = float(config["percentage"])
            min_premium = float(config.get("min_premium", 0))
            max_premium = float(config.get("max_premium", float('inf')))
            
            base_premium = coverage_amount * percentage
            final_premium = max(min_premium, min(base_premium, max_premium))
            
            return {
                "rate_base": round(final_premium, 2),
                "breakdown": {
                    "strategy": strategy,
                    "coverage_amount": coverage_amount,
                    "percentage": percentage,
                    "calculated_premium": round(base_premium, 2),
                    "min_premium": min_premium,
                    "max_premium": max_premium if max_premium != float('inf') else None,
                    "min_premium_applied": final_premium == min_premium and base_premium < min_premium,
                    "max_premium_applied": final_premium == max_premium and base_premium > max_premium,
                    "final_premium": round(final_premium, 2)
                }
            }
        
        elif strategy == "interval_based":
            intervals = config["intervals"]
            frequency_adj = config.get("payment_frequency_adjustments", {})
            
            # Find matching interval
            base_premium = None
            matched_interval = None
            
            for interval in intervals:
                min_val = interval.get("min", 0)
                max_val = interval.get("max")
                
                if max_val is None:
                    max_val = float('inf')
                
                if min_val <= coverage_amount < max_val:
                    base_premium = float(interval["premium"])
                    matched_interval = interval
                    break
            
            if base_premium is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No interval matches coverage amount: {coverage_amount}"
                )
            
            # Apply frequency adjustment
            multiplier = float(frequency_adj.get(payment_frequency, 1.0))
            final_premium = base_premium * multiplier
            
            return {
                "rate_base": round(final_premium, 2),
                "breakdown": {
                    "strategy": strategy,
                    "coverage_amount": coverage_amount,
                    "matched_interval": matched_interval,
                    "base_premium": base_premium,
                    "payment_frequency": payment_frequency,
                    "frequency_multiplier": multiplier,
                    "final_premium": round(final_premium, 2)
                }
            }
        
        elif strategy == "tiered_percentage":
            tiers = config["tiers"]
            min_premium = float(config.get("min_premium", 0))
            max_premium = float(config.get("max_premium", float('inf')))
            
            total_premium = 0.0
            tier_breakdowns = []
            
            # Sort tiers by min
            sorted_tiers = sorted(tiers, key=lambda t: t.get("min", 0))
            
            for tier in sorted_tiers:
                tier_min = tier.get("min", 0)
                tier_max = tier.get("max")
                tier_percentage = float(tier["percentage"])
                
                if tier_max is None:
                    tier_max = float('inf')
                
                if coverage_amount > tier_min:
                    tier_coverage_start = max(tier_min, 0)
                    tier_coverage_end = min(coverage_amount, tier_max)
                    tier_coverage_amount = tier_coverage_end - tier_coverage_start
                    
                    if tier_coverage_amount > 0:
                        tier_premium = tier_coverage_amount * tier_percentage
                        total_premium += tier_premium
                        
                        tier_breakdowns.append({
                            "tier_min": tier_min,
                            "tier_max": tier_max if tier_max != float('inf') else None,
                            "tier_percentage": tier_percentage,
                            "coverage_in_tier": round(tier_coverage_amount, 2),
                            "tier_premium": round(tier_premium, 2)
                        })
            
            final_premium = max(min_premium, min(total_premium, max_premium))
            
            return {
                "rate_base": round(final_premium, 2),
                "breakdown": {
                    "strategy": strategy,
                    "coverage_amount": coverage_amount,
                    "tiers": tier_breakdowns,
                    "calculated_premium": round(total_premium, 2),
                    "min_premium": min_premium,
                    "max_premium": max_premium if max_premium != float('inf') else None,
                    "final_premium": round(final_premium, 2),
                    "bounding_applied": final_premium != total_premium
                }
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strategy '{strategy}' test calculation not implemented"
            )
    
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required configuration field: {e}"
        )
    except (ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration value: {e}"
        )
