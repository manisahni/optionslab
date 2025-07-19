# ThetaData Client Recovery Guide

If the ThetaData client files are missing or corrupted, here's how to recover:

## Quick Recovery Options

### 1. From Git History (Easiest)
```bash
# View the client files in git history
git log --oneline -- thetadata_client/

# Restore all client files from last commit
git checkout HEAD -- thetadata_client/

# Or restore from specific commit
git checkout <commit-hash> -- thetadata_client/
```

### 2. From Backup
If you ran the backup command earlier:
```bash
cp -r ../thetadata-client-backup/* thetadata_client/
```

### 3. Manual Recovery
The essential files are:
- `__init__.py` - Package initialization
- `utils.py` - Main functionality (34KB)
- `discovery.py` - Option discovery (2.7KB)

## What Still Works Without ThetaData Client

Even if the ThetaData client is missing, you can still:
- ✅ Run backtests on existing parquet files
- ✅ Use all strategy features
- ✅ Export results
- ✅ Create visualizations

What won't work:
- ❌ Downloading new data from ThetaData
- ❌ Real-time data functions
- ❌ Option discovery features

## Verification

To check if recovery was successful:
```bash
python verify_thetadata_client.py
```

## Prevention

To prevent future issues:
1. Run `./install_thetadata_client.sh` to install as package
2. Keep regular git commits
3. Consider the optional OS-level protection