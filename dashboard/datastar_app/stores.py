# Server truth; used to project UI state via patch_signals
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from core.models import ManagedError, FilterCriteria

@dataclass
class AppState:
    selected_document: Optional[str] = None
    errors: List[ManagedError] = field(default_factory=list)
    filter_criteria: FilterCriteria = field(default_factory=FilterCriteria)
    selected_errors: List[str] = field(default_factory=list)
    chart_payloads: Dict[str, Any] = field(default_factory=dict)

app_state = AppState()

def project_signals() -> dict:
    # Narrow UI-friendly projection to keep payloads lean
    return {
        "selectedDocument": app_state.selected_document,
        "filter": app_state.filter_criteria.model_dump() if hasattr(app_state.filter_criteria, "model_dump") else dict(app_state.filter_criteria),
        "counts": {
            "total": len(app_state.errors),
            "pending": sum(e.status == "Pending" for e in app_state.errors),
            "completed": sum(e.status == "Resolved" for e in app_state.errors),
        },
    }