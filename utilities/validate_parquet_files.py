#!/usr/bin/env python3
"""
Parquet File Validator for SPY Options Data

This script systematically validates all parquet files to identify corruption,
schema inconsistencies, and other issues causing "repetition level histogram size mismatch" errors.
"""

import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
from pathlib import Path
import logging
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import traceback
import glob

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parquet_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ParquetValidator:
    """Validates parquet files for corruption and schema consistency"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.results = {
            'validation_time': datetime.now().isoformat(),
            'total_files': 0,
            'valid_files': 0,
            'corrupted_files': 0,
            'schema_mismatches': 0,
            'file_details': {},
            'common_schema': None,
            'errors': []
        }
    
    def validate_single_file(self, file_path: Path) -> Dict:
        """Validate a single parquet file"""
        result = {
            'file_path': str(file_path),
            'file_size': file_path.stat().st_size if file_path.exists() else 0,
            'is_valid': False,
            'can_read_pandas': False,
            'can_read_pyarrow': False,
            'schema': None,
            'row_count': 0,
            'column_count': 0,
            'error': None,
            'repair_suggestions': []
        }
        
        if not file_path.exists():
            result['error'] = "File does not exist"
            return result
        
        # Test PyArrow reading
        try:
            table = pq.read_table(file_path)
            result['can_read_pyarrow'] = True
            result['schema'] = str(table.schema)
            result['row_count'] = len(table)
            result['column_count'] = len(table.column_names)
            logger.info(f"✅ PyArrow read successful: {file_path.name}")
        except Exception as e:
            result['error'] = f"PyArrow error: {str(e)}"
            logger.error(f"❌ PyArrow failed: {file_path.name} - {e}")
            
            # Try with different PyArrow options
            try:
                table = pq.read_table(file_path, use_legacy_dataset=True)
                result['can_read_pyarrow'] = True
                result['repair_suggestions'].append("Use legacy dataset format")
                logger.info(f"⚠️ PyArrow legacy mode works: {file_path.name}")
            except Exception as e2:
                logger.error(f"❌ PyArrow legacy also failed: {file_path.name} - {e2}")
        
        # Test pandas reading
        try:
            df = pd.read_parquet(file_path, engine='pyarrow')
            result['can_read_pandas'] = True
            if not result['can_read_pyarrow']:  # Update from pandas if PyArrow failed
                result['row_count'] = len(df)
                result['column_count'] = len(df.columns)
            logger.info(f"✅ Pandas read successful: {file_path.name}")
        except Exception as e:
            logger.error(f"❌ Pandas failed: {file_path.name} - {e}")
            if not result['error']:
                result['error'] = f"Pandas error: {str(e)}"
            
            # Try alternative pandas engines
            for engine in ['fastparquet', 'auto']:
                try:
                    df = pd.read_parquet(file_path, engine=engine)
                    result['can_read_pandas'] = True
                    result['repair_suggestions'].append(f"Use pandas engine: {engine}")
                    logger.info(f"⚠️ Pandas {engine} engine works: {file_path.name}")
                    break
                except Exception:
                    continue
        
        # Overall validity
        result['is_valid'] = result['can_read_pandas'] or result['can_read_pyarrow']
        
        return result
    
    def find_parquet_files(self) -> List[Path]:
        """Find all parquet files in the data directory"""
        patterns = [
            "spy_options_eod_*.parquet",
            "**/*.parquet"
        ]
        
        files = []
        for pattern in patterns:
            files.extend(glob.glob(str(self.data_dir / pattern), recursive=True))
        
        return [Path(f) for f in files]
    
    def validate_all_files(self) -> Dict:
        """Validate all parquet files"""
        logger.info(f"🔍 Starting validation of parquet files in {self.data_dir}")
        
        parquet_files = self.find_parquet_files()
        self.results['total_files'] = len(parquet_files)
        
        if not parquet_files:
            logger.warning(f"⚠️ No parquet files found in {self.data_dir}")
            return self.results
        
        logger.info(f"📊 Found {len(parquet_files)} parquet files to validate")
        
        schemas = {}
        
        for i, file_path in enumerate(parquet_files):
            logger.info(f"🔍 Validating {i+1}/{len(parquet_files)}: {file_path.name}")
            
            try:
                result = self.validate_single_file(file_path)
                self.results['file_details'][str(file_path)] = result
                
                if result['is_valid']:
                    self.results['valid_files'] += 1
                    if result['schema']:
                        schema_key = result['schema']
                        schemas[schema_key] = schemas.get(schema_key, 0) + 1
                else:
                    self.results['corrupted_files'] += 1
                    self.results['errors'].append({
                        'file': str(file_path),
                        'error': result['error']
                    })
                
            except Exception as e:
                logger.error(f"❌ Unexpected error validating {file_path.name}: {e}")
                self.results['corrupted_files'] += 1
                self.results['errors'].append({
                    'file': str(file_path),
                    'error': f"Validation exception: {str(e)}"
                })
        
        # Determine most common schema
        if schemas:
            self.results['common_schema'] = max(schemas, key=schemas.get)
            schema_counts = len(schemas)
            if schema_counts > 1:
                self.results['schema_mismatches'] = schema_counts - 1
                logger.warning(f"⚠️ Found {schema_counts} different schemas")
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a detailed validation report"""
        report = []
        report.append("=" * 80)
        report.append("PARQUET FILE VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"Validation Time: {self.results['validation_time']}")
        report.append(f"Data Directory: {self.data_dir}")
        report.append("")
        
        # Summary
        report.append("SUMMARY:")
        report.append(f"  Total Files: {self.results['total_files']}")
        report.append(f"  Valid Files: {self.results['valid_files']}")
        report.append(f"  Corrupted Files: {self.results['corrupted_files']}")
        report.append(f"  Schema Mismatches: {self.results['schema_mismatches']}")
        
        if self.results['total_files'] > 0:
            success_rate = (self.results['valid_files'] / self.results['total_files']) * 100
            report.append(f"  Success Rate: {success_rate:.1f}%")
        
        report.append("")
        
        # Corrupted files details
        if self.results['corrupted_files'] > 0:
            report.append("CORRUPTED FILES:")
            for error in self.results['errors']:
                report.append(f"  ❌ {Path(error['file']).name}: {error['error']}")
            report.append("")
        
        # Repair suggestions
        repair_suggestions = set()
        for file_details in self.results['file_details'].values():
            repair_suggestions.update(file_details.get('repair_suggestions', []))
        
        if repair_suggestions:
            report.append("REPAIR SUGGESTIONS:")
            for suggestion in repair_suggestions:
                report.append(f"  💡 {suggestion}")
            report.append("")
        
        # Schema analysis
        if self.results['schema_mismatches'] > 0:
            report.append("SCHEMA ANALYSIS:")
            report.append("  Multiple schemas detected. Consider standardizing.")
            report.append("")
        
        return "\n".join(report)
    
    def save_results(self, output_file: str = "parquet_validation_results.json"):
        """Save validation results to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"💾 Results saved to {output_file}")

def main():
    """Main validation function"""
    print("🚀 SPY Options Data Parquet Validator")
    print("=" * 50)
    
    # Check multiple possible data directories
    possible_dirs = [
        "spy_options_downloader/spy_options_parquet",
        "/Users/nish_macbook/thetadata-api/spy_options_downloader/spy_options_parquet",
        "data",
        "spy_options_data"
    ]
    
    data_dir = None
    for dir_path in possible_dirs:
        if Path(dir_path).exists():
            data_dir = dir_path
            break
    
    if not data_dir:
        logger.error("❌ Could not find parquet data directory")
        print("\nSearched directories:")
        for dir_path in possible_dirs:
            print(f"  - {dir_path}")
        return
    
    # Run validation
    validator = ParquetValidator(data_dir)
    results = validator.validate_all_files()
    
    # Generate and display report
    report = validator.generate_report()
    print("\n" + report)
    
    # Save results
    validator.save_results()
    
    # Return exit code based on results
    if results['corrupted_files'] > 0:
        logger.error(f"❌ Validation completed with {results['corrupted_files']} corrupted files")
        return 1
    else:
        logger.info("✅ All files validated successfully")
        return 0

if __name__ == "__main__":
    exit(main())