"""Main analysis pipeline orchestrating PDF processing and LLM analysis."""

import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import asyncio
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from .config import get_settings, get_dspy_config, initialize_system, PROVIDER_MODELS
from .pdf_processor import PDFProcessor
from .llm_modules import AnalysisOrchestrator
from .data_models import (
    TextBlock, 
    AnalysisResult, 
    ThesisAnalysisReport,
    ErrorSeverity
)
import dspy

logger = logging.getLogger(__name__)


class ThesisAnalysisPipeline:
    """Main pipeline for comprehensive thesis analysis."""
    
    def __init__(self):
        """Initialize the analysis pipeline with all necessary components."""
        self.settings = get_settings()
        self.dspy_config = get_dspy_config()
        
        # Initialize components
        self.pdf_processor = PDFProcessor()
        self.analysis_orchestrator = AnalysisOrchestrator()
        
        logger.info("Thesis analysis pipeline initialized")
    
    def _calculate_llm_usage(self) -> tuple[Dict[str, int], float]:
        """
        Calculate token usage and estimated cost from DSPy LLM history.
        
        Returns:
            Tuple of (token_usage_dict, estimated_cost)
        """
        try:
            # Get the current DSPy LM instance
            if not hasattr(dspy.settings, 'lm') or not dspy.settings.lm:
                return {}, 0.0
            
            lm = dspy.settings.lm
            
            # Initialize counters
            total_prompt_tokens = 0
            total_completion_tokens = 0
            
            # Check if the LM has a history attribute
            if hasattr(lm, 'history') and lm.history:
                for call in lm.history:
                    # Extract token counts from call metadata
                    if hasattr(call, 'usage') and call.usage:
                        total_prompt_tokens += getattr(call.usage, 'prompt_tokens', 0)
                        total_completion_tokens += getattr(call.usage, 'completion_tokens', 0)
                    elif hasattr(call, 'response') and hasattr(call.response, 'usage'):
                        usage = call.response.usage
                        total_prompt_tokens += getattr(usage, 'prompt_tokens', 0)
                        total_completion_tokens += getattr(usage, 'completion_tokens', 0)
            
            total_tokens = total_prompt_tokens + total_completion_tokens
            
            # Calculate cost based on current provider and model
            estimated_cost = self._calculate_cost(
                total_prompt_tokens, 
                total_completion_tokens
            )
            
            # Prepare usage dictionary
            token_usage = {
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'total_tokens': total_tokens
            }
            
            # Clear history to avoid double counting on subsequent runs
            if hasattr(lm, 'history'):
                lm.history.clear()
            
            return token_usage, estimated_cost
            
        except Exception as e:
            logger.warning(f"Failed to calculate LLM usage: {e}")
            return {}, 0.0
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate estimated cost based on current provider and model.
        
        Args:
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            
        Returns:
            Estimated cost in USD
        """
        try:
            provider = self.settings.llm_provider
            model = self.settings.default_model
            
            # Get provider pricing information
            if provider not in PROVIDER_MODELS:
                return 0.0
            
            provider_config = PROVIDER_MODELS[provider]
            pricing = provider_config.get('pricing', {})
            
            # Find pricing for the specific model
            model_pricing = None
            if model in pricing:
                model_pricing = pricing[model]
            elif provider == 'custom':
                # Use default pricing for custom providers
                model_pricing = pricing.get('default', {'prompt': 0.0, 'completion': 0.0})
            
            if not model_pricing:
                logger.warning(f"No pricing information found for {provider}/{model}")
                return 0.0
            
            # Calculate cost (pricing is per 1K tokens)
            prompt_cost = (prompt_tokens / 1000.0) * model_pricing['prompt']
            completion_cost = (completion_tokens / 1000.0) * model_pricing['completion']
            
            total_cost = prompt_cost + completion_cost
            
            return round(total_cost, 6)  # Round to 6 decimal places for precision
            
        except Exception as e:
            logger.warning(f"Failed to calculate cost: {e}")
            return 0.0
    
    def analyze_thesis(
        self, 
        pdf_path: str,
        output_directory: Optional[str] = None,
        citation_style: str = "APA",
        context: str = "academic thesis"
    ) -> ThesisAnalysisReport:
        """
        Perform complete analysis of a thesis PDF document.
        
        Args:
            pdf_path: Path to the PDF file to analyze
            output_directory: Directory to save analysis results (optional)
            citation_style: Expected citation style (APA, MLA, Chicago, etc.)
            context: Document context for analysis
            
        Returns:
            ThesisAnalysisReport containing complete analysis results
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            RuntimeError: If analysis fails
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Starting thesis analysis: {pdf_path.name}")
        
        try:
            # Step 1: Initialize system and LLM
            logger.info("Initializing system configuration...")
            initialize_system()
            
            # Step 2: Extract text blocks from PDF
            logger.info("Extracting text blocks from PDF...")
            text_blocks = self.pdf_processor.extract_text_blocks_from_pdf(str(pdf_path))
            
            if not text_blocks:
                logger.warning("No text blocks extracted from PDF")
                return self._create_empty_report(pdf_path)
            
            logger.info(f"Extracted {len(text_blocks)} text blocks")
            
            # Step 3: Extract bibliography section
            logger.info("Extracting bibliography section...")
            bibliography = self.pdf_processor.extract_bibliography_section(str(pdf_path)) or ""
            
            # Step 4: Get document metadata
            metadata = self.pdf_processor.get_document_metadata(str(pdf_path))
            
            # Step 5: Analyze text blocks
            logger.info("Starting LLM analysis of text blocks...")
            analysis_results = self._analyze_text_blocks(
                text_blocks, 
                bibliography, 
                citation_style, 
                context
            )
            
            # Step 6: Create comprehensive report
            processing_time = time.time() - start_time
            report = self._create_analysis_report(
                pdf_path,
                text_blocks,
                analysis_results,
                processing_time,
                metadata
            )
            
            logger.info(f"Analysis completed in {processing_time:.2f} seconds")
            logger.info(f"Found {report.total_errors} total errors across {report.total_pages} pages")
            
            # Step 7: Save results if output directory specified
            if output_directory:
                self._save_analysis_results(report, output_directory)
            
            return report
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise RuntimeError(f"Thesis analysis failed: {e}")
    
    def _analyze_text_blocks(
        self,
        text_blocks: List[TextBlock],
        bibliography: str,
        citation_style: str,
        context: str
    ) -> List[AnalysisResult]:
        """
        Analyze all text blocks using the configured analysis approach.
        
        Args:
            text_blocks: List of text blocks to analyze
            bibliography: Bibliography section content
            citation_style: Expected citation style
            context: Document context
            
        Returns:
            List of AnalysisResult objects
        """
        if self.settings.parallel_processing:
            return self._analyze_blocks_parallel(
                text_blocks, bibliography, citation_style, context
            )
        else:
            return self._analyze_blocks_sequential(
                text_blocks, bibliography, citation_style, context
            )
    
    def _analyze_blocks_sequential(
        self,
        text_blocks: List[TextBlock],
        bibliography: str,
        citation_style: str,
        context: str
    ) -> List[AnalysisResult]:
        """Analyze text blocks sequentially."""
        analysis_results = []
        
        for i, text_block in enumerate(text_blocks):
            logger.debug(f"Analyzing block {i+1}/{len(text_blocks)} (page {text_block.page_number})")
            
            block_start_time = time.time()
            
            try:
                # Analyze the text block
                errors = self.analysis_orchestrator.analyze_text_block(
                    text_block, bibliography, citation_style, context
                )
                
                # Create analysis result
                processing_time = time.time() - block_start_time
                result = AnalysisResult(
                    text_block=text_block,
                    errors=errors,
                    processing_time_seconds=processing_time
                )
                
                analysis_results.append(result)
                
                # Log progress every 10 blocks
                if (i + 1) % 10 == 0:
                    total_errors = sum(len(r.errors) for r in analysis_results)
                    logger.info(f"Progress: {i+1}/{len(text_blocks)} blocks analyzed, "
                              f"{total_errors} errors found so far")
                
            except Exception as e:
                logger.error(f"Failed to analyze block {i}: {e}")
                # Create empty result for failed analysis
                result = AnalysisResult(
                    text_block=text_block,
                    errors=[],
                    processing_time_seconds=0.0
                )
                analysis_results.append(result)
        
        return analysis_results
    
    def _analyze_blocks_parallel(
        self,
        text_blocks: List[TextBlock],
        bibliography: str,
        citation_style: str,
        context: str
    ) -> List[AnalysisResult]:
        """Analyze text blocks in parallel using ThreadPoolExecutor."""
        analysis_results = []
        max_workers = min(self.settings.max_concurrent_requests, len(text_blocks))
        
        logger.info(f"Starting parallel analysis with {max_workers} workers")
        
        def analyze_single_block(text_block: TextBlock) -> AnalysisResult:
            """Analyze a single text block."""
            block_start_time = time.time()
            
            try:
                errors = self.analysis_orchestrator.analyze_text_block(
                    text_block, bibliography, citation_style, context
                )
                
                processing_time = time.time() - block_start_time
                return AnalysisResult(
                    text_block=text_block,
                    errors=errors,
                    processing_time_seconds=processing_time
                )
                
            except Exception as e:
                logger.error(f"Failed to analyze block {text_block.block_index}: {e}")
                return AnalysisResult(
                    text_block=text_block,
                    errors=[],
                    processing_time_seconds=0.0
                )
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_block = {
                executor.submit(analyze_single_block, block): block 
                for block in text_blocks
            }
            
            # Collect results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(future_to_block)):
                try:
                    result = future.result()
                    analysis_results.append(result)
                    
                    # Log progress
                    if (i + 1) % 10 == 0:
                        logger.info(f"Completed {i+1}/{len(text_blocks)} blocks")
                        
                except Exception as e:
                    block = future_to_block[future]
                    logger.error(f"Analysis failed for block {block.block_index}: {e}")
        
        # Sort results by block index to maintain order
        analysis_results.sort(key=lambda x: x.text_block.block_index)
        
        return analysis_results
    
    def _create_analysis_report(
        self,
        pdf_path: Path,
        text_blocks: List[TextBlock],
        analysis_results: List[AnalysisResult],
        processing_time: float,
        metadata: Dict[str, Any]
    ) -> ThesisAnalysisReport:
        """Create comprehensive analysis report."""
        
        # Calculate token usage and cost
        token_usage, estimated_cost = self._calculate_llm_usage()
        
        # Calculate total pages (get max page number from text blocks)
        total_pages = max(block.page_number for block in text_blocks) if text_blocks else 0
        
        # Create report
        report = ThesisAnalysisReport(
            document_name=pdf_path.name,
            document_path=str(pdf_path),
            total_pages=total_pages,
            total_text_blocks=len(text_blocks),
            analysis_results=analysis_results,
            total_processing_time_seconds=processing_time,
            token_usage=token_usage if token_usage else None,
            estimated_cost=estimated_cost if estimated_cost > 0 else None,
            configuration_used={
                'grammar_analysis_enabled': self.settings.grammar_analysis_enabled,
                'content_analysis_enabled': self.settings.content_analysis_enabled,
                'citation_analysis_enabled': self.settings.citation_analysis_enabled,
                'model': self.settings.default_model,
                'parallel_processing': self.settings.parallel_processing,
                'max_concurrent_requests': self.settings.max_concurrent_requests,
            }
        )
        
        return report
    
    def _create_empty_report(self, pdf_path: Path) -> ThesisAnalysisReport:
        """Create an empty report for cases where no analysis could be performed."""
        return ThesisAnalysisReport(
            document_name=pdf_path.name,
            document_path=str(pdf_path),
            total_pages=0,
            total_text_blocks=0,
            analysis_results=[],
            total_processing_time_seconds=0.0
        )
    
    def _save_analysis_results(self, report: ThesisAnalysisReport, output_directory: str):
        """Save analysis results to files."""
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{report.document_name}_{timestamp}"
        
        # Save JSON report
        json_path = output_path / f"{base_name}_report.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(report.model_dump_json(indent=2))
        
        logger.info(f"Analysis report saved to: {json_path}")


class QuickAnalysisPipeline:
    """Simplified pipeline for quick analysis of small documents or testing."""
    
    def __init__(self):
        self.settings = get_settings()
        self.pdf_processor = PDFProcessor()
        self.analysis_orchestrator = AnalysisOrchestrator()
    
    def quick_analyze(self, pdf_path: str, max_blocks: int = 10) -> ThesisAnalysisReport:
        """
        Perform quick analysis on first N blocks of a document.
        
        Args:
            pdf_path: Path to PDF file
            max_blocks: Maximum number of blocks to analyze
            
        Returns:
            ThesisAnalysisReport with limited analysis
        """
        logger.info(f"Starting quick analysis of {pdf_path} (max {max_blocks} blocks)")
        
        start_time = time.time()
        
        try:
            # Initialize system
            initialize_system()
            
            # Extract limited text blocks
            all_blocks = self.pdf_processor.extract_text_blocks_from_pdf(pdf_path)
            text_blocks = all_blocks[:max_blocks]
            
            if not text_blocks:
                return ThesisAnalysisReport(
                    document_name=Path(pdf_path).name,
                    document_path=pdf_path,
                    total_pages=0,
                    total_text_blocks=0,
                    analysis_results=[]
                )
            
            # Quick analysis (sequential only)
            analysis_results = []
            for text_block in text_blocks:
                errors = self.analysis_orchestrator.analyze_text_block(text_block)
                result = AnalysisResult(text_block=text_block, errors=errors)
                analysis_results.append(result)
            
            # Create report
            processing_time = time.time() - start_time
            total_pages = max(block.page_number for block in all_blocks) if all_blocks else 0
            
            # Calculate token usage and cost
            token_usage, estimated_cost = self._calculate_llm_usage()
            
            report = ThesisAnalysisReport(
                document_name=Path(pdf_path).name,
                document_path=pdf_path,
                total_pages=total_pages,
                total_text_blocks=len(all_blocks),
                analysis_results=analysis_results,
                total_processing_time_seconds=processing_time,
                token_usage=token_usage if token_usage else None,
                estimated_cost=estimated_cost if estimated_cost > 0 else None
            )
            
            logger.info(f"Quick analysis completed: {report.total_errors} errors in {processing_time:.2f}s")
            return report
            
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}")
            raise
    
    def _calculate_llm_usage(self) -> tuple[Dict[str, int], float]:
        """
        Calculate token usage and estimated cost from DSPy LLM history.
        
        Returns:
            Tuple of (token_usage_dict, estimated_cost)
        """
        try:
            # Get the current DSPy LM instance
            if not hasattr(dspy.settings, 'lm') or not dspy.settings.lm:
                return {}, 0.0
            
            lm = dspy.settings.lm
            
            # Initialize counters
            total_prompt_tokens = 0
            total_completion_tokens = 0
            
            # Check if the LM has a history attribute
            if hasattr(lm, 'history') and lm.history:
                for call in lm.history:
                    # Extract token counts from call metadata
                    if hasattr(call, 'usage') and call.usage:
                        total_prompt_tokens += getattr(call.usage, 'prompt_tokens', 0)
                        total_completion_tokens += getattr(call.usage, 'completion_tokens', 0)
                    elif hasattr(call, 'response') and hasattr(call.response, 'usage'):
                        usage = call.response.usage
                        total_prompt_tokens += getattr(usage, 'prompt_tokens', 0)
                        total_completion_tokens += getattr(usage, 'completion_tokens', 0)
            
            total_tokens = total_prompt_tokens + total_completion_tokens
            
            # Calculate cost based on current provider and model
            estimated_cost = self._calculate_cost(
                total_prompt_tokens, 
                total_completion_tokens
            )
            
            # Prepare usage dictionary
            token_usage = {
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'total_tokens': total_tokens
            }
            
            # Clear history to avoid double counting on subsequent runs
            if hasattr(lm, 'history'):
                lm.history.clear()
            
            return token_usage, estimated_cost
            
        except Exception as e:
            logger.warning(f"Failed to calculate LLM usage: {e}")
            return {}, 0.0
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate estimated cost based on current provider and model.
        
        Args:
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            
        Returns:
            Estimated cost in USD
        """
        try:
            provider = self.settings.llm_provider
            model = self.settings.default_model
            
            # Get provider pricing information
            if provider not in PROVIDER_MODELS:
                return 0.0
            
            provider_config = PROVIDER_MODELS[provider]
            pricing = provider_config.get('pricing', {})
            
            # Find pricing for the specific model
            model_pricing = None
            if model in pricing:
                model_pricing = pricing[model]
            else:
                # Try to find a matching model (handle provider prefixes)
                for price_model, price_info in pricing.items():
                    if model.endswith(price_model) or price_model.endswith(model):
                        model_pricing = price_info
                        break
            
            # Calculate cost if pricing is available
            if model_pricing and isinstance(model_pricing, dict):
                prompt_cost = (prompt_tokens / 1000) * model_pricing.get('prompt', 0)
                completion_cost = (completion_tokens / 1000) * model_pricing.get('completion', 0)
                return prompt_cost + completion_cost
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Failed to calculate cost: {e}")
            return 0.0


def create_analysis_pipeline() -> ThesisAnalysisPipeline:
    """Factory function to create a configured analysis pipeline."""
    return ThesisAnalysisPipeline()


def create_quick_pipeline() -> QuickAnalysisPipeline:
    """Factory function to create a quick analysis pipeline."""
    return QuickAnalysisPipeline()


def run_pipeline_test():
    """Test function to verify the complete pipeline works."""
    from .pdf_processor import create_test_pdf
    import tempfile
    import os
    
    try:
        # Create test PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            test_pdf_path = tmp_file.name
        
        create_test_pdf(test_pdf_path)
        
        # Run quick analysis
        pipeline = create_quick_pipeline()
        report = pipeline.quick_analyze(test_pdf_path, max_blocks=3)
        
        print(f"Pipeline test results:")
        print(f"- Document: {report.document_name}")
        print(f"- Pages: {report.total_pages}")
        print(f"- Blocks analyzed: {len(report.analysis_results)}")
        print(f"- Total errors: {report.total_errors}")
        print(f"- Processing time: {report.total_processing_time_seconds:.2f}s")
        
        if report.total_errors > 0:
            print(f"- Error types: {list(report.errors_by_type.keys())}")
            
            # Show first error as example
            first_result = next((r for r in report.analysis_results if r.errors), None)
            if first_result:
                first_error = first_result.errors[0]
                print(f"- Example error: {first_error.error_type} - {first_error.original_text[:50]}...")
        
        # Cleanup
        os.unlink(test_pdf_path)
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        print(f"Pipeline test failed: {e}")
        return False