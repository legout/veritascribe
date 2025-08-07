"""
Test suite for VeritaScribe Dashboard

Tests both FastHTML and Panel implementations with sample data.
"""

import sys
from pathlib import Path
import tempfile
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.data_processor import DataProcessor
from core.error_manager import ErrorManager
from core.models import ErrorType, Severity, ErrorStatus
from core.visualizations import *


class TestDataProcessor:
    """Test data processing utilities."""
    
    def test_create_sample_report(self):
        """Test sample report creation."""
        report = DataProcessor.create_sample_report()
        
        assert report.document_name == "Sample Thesis.pdf"
        assert report.total_pages == 25
        assert len(report.analysis_results) == 1
        assert len(report.get_all_errors()) == 2
        
        # Check error types
        errors = report.get_all_errors()
        assert any(e.error_type == ErrorType.CITATION_FORMAT for e in errors)
        assert any(e.error_type == ErrorType.GRAMMAR for e in errors)
    
    def test_json_conversion(self):
        """Test JSON import/export functionality."""
        # Create sample report
        original_report = DataProcessor.create_sample_report()
        
        # Export to JSON
        json_data = DataProcessor.export_report_to_json(original_report)
        
        # Validate JSON structure
        assert "document_name" in json_data
        assert "analysis_results" in json_data
        assert "document_stats" in json_data
        assert "progress_stats" in json_data
        
        # Convert back to report
        converted_report = DataProcessor.convert_json_to_analysis_report(json_data)
        
        # Validate conversion
        assert converted_report.document_name == original_report.document_name
        assert converted_report.total_pages == original_report.total_pages
        assert len(converted_report.get_all_errors()) == len(original_report.get_all_errors())


class TestErrorManager:
    """Test error management functionality."""
    
    @pytest.fixture
    def temp_db_manager(self):
        """Create temporary error manager for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        manager = ErrorManager(db_path)
        yield manager
        
        # Cleanup
        if db_path.exists():
            db_path.unlink()
    
    def test_import_report(self, temp_db_manager):
        """Test importing a report."""
        report = DataProcessor.create_sample_report()
        
        # Import report
        temp_db_manager.import_analysis_report(report)
        
        # Verify import
        documents = temp_db_manager.get_document_list()
        assert len(documents) == 1
        assert documents[0]["document_name"] == "Sample Thesis.pdf"
        
        # Check errors
        errors = temp_db_manager.get_errors()
        assert len(errors) == 2
        assert all(e.status == ErrorStatus.PENDING for e in errors)
    
    def test_error_filtering(self, temp_db_manager):
        """Test error filtering functionality."""
        report = DataProcessor.create_sample_report()
        temp_db_manager.import_analysis_report(report)
        
        # Filter by status
        from core.models import FilterCriteria
        criteria = FilterCriteria(status=[ErrorStatus.PENDING])
        filtered = temp_db_manager.get_errors(criteria=criteria)
        assert len(filtered) == 2  # Both errors are pending
        
        # Filter by error type
        criteria = FilterCriteria(error_type=[ErrorType.GRAMMAR])
        filtered = temp_db_manager.get_errors(criteria=criteria)
        assert len(filtered) == 1
        assert filtered[0].error_type == ErrorType.GRAMMAR
    
    def test_error_updates(self, temp_db_manager):
        """Test updating error status."""
        report = DataProcessor.create_sample_report()
        temp_db_manager.import_analysis_report(report)
        
        errors = temp_db_manager.get_errors()
        error_id = errors[0].error_id
        
        # Update error status
        success = temp_db_manager.update_error(
            error_id, 
            {"status": ErrorStatus.RESOLVED}, 
            "test_user"
        )
        assert success
        
        # Verify update
        updated_errors = temp_db_manager.get_errors()
        updated_error = next(e for e in updated_errors if e.error_id == error_id)
        assert updated_error.status == ErrorStatus.RESOLVED
    
    def test_bulk_operations(self, temp_db_manager):
        """Test bulk operations."""
        report = DataProcessor.create_sample_report()
        temp_db_manager.import_analysis_report(report)
        
        errors = temp_db_manager.get_errors()
        error_ids = [e.error_id for e in errors]
        
        # Bulk update
        count = temp_db_manager.bulk_update_errors(
            error_ids,
            {"status": ErrorStatus.DISMISSED},
            "test_user"
        )
        assert count == 2
        
        # Verify updates
        updated_errors = temp_db_manager.get_errors()
        assert all(e.status == ErrorStatus.DISMISSED for e in updated_errors)
    
    def test_progress_stats(self, temp_db_manager):
        """Test progress statistics calculation."""
        report = DataProcessor.create_sample_report()
        temp_db_manager.import_analysis_report(report)
        
        # Get initial stats
        stats = temp_db_manager.get_progress_stats()
        assert stats.total_errors == 2
        assert stats.pending_errors == 2
        assert stats.resolved_errors == 0
        assert stats.completion_percentage == 0.0
        
        # Resolve one error
        errors = temp_db_manager.get_errors()
        temp_db_manager.update_error(
            errors[0].error_id,
            {"status": ErrorStatus.RESOLVED},
            "test_user"
        )
        
        # Check updated stats
        updated_stats = temp_db_manager.get_progress_stats()
        assert updated_stats.resolved_errors == 1
        assert updated_stats.completion_percentage == 50.0


class TestVisualizations:
    """Test visualization functions."""
    
    def test_error_summary_chart(self):
        """Test error summary chart creation."""
        errors = [DataProcessor.get_sample_error_for_testing()]
        fig = create_error_summary_chart(errors)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
    
    def test_empty_charts(self):
        """Test charts with empty data."""
        empty_errors = []
        
        # Test all chart functions with empty data
        charts = [
            create_error_summary_chart(empty_errors),
            create_status_pie_chart(empty_errors),
            create_page_heatmap(empty_errors, 10),
            create_confidence_histogram(empty_errors)
        ]
        
        for chart in charts:
            assert isinstance(chart, go.Figure)
            # Should have annotation for empty state
            assert len(chart.layout.annotations) > 0
    
    def test_plotly_config(self):
        """Test Plotly configuration."""
        config = get_plotly_config()
        
        assert isinstance(config, dict)
        assert "displayModeBar" in config
        assert config["displaylogo"] is False


class TestIntegration:
    """Integration tests for complete workflow."""
    
    def test_complete_workflow(self):
        """Test complete import -> manage -> export workflow."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            manager = ErrorManager(db_path)
            
            # 1. Create and import sample report
            report = DataProcessor.create_sample_report()
            manager.import_analysis_report(report)
            
            # 2. Verify import
            documents = manager.get_document_list()
            assert len(documents) == 1
            
            errors = manager.get_errors()
            assert len(errors) == 2
            
            # 3. Update some errors
            manager.update_error(
                errors[0].error_id,
                {"status": ErrorStatus.RESOLVED, "assigned_to": "test_user"},
                "test_user"
            )
            
            # 4. Check statistics
            stats = manager.get_progress_stats()
            assert stats.resolved_errors == 1
            assert stats.completion_percentage == 50.0
            
            # 5. Test visualizations
            fig = create_status_pie_chart(manager.get_errors())
            assert isinstance(fig, go.Figure)
            
            # 6. Export data
            export_data = manager.export_errors_to_json()
            assert "errors" in export_data
            assert len(export_data["errors"]) == 2
            
        finally:
            # Cleanup
            if db_path.exists():
                db_path.unlink()


def test_sample_json_import():
    """Test importing from the actual sample JSON file."""
    # Use the sample file from the project
    sample_file = Path(__file__).parent.parent.parent / "output" / "ba_daniel-2025-08-06_10" / "ba_daniel_grundlagen_20250806_215716_data.json"
    
    if sample_file.exists():
        # Test loading
        json_data = DataProcessor.load_json_report(sample_file)
        assert "document_name" in json_data
        assert "analysis_results" in json_data
        
        # Test conversion
        report = DataProcessor.convert_json_to_analysis_report(json_data)
        assert report.document_name is not None
        assert len(report.analysis_results) > 0
        
        errors = report.get_all_errors()
        assert len(errors) > 0
        
        print(f"Loaded {len(errors)} errors from sample file")
    else:
        print("Sample file not found - skipping real data test")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])