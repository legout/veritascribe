"""
Panel Dashboard Application

Scientific dashboard for VeritaScribe error management using Panel framework.
Features reactive widgets, interactive tables, and integrated analytics.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import panel as pn
import pandas as pd
from datetime import datetime

from core.error_manager import ErrorManager
from core.data_processor import DataProcessor
from core.visualizations import *
from core.models import FilterCriteria, ErrorStatus, ErrorType, Severity, ManagedError
import panel_material_ui as pmui
import param

# Import new modules
from dashboard.panel_app.state.app_state import AppState
from dashboard.panel_app.services.data_service import DataService

# Enable Panel extensions
pn.extension("plotly", "tabulator", template="material")
# Helper factory to return Material UI widget if available else fallback


# Configure Panel
pn.config.sizing_mode = "stretch_width"


class VeritaScribeDashboard(pn.viewable.Viewer):
    """Main dashboard class implemented as a Panel Viewer with a Page-based layout."""
    
    def __init__(self, **params):
        super().__init__(**params)
        
        # Initialize app state
        self.app_state = AppState()
        
        # Initialize data service
        self.error_manager = ErrorManager()
        self.data_service = DataService(self.error_manager, self.app_state)
        
        # View/router state
        self.current_view = "dashboard"
        
        # Initialize widgets
        self._setup_widgets()
        self._setup_layout()
        self._setup_navigation()
        
        # Load initial data
        self.data_service.load_documents()
        
        # Initial render
        self._render_view(self.current_view)
    
    def _setup_widgets(self):
        """Initialize Panel widgets."""
        # Document selector
        self.document_select = pmui.Select(
            name="Select Document",
            options={},
            width=300
        )
        self.document_select.param.watch(self._on_document_change, "value")
        
        # Filter widgets - use enum values directly with friendly labels
        self.status_widget = pmui.Select(
            name="Status Filter",
            options={
                "All Statuses": None,
                "Pending": ErrorStatus.PENDING,
                "In Progress": ErrorStatus.IN_PROGRESS,
                "Resolved": ErrorStatus.RESOLVED,
                "Dismissed": ErrorStatus.DISMISSED,
                "Needs Review": ErrorStatus.NEEDS_REVIEW,
            },
            value=None,
            width=200,
        )

        self.type_widget = pmui.Select(
            name="Error Type",
            options={
                "All Types": None,
                "Citation Format": ErrorType.CITATION_FORMAT,
                "Grammar": ErrorType.GRAMMAR,
                "Content Plausibility": ErrorType.CONTENT_PLAUSIBILITY,
            },
            value=None,
            width=200,
        )

        self.severity_widget = pmui.Select(
            name="Severity",
            options={
                "All Severities": None,
                "High": Severity.HIGH,
                "Medium": Severity.MEDIUM,
                "Low": Severity.LOW,
            },
            value=None,
            width=200,
        )

        self.search_widget = pmui.TextInput(
            name="Search Text",
            placeholder="Search in error text...",
            width=300
        )
        
        # Bind filter widgets to update method
        for widget in [self.status_widget, self.type_widget, self.severity_widget, self.search_widget]:
            widget.param.watch(self._update_filters, "value")
        
        # Bulk action widgets
        self.bulk_action_select = pmui.Select(
            name="Bulk Action",
            options=["Select Action...", "Mark as Resolved", "Mark as Dismissed", "Assign to Me"],
            value="Select Action...",
            width=200
        )
        
        self.bulk_apply_button = pmui.Button(
            name="Apply to Selected",
            button_type="primary",
            width=150
        )
        self.bulk_apply_button.on_click(self._apply_bulk_action)
        
        # Import widgets
        self.file_input = pmui.FileInput(
            name="Upload JSON Report",
            accept=".json",
            width=300
        )
        self.file_input.param.watch(self._handle_file_upload, "value")
        
        self.import_button = pmui.Button(
            name="Import Report",
            button_type="primary",
            width=150
        )
        self.import_button.on_click(self._import_report)
        
        # Status indicators
        self.status_indicator = pn.pane.Markdown("Ready", width=200)

        # Prebuild view fragments to reuse
        self._filters_row = pmui.Row(
            self.status_widget,
            self.type_widget,
            self.severity_widget,
            self.search_widget,
            margin=(0, 0, 10, 0),
        )
        self._bulk_row = pmui.Row(
            self.bulk_action_select,
            self.bulk_apply_button,
            self.status_indicator,
            margin=(0, 0, 10, 0),
        )
        self._import_row = pmui.Row(self.file_input, self.import_button, margin=(0, 0, 10, 0))
        
    def _setup_layout(self):
        """Setup the dashboard layout using pmui.Page with a minimal, casual style."""
        # App Header (use safe pmui.Card instead of unsupported AppBar)
        # self.header = pmui.Card(
        #     objects=[
        #         pmui.Typography("VeritaScribe", variant="h5"),
        #         pmui.Typography("Error Management", variant="subtitle2", sx={"opacity": 0.85}),
        #     ],
        #     elevation=0,
        #     sx={"padding": "12px", "margin-bottom": "8px"}
        # )
    
        # Statistics container (content updated dynamically)
        self.stats_pane = pmui.Column(pn.pane.HTML("<div>Loading statistics...</div>"))
    
        # Charts pane (keep pn.Tabs for serialization stability)
        self.charts_pane = pmui.Tabs(
            ("Overview", pn.pane.HTML("Select a document to view charts")),
            tabs_location="above",
            width=900,
            height=460,
        )
        existing = self.charts_pane.css_classes
        if not isinstance(existing, list):
            existing = [] if existing in (None, pn.panel._param.undefined) else list(existing)  # type: ignore[attr-defined]
        if "vs-material-tabs" not in existing:
            existing.append("vs-material-tabs")
        self.charts_pane.css_classes = existing
    
        # Error table
        self.error_table = pn.widgets.Tabulator(
            value=pd.DataFrame(),
            selectable="checkbox",
            height=500,
            pagination="remote",
            page_size=50,
            sizing_mode="stretch_width",
        )
    
        # Sidebar navigation and global controls
        self._nav_dashboard_btn = pmui.Button(name="Dashboard", variant="text", color="primary")
        self._nav_manage_btn = pmui.Button(name="Manage Errors", variant="text", color="primary")
        self._nav_import_btn = pmui.Button(name="Import", variant="text", color="primary")
    
        sidebar_content = pmui.Column(
            pmui.Typography("Document", variant="subtitle2", sx={"margin-top": "8px"}),
            self.document_select,
            pmui.Divider(),
            pmui.Typography("Navigate", variant="subtitle2"),
            pn.Column(self._nav_dashboard_btn, self._nav_manage_btn, self._nav_import_btn, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
            margin=(8, 8, 8, 8),
        )
    
        # Sidebar (safe Card instead of Drawer)
        self._sidebar = [sidebar_content]

        # Main content area (swapped by router)
        self._view_content = pn.Column()  # Initialize with empty column
        self._main= [self._view_content]

        # Page assembly: Keep Page strictly for header; render body alongside in __panel__
        self.page = pmui.Page(
            sidebar=self._sidebar, main=self._main, dark_theme=True
        )

    def _load_documents(self):
        """Load available documents."""
        self.data_service.load_documents()
        
        # Update document selector options
        # Check if document_list has content
        document_list = self.app_state.document_list
        # Handle potential undefined values from Param
        if isinstance(document_list, list) and len(document_list) > 0:
            try:
                doc_options = {
                    f"{doc['document_name']} ({doc['completion_percentage']:.1f}% complete)": doc['document_path']
                    for doc in document_list
                }
                self.document_select.options = doc_options

                # Select first document by default
                if doc_options:
                    first_doc_path = list(doc_options.values())[0]
                    self.document_select.value = first_doc_path
                    if isinstance(first_doc_path, str) and first_doc_path:
                        self.data_service.load_errors_for_document(first_doc_path)
                        self.app_state.selected_document_path = first_doc_path
            except Exception as e:
                print(f"Error processing document list: {e}")
                self.document_select.options = {"No documents available": ""}
        else:
            self.document_select.options = {"No documents available": ""}
    
    def _on_document_change(self, event):
        """Handle document selection change."""
        new_path = event.new
        if isinstance(new_path, str) and new_path:
            self.data_service.load_errors_for_document(new_path)
            self.app_state.selected_document_path = new_path
    
    def _load_document_data(self, document_path: str):
        """Load data for selected document."""
        # This method is no longer needed as data loading is handled by data service
        # and state updates are handled by app state
        pass
    
    def _update_statistics(self, document_path: str):
        """Update statistics display."""
        try:
            # Use all errors from app state for statistics
            all_errors = self.app_state.all_errors
            em: ErrorManager = self.error_manager if isinstance(self.error_manager, ErrorManager) else ErrorManager()
            documents = em.get_document_list()
            doc_info = next((d for d in documents if d["document_path"] == document_path), {})
            
            # Create a mock stats object from app state data
            class MockStats:
                def __init__(self, errors):
                    self.total_errors = len(errors)
                    self.pending_errors = len([e for e in errors if e.status == ErrorStatus.PENDING])
                    self.completion_percentage = (
                        len([e for e in errors if e.status == ErrorStatus.RESOLVED]) / len(errors) * 100
                        if errors else 100.0
                    )
            
            stats = MockStats(all_errors)
            
            # Guarded debug logging
            try:
                print(f"[VS-Debug] _update_statistics: path={document_path}, total_errors={getattr(stats, 'total_errors', None)}, completed={getattr(stats, 'completion_percentage', None)}, pending={getattr(stats, 'pending_errors', None)}, pages={doc_info.get('total_pages', None)}")
            except Exception:
                pass
        except Exception as e:
            try:
                print(f"[VS-Debug] _update_statistics error: {e}")
            except Exception:
                pass
            # Fallback safe defaults
            class _EmptyStats:
                total_errors = 0
                completion_percentage = 0.0
                pending_errors = 0
            stats = _EmptyStats()
            doc_info = {}

        # Build stats with plain Panel components only to avoid Bokeh serialization issues
        html = f"""
        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;'>
          <div style='background: linear-gradient(135deg, #2E86AB, #A23B72); color: white; padding: 20px; border-radius: 8px; text-align: center;'>
            <div style='font-size: 2em; font-weight: bold;'>{stats.total_errors}</div>
            <div style='font-size: 0.9em; opacity: 0.9;'>Total Errors</div>
          </div>
          <div style='background: linear-gradient(135deg, #28A745, #20C997); color: white; padding: 20px; border-radius: 8px; text-align: center;'>
            <div style='font-size: 2em; font-weight: bold;'>{getattr(stats, 'completion_percentage', 0.0):.1f}%</div>
            <div style='font-size: 0.9em; opacity: 0.9;'>Completed</div>
          </div>
          <div style='background: linear-gradient(135deg, #FFC107, #FF8C00); color: white; padding: 20px; border-radius: 8px; text-align: center;'>
            <div style='font-size: 2em; font-weight: bold;'>{getattr(stats, 'pending_errors', 0)}</div>
            <div style='font-size: 0.9em; opacity: 0.9;'>Pending</div>
          </div>
          <div style='background: linear-gradient(135deg, #17A2B8, #138496); color: white; padding: 20px; border-radius: 8px; text-align: center;'>
            <div style='font-size: 2em; font-weight: bold;'>{doc_info.get('total_pages', 0)}</div>
            <div style='font-size: 0.9em; opacity: 0.9;'>Pages</div>
          </div>
        </div>
        """
        self.stats_pane.objects = [pn.pane.HTML(html)]
        # else:
        #     html = f"""
        #     <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
        #         <div style="background: linear-gradient(135deg, #2E86AB, #A23B72); color: white; padding: 20px; border-radius: 8px; text-align: center;">
        #             <div style="font-size: 2em; font-weight: bold;">{stats.total_errors}</div>
        #             <div style="font-size: 0.9em; opacity: 0.9;">Total Errors</div>
        #         </div>
        #         <div style="background: linear-gradient(135deg, #28A745, #20C997); color: white; padding: 20px; border-radius: 8px; text-align: center;">
        #             <div style="font-size: 2em; font-weight: bold;">{stats.completion_percentage:.1f}%</div>
        #             <div style="font-size: 0.9em; opacity: 0.9;">Completed</div>
        #         </div>
        #         <div style="background: linear-gradient(135deg, #FFC107, #FF8C00); color: white; padding: 20px; border-radius: 8px; text-align: center;">
        #             <div style="font-size: 2em; font-weight: bold;">{stats.pending_errors}</div>
        #             <div style="font-size: 0.9em; opacity: 0.9;">Pending</div>
        #         </div>
        #         <div style="background: linear-gradient(135deg, #17A2B8, #138496); color: white; padding: 20px; border-radius: 8px; text-align: center;">
        #             <div style="font-size: 2em; font-weight: bold;">{doc_info.get('total_pages', 0)}</div>
        #             <div style="font-size: 0.9em; opacity: 0.9;">Pages</div>
        #         </div>
        #     </div>
        #     """
        #     # Fallback to simple HTML stats
        #     self.stats_pane.objects = [pn.pane.HTML(html)]
    
    def _setup_navigation(self):
        """Wire navigation actions for switching views."""
        def _go(target: str):
            self.current_view = target
            self._render_view(target)

        self._nav_dashboard_btn.on_click(lambda e: _go("Dashboard"))
        self._nav_manage_btn.on_click(lambda e: _go("Manage"))
        self._nav_import_btn.on_click(lambda e: _go("Import"))

    def _render_view(self, view: str):
        """Swap the main content based on current view."""
        if view == "Dashboard":
            self._view_content = self._create_dashboard_view()
        elif view == "Manage":
            self._view_content = self._create_manage_view()
        elif view == "Import":
            self._view_content = self._create_import_view()
        else:
            self._view_content = pn.pane.Markdown("Unknown view")

    def _create_dashboard_view(self):
        """Dashboard view containing stats and analytics charts."""
        return pmui.Column(
            pmui.Typography("Overview", variant="h6", sx={"margin": "8px 0"}),
            self.stats_pane,
            pmui.Card(objects=[self.charts_pane], elevation=0, sx={"padding": "8px"}),
            sizing_mode="stretch_width",
        )

    def _create_manage_view(self):
        """Manage Errors view with filters, table, and bulk actions."""
        return pmui.Column(
            pmui.Typography("Manage Errors", variant="h6", sx={"margin": "8px 0"}),
            pmui.Card(objects=[pmui.Typography("Filters", variant="subtitle2"), self._filters_row], elevation=0),
            pmui.Card(objects=[self.error_table], elevation=0, sx={"margin-top": "8px"}),
            pmui.Card(objects=[pmui.Typography("Bulk Actions", variant="subtitle2"), self._bulk_row], elevation=0, sx={"margin-top": "8px"}),
            sizing_mode="stretch_width",
        )

    def _create_import_view(self):
        """Import view focused on file upload workflow."""
        return pmui.Column(
            pmui.Typography("Import Report", variant="h6", sx={"margin": "8px 0"}),
            pmui.Card(objects=[pmui.Typography("Upload JSON", variant="subtitle2"), self._import_row], elevation=0),
            sizing_mode="stretch_width",
        )

    def _update_charts(self):
        """Update visualization charts."""
        try:
            # Use all errors from app state
            all_errors = self.app_state.all_errors
            if not isinstance(all_errors, list) or len(all_errors) == 0:
                self.charts_pane[:] = [("Overview", pn.pane.HTML("No errors to visualize"))]
                try:
                    print("[VS-Debug] _update_charts: no current_errors")
                except Exception:
                    pass
                return
            
            # Get document info for page count
            doc_path = getattr(self.document_select, "value", None)
            if not isinstance(doc_path, str) or not doc_path:
                # Fallback: no valid path selected, clear charts
                self.charts_pane[:] = [("Overview", pn.pane.HTML("No document selected"))]
                try:
                    print(f"[VS-Debug] _update_charts: invalid doc_path={doc_path}")
                except Exception:
                    pass
                return
            em: ErrorManager = self.error_manager if isinstance(self.error_manager, ErrorManager) else ErrorManager()
            documents = em.get_document_list()
            doc_info = next((d for d in documents if d["document_path"] == doc_path), {})
            total_pages = doc_info.get("total_pages", 10)
            
            # Create charts
            summary_chart = create_error_summary_chart(all_errors)
            status_chart = create_status_pie_chart(all_errors)
            heatmap_chart = create_page_heatmap(all_errors, total_pages)
            confidence_chart = create_confidence_histogram(all_errors)
            
            em: ErrorManager = self.error_manager if isinstance(self.error_manager, ErrorManager) else ErrorManager()
            stats = em.get_progress_stats(doc_path)
            progress_chart = create_progress_timeline(stats)
            workload_chart = create_workload_distribution(stats)

            # Guarded debug logging
            try:
                print(f"[VS-Debug] _update_charts: doc_path={doc_path}, errors={len(all_errors)}, pages={total_pages}")
            except Exception:
                pass
            
            # Update charts tabs
            tabs_content = [
                ("Summary", pn.pane.Plotly(summary_chart, height=400, config=get_plotly_config())),
                ("Status", pn.pane.Plotly(status_chart, height=400, config=get_plotly_config())),
                ("Page Distribution", pn.pane.Plotly(heatmap_chart, height=400, config=get_plotly_config())),
                ("Confidence", pn.pane.Plotly(confidence_chart, height=400, config=get_plotly_config())),
                ("Progress", pn.pane.Plotly(progress_chart, height=400, config=get_plotly_config())),
                ("Workload", pn.pane.Plotly(workload_chart, height=400, config=get_plotly_config()))
            ]
            try:
                # Prefer Panel Tabs to ensure serialization; if pmui is available, we still write into pn.Tabs
                self.charts_pane[:] = tabs_content
                try:
                    print(f"[VS-Debug] _update_charts: tabs updated with {len(tabs_content)} tabs")
                except Exception:
                    pass
            except Exception as e:
                try:
                    print(f"[VS-Debug] _update_charts: tabs update failed: {e}")
                except Exception:
                    pass
                self.charts_pane[:] = [("Overview", pn.pane.HTML("Chart rendering failed"))]
        except Exception as e:
            try:
                print(f"[VS-Debug] _update_charts error: {e}")
            except Exception:
                pass
            # Minimal safe fallback
            self.charts_pane[:] = [("Overview", pn.pane.HTML("Chart rendering failed"))]
        # Ensure nothing non-serializable like methods or callbacks are stored in panel objects
    
    def _update_filters(self, event):
        """Update filtered errors based on widget values."""
        criteria = FilterCriteria()
        
        # Status filter (enum or None)
        sv = getattr(self.status_widget, "value", None)
        if isinstance(sv, ErrorStatus):
            criteria.status = [sv]

        # Type filter (enum or None)
        tv = getattr(self.type_widget, "value", None)
        if isinstance(tv, ErrorType):
            criteria.error_type = [tv]

        # Severity filter (enum or None)
        sev = getattr(self.severity_widget, "value", None)
        if isinstance(sev, Severity):
            criteria.severity = [sev]
        
        # Search filter
        st = getattr(self.search_widget, "value", "")
        if isinstance(st, str) and st.strip():
            criteria.search_text = st.strip()
        
        # Update the filter criteria in app state
        self.app_state.filter_criteria = criteria
        
        # Apply filters through data service
        self.data_service.apply_filters(criteria)
        
        # Update table with filtered errors from app state
        self._update_error_table()
    
    def _update_error_table(self):
        """Update the error table with current filtered errors."""
        # Use filtered errors from app state
        filtered_errors = self.app_state.filtered_errors
        if not isinstance(filtered_errors, list) or len(filtered_errors) == 0:
            self.error_table.value = pd.DataFrame()
            return
         
        # Convert errors to DataFrame
        data = []
        for error in filtered_errors:
            data.append({
                "ID": error.error_id[:8],  # Short ID for display
                "Status": error.status.value.replace("_", " ").title(),
                "Type": error.error_type.value.replace("_", " ").title(),
                "Severity": error.severity.value.title(),
                "Page": error.location.page_number,
                "Original Text": error.original_text[:100] + ("..." if len(error.original_text) > 100 else ""),
                "Suggested Correction": error.suggested_correction[:100] + ("..." if len(error.suggested_correction) > 100 else ""),
                "Confidence": error.confidence_score,
                "Assigned To": error.assigned_to or "Unassigned",
                "Created": error.created_at.strftime("%Y-%m-%d %H:%M")
            })

        df = pd.DataFrame(data)

        # Pre-render HTML for formatted columns if data exists
        if not df.empty:
            df["Status"] = df["Status"].apply(self._format_status_html)
            df["Severity"] = df["Severity"].apply(self._format_severity_html)
            df["Confidence"] = df["Confidence"].apply(self._format_confidence_html)

        # Configure table formatting to render raw HTML
        formatters = {
            "Status": {"type": "html"},
            "Severity": {"type": "html"},
            "Confidence": {"type": "html"}
        }

        self.error_table.value = df
        self.error_table.formatters = formatters
        
        # Configure table options
        # Apply basic styling consistent with material theme
        try:
            # Prefer supported properties on Tabulator
            self.error_table.theme = "materialize"  # fallback theme resembling material
            self.error_table.styles = {"rowHeight": 60}
        except Exception:
            pass
    
    def _format_status_html(self, status: str) -> str:
        """Formats a status string into a colored HTML badge."""
        colors = {
            "Pending": "#ffeaa7",
            "In Progress": "#fab1a0", 
            "Resolved": "#00b894",
            "Dismissed": "#636e72",
            "Needs Review": "#74b9ff"
        }
        color = colors.get(status, "#ddd")
        return f'<span style="background: {color}; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: 500;">{status}</span>'
    
    def _format_severity_html(self, severity: str) -> str:
        """Formats a severity string into a colored HTML span."""
        colors = {"High": "#DC3545", "Medium": "#FFC107", "Low": "#28A745"}
        color = colors.get(severity, "#333")
        return f'<span style="color: {color}; font-weight: bold;">{severity}</span>'
    
    def _format_confidence_html(self, confidence: float) -> str:
        """Formats a confidence score into a colored HTML span."""
        confidence = float(confidence)
        color = "#28A745" if confidence > 0.8 else "#FFC107" if confidence > 0.6 else "#DC3545"
        return f'<span style="color: {color}; font-weight: bold;">{confidence:.2f}</span>'
    
    def _apply_bulk_action(self, event):
        """Apply bulk action to selected errors."""
        selected_rows = list(self.error_table.selection or [])
        if not selected_rows:
            self.status_indicator.object = "⚠️ No errors selected"
            return
         
        action = self.bulk_action_select.value
        if action == "Select Action...":
            self.status_indicator.object = "⚠️ Please select an action"
            return
         
        # Get selected error IDs (need to map from display indices to actual error IDs)
        selected_error_ids = []
        # Use filtered errors from app state
        filtered_errors = self.app_state.filtered_errors
        # Defensive: ensure filtered_errors is a list before indexing
        if isinstance(filtered_errors, list):
            for idx in selected_rows:
                if isinstance(idx, int) and 0 <= idx < len(filtered_errors):
                    selected_error_ids.append(filtered_errors[idx].error_id)
         
        # Prepare updates based on action
        updates = {}
        if action == "Mark as Resolved":
            updates = {"status": ErrorStatus.RESOLVED}
        elif action == "Mark as Dismissed":
            updates = {"status": ErrorStatus.DISMISSED}
        elif action == "Assign to Me":
            updates = {"assigned_to": "panel_user", "status": ErrorStatus.IN_PROGRESS}
         
        # Perform bulk update through data service
        if updates:
            count = self.data_service.perform_bulk_update(selected_error_ids, updates)
            self.status_indicator.object = f"✅ Updated {count} errors"
    
    def _handle_file_upload(self, event):
        """Handle file upload for import."""
        if event.new is not None:
            self.status_indicator.object = "📁 File selected, click Import to process"
    
    def _import_report(self, event):
        """Import uploaded JSON report."""
        if self.file_input.value is None:
            self.status_indicator.object = "⚠️ Please select a file first"
            return
        if not isinstance(self.file_input.value, (bytes, bytearray)):
            self.status_indicator.object = "⚠️ Invalid file content"
            return
         
        try:
            # Import through data service
            success = self.data_service.import_report(self.file_input.value)
            
            if success:
                # Refresh document list
                self._load_documents()
                self.status_indicator.object = "✅ Report imported successfully"
            else:
                self.status_indicator.object = "❌ Import failed"
             
        except Exception as e:
            self.status_indicator.object = f"❌ Import failed: {str(e)}"
    
    def __panel__(self):
        """Return the composed layout for robust rendering."""
        # Ensure current view content exists
        if not hasattr(self, "_view_content") or self._view_content is None:
            self._render_view(self.current_view if hasattr(self, "current_view") else "Dashboard")

        # Build a simple body container from current view
        body = pmui.Column(
            self._view_content,
            sizing_mode="stretch_width",
        )
        # Keep reference for potential external access while avoiding attribute errors
        self._page_body = body

        # Return page with body
        return pn.Column(self.page, body, sizing_mode="stretch_width")


# Create global dashboard instance
dashboard = VeritaScribeDashboard()

# Create Panel app
def create_app():
    """Create and return the Panel application."""
    return dashboard

# For serving
if __name__ == "__main__":
    # Create the app
    app = create_app()
    
    # Serve the app
    pn.serve(
        app,
        title="VeritaScribe Dashboard",
        port=5007,
        show=True,
        allow_websocket_origin=["localhost:5007"],
        autoreload=True
    )