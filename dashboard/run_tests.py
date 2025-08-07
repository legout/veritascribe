#!/usr/bin/env python3
"""
Run Dashboard Tests (Non-interactive)

Test both FastHTML and Panel implementations without user interaction.
"""

import sys
from pathlib import Path
import tempfile

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.data_processor import DataProcessor
from core.error_manager import ErrorManager
from core.visualizations import create_error_summary_chart, create_status_pie_chart

def test_core_functionality():
    """Test core functionality with sample data."""
    print("🧪 Testing Core Functionality...")
    
    # Test 1: Create sample data
    print("  ✅ Creating sample data...")
    sample_report = DataProcessor.create_sample_report()
    print(f"     Created report with {len(sample_report.get_all_errors())} errors")
    
    # Test 2: Database operations
    print("  ✅ Testing database operations...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        manager = ErrorManager(db_path)
        manager.import_analysis_report(sample_report)
        
        errors = manager.get_errors()
        print(f"     Imported {len(errors)} errors to database")
        
        # Test filtering
        from core.models import FilterCriteria, ErrorStatus
        criteria = FilterCriteria(status=[ErrorStatus.PENDING])
        filtered = manager.get_errors(criteria=criteria)
        print(f"     Filtered to {len(filtered)} pending errors")
        
        # Test bulk update
        error_ids = [e.error_id for e in errors[:1]]
        count = manager.bulk_update_errors(error_ids, {"status": ErrorStatus.RESOLVED}, "test")
        print(f"     Updated {count} errors to resolved")
        
        # Test statistics
        stats = manager.get_progress_stats()
        print(f"     Progress: {stats.completion_percentage:.1f}% complete")
        
    finally:
        db_path.unlink()
    
    # Test 3: Visualizations
    print("  ✅ Testing visualizations...")
    errors = sample_report.get_all_errors()
    
    try:
        summary_chart = create_error_summary_chart(errors)
        status_chart = create_status_pie_chart(errors)
        print(f"     Generated {len([summary_chart, status_chart])} charts")
        
        # Test empty data
        empty_chart = create_error_summary_chart([])
        print("     Generated empty chart (fallback)")
        
    except Exception as e:
        print(f"     ❌ Visualization error: {e}")
        return False
    
    print("✅ Core functionality tests passed!")
    return True


def test_with_real_data():
    """Test with actual sample JSON file if available."""
    sample_file = Path("../output/ba_daniel-2025-08-06_10/ba_daniel_grundlagen_20250806_215716_data.json")
    
    if not sample_file.exists():
        print("📁 Real sample data not found - skipping real data test")
        return True
    
    print("📁 Testing with real sample data...")
    
    try:
        # Load real data
        json_data = DataProcessor.load_json_report(sample_file)
        report = DataProcessor.convert_json_to_analysis_report(json_data)
        
        errors = report.get_all_errors()
        print(f"   ✅ Loaded {len(errors)} real errors from {report.document_name}")
        
        # Test import to database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            manager = ErrorManager(db_path)
            manager.import_analysis_report(report)
            print("   ✅ Successfully imported real data to database")
            
            # Show some statistics
            stats = manager.get_progress_stats()
            print(f"      Total errors: {stats.total_errors}")
            print(f"      Error types: {len(set(e.error_type for e in errors))}")
            print(f"      Pages with errors: {len(set(e.location.page_number for e in errors))}")
            
        finally:
            db_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing with real data: {e}")
        return False


def test_framework_imports():
    """Test that both frameworks can be imported."""
    print("🔧 Testing Framework Imports...")
    
    # Test FastHTML import
    try:
        from fasthtml_app.app import app
        print("  ✅ FastHTML app imports successfully")
    except Exception as e:
        print(f"  ❌ FastHTML import error: {e}")
        return False
    
    # Test Panel import
    try:
        from panel_app.app import VeritaScribeDashboard
        print("  ✅ Panel app imports successfully")
    except Exception as e:
        print(f"  ❌ Panel import error: {e}")
        return False
    
    print("✅ Framework import tests passed!")
    return True


def main():
    """Main test function."""
    print("🎯 VeritaScribe Dashboard Test Suite")
    print("=" * 50)
    
    all_passed = True
    
    # Test core functionality
    if not test_core_functionality():
        all_passed = False
    print()
    
    # Test with real data if available
    if not test_with_real_data():
        all_passed = False
    print()
    
    # Test framework imports
    if not test_framework_imports():
        all_passed = False
    print()
    
    if all_passed:
        print("🎉 All tests passed! Dashboard is ready to use.")
        print()
        print("🚀 To start the dashboards:")
        print("   FastHTML: uv run python launch_fasthtml.py")
        print("   Panel:    uv run python launch_panel.py")
        print()
        print("📁 To import your data:")
        print("   1. Start either dashboard")
        print("   2. Go to Import page")
        print("   3. Upload your VeritaScribe JSON report")
        print("   4. Start managing errors!")
    else:
        print("❌ Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()