#!/bin/bash
# Script to help push to remote repository

echo "📤 Push to Remote Repository Helper"
echo "==================================="
echo ""

# Check if remote is already configured
if git remote | grep -q "origin"; then
    echo "✅ Remote 'origin' already configured:"
    git remote get-url origin
    echo ""
    read -p "Push to this remote? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Pushing to origin..."
        git push -u origin main
        echo "✅ Push complete!"
    fi
else
    echo "❌ No remote repository configured yet!"
    echo ""
    echo "📝 Instructions:"
    echo "1. Go to GitHub.com and create a new repository"
    echo "2. Name it: thetadata-api"
    echo "3. Set as Private (recommended)"
    echo "4. DON'T initialize with any files"
    echo ""
    echo "Then run these commands:"
    echo ""
    echo "git remote add origin https://github.com/YOUR_USERNAME/thetadata-api.git"
    echo "git push -u origin main"
    echo ""
    echo "Or for SSH (if configured):"
    echo "git remote add origin git@github.com:YOUR_USERNAME/thetadata-api.git"
    echo "git push -u origin main"
fi

echo ""
echo "💡 Tip: For automatic backups, consider setting up GitHub Actions!"