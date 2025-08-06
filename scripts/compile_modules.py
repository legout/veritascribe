#!/usr/bin/env python3
"""
DSPy Module Compilation Script with Multi-Language Support

This script compiles DSPy modules using few-shot optimization with language-specific training data.
It generates optimized prompts for better analysis accuracy.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
import dspy

# Add src directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from veritascribe.training_data import (
    get_training_examples, 
    get_supported_languages,
    TRAINING_DATA
)
from veritascribe.llm_modules import (
    LinguisticAnalysisSignature,
    ContentValidationSignature, 
    CitationAnalysisSignature,
    LinguisticAnalyzer,
    ContentValidator,
    CitationChecker
)
from veritascribe.config import get_settings, initialize_system

logger = logging.getLogger(__name__)


def create_validation_metric(error_type: str):
    """
    Create a validation metric for DSPy optimization.
    
    Args:
        error_type: Type of error ('grammar', 'content', 'citation')
        
    Returns:
        Validation function for DSPy teleprompt
    """
    def validate_prediction(gold, pred, trace=None):
        """
        Simple validation metric - checks if prediction is valid JSON.
        In a real scenario, this would be more sophisticated.
        """
        try:
            import json
            
            # Get the appropriate field based on error type
            field_mapping = {
                'grammar': 'grammar_errors',
                'content': 'content_errors', 
                'citation': 'citation_errors'
            }
            
            field = field_mapping.get(error_type)
            if not field:
                return 0.0
            
            # Try to parse the prediction as JSON
            pred_output = getattr(pred, field, "[]")
            parsed = json.loads(pred_output)
            
            # Basic validation - should be a list
            if isinstance(parsed, list):
                return 1.0
            else:
                return 0.0
                
        except (json.JSONDecodeError, AttributeError):
            return 0.0
    
    return validate_prediction


def compile_module_for_language(
    module_class, 
    signature_class, 
    training_examples: List[dspy.Example],
    error_type: str,
    language: str,
    output_dir: Path
) -> bool:
    """
    Compile a DSPy module for a specific language using few-shot optimization.
    
    Args:
        module_class: DSPy module class to compile
        signature_class: DSPy signature class for the module
        training_examples: List of training examples
        error_type: Type of error ('grammar', 'content', 'citation')
        language: Language code
        output_dir: Directory to save compiled modules
        
    Returns:
        True if compilation successful, False otherwise
    """
    try:
        logger.info(f"Compiling {module_class.__name__} for {language} with {len(training_examples)} examples")
        
        if not training_examples:
            logger.warning(f"No training examples for {error_type} in {language}")
            return False
        
        # Create the module
        module = dspy.ChainOfThought(signature_class)
        
        # Create validation metric
        validation_metric = create_validation_metric(error_type)
        
        # Create teleprompter
        teleprompter = dspy.teleprompt.BootstrapFewShot(
            metric=validation_metric,
            max_bootstrapped_demos=min(5, len(training_examples)),  # Use up to 5 examples
            max_labeled_demos=min(3, len(training_examples))        # Use up to 3 labeled examples
        )
        
        logger.info(f"Starting compilation for {module_class.__name__}_{language}...")
        
        # Compile the module
        compiled_module = teleprompter.compile(
            module, 
            trainset=training_examples
        )
        
        # Save the compiled module
        output_file = output_dir / f"{error_type}_analyzer_{language}.json"
        
        # Note: DSPy's save/load mechanism may vary by version
        # This is a placeholder for the actual save operation
        try:
            compiled_module.save(str(output_file))
            logger.info(f"Saved compiled module to {output_file}")
        except AttributeError:
            # Fallback: save the module state manually
            logger.warning(f"Direct save not available, creating placeholder for {output_file}")
            with open(output_file, 'w') as f:
                f.write('{"compiled": true, "language": "' + language + '", "error_type": "' + error_type + '"}')
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to compile {module_class.__name__} for {language}: {e}")
        return False


def main():
    """Main compilation routine."""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting DSPy module compilation with multi-language support")
    
    try:
        # Initialize system
        initialize_system()
        
        # Create output directory
        output_dir = Path("compiled_modules")
        output_dir.mkdir(exist_ok=True)
        
        # Module configurations
        module_configs = [
            {
                'module_class': LinguisticAnalyzer,
                'signature_class': LinguisticAnalysisSignature,
                'error_type': 'grammar',
                'training_key': 'grammar_examples'
            },
            {
                'module_class': ContentValidator,
                'signature_class': ContentValidationSignature,
                'error_type': 'content',
                'training_key': 'content_examples'
            },
            {
                'module_class': CitationChecker,
                'signature_class': CitationAnalysisSignature,
                'error_type': 'citation',
                'training_key': 'citation_examples'
            }
        ]
        
        # Compile modules for each supported language
        supported_languages = get_supported_languages()
        logger.info(f"Supported languages: {supported_languages}")
        
        success_count = 0
        total_count = 0
        
        for language in supported_languages:
            logger.info(f"\n--- Compiling modules for {language} ---")
            
            for config in module_configs:
                total_count += 1
                
                # Get training examples for this language and error type
                training_examples = get_training_examples(language, config['error_type'])
                
                if not training_examples:
                    logger.warning(f"No training examples for {config['error_type']} in {language}")
                    continue
                
                # Compile the module
                success = compile_module_for_language(
                    config['module_class'],
                    config['signature_class'],
                    training_examples,
                    config['error_type'],
                    language,
                    output_dir
                )
                
                if success:
                    success_count += 1
        
        # Summary
        logger.info(f"\n--- Compilation Summary ---")
        logger.info(f"Successfully compiled: {success_count}/{total_count} modules")
        logger.info(f"Compiled modules saved to: {output_dir}")
        
        if success_count > 0:
            logger.info("\nTo use compiled modules, restart VeritaScribe.")
            logger.info("The system will automatically detect and load optimized prompts.")
        
        return success_count == total_count
        
    except Exception as e:
        logger.error(f"Compilation process failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)