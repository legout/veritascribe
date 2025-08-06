"""Main CLI interface for VeritaScribe using Typer."""

import logging
import sys
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .config import get_settings, initialize_system, get_dspy_config, PROVIDER_MODELS
from .pipeline import create_analysis_pipeline, create_quick_pipeline
from .report_generator import create_report_generator
from .pdf_processor import create_test_pdf
from .data_models import ErrorSeverity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Typer app
app = typer.Typer(
    name="veritascribe",
    help="AI-powered bachelor thesis review tool",
    add_completion=False
)

console = Console()


@app.command()
def analyze(
    pdf_path: str = typer.Argument(..., help="Path to the PDF thesis file to analyze"),
    output_dir: Optional[str] = typer.Option(
        None, 
        "--output", "-o", 
        help="Output directory for reports and visualizations"
    ),
    citation_style: str = typer.Option(
        "APA", 
        "--citation-style", "-c", 
        help="Expected citation style (APA, MLA, Chicago, etc.)"
    ),
    quick: bool = typer.Option(
        False, 
        "--quick", "-q", 
        help="Perform quick analysis (first 10 blocks only)"
    ),
    no_visualizations: bool = typer.Option(
        False, 
        "--no-viz", 
        help="Skip generating visualization charts"
    ),
    verbose: bool = typer.Option(
        False, 
        "--verbose", "-v", 
        help="Enable verbose logging"
    ),
    annotate_pdf: bool = typer.Option(
        False,
        "--annotate", 
        help="Generate an annotated PDF with highlighted errors"
    )
):
    """Analyze a thesis PDF document for quality issues."""
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"[red]Error: PDF file not found: {pdf_path}[/red]")
        raise typer.Exit(1)
    
    if not pdf_file.suffix.lower() == '.pdf':
        console.print(f"[red]Error: File must be a PDF: {pdf_path}[/red]")
        raise typer.Exit(1)
    
    # Set up output directory
    if output_dir is None:
        settings = get_settings()
        output_dir = settings.output_directory
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[blue]Starting analysis of: {pdf_file.name}[/blue]")
    console.print(f"[blue]Output directory: {output_path}[/blue]")
    
    try:
        # Initialize system
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Analysis phase
            task = progress.add_task("Analyzing document...", total=None)
            
            if quick:
                pipeline = create_quick_pipeline()
                report = pipeline.quick_analyze(str(pdf_file), max_blocks=10)
            else:
                pipeline = create_analysis_pipeline()
                report = pipeline.analyze_thesis(
                    str(pdf_file),
                    str(output_path),
                    citation_style=citation_style
                )
            
            progress.update(task, description="Analysis complete!")
        
        # Display results summary
        _display_analysis_summary(report)
        
        # Generate reports
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Generating reports...", total=None)
            
            report_generator = create_report_generator()
            
            # Generate text report
            timestamp = report.analysis_timestamp.strftime("%Y%m%d_%H%M%S")
            report_name = f"{pdf_file.stem}_{timestamp}"
            
            #text_report_path = output_path / f"{report_name}_report.md"
            #report_generator.generate_text_report(report, str(text_report_path))
            
            # Generate JSON export
            json_report_path = output_path / f"{report_name}_data.json"
            report_generator.export_json_report(report, str(json_report_path))
            
            # Generate visualizations
            if not no_visualizations and report.total_errors > 0:
                viz_dir = output_path / f"{report_name}_visualizations"
                viz_files = report_generator.visualize_errors(report, str(viz_dir))
            
            # Generate annotated PDF if requested
            annotated_pdf_path = None
            if annotate_pdf and report.total_errors > 0:
                annotated_pdf_path = output_path / f"{report_name}_annotated.pdf"
                report_generator.generate_annotated_pdf(
                    report, 
                    str(pdf_file),
                    str(annotated_pdf_path)
                )
            
            # Update progress message
            if annotate_pdf and not no_visualizations and report.total_errors > 0:
                progress.update(task, description="Reports, visualizations, and annotated PDF generated!")
            elif annotate_pdf and report.total_errors > 0:
                progress.update(task, description="Reports and annotated PDF generated!")
            elif not no_visualizations and report.total_errors > 0:
                progress.update(task, description="Reports and visualizations generated!")
            else:
                progress.update(task, description="Reports generated!")
        
        # Display output summary
        console.print("\n[green]✓ Analysis completed successfully![/green]")
        console.print(f"\n[bold]Generated files:[/bold]")
        #console.print(f"  📄 Text report: {text_report_path}")
        console.print(f"  📊 JSON data: {json_report_path}")
        
        if not no_visualizations and report.total_errors > 0:
            console.print(f"  📈 Visualizations: {viz_dir}/")
        
        if annotated_pdf_path:
            console.print(f"  📑 Annotated PDF: {annotated_pdf_path}")
        
        # Show recommendations
        summary = report_generator.create_summary_report(report)
        console.print(f"\n[bold]Recommendation:[/bold] {summary['recommendation']}")
        
    except Exception as e:
        console.print(f"[red]Analysis failed: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def quick(
    pdf_path: str = typer.Argument(..., help="Path to the PDF thesis file to analyze"),
    blocks: int = typer.Option(5, "--blocks", "-b", help="Number of text blocks to analyze")
):
    """Perform quick analysis on a subset of the document."""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"[red]Error: PDF file not found: {pdf_path}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]Quick analysis of: {pdf_file.name} (first {blocks} blocks)[/blue]")
    
    try:
        with console.status("[bold green]Analyzing...") as status:
            pipeline = create_quick_pipeline()
            report = pipeline.quick_analyze(str(pdf_file), max_blocks=blocks)
        
        _display_analysis_summary(report, quick=True)
        
    except Exception as e:
        console.print(f"[red]Quick analysis failed: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def demo():
    """Create and analyze a sample thesis document for demonstration."""
    
    console.print("[blue]Creating demo thesis document...[/blue]")
    
    try:
        # Create demo PDF
        demo_pdf = Path("demo_thesis.pdf")
        create_test_pdf(str(demo_pdf))
        
        console.print("[green]✓ Demo document created: demo_thesis.pdf[/green]")
        
        # Check if API key is available for analysis
        settings = get_settings()
        if settings.openai_api_key:
            # Run quick analysis
            console.print("[blue]Running quick analysis...[/blue]")
            
            with console.status("[bold green]Analyzing demo document..."):
                pipeline = create_quick_pipeline()
                report = pipeline.quick_analyze(str(demo_pdf), max_blocks=5)
            
            _display_analysis_summary(report, quick=True)
        else:
            console.print("[yellow]⚠ No OpenAI API key configured - skipping analysis[/yellow]")
            console.print("Set OPENAI_API_KEY environment variable to enable analysis")
        
        console.print(f"\n[green]✓ Demo completed![/green]")
        console.print(f"Demo PDF saved as: {demo_pdf}")
        
        if settings.openai_api_key:
            console.print("You can now run full analysis with: [bold]veritascribe analyze demo_thesis.pdf[/bold]")
        else:
            console.print("Configure API key and run: [bold]veritascribe analyze demo_thesis.pdf[/bold]")
        
    except Exception as e:
        console.print(f"[red]Demo failed: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def config():
    """Display current configuration settings."""
    
    try:
        settings = get_settings()
        dspy_config = get_dspy_config()
        provider_info = dspy_config.get_provider_info()
        
        # Create provider information panel
        formatted_model = provider_info['formatted_model']
        current_model = provider_info['current_model']
        model_display = formatted_model if formatted_model != current_model else current_model
        
        provider_panel = Panel(
            f"[bold]{provider_info['provider_name']}[/bold]\n"
            f"Model: [cyan]{model_display}[/cyan]\n"
            f"Base URL: [dim]{provider_info['base_url'] or 'Default'}[/dim]\n"
            f"API Key: [{'green' if provider_info['api_key_configured'] else 'red'}]"
            f"{'✓ Configured' if provider_info['api_key_configured'] else '✗ Not configured'}[/]\n",
            title="LLM Provider",
            border_style="blue"
        )
        console.print(provider_panel)
        
        # Create configuration table
        table = Table(title="VeritaScribe Configuration")
        table.add_column("Setting", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")
        table.add_column("Description", style="green")
        
        config_items = [
            ("LLM Provider", provider_info['provider_name'], "Active LLM provider"),
            ("Default Model", settings.default_model, "LLM model for analysis"),
            ("Max Tokens", str(settings.max_tokens), "Maximum tokens per request"),
            ("Temperature", str(settings.temperature), "LLM temperature setting"),
            ("Grammar Analysis", "✓" if settings.grammar_analysis_enabled else "✗", "Grammar checking enabled"),
            ("Content Analysis", "✓" if settings.content_analysis_enabled else "✗", "Content validation enabled"),
            ("Citation Analysis", "✓" if settings.citation_analysis_enabled else "✗", "Citation checking enabled"),
            ("Parallel Processing", "✓" if settings.parallel_processing else "✗", "Parallel LLM requests"),
            ("Max Concurrent", str(settings.max_concurrent_requests), "Maximum parallel requests"),
            ("Output Directory", settings.output_directory, "Default output location"),
            ("Max Retries", str(settings.max_retries), "LLM request retry limit"),
        ]
        
        for setting, value, description in config_items:
            table.add_row(setting, value, description)
        
        console.print(table)
        
        # Show recommended models for the provider
        recommended = provider_info.get('recommended_models', {})
        if recommended:
            console.print(f"\n[bold]Recommended Models for {provider_info['provider_name']}:[/bold]")
            for category, model in recommended.items():
                console.print(f"  {category.title()}: [cyan]{model}[/cyan]")
        
        # Model validation
        if not dspy_config.validate_model():
            console.print(f"\n[yellow]⚠ Consider using a recommended model for better compatibility[/yellow]")
        
        # API key status
        if not provider_info['api_key_configured']:
            provider = settings.llm_provider
            if provider == "openai" or provider == "custom":
                console.print(f"\n[red]✗ OpenAI API key not configured[/red]")
                console.print("Set OPENAI_API_KEY environment variable or create .env file")
            elif provider == "openrouter":
                console.print(f"\n[red]✗ OpenRouter API key not configured[/red]")
                console.print("Set OPENROUTER_API_KEY environment variable or create .env file")
            elif provider == "anthropic":
                console.print(f"\n[red]✗ Anthropic API key not configured[/red]")
                console.print("Set ANTHROPIC_API_KEY environment variable or create .env file")
        else:
            console.print(f"\n[green]✓ {provider_info['provider_name']} API key is configured[/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to load configuration: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def optimize_prompts():
    """Optimize DSPy prompts using few-shot learning with multi-language support."""
    
    console.print("[blue]Starting DSPy prompt optimization...[/blue]")
    console.print("This will create optimized prompts for better analysis accuracy.")
    
    # Confirm with user
    confirm = typer.confirm("This process may take several minutes. Continue?")
    if not confirm:
        console.print("Optimization cancelled.")
        raise typer.Exit(0)
    
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # Get the compilation script path
        script_path = Path(__file__).parent.parent.parent / "scripts" / "compile_modules.py"
        
        if not script_path.exists():
            console.print(f"[red]Compilation script not found: {script_path}[/red]")
            raise typer.Exit(1)
        
        # Run the compilation script
        with console.status("[bold green]Compiling modules...") as status:
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("[green]✓ Prompt optimization completed successfully![/green]")
            console.print("\n[bold]Optimized modules created for:[/bold]")
            console.print("  • English grammar, content, and citation analysis")
            console.print("  • German grammar, content, and citation analysis")
            console.print("\n[blue]Restart VeritaScribe to use the optimized prompts.[/blue]")
            
            # Show compilation output if verbose
            if result.stdout:
                console.print("\n[dim]Compilation details:[/dim]")
                console.print(result.stdout)
        else:
            console.print("[red]Prompt optimization failed![/red]")
            if result.stderr:
                console.print(f"[red]Error: {result.stderr}[/red]")
            if result.stdout:
                console.print(f"Output: {result.stdout}")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error during optimization: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def providers():
    """Display information about available LLM providers and models."""
    
    console.print("[blue]Available LLM Providers[/blue]\n")
    
    for provider_id, provider_config in PROVIDER_MODELS.items():
        # Provider header
        provider_names = {
            "openai": "OpenAI",
            "openrouter": "OpenRouter", 
            "anthropic": "Anthropic Claude",
            "custom": "Custom OpenAI-Compatible"
        }
        provider_name = provider_names.get(provider_id, provider_id.title())
        
        console.print(f"[bold cyan]{provider_name}[/bold cyan]")
        console.print(f"Default Model: [green]{provider_config['default']}[/green]")
        
        # Recommended models
        recommended = provider_config['recommended']
        console.print("Recommended Models:")
        for category, model in recommended.items():
            console.print(f"  • {category.title()}: [cyan]{model}[/cyan]")
        
        # Show some example models
        models = provider_config['models']
        if models:
            shown_models = models[:5]  # Show first 5
            console.print(f"Example Models: {', '.join([f'[dim]{m}[/dim]' for m in shown_models])}")
            if len(models) > 5:
                console.print(f"  (and {len(models) - 5} more...)")
        
        # Configuration example
        console.print("Configuration:")
        if provider_id == "openai":
            console.print("  [dim]LLM_PROVIDER=openai[/dim]")
            console.print("  [dim]OPENAI_API_KEY=sk-your-key[/dim]")
        elif provider_id == "openrouter":
            console.print("  [dim]LLM_PROVIDER=openrouter[/dim]")
            console.print("  [dim]OPENROUTER_API_KEY=sk-or-your-key[/dim]")
        elif provider_id == "anthropic":
            console.print("  [dim]LLM_PROVIDER=anthropic[/dim]")
            console.print("  [dim]ANTHROPIC_API_KEY=sk-ant-your-key[/dim]")
        elif provider_id == "custom":
            console.print("  [dim]LLM_PROVIDER=custom[/dim]")
            console.print("  [dim]OPENAI_API_KEY=your-key[/dim]")
            console.print("  [dim]OPENAI_BASE_URL=https://your-endpoint.com/v1[/dim]")
        
        console.print()  # Empty line between providers
    
    # Usage examples
    console.print("[bold]Quick Setup Examples:[/bold]")
    console.print("• Standard OpenAI: [dim]cp .env.example .env && edit OPENAI_API_KEY[/dim]")
    console.print("• OpenRouter (100+ models): [dim]Set LLM_PROVIDER=openrouter && OPENROUTER_API_KEY[/dim]")
    console.print("• Claude directly: [dim]Set LLM_PROVIDER=anthropic && ANTHROPIC_API_KEY[/dim]")
    console.print("• Local Ollama: [dim]Set LLM_PROVIDER=custom && OPENAI_BASE_URL=http://localhost:11434/v1[/dim]")


@app.command()
def test():
    """Run system tests to verify functionality."""
    
    console.print("[blue]Running VeritaScribe system tests...[/blue]")
    
    tests_passed = 0
    tests_total = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Test 1: Configuration loading
        task = progress.add_task("Testing configuration...", total=None)
        tests_total += 1
        try:
            settings = get_settings()
            console.print("[green]✓ Configuration loading works[/green]")
            tests_passed += 1
        except Exception as e:
            console.print(f"[red]✗ Configuration loading failed: {e}[/red]")
        
        # Test 2: PDF processing
        progress.update(task, description="Testing PDF processing...")
        tests_total += 1
        try:
            from .pdf_processor import PDFProcessor
            from tempfile import NamedTemporaryFile
            import os
            
            with NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                create_test_pdf(tmp.name)
                processor = PDFProcessor()
                blocks = processor.extract_text_blocks_from_pdf(tmp.name)
                os.unlink(tmp.name)
                
            if blocks:
                console.print("[green]✓ PDF processing works[/green]")
                tests_passed += 1
            else:
                console.print("[red]✗ PDF processing returned no blocks[/red]")
                
        except Exception as e:
            console.print(f"[red]✗ PDF processing failed: {e}[/red]")
        
        # Test 3: Analysis modules (if API key available)
        progress.update(task, description="Testing analysis modules...")
        tests_total += 1
        try:
            # Check if appropriate API key is configured
            dspy_config = get_dspy_config()
            provider_info = dspy_config.get_provider_info()
            
            if provider_info['api_key_configured']:
                from .llm_modules import test_analysis_modules
                if test_analysis_modules():
                    console.print("[green]✓ Analysis modules work[/green]")
                    tests_passed += 1
                else:
                    console.print("[red]✗ Analysis modules failed[/red]")
            else:
                provider_name = provider_info['provider_name']
                console.print(f"[yellow]⚠ Skipping analysis test (no {provider_name} API key)[/yellow]")
                tests_total -= 1  # Don't count this test
                
        except Exception as e:
            console.print(f"[red]✗ Analysis modules failed: {e}[/red]")
        
        progress.update(task, description="Tests completed!")
    
    # Summary
    console.print(f"\n[bold]Test Results: {tests_passed}/{tests_total} passed[/bold]")
    
    if tests_passed == tests_total:
        console.print("[green]🎉 All tests passed! VeritaScribe is ready to use.[/green]")
    else:
        console.print(f"[red]⚠ {tests_total - tests_passed} tests failed. Please check configuration.[/red]")
        raise typer.Exit(1)


def _display_analysis_summary(report, quick: bool = False):
    """Display a summary of analysis results."""
    
    # Create summary panel
    if quick:
        title = f"Quick Analysis Results: {report.document_name}"
    else:
        title = f"Analysis Results: {report.document_name}"
    
    summary_text = []
    summary_text.append(f"📄 Pages: {report.total_pages}")
    summary_text.append(f"📝 Words: {report.total_words:,}")
    summary_text.append(f"🔍 Text blocks analyzed: {report.total_text_blocks}")
    summary_text.append(f"⚠️  Total errors: {report.total_errors}")
    
    if report.total_words > 0:
        summary_text.append(f"📊 Error rate: {report.error_rate:.2f} per 1,000 words")
    
    summary_text.append(f"⏱️  Processing time: {report.total_processing_time_seconds:.2f}s")
    
    # Add token usage and cost information if available
    if report.token_usage:
        total_tokens = report.token_usage.get('total_tokens', 0)
        summary_text.append(f"🔤 Token usage: {total_tokens:,} tokens")
    
    if report.estimated_cost is not None and report.estimated_cost > 0:
        summary_text.append(f"💰 Estimated cost: ${report.estimated_cost:.4f} USD")
    
    summary_panel = Panel(
        "\n".join(summary_text),
        title=title,
        border_style="blue"
    )
    
    console.print(summary_panel)
    
    # Error breakdown if errors found
    if report.total_errors > 0:
        
        # Error types table
        if report.errors_by_type:
            error_table = Table(title="Errors by Type")
            error_table.add_column("Type", style="cyan")
            error_table.add_column("Count", style="magenta", justify="right")
            error_table.add_column("Percentage", style="green", justify="right")
            
            for error_type, count in sorted(report.errors_by_type.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / report.total_errors * 100) if report.total_errors > 0 else 0
                error_table.add_row(
                    error_type.replace('_', ' ').title(),
                    str(count),
                    f"{percentage:.1f}%"
                )
            
            console.print(error_table)
        
        # Severity breakdown
        if report.errors_by_severity:
            severity_info = []
            for severity in ['high', 'medium', 'low']:
                count = report.errors_by_severity.get(severity, 0)
                if count > 0:
                    icon = "🔴" if severity == 'high' else "🟡" if severity == 'medium' else "🟢"
                    severity_info.append(f"{icon} {severity.title()}: {count}")
            
            if severity_info:
                console.print(f"\n[bold]Severity Breakdown:[/bold] {' | '.join(severity_info)}")
        
        # High priority issues
        high_severity_errors = report.get_high_severity_errors()
        if high_severity_errors:
            console.print(f"\n[red]🚨 {len(high_severity_errors)} high-priority issues require immediate attention![/red]")
    
    else:
        console.print("\n[green]🎉 No errors detected! The document looks great.[/green]")


def main():
    """Main entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()