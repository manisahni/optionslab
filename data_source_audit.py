#!/usr/bin/env python3
"""
Data Source Audit Tool

This tool audits all existing data sources and storage formats across the 
backtesting system to identify inconsistencies and create migration mappings.
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import hashlib
from dataclasses import dataclass, asdict
import pickle

@dataclass
class DataSource:
    """Information about a data source."""
    name: str
    location: Path
    format_type: str  # 'csv', 'json', 'parquet', 'pickle', 'other'
    file_count: int
    total_size_mb: float
    sample_files: List[str]
    schema_info: Dict[str, Any]
    last_modified: datetime
    notes: str = ""

@dataclass
class DataSourceAuditResult:
    """Complete audit result."""
    audit_timestamp: datetime
    sources_found: List[DataSource]
    inconsistencies: List[Dict[str, Any]]
    migration_recommendations: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]

class DataSourceAuditor:
    """
    Audits all data sources in the backtesting system to identify:
    - Different storage formats and locations
    - Schema inconsistencies 
    - Data duplication
    - Migration requirements
    """
    
    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = Path(base_dir)
        self.logger = self._setup_logging()
        
        # Known data source patterns
        self.data_patterns = {
            'cli_results': {
                'paths': ['spy_backtester/results', 'results'],
                'patterns': ['*.csv', '*.json', '*backtest*'],
                'expected_format': 'csv'
            },
            'streamlit_results': {
                'paths': ['streamlit-backtester/backtest_results', 'backtest_results'],
                'patterns': ['*.json'],
                'expected_format': 'json'
            },
            'streamlit_temp_logs': {
                'paths': ['streamlit-backtester/tmp_trade_logs', 'tmp_trade_logs'],
                'patterns': ['*.csv', '*.log'],
                'expected_format': 'csv'
            },
            'enhanced_logs': {
                'paths': ['streamlit-backtester/trade_logs', 'trade_logs'],
                'patterns': ['*.json', '*.pickle'],
                'expected_format': 'json'
            },
            'unified_results': {
                'paths': ['results/unified', 'unified_results'],
                'patterns': ['*.json', '*.json.gz'],
                'expected_format': 'json'
            },
            'legacy_backups': {
                'paths': ['results/backups', 'backups', 'backup_results'],
                'patterns': ['*backup*', '*legacy*'],
                'expected_format': 'various'
            },
            'parquet_data': {
                'paths': ['spy_options_downloader/spy_options_parquet', 'data/parquet'],
                'patterns': ['*.parquet'],
                'expected_format': 'parquet'
            }
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the auditor."""
        logger = logging.getLogger('DataSourceAuditor')
        logger.setLevel(logging.INFO)
        
        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _get_directory_size(self, directory: Path) -> float:
        """Get directory size in MB."""
        try:
            total_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
            return total_size / (1024 * 1024)
        except Exception:
            return 0.0
    
    def _analyze_file_schema(self, file_path: Path) -> Dict[str, Any]:
        """Analyze the schema/structure of a file."""
        schema_info = {
            'columns': [],
            'data_types': {},
            'sample_data': {},
            'row_count': 0,
            'format_details': {}
        }
        
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, nrows=100)  # Sample first 100 rows
                schema_info['columns'] = df.columns.tolist()
                schema_info['data_types'] = df.dtypes.astype(str).to_dict()
                schema_info['row_count'] = len(pd.read_csv(file_path))
                if not df.empty:
                    schema_info['sample_data'] = df.head(3).to_dict('records')
                    
            elif file_path.suffix.lower() == '.json':
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    schema_info['columns'] = list(data.keys())
                    schema_info['format_details'] = {
                        'type': 'object',
                        'keys': list(data.keys())[:10]  # First 10 keys
                    }
                elif isinstance(data, list) and data:
                    if isinstance(data[0], dict):
                        schema_info['columns'] = list(data[0].keys())
                        schema_info['row_count'] = len(data)
                        schema_info['sample_data'] = data[:3]
                        
            elif file_path.suffix.lower() == '.parquet':
                df = pd.read_parquet(file_path, engine='fastparquet')
                schema_info['columns'] = df.columns.tolist()
                schema_info['data_types'] = df.dtypes.asdict(str).to_dict()
                schema_info['row_count'] = len(df)
                if not df.empty:
                    schema_info['sample_data'] = df.head(3).to_dict('records')
                    
        except Exception as e:
            schema_info['error'] = str(e)
            
        return schema_info
    
    def _scan_data_source(self, source_name: str, config: Dict[str, Any]) -> Optional[DataSource]:
        """Scan a specific data source."""
        self.logger.info(f"Scanning data source: {source_name}")
        
        # Find the actual directory
        actual_path = None
        for potential_path in config['paths']:
            full_path = self.base_dir / potential_path
            if full_path.exists():
                actual_path = full_path
                break
        
        if not actual_path:
            self.logger.debug(f"No directory found for {source_name}")
            return None
        
        # Collect files matching patterns
        all_files = []
        for pattern in config['patterns']:
            all_files.extend(actual_path.rglob(pattern))
        
        if not all_files:
            self.logger.debug(f"No files found for {source_name}")
            return None
        
        # Sample files for analysis
        sample_files = all_files[:5] if len(all_files) > 5 else all_files
        sample_file_names = [f.name for f in sample_files]
        
        # Analyze schema of first valid file
        schema_info = {}
        for file_path in sample_files:
            if file_path.is_file():
                schema_info = self._analyze_file_schema(file_path)
                if 'error' not in schema_info:
                    break
        
        # Get last modified time
        try:
            last_modified = max(f.stat().st_mtime for f in all_files if f.is_file())
            last_modified = datetime.fromtimestamp(last_modified)
        except:
            last_modified = datetime.now()
        
        return DataSource(
            name=source_name,
            location=actual_path,
            format_type=config['expected_format'],
            file_count=len(all_files),
            total_size_mb=self._get_directory_size(actual_path),
            sample_files=sample_file_names,
            schema_info=schema_info,
            last_modified=last_modified
        )
    
    def _detect_inconsistencies(self, sources: List[DataSource]) -> List[Dict[str, Any]]:
        """Detect inconsistencies between data sources."""
        inconsistencies = []
        
        # Group sources that should have similar schemas
        result_sources = [s for s in sources if 'result' in s.name]
        
        if len(result_sources) > 1:
            # Compare schemas between result sources
            base_schema = result_sources[0].schema_info.get('columns', [])
            base_name = result_sources[0].name
            
            for source in result_sources[1:]:
                source_schema = source.schema_info.get('columns', [])
                
                # Check for missing columns
                missing_in_source = set(base_schema) - set(source_schema)
                extra_in_source = set(source_schema) - set(base_schema)
                
                if missing_in_source or extra_in_source:
                    inconsistencies.append({
                        'type': 'schema_mismatch',
                        'source1': base_name,
                        'source2': source.name,
                        'missing_columns': list(missing_in_source),
                        'extra_columns': list(extra_in_source),
                        'severity': 'high' if len(missing_in_source) > 5 else 'medium'
                    })
        
        # Check for duplicate data (similar file counts in different locations)
        for i, source1 in enumerate(sources):
            for source2 in sources[i+1:]:
                if (source1.file_count == source2.file_count and 
                    source1.file_count > 0 and
                    abs(source1.total_size_mb - source2.total_size_mb) < 1.0):
                    
                    inconsistencies.append({
                        'type': 'potential_duplicate',
                        'source1': source1.name,
                        'source2': source2.name,
                        'file_count': source1.file_count,
                        'size_diff_mb': abs(source1.total_size_mb - source2.total_size_mb),
                        'severity': 'medium'
                    })
        
        # Check for very old data
        cutoff_date = datetime.now().replace(month=datetime.now().month-6)  # 6 months ago
        for source in sources:
            if source.last_modified < cutoff_date and source.file_count > 0:
                inconsistencies.append({
                    'type': 'stale_data',
                    'source': source.name,
                    'last_modified': source.last_modified.isoformat(),
                    'age_days': (datetime.now() - source.last_modified).days,
                    'severity': 'low'
                })
        
        return inconsistencies
    
    def _generate_migration_recommendations(self, sources: List[DataSource], 
                                          inconsistencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate migration recommendations."""
        recommendations = []
        
        # Recommend unified storage for all result sources
        result_sources = [s for s in sources if 'result' in s.name and s.file_count > 0]
        if len(result_sources) > 1:
            recommendations.append({
                'type': 'unify_storage',
                'description': 'Migrate all result sources to unified format',
                'affected_sources': [s.name for s in result_sources],
                'target_format': 'unified_json',
                'estimated_effort': 'medium',
                'priority': 'high'
            })
        
        # Recommend cleanup for stale data
        stale_sources = [s for s in sources if any(
            i['type'] == 'stale_data' and i['source'] == s.name 
            for i in inconsistencies
        )]
        if stale_sources:
            recommendations.append({
                'type': 'cleanup_stale',
                'description': 'Archive or remove stale data sources',
                'affected_sources': [s.name for s in stale_sources],
                'estimated_effort': 'low',
                'priority': 'medium'
            })
        
        # Recommend deduplication
        duplicate_pairs = [i for i in inconsistencies if i['type'] == 'potential_duplicate']
        if duplicate_pairs:
            recommendations.append({
                'type': 'deduplicate',
                'description': 'Resolve duplicate data sources',
                'affected_pairs': [(i['source1'], i['source2']) for i in duplicate_pairs],
                'estimated_effort': 'medium',
                'priority': 'medium'
            })
        
        # Recommend schema standardization
        schema_mismatches = [i for i in inconsistencies if i['type'] == 'schema_mismatch']
        if schema_mismatches:
            recommendations.append({
                'type': 'standardize_schema',
                'description': 'Standardize schemas across result sources',
                'affected_sources': list(set([i['source1'] for i in schema_mismatches] + 
                                           [i['source2'] for i in schema_mismatches])),
                'estimated_effort': 'high',
                'priority': 'high'
            })
        
        return recommendations
    
    def run_audit(self) -> DataSourceAuditResult:
        """Run complete data source audit."""
        self.logger.info("Starting data source audit...")
        
        sources_found = []
        
        # Scan all known data source patterns
        for source_name, config in self.data_patterns.items():
            source = self._scan_data_source(source_name, config)
            if source:
                sources_found.append(source)
        
        # Detect inconsistencies
        inconsistencies = self._detect_inconsistencies(sources_found)
        
        # Generate recommendations
        recommendations = self._generate_migration_recommendations(sources_found, inconsistencies)
        
        # Calculate summary statistics
        total_files = sum(s.file_count for s in sources_found)
        total_size_mb = sum(s.total_size_mb for s in sources_found)
        
        summary_stats = {
            'total_sources': len(sources_found),
            'total_files': total_files,
            'total_size_mb': total_size_mb,
            'sources_with_data': len([s for s in sources_found if s.file_count > 0]),
            'inconsistencies_found': len(inconsistencies),
            'high_priority_issues': len([i for i in inconsistencies if i.get('severity') == 'high']),
            'recommendations_count': len(recommendations)
        }
        
        audit_result = DataSourceAuditResult(
            audit_timestamp=datetime.now(),
            sources_found=sources_found,
            inconsistencies=inconsistencies,
            migration_recommendations=recommendations,
            summary_stats=summary_stats
        )
        
        self.logger.info(f"Audit complete: Found {len(sources_found)} sources, "
                        f"{len(inconsistencies)} inconsistencies, {len(recommendations)} recommendations")
        
        return audit_result
    
    def generate_report(self, audit_result: DataSourceAuditResult, 
                       output_file: Optional[Path] = None) -> str:
        """Generate detailed audit report."""
        
        if output_file is None:
            timestamp = audit_result.audit_timestamp.strftime('%Y%m%d_%H%M%S')
            output_file = self.base_dir / f"data_source_audit_{timestamp}.md"
        
        report_lines = []
        
        # Header
        report_lines.extend([
            "# Data Source Audit Report",
            f"Generated: {audit_result.audit_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            ""
        ])
        
        # Summary statistics
        stats = audit_result.summary_stats
        report_lines.extend([
            f"- **Total Sources Found**: {stats['total_sources']}",
            f"- **Sources with Data**: {stats['sources_with_data']}",
            f"- **Total Files**: {stats['total_files']:,}",
            f"- **Total Storage**: {stats['total_size_mb']:.2f} MB",
            f"- **Inconsistencies**: {stats['inconsistencies_found']}",
            f"- **High Priority Issues**: {stats['high_priority_issues']}",
            f"- **Recommendations**: {stats['recommendations_count']}",
            ""
        ])
        
        # Data sources detail
        report_lines.extend([
            "## Data Sources Found",
            ""
        ])
        
        for source in audit_result.sources_found:
            report_lines.extend([
                f"### {source.name}",
                f"- **Location**: `{source.location}`",
                f"- **Format**: {source.format_type}",
                f"- **Files**: {source.file_count}",
                f"- **Size**: {source.total_size_mb:.2f} MB",
                f"- **Last Modified**: {source.last_modified.strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ])
            
            # Schema info
            if source.schema_info.get('columns'):
                columns = source.schema_info['columns']
                if len(columns) <= 10:
                    report_lines.append(f"- **Columns**: {', '.join(columns)}")
                else:
                    report_lines.append(f"- **Columns**: {len(columns)} columns ({', '.join(columns[:5])}, ...)")
                report_lines.append("")
            
            # Sample files
            if source.sample_files:
                report_lines.append("- **Sample Files**:")
                for sample_file in source.sample_files[:3]:
                    report_lines.append(f"  - `{sample_file}`")
                report_lines.append("")
        
        # Inconsistencies
        if audit_result.inconsistencies:
            report_lines.extend([
                "## Inconsistencies Found",
                ""
            ])
            
            for i, inconsistency in enumerate(audit_result.inconsistencies, 1):
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(inconsistency.get('severity', 'low'), "⚪")
                report_lines.extend([
                    f"### {i}. {inconsistency['type'].title().replace('_', ' ')} {severity_emoji}",
                    ""
                ])
                
                if inconsistency['type'] == 'schema_mismatch':
                    report_lines.extend([
                        f"- **Sources**: {inconsistency['source1']} vs {inconsistency['source2']}",
                        f"- **Missing Columns**: {inconsistency['missing_columns']}",
                        f"- **Extra Columns**: {inconsistency['extra_columns']}",
                        ""
                    ])
                elif inconsistency['type'] == 'potential_duplicate':
                    report_lines.extend([
                        f"- **Sources**: {inconsistency['source1']} and {inconsistency['source2']}",
                        f"- **File Count**: {inconsistency['file_count']}",
                        f"- **Size Difference**: {inconsistency['size_diff_mb']:.2f} MB",
                        ""
                    ])
                elif inconsistency['type'] == 'stale_data':
                    report_lines.extend([
                        f"- **Source**: {inconsistency['source']}",
                        f"- **Age**: {inconsistency['age_days']} days",
                        f"- **Last Modified**: {inconsistency['last_modified']}",
                        ""
                    ])
        
        # Recommendations
        if audit_result.migration_recommendations:
            report_lines.extend([
                "## Migration Recommendations",
                ""
            ])
            
            for i, rec in enumerate(audit_result.migration_recommendations, 1):
                priority_emoji = {"high": "🔥", "medium": "⚡", "low": "💡"}[rec['priority']]
                effort_emoji = {"high": "⏰", "medium": "⌚", "low": "⏱️"}[rec['estimated_effort']]
                
                report_lines.extend([
                    f"### {i}. {rec['type'].title().replace('_', ' ')} {priority_emoji} {effort_emoji}",
                    f"{rec['description']}",
                    ""
                ])
                
                if 'affected_sources' in rec:
                    report_lines.append(f"**Affected Sources**: {', '.join(rec['affected_sources'])}")
                if 'affected_pairs' in rec:
                    pairs_str = ', '.join([f"({p[0]} & {p[1]})" for p in rec['affected_pairs']])
                    report_lines.append(f"**Affected Pairs**: {pairs_str}")
                if 'target_format' in rec:
                    report_lines.append(f"**Target Format**: {rec['target_format']}")
                
                report_lines.extend(["", ""])
        
        # Action items
        report_lines.extend([
            "## Next Steps",
            "",
            "1. **Immediate**: Address high-priority inconsistencies",
            "2. **Short-term**: Implement unified storage format",
            "3. **Medium-term**: Migrate all legacy data sources",
            "4. **Long-term**: Establish automated consistency monitoring",
            ""
        ])
        
        # Write report
        report_content = "\n".join(report_lines)
        with open(output_file, 'w') as f:
            f.write(report_content)
        
        return str(output_file)
    
    def save_audit_data(self, audit_result: DataSourceAuditResult,
                       output_file: Optional[Path] = None) -> str:
        """Save audit data as JSON for programmatic use."""
        
        if output_file is None:
            timestamp = audit_result.audit_timestamp.strftime('%Y%m%d_%H%M%S')
            output_file = self.base_dir / f"data_source_audit_{timestamp}.json"
        
        # Convert to serializable format
        audit_data = {
            'audit_timestamp': audit_result.audit_timestamp.isoformat(),
            'sources_found': [asdict(source) for source in audit_result.sources_found],
            'inconsistencies': audit_result.inconsistencies,
            'migration_recommendations': audit_result.migration_recommendations,
            'summary_stats': audit_result.summary_stats
        }
        
        # Convert Path objects to strings
        for source_data in audit_data['sources_found']:
            source_data['location'] = str(source_data['location'])
            source_data['last_modified'] = source_data['last_modified'].isoformat()
        
        with open(output_file, 'w') as f:
            json.dump(audit_data, f, indent=2, default=str)
        
        return str(output_file)


def create_migration_mapping(audit_result: DataSourceAuditResult) -> Dict[str, Any]:
    """Create detailed migration mapping from audit results."""
    
    mapping = {
        'migration_plan': {
            'phase1_immediate': [],
            'phase2_unification': [],
            'phase3_cleanup': []
        },
        'source_mapping': {},
        'schema_transformations': {},
        'data_flows': []
    }
    
    # Map each source to migration phase
    for source in audit_result.sources_found:
        source_info = {
            'name': source.name,
            'current_location': str(source.location),
            'current_format': source.format_type,
            'file_count': source.file_count,
            'priority': 'high' if 'result' in source.name else 'medium'
        }
        
        # Assign to migration phase based on source type
        if 'result' in source.name and source.file_count > 0:
            mapping['migration_plan']['phase2_unification'].append(source_info)
        elif source.file_count == 0 or 'temp' in source.name:
            mapping['migration_plan']['phase3_cleanup'].append(source_info)
        else:
            mapping['migration_plan']['phase1_immediate'].append(source_info)
        
        # Create source mapping
        mapping['source_mapping'][source.name] = {
            'source_path': str(source.location),
            'target_path': f"results/unified/{source.name}",
            'transformation_required': source.format_type != 'json',
            'schema': source.schema_info.get('columns', [])
        }
    
    return mapping


if __name__ == "__main__":
    # Run data source audit
    print("🔍 Starting Data Source Audit...")
    
    auditor = DataSourceAuditor()
    audit_result = auditor.run_audit()
    
    # Generate reports
    report_file = auditor.generate_report(audit_result)
    data_file = auditor.save_audit_data(audit_result)
    
    # Create migration mapping
    migration_mapping = create_migration_mapping(audit_result)
    
    # Save migration mapping
    mapping_file = Path("migration_mapping.json")
    with open(mapping_file, 'w') as f:
        json.dump(migration_mapping, f, indent=2, default=str)
    
    # Print summary
    stats = audit_result.summary_stats
    print(f"\n📊 Audit Summary:")
    print(f"   Sources Found: {stats['total_sources']}")
    print(f"   Total Files: {stats['total_files']:,}")
    print(f"   Total Size: {stats['total_size_mb']:.1f} MB")
    print(f"   Inconsistencies: {stats['inconsistencies_found']}")
    print(f"   Recommendations: {stats['recommendations_count']}")
    
    print(f"\n📄 Reports Generated:")
    print(f"   Audit Report: {report_file}")
    print(f"   Audit Data: {data_file}")
    print(f"   Migration Mapping: {mapping_file}")
    
    print("\n✅ Data Source Audit Complete!")
    
    # Show sample of findings
    if audit_result.sources_found:
        print(f"\n📁 Sample Sources Found:")
        for source in audit_result.sources_found[:3]:
            print(f"   {source.name}: {source.file_count} files, {source.total_size_mb:.1f} MB")
    
    if audit_result.inconsistencies:
        print(f"\n⚠️  Sample Inconsistencies:")
        for issue in audit_result.inconsistencies[:2]:
            print(f"   {issue['type']}: {issue.get('severity', 'unknown')} severity")