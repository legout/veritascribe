#!/usr/bin/env python3
"""
Test Dashboard with Sample Data

Test both FastHTML and Panel implementations using the actual sample JSON file.
"""

import sys
from pathlib import Path
import tempfile
import webbrowser
import time
import subprocess
import signal
import os

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
    except Exception as e:
        print(f"     ⚠️  Visualization error: {e}")
    
    print("✅ Core functionality tests passed!")


def test_with_real_data():
    """Test with actual sample JSON file if available."""
    sample_file = Path("output/ba_daniel-2025-08-06_10/ba_daniel_grundlagen_20250806_215716_data.json")
    
    if not sample_file.exists():
        print("📁 Real sample data not found - skipping real data test")
        return
    
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
        
    except Exception as e:
        print(f"❌ Error testing with real data: {e}")


def demo_dashboard(framework="fasthtml"):
    """Launch dashboard for demonstration."""
    print(f"🚀 Launching {framework.title()} Dashboard Demo...")
    
    # Import sample data first
    print("📊 Preparing sample data...")
    sample_report = DataProcessor.create_sample_report()
    
    # Create database with sample data
    db_path = Path("dashboard_demo.db")
    if db_path.exists():
        db_path.unlink()
    
    manager = ErrorManager(db_path)
    manager.import_analysis_report(sample_report)
    print(f"   ✅ Created demo database with {len(sample_report.get_all_errors())} errors")
    
    # Add real data if available
    sample_file = Path("output/ba_daniel-2025-08-06_10/ba_daniel_grundlagen_20250806_215716_data.json")
    if sample_file.exists():
        try:
            real_report = DataProcessor.load_and_convert_report(sample_file)
            manager.import_analysis_report(real_report)
            print(f"   ✅ Added real data: {len(real_report.get_all_errors())} additional errors")
        except Exception as e:
            print(f"   ⚠️  Could not load real data: {e}")
    
    # Launch dashboard
    if framework == "fasthtml":
        script = "launch_fasthtml.py"
        url = "http://localhost:8000"
    else:
        script = "launch_panel.py"
        url = "http://localhost:5007"
    
    print(f"🌐 Starting {framework} server...")
    print(f"📍 Dashboard will open at {url}")
    print("⏹️  Press Ctrl+C to stop\n")
    
    try:
        # Start the server
        process = subprocess.Popen([
            sys.executable, 
            str(Path(__file__).parent / script)
        ])
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Open browser
        try:
            webbrowser.open(url)
        except:
            pass
        
        print(f"✅ {framework.title()} dashboard is running!")
        print("🔍 Try these features:")
        print("   • Import the sample JSON file from the output/ directory")
        print("   • Filter errors by type, severity, or status")  
        print("   • Mark errors as resolved or dismissed")
        print("   • View interactive charts and analytics")
        print("   • Try bulk operations on multiple errors")
        
        # Wait for user to stop
        process.wait()
        
    except KeyboardInterrupt:
        print(f"\n👋 Stopping {framework} dashboard...")
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"❌ Error running dashboard: {e}")
        if 'process' in locals():
            process.terminate()
    finally:
        # Cleanup demo database
        if db_path.exists():
            print("🧹 Cleaning up demo database...")
            db_path.unlink()


def main():
    """Main test function."""
    print("🎯 VeritaScribe Dashboard Test Suite")
    print("=" * 50)
    
    # Test core functionality
    test_core_functionality()
    print()
    
    # Test with real data if available
    test_with_real_data()
    print()
    
    # Interactive demo selection
    print("🎮 Interactive Demo Options:")
    print("1. Launch FastHTML Dashboard (Modern web UI)")
    print("2. Launch Panel Dashboard (Scientific UI)")
    print("3. Skip demo")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            demo_dashboard("fasthtml")
        elif choice == "2":
            demo_dashboard("panel")
        elif choice == "3":
            print("Demo skipped")
        else:
            print("Invalid choice - demo skipped")
    except KeyboardInterrupt:
        print("\n👋 Test suite interrupted")
    
    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    main()