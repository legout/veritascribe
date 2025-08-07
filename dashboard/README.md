# VeritaScribe Dashboard

Interactive error management dashboard for VeritaScribe thesis analysis reports. Available in both FastHTML and Panel implementations.

## 🌟 Features

- **📊 Interactive Error Management**: Mark errors as resolved, dismissed, or in progress
- **🔍 Advanced Filtering**: Filter by status, type, severity, page, confidence score
- **📈 Visual Analytics**: Charts showing error distribution, progress, and statistics  
- **⚡ Real-time Updates**: HTMX (FastHTML) or reactive widgets (Panel)
- **📋 Bulk Operations**: Update multiple errors simultaneously
- **💾 Persistent Storage**: SQLite database for error state management
- **📁 Import/Export**: Load VeritaScribe JSON reports and export results

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd dashboard
pip install -r requirements.txt
```

### 2. Choose Your Framework

**Option A: FastHTML (Web-native, HTMX-powered)**
```bash
python launch_fasthtml.py
# Opens at http://localhost:8000
```

**Option B: Panel (Scientific computing focus)**  
```bash
python launch_panel.py
# Opens at http://localhost:5007
```

### 3. Import Your Data

1. Click "Import" in the navigation
2. Upload your VeritaScribe JSON report
3. Start managing errors!

## 📁 Architecture

Both implementations share 85% of their codebase:

```
dashboard/
├── core/                    # 🔄 SHARED COMPONENTS
│   ├── models.py           # Enhanced data models with error management
│   ├── error_manager.py    # SQLite database and business logic  
│   ├── data_processor.py   # JSON loading/conversion utilities
│   ├── visualizations.py   # Plotly charts (works in both frameworks)
│   └── __init__.py
├── fasthtml_app/           # 🚀 FastHTML Implementation
│   ├── app.py              # Main FastHTML application
│   ├── components.py       # HTML components and templates
│   └── __init__.py
├── panel_app/              # 📊 Panel Implementation
│   ├── app.py              # Main Panel application  
│   └── __init__.py
├── tests/                  # 🧪 Test Suite
│   └── test_dashboard.py   # Comprehensive tests
├── requirements.txt        # Dependencies
├── launch_fasthtml.py      # FastHTML launcher
├── launch_panel.py         # Panel launcher
└── README.md
```

## 🎯 Error Management Workflow

### Status Tracking
- **🔴 Pending**: Newly detected errors
- **🟡 In Progress**: Being worked on (assigned)
- **🟢 Resolved**: Fixed and verified
- **⚪ Dismissed**: Intentionally ignored
- **🔵 Needs Review**: Requires second opinion

### Filtering Options
- **Status**: Pending, In Progress, Resolved, etc.
- **Error Type**: Citation, Grammar, Content Plausibility
- **Severity**: High, Medium, Low  
- **Page Range**: Specific page numbers
- **Confidence**: AI confidence scores
- **Search**: Text search in error content

### Bulk Operations
- Mark multiple errors as resolved
- Dismiss false positives in bulk
- Assign errors to team members
- Export filtered error lists

## 📊 Visualizations

Both frameworks use the same Plotly charts:

- **Error Summary**: Bar charts by type and severity
- **Status Distribution**: Pie chart of error statuses
- **Page Heatmap**: Error distribution across document pages
- **Confidence Analysis**: Histogram of AI confidence scores
- **Progress Timeline**: Resolution progress over time
- **Workload Distribution**: Errors by assignee

## 🔧 Technical Details

### FastHTML Implementation
- **Framework**: FastHTML with HTMX for dynamic interactions
- **Styling**: Custom CSS with modern design
- **Interactions**: Server-side rendering with HTMX updates
- **Benefits**: Clean URLs, fast loading, mobile-responsive

### Panel Implementation  
- **Framework**: Panel with Param for reactive programming
- **Widgets**: Tabulator for advanced table features
- **Interactions**: Client-side reactivity with automatic updates
- **Benefits**: Scientific computing integration, Jupyter compatibility

### Shared Core
- **Database**: SQLite for persistent error state
- **Models**: Pydantic for data validation
- **Visualizations**: Plotly for interactive charts
- **Processing**: Pandas for data manipulation

## 🧪 Testing

Run the test suite to validate both implementations:

```bash
cd dashboard
python -m pytest tests/test_dashboard.py -v
```

Tests cover:
- Data import/export functionality
- Error filtering and management
- Bulk operations
- Visualization generation
- Database persistence
- Complete workflow integration

## 📈 Performance

**Shared Components Benefits**:
- 85% code reuse between frameworks
- Consistent visualization appearance
- Single database for both implementations
- Unified data processing logic

**Framework Comparison**:
- **FastHTML**: Lighter weight, faster initial load
- **Panel**: Richer widgets, better for data exploration

## 🔒 Data Security

- Local SQLite database (no cloud dependencies)
- No external API calls for core functionality
- User activity logging for audit trails
- Export capabilities for backup/archival

## 🛠️ Development

### Adding New Features

1. **Shared Logic**: Add to `core/` modules
2. **FastHTML UI**: Update `fasthtml_app/` components  
3. **Panel UI**: Update `panel_app/` widgets
4. **Tests**: Add to `tests/test_dashboard.py`

### Database Schema

The SQLite database includes:
- `errors`: Main error table with status tracking
- `documents`: Document metadata
- `activity_log`: User action audit trail

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new functionality
4. Ensure both FastHTML and Panel implementations work
5. Submit a pull request

## 📝 License

Part of the VeritaScribe project. See main project for license details.

---

**Choose your preferred framework and start managing thesis errors more efficiently!** 🎓✨