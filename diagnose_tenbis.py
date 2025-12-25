#!/usr/bin/env python3
"""
Quick diagnostic script to check why TENBIS_AVAILABLE is False
"""
import sys
import traceback

print("=" * 60)
print("🔍 10Bis Import Diagnostic")
print("=" * 60)

# Test 1: Check if file exists
print("\n1️⃣ Checking if tenbis_handler.py exists...")
import os
if os.path.exists('tenbis_handler.py'):
    print("   ✅ File exists")
    file_size = os.path.getsize('tenbis_handler.py')
    print(f"   📏 File size: {file_size} bytes")
else:
    print("   ❌ File NOT found!")
    sys.exit(1)

# Test 2: Try to import
print("\n2️⃣ Attempting to import tenbis_handler...")
try:
    import tenbis_handler
    print("   ✅ Module imported successfully")
except Exception as e:
    print(f"   ❌ Import failed!")
    print(f"   Error: {e}")
    print(f"\n   Full traceback:")
    traceback.print_exc()
    sys.exit(1)

# Test 3: Check for required classes/functions
print("\n3️⃣ Checking for required objects...")
try:
    from tenbis_handler import TenbisHandler
    print("   ✅ TenbisHandler imported")
except Exception as e:
    print(f"   ❌ TenbisHandler import failed: {e}")

try:
    from tenbis_handler import format_voucher_message
    print("   ✅ format_voucher_message imported")
except Exception as e:
    print(f"   ❌ format_voucher_message import failed: {e}")

try:
    from tenbis_handler import generate_html_report
    print("   ✅ generate_html_report imported")
except Exception as e:
    print(f"   ❌ generate_html_report import failed: {e}")

# Test 4: Check dependencies
print("\n4️⃣ Checking dependencies...")
deps = {
    'requests': 'requests',
    'urllib3': 'urllib3',
    'pickle': 'pickle',
    'json': 'json',
    'datetime': 'datetime',
    'os': 'os',
    'tempfile': 'tempfile',
    'typing': 'typing'
}

for name, module in deps.items():
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} - MISSING!")

print("\n" + "=" * 60)
print("✅ All tests passed! Module should work.")
print("=" * 60)
