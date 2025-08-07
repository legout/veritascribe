#!/usr/bin/env python3
"""
Launch FastHTML Dashboard

Easy launcher for the FastHTML-based VeritaScribe dashboard.
"""

import sys
import subprocess
import os
from pathlib import Path

def main():
    """Launch the FastHTML dashboard."""
    print("🚀 Starting VeritaScribe FastHTML Dashboard...")
    print("📍 Dashboard will be available at: http://localhost:8000")
    print("🔄 Hot reload enabled - changes will be reflected automatically")
    print("⏹️  Press Ctrl+C to stop the server\n")
    
    # Change to the fasthtml_app directory
    app_dir = Path(__file__).parent / "fasthtml_app"
    
    # Check if required packages are installed
    try:
        import fasthtml
        import plotly
        import pandas
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("💡 Install with: pip install -r dashboard/requirements.txt")
        sys.exit(1)
    
    try:
        # Change to the app directory and run
        os.chdir(app_dir)
        subprocess.run([
            sys.executable, 
            "app.py"
        ])
    except KeyboardInterrupt:
        print("\n👋 FastHTML Dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()