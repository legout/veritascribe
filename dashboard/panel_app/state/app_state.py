"""
Centralized application state management for VeritaScribe Dashboard.
"""
import param
from typing import List, Optional
from dashboard.core.models import ManagedError, FilterCriteria


class AppState(param.Parameterized):
    """Centralized application state using Param."""
    
    # Currently selected document
    selected_document_path = param.String(default="", doc="Path to the currently selected document")
    
    # All errors for the selected document
    all_errors = param.List(item_type=ManagedError, default=[], doc="All errors for the selected document")
    
    # Filtered errors based on UI controls
    filtered_errors = param.List(item_type=ManagedError, default=[], doc="Filtered errors for display")
    
    # Current filter criteria
    filter_criteria = param.ClassSelector(class_=FilterCriteria, default=FilterCriteria(), doc="Current filter criteria")
    
    # Loading states
    is_loading_documents = param.Boolean(default=False, doc="Whether documents are currently loading")
    is_loading_data = param.Boolean(default=False, doc="Whether error data is currently loading")
    
    # UI state
    current_view = param.String(default="dashboard", doc="Currently active view")
    bulk_action = param.String(default="", doc="Currently selected bulk action")
    status_message = param.String(default="", doc="Current status message for user feedback")
    
    # Document list for the selector
    document_list = param.List(default=[], doc="List of available documents")
    
    def __init__(self, **params):
        super().__init__(**params)