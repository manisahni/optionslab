#!/bin/bash
# Comprehensive Backup Script for ThetaData API Project
# Creates timestamped backup including all code and documentation

echo "🗄️ Creating Comprehensive Backup of ThetaData API Project"
echo "=========================================================="

# Create backup directory with timestamp
BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="../thetadata-api-backup-${BACKUP_DATE}"
echo "📁 Creating backup directory: $BACKUP_DIR"

# Create the backup directory
mkdir -p "$BACKUP_DIR"

# Copy all project files (excluding large data files)
echo "📋 Copying project files..."
rsync -av --progress . "$BACKUP_DIR" \
    --exclude='*.parquet' \
    --exclude='spy_options_downloader/spy_options_parquet/' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='.claude/' \
    --exclude='logs/' \
    --exclude='results/' \
    --exclude='*.log' \
    --exclude='*.tmp' \
    --exclude='venv/' \
    --exclude='.venv/' \
    --exclude='.env'

# Create a summary of what was backed up
echo "📊 Creating backup summary..."
cat > "$BACKUP_DIR/BACKUP_SUMMARY.md" << EOF
# ThetaData API Project Backup Summary

**Backup Date:** $(date)
**Backup Location:** $BACKUP_DIR
**Original Location:** $(pwd)

## What's Included:
- ✅ All Python source code
- ✅ ThetaData client library (thetadata_client/)
- ✅ Strategy configurations (YAML files)
- ✅ Documentation and README files
- ✅ Project configuration files
- ✅ Test suites
- ✅ Web interface (Gradio app)
- ✅ Backup and utility scripts

## What's Excluded:
- ❌ Large data files (*.parquet)
- ❌ Git repository (.git/)
- ❌ Log files and temporary files
- ❌ Virtual environments
- ❌ Environment variables (.env)

## Project Structure:
\`\`\`
$(find . -type f -name "*.py" -o -name "*.yaml" -o -name "*.md" -o -name "*.sh" | head -20 | sed 's|^\./||')
... and more files
\`\`\`

## To Restore:
1. Copy this backup to your desired location
2. Run: \`pip install -r requirements.txt\`
3. Run: \`./install_thetadata_client.sh\`
4. Start the system: \`cd optionslab && ./start_auditable.sh\`

## Important Notes:
- This backup contains the complete OptionsLab backtesting system
- The ThetaData client library is included for API integration
- All strategy configurations are preserved
- The web interface (Gradio) is ready to use
- Data files need to be downloaded separately if needed

EOF

# Create a quick restore script
cat > "$BACKUP_DIR/restore.sh" << 'EOF'
#!/bin/bash
# Quick restore script for ThetaData API Project

echo "🔄 Restoring ThetaData API Project..."
echo "====================================="

# Check if we're in the backup directory
if [ ! -f "BACKUP_SUMMARY.md" ]; then
    echo "❌ Error: Please run this script from the backup directory"
    exit 1
fi

# Create target directory
TARGET_DIR="../thetadata-api-restored"
echo "📁 Creating target directory: $TARGET_DIR"

# Copy all files
echo "📋 Copying files..."
cp -r * "$TARGET_DIR/"

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x "$TARGET_DIR"/*.sh
chmod +x "$TARGET_DIR"/optionslab/*.sh

echo "✅ Restore complete!"
echo "📁 Restored to: $TARGET_DIR"
echo ""
echo "Next steps:"
echo "1. cd $TARGET_DIR"
echo "2. pip install -r requirements.txt"
echo "3. ./install_thetadata_client.sh"
echo "4. cd optionslab && ./start_auditable.sh"
EOF

chmod +x "$BACKUP_DIR/restore.sh"

# Create a compressed archive
echo "🗜️ Creating compressed archive..."
tar -czf "${BACKUP_DIR}.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"

# Show backup summary
echo ""
echo "✅ Backup Complete!"
echo "=================="
echo "📁 Backup Directory: $BACKUP_DIR"
echo "🗜️ Compressed Archive: ${BACKUP_DIR}.tar.gz"
echo "📊 Summary: $BACKUP_DIR/BACKUP_SUMMARY.md"
echo "🔄 Restore Script: $BACKUP_DIR/restore.sh"
echo ""
echo "📈 Backup Size:"
du -sh "$BACKUP_DIR"
du -sh "${BACKUP_DIR}.tar.gz"
echo ""
echo "💡 To restore later, run: $BACKUP_DIR/restore.sh"
echo "💡 Or extract: tar -xzf ${BACKUP_DIR}.tar.gz" 