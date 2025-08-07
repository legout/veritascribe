#!/usr/bin/env python3
"""
Launch Panel Dashboard

Easy launcher for the Panel-based VeritaScribe dashboard.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Launch the Panel dashboard."""
    print("🚀 Starting VeritaScribe Panel Dashboard...")
    print("📍 Dashboard will be available at: http://localhost:5007") 
    print("🔄 Auto-reload enabled - changes will be reflected automatically")
    print("⏹️  Press Ctrl+C to stop the server\n")
    
    # Change to the panel_app directory
    app_dir = Path(__file__).parent / "panel_app"
    
    # Check if required packages are installed
    try:
        import panel
        import plotly
        import pandas
        import param
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("💡 Install with: pip install -r dashboard/requirements.txt")
        sys.exit(1)
    
    try:
        # Run the Panel app
        subprocess.run([
            sys.executable, 
            str(app_dir / "app.py")
        ], cwd=app_dir)
    except KeyboardInterrupt:
        print("\n👋 Panel Dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()