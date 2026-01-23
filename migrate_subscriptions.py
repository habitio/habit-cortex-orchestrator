#!/usr/bin/env python3
"""
Migrate MQTT subscriptions to event subscriptions.

This script migrates data from the old MQTT structure:
  mqtt_configs -> mqtt_subscriptions
  
To the new simplified structure:
  products -> event_subscriptions
"""

from sqlalchemy import create_engine, text
import os
import sys
import json

def migrate_subscriptions(db_url):
    """Migrate subscriptions from old MQTT tables to new event_subscriptions table."""
    
    engine = create_engine(db_url)
    
    with engine.begin() as conn:
        # 1. Create event_subscriptions table if it doesn't exist
        print("Creating event_subscriptions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_subscriptions (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                event_type VARCHAR(255) NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT true,
                description TEXT,
                actions JSONB DEFAULT '[]'::jsonb,
                messages_received INTEGER NOT NULL DEFAULT 0,
                last_message_at TIMESTAMP,
                actions_executed INTEGER NOT NULL DEFAULT 0,
                actions_failed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_event_subscriptions_product_id ON event_subscriptions(product_id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_event_subscriptions_product_event ON event_subscriptions(product_id, event_type)"))
        
        print("✓ event_subscriptions table ready")
        
        # 2. Get all mqtt_configs and their subscriptions
        print("\nMigrating subscriptions...")
        result = conn.execute(text("""
            SELECT 
                mc.id as mqtt_config_id,
                mc.product_id,
                ms.id as subscription_id,
                ms.name,
                ms.enabled,
                ms.description,
                ms.actions,
                ms.messages_received,
                ms.last_message_at,
                ms.actions_executed,
                ms.actions_failed,
                ms.created_at,
                ms.updated_at
            FROM mqtt_configs mc
            JOIN mqtt_subscriptions ms ON ms.mqtt_config_id = mc.id
            ORDER BY mc.product_id, ms.id
        """))
        
        subscriptions = result.fetchall()
        
        if not subscriptions:
            print("⚠ No subscriptions found to migrate")
            return
        
        print(f"Found {len(subscriptions)} subscriptions to migrate")
        
        # 3. Insert into event_subscriptions
        migrated = 0
        skipped = 0
        
        for sub in subscriptions:
            product_id = sub[1]
            event_type = sub[3]  # Using 'name' as event_type
            enabled = sub[4]
            description = sub[5]
            actions = sub[6] if sub[6] else []
            # Convert actions to JSON string if it's a dict/list
            if isinstance(actions, (dict, list)):
                actions = json.dumps(actions)
            messages_received = sub[7] or 0
            last_message_at = sub[8]
            actions_executed = sub[9] or 0
            actions_failed = sub[10] or 0
            created_at = sub[11]
            updated_at = sub[12]
            
            try:
                # Check if already exists
                check = conn.execute(text("""
                    SELECT id FROM event_subscriptions 
                    WHERE product_id = :product_id AND event_type = :event_type
                """), {
                    "product_id": product_id,
                    "event_type": event_type
                })
                
                if check.fetchone():
                    print(f"  ⚠ Skipping product {product_id}, event '{event_type}' (already exists)")
                    skipped += 1
                    continue
                
                # Insert new subscription
                conn.execute(text("""
                    INSERT INTO event_subscriptions (
                        product_id, event_type, enabled, description, actions,
                        messages_received, last_message_at, actions_executed, actions_failed,
                        created_at, updated_at
                    ) VALUES (
                        :product_id, :event_type, :enabled, :description, :actions,
                        :messages_received, :last_message_at, :actions_executed, :actions_failed,
                        :created_at, :updated_at
                    )
                """), {
                    "product_id": product_id,
                    "event_type": event_type,
                    "enabled": enabled,
                    "description": description,
                    "actions": actions,
                    "messages_received": messages_received,
                    "last_message_at": last_message_at,
                    "actions_executed": actions_executed,
                    "actions_failed": actions_failed,
                    "created_at": created_at,
                    "updated_at": updated_at
                })
                
                print(f"  ✓ Migrated product {product_id}, event '{event_type}'")
                migrated += 1
                
            except Exception as e:
                print(f"  ✗ Failed to migrate product {product_id}, event '{event_type}': {e}")
                raise
        
        print(f"\n✓ Migration complete: {migrated} migrated, {skipped} skipped")
        
        # 4. Show summary
        print("\n=== Summary ===")
        result = conn.execute(text("""
            SELECT product_id, COUNT(*) as subscription_count
            FROM event_subscriptions
            GROUP BY product_id
            ORDER BY product_id
        """))
        
        for row in result.fetchall():
            print(f"  Product {row[0]}: {row[1]} subscriptions")


def main():
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Usage: source .env && python migrate_subscriptions.py")
        sys.exit(1)
    
    print(f"Database: {db_url.split('@')[1] if '@' in db_url else 'configured'}")
    print("=" * 60)
    
    try:
        migrate_subscriptions(db_url)
        print("\n" + "=" * 60)
        print("✓ Migration successful!")
        print("\nNext steps:")
        print("1. Test the new /api/v1/products/{id}/subscriptions endpoints")
        print("2. Verify data in event_subscriptions table")
        print("3. Once confirmed, you can drop old tables:")
        print("   - DROP TABLE mqtt_subscriptions;")
        print("   - DROP TABLE mqtt_connection_status;")
        print("   - DROP TABLE mqtt_configs;")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
