"""Report generation and visualization for thesis analysis results."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter
import fitz  # PyMuPDF

from .data_models import (
    ThesisAnalysisReport,
    AnalysisResult,
    ErrorSeverity,
    ErrorType,
    BaseError
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates comprehensive reports and visualizations from analysis results."""
    
    def __init__(self):
        # Configure matplotlib for better-looking plots
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
    
    def generate_text_report(
        self, 
        report: ThesisAnalysisReport, 
        output_path: str,
        include_detailed_errors: bool = True
    ) -> str:
        """
        Generate a comprehensive text report in Markdown format.
        
        Args:
            report: ThesisAnalysisReport to generate report from
            output_path: Path where the report should be saved
            include_detailed_errors: Whether to include detailed error listings
            
        Returns:
            Path to the generated report file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report_content = self._generate_markdown_content(report, include_detailed_errors)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Text report generated: {output_path}")
        return str(output_path)
    
    def _generate_markdown_content(
        self, 
        report: ThesisAnalysisReport, 
        include_detailed_errors: bool
    ) -> str:
        """Generate the markdown content for the report."""
        
        content = []
        
        # Header
        content.append(f"# Thesis Analysis Report")
        content.append(f"")
        content.append(f"**Document:** {report.document_name}")
        content.append(f"**Analysis Date:** {report.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**Processing Time:** {report.total_processing_time_seconds:.2f} seconds")
        
        # Add token usage and cost information if available
        if report.token_usage:
            content.append(f"**Token Usage:** {report.token_usage['total_tokens']:,} tokens (Prompt: {report.token_usage['prompt_tokens']:,}, Completion: {report.token_usage['completion_tokens']:,})")
        
        if report.estimated_cost is not None:
            content.append(f"**Estimated Cost:** ${report.estimated_cost:.4f} USD")
        
        content.append(f"")
        
        # Executive Summary
        content.append("## Executive Summary")
        content.append("")
        content.append(f"- **Total Pages:** {report.total_pages}")
        content.append(f"- **Text Blocks Analyzed:** {report.total_text_blocks}")
        content.append(f"- **Total Words:** {report.total_words:,}")
        content.append(f"- **Total Errors Found:** {report.total_errors}")
        content.append(f"- **Error Rate:** {report.error_rate:.2f} errors per 1,000 words")
        content.append(f"- **Pages with Errors:** {report.pages_with_errors} ({report.pages_with_errors/max(report.total_pages, 1)*100:.1f}%)")
        content.append(f"- **Average Errors per Page:** {report.average_errors_per_page:.2f}")
        content.append("")
        
        # Analysis Configuration
        if report.configuration_used:
            content.append("## Analysis Configuration")
            content.append("")
            config = report.configuration_used
            content.append(f"- **Grammar Analysis:** {'✓' if config.get('grammar_analysis_enabled') else '✗'}")
            content.append(f"- **Content Analysis:** {'✓' if config.get('content_analysis_enabled') else '✗'}")
            content.append(f"- **Citation Analysis:** {'✓' if config.get('citation_analysis_enabled') else '✗'}")
            content.append(f"- **LLM Model:** {config.get('model', 'Unknown')}")
            content.append(f"- **Parallel Processing:** {'✓' if config.get('parallel_processing') else '✗'}")
            content.append("")
        
        # Error Summary by Type
        if report.errors_by_type:
            content.append("## Error Summary by Type")
            content.append("")
            content.append("| Error Type | Count | Percentage |")
            content.append("|------------|-------|------------|")
            
            for error_type, count in sorted(report.errors_by_type.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / report.total_errors * 100) if report.total_errors > 0 else 0
                content.append(f"| {error_type.replace('_', ' ').title()} | {count} | {percentage:.1f}% |")
            content.append("")
        
        # Error Summary by Severity
        if report.errors_by_severity:
            content.append("## Error Summary by Severity")
            content.append("")
            content.append("| Severity | Count | Percentage |")
            content.append("|----------|-------|------------|")
            
            severity_order = ['high', 'medium', 'low']
            for severity in severity_order:
                count = report.errors_by_severity.get(severity, 0)
                if count > 0:
                    percentage = (count / report.total_errors * 100) if report.total_errors > 0 else 0
                    content.append(f"| {severity.title()} | {count} | {percentage:.1f}% |")
            content.append("")
        
        # High Priority Issues
        high_severity_errors = report.get_high_severity_errors()
        if high_severity_errors:
            content.append("## High Priority Issues")
            content.append("")
            content.append(f"Found {len(high_severity_errors)} high-severity issues that require immediate attention:")
            content.append("")
            
            for i, error in enumerate(high_severity_errors[:10], 1):  # Show top 10
                content.append(f"### {i}. {error.error_type.replace('_', ' ').title()}")
                content.append(f"**Page {error.location.page_number}**")
                content.append(f"")
                content.append(f"**Original:** {error.original_text}")
                if error.suggested_correction:
                    content.append(f"**Suggested:** {error.suggested_correction}")
                content.append(f"**Explanation:** {error.explanation}")
                content.append("")
            
            if len(high_severity_errors) > 10:
                content.append(f"*... and {len(high_severity_errors) - 10} more high-severity issues.*")
                content.append("")
        
        # Page-by-Page Error Distribution
        if report.errors_by_page:
            content.append("## Error Distribution by Page")
            content.append("")
            
            # Find pages with most errors
            top_error_pages = sorted(
                report.errors_by_page.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            if top_error_pages:
                content.append("### Pages with Most Errors")
                content.append("")
                content.append("| Page | Error Count |")
                content.append("|------|-------------|")
                
                for page, count in top_error_pages:
                    content.append(f"| {page} | {count} |")
                content.append("")
        
        # Detailed Error Listings
        if include_detailed_errors and report.analysis_results:
            content.append("## Detailed Error Listings")
            content.append("")
            
            # Group errors by type for better organization
            errors_by_type = self._group_errors_by_type(report.analysis_results)
            
            for error_type, errors in errors_by_type.items():
                if not errors:
                    continue
                    
                content.append(f"### {error_type.replace('_', ' ').title()} Errors ({len(errors)} found)")
                content.append("")
                
                for i, error in enumerate(errors[:20], 1):  # Limit to 20 per type
                    content.append(f"#### {i}. Page {error.location.page_number}")
                    content.append(f"**Severity:** {error.severity.title()}")
                    content.append(f"**Original Text:** {error.original_text}")
                    if error.suggested_correction:
                        content.append(f"**Suggestion:** {error.suggested_correction}")
                    content.append(f"**Explanation:** {error.explanation}")
                    content.append("")
                
                if len(errors) > 20:
                    content.append(f"*... and {len(errors) - 20} more {error_type.replace('_', ' ')} errors.*")
                    content.append("")
        
        # Footer
        content.append("---")
        content.append(f"*Report generated by VeritaScribe on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(content)
    
    def _group_errors_by_type(self, analysis_results: List[AnalysisResult]) -> Dict[str, List[BaseError]]:
        """Group all errors by type across all analysis results."""
        errors_by_type = {}
        
        for result in analysis_results:
            for error in result.errors:
                error_type = error.error_type
                if error_type not in errors_by_type:
                    errors_by_type[error_type] = []
                errors_by_type[error_type].append(error)
        
        return errors_by_type
    
    def visualize_errors(
        self, 
        report: ThesisAnalysisReport, 
        output_directory: str
    ) -> List[str]:
        """
        Generate visualization charts for the analysis results.
        
        Args:
            report: ThesisAnalysisReport to visualize
            output_directory: Directory to save visualizations
            
        Returns:
            List of paths to generated visualization files
        """
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        # Generate different types of visualizations
        try:
            # 1. Error type distribution
            if report.errors_by_type:
                file_path = self._create_error_type_chart(report, output_dir)
                generated_files.append(file_path)
            
            # 2. Error severity distribution
            if report.errors_by_severity:
                file_path = self._create_severity_chart(report, output_dir)
                generated_files.append(file_path)
            
            # 3. Error density by page
            if report.errors_by_page and len(report.errors_by_page) > 1:
                file_path = self._create_page_density_chart(report, output_dir)
                generated_files.append(file_path)
            
            # 4. Summary dashboard
            file_path = self._create_summary_dashboard(report, output_dir)
            generated_files.append(file_path)
            
        except Exception as e:
            logger.error(f"Error generating visualizations: {e}")
        
        logger.info(f"Generated {len(generated_files)} visualization files")
        return generated_files
    
    def _create_error_type_chart(self, report: ThesisAnalysisReport, output_dir: Path) -> str:
        """Create a bar chart showing error distribution by type."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        types = list(report.errors_by_type.keys())
        counts = list(report.errors_by_type.values())
        
        # Create colors for different error types
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57']
        bar_colors = colors[:len(types)]
        
        bars = ax.bar(types, counts, color=bar_colors, alpha=0.8)
        
        # Customize chart
        ax.set_title('Error Distribution by Type', fontsize=14, fontweight='bold')
        ax.set_xlabel('Error Type')
        ax.set_ylabel('Number of Errors')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        output_path = output_dir / 'error_types.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _create_severity_chart(self, report: ThesisAnalysisReport, output_dir: Path) -> str:
        """Create a pie chart showing error distribution by severity."""
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Order by severity (high, medium, low)
        severity_order = ['high', 'medium', 'low']
        sizes = []
        labels = []
        colors = ['#ff4757', '#ffa502', '#2ed573']  # Red, orange, green
        
        for severity in severity_order:
            count = report.errors_by_severity.get(severity, 0)
            if count > 0:
                sizes.append(count)
                labels.append(f'{severity.title()} ({count})')
        
        if sizes:
            wedges, texts, autotexts = ax.pie(
                sizes, 
                labels=labels, 
                colors=colors[:len(sizes)],
                autopct='%1.1f%%',
                startangle=90
            )
            
            # Improve text appearance
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        
        ax.set_title('Error Distribution by Severity', fontsize=14, fontweight='bold')
        
        output_path = output_dir / 'error_severity.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _create_page_density_chart(self, report: ThesisAnalysisReport, output_dir: Path) -> str:
        """Create a line chart showing error density across pages."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Sort pages by page number
        pages = sorted(report.errors_by_page.keys())
        error_counts = [report.errors_by_page[page] for page in pages]
        
        # Create line plot
        ax.plot(pages, error_counts, marker='o', linewidth=2, markersize=4, color='#ff6b6b')
        ax.fill_between(pages, error_counts, alpha=0.3, color='#ff6b6b')
        
        # Customize chart
        ax.set_title('Error Density by Page', fontsize=14, fontweight='bold')
        ax.set_xlabel('Page Number')
        ax.set_ylabel('Number of Errors')
        
        # Highlight pages with high error counts
        avg_errors = sum(error_counts) / len(error_counts) if error_counts else 0
        threshold = avg_errors * 2
        
        high_error_pages = [(page, count) for page, count in zip(pages, error_counts) if count > threshold]
        
        if high_error_pages:
            for page, count in high_error_pages:
                ax.annotate(f'Page {page}\n({count} errors)', 
                           xy=(page, count), 
                           xytext=(10, 10),
                           textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        plt.tight_layout()
        
        output_path = output_dir / 'error_density.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def _create_summary_dashboard(self, report: ThesisAnalysisReport, output_dir: Path) -> str:
        """Create a comprehensive summary dashboard."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Analysis Summary: {report.document_name}', fontsize=16, fontweight='bold')
        
        # 1. Key metrics (top left)
        ax1.axis('off')
        metrics_text = [
            f"Total Pages: {report.total_pages}",
            f"Total Words: {report.total_words:,}",
            f"Total Errors: {report.total_errors}",
            f"Error Rate: {report.error_rate:.2f}/1000 words",
            f"Processing Time: {report.total_processing_time_seconds:.1f}s",
            f"Pages with Errors: {report.pages_with_errors}"
        ]
        
        for i, text in enumerate(metrics_text):
            ax1.text(0.1, 0.9 - i*0.12, text, fontsize=12, fontweight='bold', 
                    transform=ax1.transAxes)
        
        ax1.set_title('Key Metrics', fontsize=12, fontweight='bold')
        
        # 2. Error types (top right)
        if report.errors_by_type:
            types = list(report.errors_by_type.keys())
            counts = list(report.errors_by_type.values())
            colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57']
            
            ax2.bar(range(len(types)), counts, color=colors[:len(types)], alpha=0.8)
            ax2.set_xticks(range(len(types)))
            ax2.set_xticklabels([t.replace('_', '\n') for t in types], fontsize=9)
            ax2.set_ylabel('Count')
            ax2.set_title('Errors by Type', fontsize=12, fontweight='bold')
        
        # 3. Severity distribution (bottom left)
        if report.errors_by_severity:
            severity_order = ['high', 'medium', 'low']
            sizes = [report.errors_by_severity.get(s, 0) for s in severity_order]
            colors = ['#ff4757', '#ffa502', '#2ed573']
            
            # Filter out zero values
            non_zero = [(s, size, color) for s, size, color in zip(severity_order, sizes, colors) if size > 0]
            if non_zero:
                labels, sizes, colors = zip(*non_zero)
                ax3.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            
            ax3.set_title('Errors by Severity', fontsize=12, fontweight='bold')
        
        # 4. Page error trend (bottom right)
        if report.errors_by_page and len(report.errors_by_page) > 1:
            pages = sorted(report.errors_by_page.keys())
            error_counts = [report.errors_by_page[page] for page in pages]
            
            ax4.plot(pages, error_counts, marker='o', linewidth=2, color='#e74c3c')
            ax4.fill_between(pages, error_counts, alpha=0.3, color='#e74c3c')
            ax4.set_xlabel('Page Number')
            ax4.set_ylabel('Error Count')
            ax4.set_title('Error Trend by Page', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        output_path = output_dir / 'summary_dashboard.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(output_path)
    
    def export_json_report(self, report: ThesisAnalysisReport, output_path: str) -> str:
        """Export the complete report as a JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report.model_dump_json(indent=2))
        
        logger.info(f"JSON report exported: {output_path}")
        return str(output_path)
    
    def create_summary_report(self, report: ThesisAnalysisReport) -> Dict[str, Any]:
        """Create a concise summary of the analysis results."""
        high_severity_errors = report.get_high_severity_errors()
        
        summary = {
            'document_name': report.document_name,
            'analysis_date': report.analysis_timestamp.isoformat(),
            'total_pages': report.total_pages,
            'total_words': report.total_words,
            'total_errors': report.total_errors,
            'error_rate_per_1000_words': round(report.error_rate, 2),
            'processing_time_seconds': round(report.total_processing_time_seconds, 2),
            'pages_with_errors': report.pages_with_errors,
            'high_severity_errors': len(high_severity_errors),
            'errors_by_type': report.errors_by_type,
            'errors_by_severity': report.errors_by_severity,
            'token_usage': report.token_usage,
            'estimated_cost': report.estimated_cost,
            'recommendation': self._generate_recommendation(report)
        }
        
        return summary
    
    def _generate_recommendation(self, report: ThesisAnalysisReport) -> str:
        """Generate a recommendation based on the analysis results."""
        if report.total_errors == 0:
            return "Excellent! No errors detected. The document appears to be well-written."
        
        error_rate = report.error_rate
        high_severity_count = len(report.get_high_severity_errors())
        
        if high_severity_count > 0:
            return f"Immediate attention required: {high_severity_count} high-severity issues found. Focus on addressing these critical errors first."
        elif error_rate > 10:
            return "Significant revision needed: High error rate detected. Consider comprehensive proofreading and content review."
        elif error_rate > 5:
            return "Moderate revision recommended: Several errors found. Review and correct identified issues."
        else:
            return "Minor revisions needed: Low error rate. Quick review should address remaining issues."
    
    def generate_annotated_pdf(
        self, 
        report: ThesisAnalysisReport, 
        original_pdf_path: str, 
        output_path: str
    ) -> str:
        """
        Generate an annotated PDF with errors highlighted and explained directly on the page.
        
        Args:
            report: ThesisAnalysisReport containing the analysis results
            original_pdf_path: Path to the original PDF file
            output_path: Path where the annotated PDF should be saved
            
        Returns:
            Path to the generated annotated PDF file
        """
        original_path = Path(original_pdf_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not original_path.exists():
            raise FileNotFoundError(f"Original PDF not found: {original_pdf_path}")
        
        try:
            # Open the original PDF
            doc = fitz.open(original_pdf_path)
            
            # Define colors for different error severities
            severity_colors = {
                ErrorSeverity.HIGH: (1.0, 0.2, 0.2),      # Red
                ErrorSeverity.MEDIUM: (1.0, 0.6, 0.0),    # Orange
                ErrorSeverity.LOW: (1.0, 1.0, 0.0)        # Yellow
            }
            
            # Track annotations per page to avoid overlaps
            page_annotations = {}
            
            # Process each analysis result
            for result in report.analysis_results:
                for error in result.errors:
                    page_num = error.location.page_number - 1  # Convert to 0-based indexing
                    
                    # Skip if page number is invalid
                    if page_num < 0 or page_num >= len(doc):
                        logger.warning(f"Invalid page number {error.location.page_number} for error: {error.original_text[:50]}...")
                        continue
                    
                    page = doc[page_num]
                    
                    # Initialize page annotation counter
                    if page_num not in page_annotations:
                        page_annotations[page_num] = 0
                    
                    # Get highlight color based on severity
                    highlight_color = severity_colors.get(error.severity, (0.8, 0.8, 0.8))
                    
                    # Add highlight annotation if bounding box is available
                    if error.location.bounding_box:
                        x0, y0, x1, y1 = error.location.bounding_box
                        rect = fitz.Rect(x0, y0, x1, y1)
                        
                        # Add highlight annotation
                        highlight = page.add_highlight_annot(rect)
                        highlight.set_colors(stroke=highlight_color)
                        highlight.update()
                    
                    # Create annotation text
                    annotation_text = self._format_error_annotation(error)
                    
                    # Determine annotation position
                    annotation_y = 50 + (page_annotations[page_num] * 80)  # Offset annotations vertically
                    annotation_point = fitz.Point(50, annotation_y)
                    
                    # Add text annotation (sticky note)
                    text_annot = page.add_text_annot(annotation_point, annotation_text)
                    text_annot.set_info(title=f"VeritaScribe - {error.error_type.title()}")
                    text_annot.update()
                    
                    page_annotations[page_num] += 1
            
            # Add summary page at the beginning
            self._add_summary_page(doc, report)
            
            # Save the annotated PDF
            doc.save(output_path)
            doc.close()
            
            logger.info(f"Annotated PDF generated: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating annotated PDF: {e}")
            raise
    
    def _format_error_annotation(self, error: BaseError) -> str:
        """Format error information for PDF annotation."""
        lines = [
            f"ERROR: {error.error_type.replace('_', ' ').title()}",
            f"Severity: {error.severity.title()}",
            f"",
            f"Original: {error.original_text}",
        ]
        
        if error.suggested_correction:
            lines.extend([
                f"",
                f"Suggested: {error.suggested_correction}"
            ])
        
        lines.extend([
            f"",
            f"Explanation: {error.explanation}",
            f"",
            f"Confidence: {error.confidence_score:.1%}"
        ])
        
        return "\n".join(lines)
    
    def _add_summary_page(self, doc: fitz.Document, report: ThesisAnalysisReport) -> None:
        """Add a summary page at the beginning of the annotated PDF."""
        # Insert a new page at the beginning
        summary_page = doc.new_page(0, width=595, height=842)  # A4 size
        
        # Title
        title_rect = fitz.Rect(50, 50, 545, 100)
        summary_page.insert_textbox(
            title_rect,
            f"VeritaScribe Analysis Summary - {report.document_name}",
            fontsize=18,
            fontname="helv-bold",
            color=(0, 0, 0)
        )
        
        # Analysis date
        date_rect = fitz.Rect(50, 110, 545, 130)
        summary_page.insert_textbox(
            date_rect,
            f"Analysis Date: {report.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            fontsize=12,
            fontname="helv",
            color=(0.3, 0.3, 0.3)
        )
        
        # Key metrics
        metrics_text = [
            f"Total Pages: {report.total_pages}",
            f"Total Words: {report.total_words:,}",
            f"Total Errors: {report.total_errors}",
            f"Error Rate: {report.error_rate:.2f} per 1,000 words",
            f"Processing Time: {report.total_processing_time_seconds:.1f} seconds"
        ]
        
        y_pos = 160
        for metric in metrics_text:
            metric_rect = fitz.Rect(50, y_pos, 545, y_pos + 20)
            summary_page.insert_textbox(
                metric_rect,
                metric,
                fontsize=11,
                fontname="helv",
                color=(0, 0, 0)
            )
            y_pos += 25
        
        # Error breakdown
        if report.errors_by_severity:
            breakdown_title_rect = fitz.Rect(50, y_pos + 20, 545, y_pos + 40)
            summary_page.insert_textbox(
                breakdown_title_rect,
                "Error Breakdown by Severity:",
                fontsize=12,
                fontname="helv-bold",
                color=(0, 0, 0)
            )
            
            y_pos += 60
            severity_order = ['high', 'medium', 'low']
            severity_colors_text = {'high': 'Red', 'medium': 'Orange', 'low': 'Yellow'}
            
            for severity in severity_order:
                count = report.errors_by_severity.get(severity, 0)
                if count > 0:
                    color_name = severity_colors_text[severity]
                    breakdown_rect = fitz.Rect(50, y_pos, 545, y_pos + 20)
                    summary_page.insert_textbox(
                        breakdown_rect,
                        f"• {severity.title()}: {count} errors (highlighted in {color_name})",
                        fontsize=11,
                        fontname="helv",
                        color=(0, 0, 0)
                    )
                    y_pos += 25
        
        # Instructions
        instructions_title_rect = fitz.Rect(50, y_pos + 20, 545, y_pos + 40)
        summary_page.insert_textbox(
            instructions_title_rect,
            "How to Use This Annotated PDF:",
            fontsize=12,
            fontname="helv-bold",
            color=(0, 0, 0)
        )
        
        instructions = [
            "• Errors are highlighted directly on the pages with colored backgrounds",
            "• Click on the sticky note icons to view detailed error explanations",
            "• High severity errors (red) require immediate attention",
            "• Medium severity errors (orange) should be addressed during revision",
            "• Low severity errors (yellow) are minor improvements"
        ]
        
        y_pos += 60
        for instruction in instructions:
            inst_rect = fitz.Rect(50, y_pos, 545, y_pos + 20)
            summary_page.insert_textbox(
                inst_rect,
                instruction,
                fontsize=10,
                fontname="helv",
                color=(0, 0, 0)
            )
            y_pos += 20


def create_report_generator() -> ReportGenerator:
    """Factory function to create a ReportGenerator instance."""
    return ReportGenerator()