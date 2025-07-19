#!/usr/bin/env python3
"""
Verification script for ThetaData client integrity
Run this before starting any backtest to ensure the client is intact
"""

import os
import sys
import hashlib
from pathlib import Path

# Critical files that must exist
CRITICAL_FILES = [
    'thetadata_client/__init__.py',
    'thetadata_client/discovery.py',
    'thetadata_client/utils.py',
    'thetadata_client/README.md'
]

# Expected file sizes (approximate, for basic validation)
MIN_FILE_SIZES = {
    'thetadata_client/__init__.py': 1000,  # bytes
    'thetadata_client/discovery.py': 1000,
    'thetadata_client/utils.py': 20000,
    'thetadata_client/README.md': 500
}

def verify_thetadata_client():
    """Verify ThetaData client installation and integrity"""
    
    print("🔍 Verifying ThetaData client integrity...")
    
    errors = []
    
    # Check directory exists
    if not Path('thetadata_client').exists():
        errors.append("❌ CRITICAL: thetadata_client directory is missing!")
        print("\n".join(errors))
        return False
    
    # Check each critical file
    for filepath in CRITICAL_FILES:
        path = Path(filepath)
        
        # Check existence
        if not path.exists():
            errors.append(f"❌ Missing critical file: {filepath}")
            continue
        
        # Check file size
        size = path.stat().st_size
        min_size = MIN_FILE_SIZES.get(filepath, 0)
        if size < min_size:
            errors.append(f"⚠️  File {filepath} seems corrupted (size: {size} bytes)")
    
    # Check if we can import the module
    try:
        import thetadata_client
        print("✅ ThetaData client module can be imported")
    except ImportError as e:
        errors.append(f"❌ Cannot import thetadata_client: {e}")
    
    # Report results
    if errors:
        print("\n🚨 ERRORS FOUND:")
        for error in errors:
            print(f"   {error}")
        print("\n⚠️  The ThetaData client needs to be restored!")
        print("   Check the backup or git history to restore missing files.")
        return False
    else:
        print("✅ All critical files present and valid")
        print("✅ ThetaData client is intact and functional")
        return True

def create_integrity_file():
    """Create a hash file for integrity checking"""
    
    print("\n📝 Creating integrity check file...")
    
    hashes = {}
    for filepath in CRITICAL_FILES:
        path = Path(filepath)
        if path.exists():
            with open(path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                hashes[filepath] = file_hash
    
    # Save hashes
    with open('thetadata_client/.integrity', 'w') as f:
        for filepath, file_hash in hashes.items():
            f.write(f"{filepath}:{file_hash}\n")
    
    print("✅ Integrity file created at thetadata_client/.integrity")

if __name__ == "__main__":
    if "--create-integrity" in sys.argv:
        create_integrity_file()
    else:
        if not verify_thetadata_client():
            print("\n❌ Verification failed!")
            sys.exit(1)
        else:
            print("\n✅ Verification passed!")
            sys.exit(0)