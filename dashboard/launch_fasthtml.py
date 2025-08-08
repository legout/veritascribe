#!/usr/bin/env python3
"""
Launch FastHTML Dashboard (datastar)

Easy launcher for the datastar-based FastHTML VeritaScribe dashboard.
"""

import uvicorn
import sys
from pathlib import Path

def main():
    print("🚀 Starting VeritaScribe FastHTML Dashboard (datastar)...")
    print("📍 Dashboard will be available at: http://localhost:8000")
    print("🔄 Hot reload enabled - changes will be reflected automatically")
    print("⏹️  Press Ctrl+C to stop the server\n")

    # Add the project root to the Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Specify the application to run (ASGI app callable)
    app_module = "dashboard.datastar_app.app:app"

    uvicorn.run(
        app_module,
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(project_root / "dashboard")]
    )

if __name__ == "__main__":
    main()