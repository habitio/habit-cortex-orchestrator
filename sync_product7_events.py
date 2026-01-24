#!/usr/bin/env python3
"""
Sync MQTT event configuration from instance to orchestrator for product 7.

This script reads the mqtt_events.json from the instance and updates the 
orchestrator database to match the configuration.
"""

import json
import psycopg2
from datetime import datetime

# Database connection
DB_URL = "postgresql://habit-bre-cortex-orchestrator:uiyiuyi65577yuyuyYTT@localhost:5432/habit-bre-cortex-orchestrator"
PRODUCT_ID = 7

# Read instance configuration
MQTT_EVENTS_PATH = "../cortex-instance/src/bre_payments/config/mqtt_events.json"

def main():
    print(f"🔄 Syncing MQTT events configuration for product {PRODUCT_ID}")
    print(f"📄 Reading from: {MQTT_EVENTS_PATH}")
    
    # Load configuration
    with open(MQTT_EVENTS_PATH, 'r') as f:
        config = json.load(f)
    
    events = config.get('events', [])
    print(f"✓ Found {len(events)} event configurations")
    
    # Connect to database
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # Get existing subscriptions
        cur.execute("""
            SELECT id, event_type, actions 
            FROM event_subscriptions 
            WHERE product_id = %s
        """, (PRODUCT_ID,))
        
        existing = {row[1]: {'id': row[0], 'actions': row[2]} for row in cur.fetchall()}
        print(f"✓ Found {len(existing)} existing subscriptions in database")
        
        updated_count = 0
        created_count = 0
        
        for event in events:
            event_type = event['name']
            description = event.get('description', '')
            enabled = event['enabled']
            actions = event.get('actions', [])
            
            # Check if subscription exists
            if event_type in existing:
                sub_id = existing[event_type]['id']
                
                # Update existing subscription
                cur.execute("""
                    UPDATE event_subscriptions 
                    SET 
                        description = %s,
                        enabled = %s,
                        actions = %s,
                        updated_at = %s
                    WHERE id = %s
                """, (
                    description,
                    enabled,
                    json.dumps(actions),
                    datetime.now(),
                    sub_id
                ))
                
                print(f"✓ Updated subscription {sub_id}: {event_type} ({len(actions)} actions)")
                updated_count += 1
            else:
                # Create new subscription
                cur.execute("""
                    INSERT INTO event_subscriptions 
                        (product_id, event_type, description, enabled, actions, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    PRODUCT_ID,
                    event_type,
                    description,
                    enabled,
                    json.dumps(actions),
                    datetime.now(),
                    datetime.now()
                ))
                
                new_id = cur.fetchone()[0]
                print(f"✓ Created subscription {new_id}: {event_type} ({len(actions)} actions)")
                created_count += 1
        
        # Commit changes
        conn.commit()
        
        print(f"\n✅ Sync complete!")
        print(f"   • Created: {created_count} subscriptions")
        print(f"   • Updated: {updated_count} subscriptions")
        print(f"   • Total:   {len(events)} event types configured")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
