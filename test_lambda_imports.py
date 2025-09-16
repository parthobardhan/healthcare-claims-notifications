#!/usr/bin/env python3
"""Test script to verify Lambda handlers can be imported successfully."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from claims.lambda_handler import lambda_handler as claims_handler
    print("✅ Claims handler imported successfully")
except Exception as e:
    print(f"❌ Failed to import claims handler: {e}")
    sys.exit(1)

try:
    from notify.lambda_handler import lambda_handler as notify_handler
    print("✅ Notify handler imported successfully")
except Exception as e:
    print(f"❌ Failed to import notify handler: {e}")
    sys.exit(1)

print("🎉 All Lambda handlers imported successfully!")
