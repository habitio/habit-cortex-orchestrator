"""
Migration: Add MQTT configuration tables

Creates tables for MQTT broker configuration, subscriptions, and connection status.

Run with:
    python -m orchestrator.database.migrations.add_mqtt_config
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from orchestrator.database.session import engine
from orchestrator.database.models import MQTTConfig, MQTTSubscription, MQTTConnectionStatus

def migrate():
    """Create MQTT configuration tables."""
    print("Creating MQTT configuration tables...")
    
    # Create only MQTT tables (others already exist)
    MQTTConfig.__table__.create(engine, checkfirst=True)
    MQTTSubscription.__table__.create(engine, checkfirst=True)
    MQTTConnectionStatus.__table__.create(engine, checkfirst=True)
    
    print("✓ MQTT tables created successfully")
    print("\nTables created:")
    print("  - mqtt_configs")
    print("  - mqtt_subscriptions")
    print("  - mqtt_connection_status")

if __name__ == "__main__":
    migrate()
