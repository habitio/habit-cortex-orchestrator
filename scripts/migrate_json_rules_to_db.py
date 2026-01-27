#!/usr/bin/env python3
"""
Migrate JSON-based business rules to database.

This script reads product_validation_rules.json from cortex-instance
and creates corresponding BusinessRule records in the orchestrator database.

Usage:
    python scripts/migrate_json_rules_to_db.py [--product-id ID] [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator.database import SessionLocal
from orchestrator.database.models import BusinessRule, Product


def load_json_rules(json_path: Path) -> dict[str, Any]:
    """Load rules from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_product_by_application_id(db, application_id: str) -> Product | None:
    """Find product by application_id in env_vars."""
    products = db.query(Product).all()
    for product in products:
        if product.env_vars and product.env_vars.get("APPLICATION_ID") == application_id:
            return product
    return None


def migrate_rules(
    json_path: Path,
    product_id: int | None = None,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Migrate rules from JSON to database.
    
    Args:
        json_path: Path to product_validation_rules.json
        product_id: Specific product ID to migrate (optional)
        dry_run: If True, only print what would be done
        
    Returns:
        Migration statistics
    """
    config = load_json_rules(json_path)
    
    db = SessionLocal()
    stats = {
        "products_processed": 0,
        "rules_created": 0,
        "rules_skipped": 0,
        "errors": [],
    }
    
    try:
        products_config = config.get("products", {})
        
        for application_id, product_config in products_config.items():
            # Find corresponding product in database
            if product_id:
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    stats["errors"].append(f"Product {product_id} not found")
                    continue
                # Skip if this application_id doesn't match
                expected_app_id = product.env_vars.get("APPLICATION_ID") if product.env_vars else None
                if expected_app_id != application_id:
                    print(f"Skipping application_id {application_id} (doesn't match product {product_id})")
                    continue
            else:
                product = get_product_by_application_id(db, application_id)
                if not product:
                    print(f"Warning: No product found for application_id {application_id}")
                    stats["errors"].append(f"No product for application_id: {application_id}")
                    continue
            
            print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing product: {product.name} (ID: {product.id})")
            print(f"  Application ID: {application_id}")
            
            stats["products_processed"] += 1
            
            # Migrate validation stages
            validation_stages = product_config.get("validation_stages", {})
            
            for stage_name, stage_config in validation_stages.items():
                rules = stage_config.get("rules", [])
                
                for rule_def in rules:
                    rule_id = rule_def.get("id", "unknown")
                    
                    # Check if rule already exists
                    existing = db.query(BusinessRule).filter(
                        BusinessRule.product_id == product.id,
                        BusinessRule.name == rule_def.get("id", f"Rule from JSON"),
                        BusinessRule.stage == stage_name
                    ).first()
                    
                    if existing:
                        print(f"  ⏭️  Skipping existing rule: {rule_id} (stage: {stage_name})")
                        stats["rules_skipped"] += 1
                        continue
                    
                    # Create new rule
                    rule_name = rule_id.replace("_", " ").title()
                    description = rule_def.get("description", "")
                    
                    new_rule = BusinessRule(
                        product_id=product.id,
                        name=rule_name,
                        description=description,
                        rule_type="field_validation",
                        rule_definition=rule_def,  # Store entire rule definition
                        stage=stage_name,
                        is_active=rule_def.get("enabled", True),
                        distributor_id=None,  # Main rules, not distributor-specific
                        priority=100,  # Default priority
                    )
                    
                    if dry_run:
                        print(f"  🔍 Would create rule: {rule_name} (stage: {stage_name})")
                    else:
                        db.add(new_rule)
                        print(f"  ✅ Created rule: {rule_name} (stage: {stage_name})")
                    
                    stats["rules_created"] += 1
            
            # Migrate distributor overrides
            distributor_overrides = product_config.get("distributor_overrides", {})
            
            for distributor_id, dist_config in distributor_overrides.items():
                dist_name = dist_config.get("name", "Unknown Distributor")
                print(f"  Distributor override: {dist_name} ({distributor_id})")
                
                dist_stages = dist_config.get("validation_stages", {})
                
                for stage_name, stage_config in dist_stages.items():
                    rules = stage_config.get("rules", [])
                    
                    for rule_def in rules:
                        rule_id = rule_def.get("id", "unknown")
                        
                        # Check if rule already exists
                        existing = db.query(BusinessRule).filter(
                            BusinessRule.product_id == product.id,
                            BusinessRule.name == rule_def.get("id", f"Rule from JSON"),
                            BusinessRule.stage == stage_name,
                            BusinessRule.distributor_id == distributor_id
                        ).first()
                        
                        if existing:
                            print(f"    ⏭️  Skipping existing override rule: {rule_id}")
                            stats["rules_skipped"] += 1
                            continue
                        
                        rule_name = f"{rule_id.replace('_', ' ').title()} (Distributor Override)"
                        description = rule_def.get("description", "")
                        
                        new_rule = BusinessRule(
                            product_id=product.id,
                            name=rule_name,
                            description=description,
                            rule_type="field_validation",
                            rule_definition=rule_def,
                            stage=stage_name,
                            is_active=rule_def.get("enabled", True),
                            distributor_id=distributor_id,
                            priority=100,
                        )
                        
                        if dry_run:
                            print(f"    🔍 Would create override rule: {rule_name}")
                        else:
                            db.add(new_rule)
                            print(f"    ✅ Created override rule: {rule_name}")
                        
                        stats["rules_created"] += 1
        
        # Commit if not dry run
        if not dry_run:
            db.commit()
            print(f"\n✅ Migration complete! Committed {stats['rules_created']} rules to database.")
        else:
            print(f"\n🔍 Dry run complete! Would create {stats['rules_created']} rules.")
        
    except Exception as e:
        db.rollback()
        stats["errors"].append(str(e))
        print(f"\n❌ Error during migration: {e}")
        raise
    finally:
        db.close()
    
    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate JSON business rules to database"
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        help="Path to product_validation_rules.json",
        default=Path(__file__).parent.parent.parent / "cortex-instance" / "src" / "bre_payments" / "config" / "product_validation_rules.json"
    )
    parser.add_argument(
        "--product-id",
        type=int,
        help="Only migrate rules for specific product ID"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    if not args.json_path.exists():
        print(f"❌ JSON file not found: {args.json_path}")
        sys.exit(1)
    
    print(f"📄 Reading rules from: {args.json_path}")
    print(f"{'🔍 DRY RUN MODE - No changes will be made' if args.dry_run else '💾 LIVE MODE - Rules will be created in database'}")
    print("=" * 80)
    
    stats = migrate_rules(
        json_path=args.json_path,
        product_id=args.product_id,
        dry_run=args.dry_run
    )
    
    print("\n" + "=" * 80)
    print("📊 Migration Statistics:")
    print(f"  Products processed: {stats['products_processed']}")
    print(f"  Rules created: {stats['rules_created']}")
    print(f"  Rules skipped: {stats['rules_skipped']}")
    if stats['errors']:
        print(f"  Errors: {len(stats['errors'])}")
        for error in stats['errors']:
            print(f"    - {error}")
    
    if not args.dry_run and stats['rules_created'] > 0:
        print("\n💡 Next steps:")
        print("  1. Update workflows to use database rules:")
        print("     Set 'use_database': true and 'rule_ids': [1, 2, 3] in validate_business_rules config")
        print("  2. Test the rules in a workflow execution")
        print("  3. Once verified, you can archive the JSON file")


if __name__ == "__main__":
    main()
