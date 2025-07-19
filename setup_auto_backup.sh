#!/bin/bash
# Setup automatic backup to remote repository

echo "🔄 Setting Up Automatic Backup"
echo "=============================="
echo ""

# Create a git hook for automatic push after each commit
cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
# Automatically push to remote after each commit

# Check if remote exists
if git remote | grep -q "origin"; then
    echo "📤 Auto-pushing to remote..."
    git push origin main --quiet &
    echo "✅ Auto-push initiated in background"
fi
EOF

chmod +x .git/hooks/post-commit

echo "✅ Automatic backup configured!"
echo ""
echo "Now every time you commit locally, it will automatically:"
echo "- Push to your remote repository in the background"
echo "- Keep your remote always up-to-date"
echo ""
echo "To disable: rm .git/hooks/post-commit"