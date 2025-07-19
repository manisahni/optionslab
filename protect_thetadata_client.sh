#!/bin/bash
# OS-level protection for ThetaData client directory

echo "🔒 Setting up OS-level protection for ThetaData client..."

# Make files immutable (requires sudo on macOS)
echo "⚠️  This script will make the ThetaData client files harder to delete."
echo "    You'll need sudo privileges to remove the protection later."
echo ""
read -p "Do you want to continue? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Set immutable flag on critical files (macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "🍎 Detected macOS - setting immutable flags..."
        sudo chflags uchg thetadata_client/*.py
        sudo chflags uchg thetadata_client/README.md
        echo "✅ Files are now protected with immutable flag"
        echo "📝 To remove protection later, run: sudo chflags nouchg thetadata_client/*"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "🐧 Detected Linux - setting immutable attribute..."
        sudo chattr +i thetadata_client/*.py
        sudo chattr +i thetadata_client/README.md
        echo "✅ Files are now protected with immutable attribute"
        echo "📝 To remove protection later, run: sudo chattr -i thetadata_client/*"
    else
        echo "⚠️  Unsupported OS: $OSTYPE"
        echo "    Manual protection recommended"
    fi
else
    echo "❌ Protection cancelled"
fi