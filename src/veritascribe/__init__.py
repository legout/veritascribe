"""VeritaScribe: AI-powered bachelor thesis review tool."""

__version__ = "0.1.0"

from .config import get_settings, initialize_system
from .pipeline import create_analysis_pipeline, create_quick_pipeline
from .report_generator import create_report_generator
from .data_models import ThesisAnalysisReport, ErrorType, ErrorSeverity

__all__ = [
    "get_settings",
    "initialize_system", 
    "create_analysis_pipeline",
    "create_quick_pipeline", 
    "create_report_generator",
    "ThesisAnalysisReport",
    "ErrorType",
    "ErrorSeverity"
]


def hello() -> str:
    return "Hello from VeritaScribe!"
