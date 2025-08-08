"""
Data service layer for VeritaScribe Dashboard.
This service mediates between the UI and the core logic modules.
"""
from typing import List, Dict, Any, Optional
from dashboard.core.error_manager import ErrorManager
from dashboard.panel_app.state.app_state import AppState
from dashboard.core.models import ManagedError, FilterCriteria
import panel as pn
import json


class DataService:
    """Service layer that handles data operations and interactions with core modules."""
    
    def __init__(self, error_manager: ErrorManager, app_state: AppState):
        self.error_manager = error_manager
        self.app_state = app_state
    
    def load_documents(self) -> None:
        """Load available documents and update app state."""
        try:
            documents = self.error_manager.get_document_list()
            self.app_state.document_list = documents
        except Exception as e:
            print(f"Failed to load documents: {str(e)}")
    
    def load_errors_for_document(self, document_path: str) -> None:
        """Load errors for a specific document and update app state."""
        if not document_path:
            return
            
        try:
            self.app_state.is_loading_data = True
            errors = self.error_manager.get_errors(document_path)
            self.app_state.all_errors = errors
            self.app_state.filtered_errors = errors.copy()
            self.app_state.is_loading_data = False
        except Exception as e:
            self.app_state.is_loading_data = False
            print(f"Failed to load errors: {str(e)}")
    
    def apply_filters(self, filter_criteria: FilterCriteria) -> None:
        """Apply filters to the error list and update app state."""
        try:
            self.app_state.is_loading_data = True
            document_path = self.app_state.selected_document_path
            # Only apply filters if we have a document path
            # Handle potential undefined values from Param
            if isinstance(document_path, str) and document_path:
                filtered_errors = self.error_manager.get_errors(
                    document_path,
                    filter_criteria
                )
                self.app_state.filtered_errors = filtered_errors
            self.app_state.is_loading_data = False
        except Exception as e:
            self.app_state.is_loading_data = False
            print(f"Failed to apply filters: {str(e)}")
    
    def perform_bulk_update(self, error_ids: List[str], updates: Dict[str, Any]) -> int:
        """Perform bulk update on errors and return number of updated errors."""
        try:
            self.app_state.is_loading_data = True
            updated_count = self.error_manager.bulk_update_errors(error_ids, updates)
            # Refresh data after update
            # Handle potential undefined values from Param
            selected_document_path = self.app_state.selected_document_path
            if isinstance(selected_document_path, str) and selected_document_path:
                self.load_errors_for_document(selected_document_path)
            self.app_state.is_loading_data = False
            return updated_count
        except Exception as e:
            self.app_state.is_loading_data = False
            print(f"Failed to perform bulk update: {str(e)}")
            return 0
    
    def import_report(self, file_content: bytes) -> bool:
        """Import a JSON report and update the database."""
        try:
            self.app_state.is_loading_data = True
            # Save file content to temporary file
            import tempfile
            import json
            from dashboard.core.data_processor import DataProcessor
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                # Write the uploaded content
                try:
                    content = file_content.decode("utf-8")
                except Exception:
                    # Fallback if decode fails; write raw bytes decoded with errors ignored
                    content = file_content.decode("utf-8", errors="ignore")
                temp_file.write(content)
                temp_path = temp_file.name
            
            # Load and convert report using DataProcessor
            report = DataProcessor.load_and_convert_report(temp_path)
            
            # Import using error manager
            self.error_manager.import_analysis_report(report)
            
            # Clean up temporary file
            import os
            os.unlink(temp_path)
            
            # Refresh document list
            self.load_documents()
            
            self.app_state.is_loading_data = False
            print("Report imported successfully")
            return True
        except Exception as e:
            self.app_state.is_loading_data = False
            print(f"Failed to import report: {str(e)}")
            return False