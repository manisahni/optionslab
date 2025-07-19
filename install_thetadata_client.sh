#!/bin/bash
# Install ThetaData client as a development package
# This creates a link to the package, preventing accidental deletion

echo "🔒 Installing ThetaData client as protected package..."
cd thetadata_client
pip install -e .
cd ..

echo "✅ ThetaData client installed as development package"
echo "📍 Location: $(pwd)/thetadata_client"
echo "⚠️  WARNING: This package is now linked to your Python environment"
echo "    Deleting the directory will break imports!"