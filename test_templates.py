#!/usr/bin/env python3
"""
Test script for Template API endpoints.
Tests all CRUD operations for both Email and SMS templates.
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8004"
PRODUCT_ID = 2  # Invoice Protection

# Test data
email_template_data = {
    "name": "Test Payment Confirmation",
    "listmonk_template_id": 42,
    "description": "Test email template for payment confirmation",
    "template_type": "transactional",
    "available_variables": ["customer_name", "policy_number", "amount"]
}

sms_template_data = {
    "name": "Test Policy Reminder",
    "message": "Your policy {{policy_number}} expires on {{expiry_date}}. Renew at {{link}}",
    "description": "Test SMS template for policy reminder",
    "template_type": "notification",
    "available_variables": ["policy_number", "expiry_date", "link"]
}

def print_test(name):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

def print_response(response):
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

# Session for auth (would need actual login in production)
session = requests.Session()

# ============================================
# EMAIL TEMPLATE TESTS
# ============================================

print_test("1. List Email Templates (Empty)")
response = session.get(f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email")
print_response(response)

print_test("2. Create Email Template")
response = session.post(
    f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email",
    json=email_template_data
)
print_response(response)
email_template_id = response.json().get("id") if response.status_code == 201 else None

if email_template_id:
    print_test("3. Get Single Email Template")
    response = session.get(
        f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email/{email_template_id}"
    )
    print_response(response)

    print_test("4. Update Email Template")
    update_data = {
        "description": "Updated description for payment confirmation",
        "available_variables": ["customer_name", "policy_number", "amount", "date"]
    }
    response = session.put(
        f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email/{email_template_id}",
        json=update_data
    )
    print_response(response)

    print_test("5. List Email Templates (Should have 1)")
    response = session.get(f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email")
    print_response(response)

# ============================================
# SMS TEMPLATE TESTS
# ============================================

print_test("6. List SMS Templates (Empty)")
response = session.get(f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/sms")
print_response(response)

print_test("7. Create SMS Template")
response = session.post(
    f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/sms",
    json=sms_template_data
)
print_response(response)
sms_template_id = response.json().get("id") if response.status_code == 201 else None

if sms_template_id:
    print_test("8. Get Single SMS Template")
    response = session.get(
        f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/sms/{sms_template_id}"
    )
    print_response(response)

    print_test("9. Update SMS Template")
    update_data = {
        "message": "UPDATED: Policy {{policy_number}} expires {{expiry_date}}",
        "description": "Updated SMS reminder"
    }
    response = session.put(
        f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/sms/{sms_template_id}",
        json=update_data
    )
    print_response(response)

    print_test("10. List SMS Templates (Should have 1)")
    response = session.get(f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/sms")
    print_response(response)

# ============================================
# ERROR HANDLING TESTS
# ============================================

print_test("11. Duplicate Email Template Name (Should Fail)")
response = session.post(
    f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email",
    json=email_template_data  # Same name as first one
)
print_response(response)

print_test("12. Get Non-existent Email Template (Should Fail)")
response = session.get(
    f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email/99999"
)
print_response(response)

# ============================================
# CLEANUP (DELETE TESTS)
# ============================================

if email_template_id:
    print_test("13. Delete Email Template")
    response = session.delete(
        f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email/{email_template_id}"
    )
    print(f"Status: {response.status_code}")
    print("Response: (empty for 204 No Content)")

if sms_template_id:
    print_test("14. Delete SMS Template")
    response = session.delete(
        f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/sms/{sms_template_id}"
    )
    print(f"Status: {response.status_code}")
    print("Response: (empty for 204 No Content)")

print_test("15. Final Count - Should be Empty")
email_count = session.get(f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/email").json()
sms_count = session.get(f"{BASE_URL}/api/v1/products/{PRODUCT_ID}/templates/sms").json()
print(f"Email Templates: {len(email_count)}")
print(f"SMS Templates: {len(sms_count)}")

print("\n" + "="*60)
print("ALL TESTS COMPLETED!")
print("="*60)
