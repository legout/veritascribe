"""PDF processing module using PyMuPDF for text extraction with layout preservation."""

import fitz  # PyMuPDF
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import logging
import re

from .data_models import TextBlock, LocationHint
from .config import get_settings

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF document processing and text extraction."""
    
    def __init__(self):
        self.settings = get_settings()
        self.min_block_size = self.settings.min_text_block_size
        self.max_block_size = self.settings.max_text_block_size
    
    def extract_text_blocks_from_pdf(self, pdf_path: str) -> List[TextBlock]:
        """
        Extract text blocks from a PDF document with layout preservation.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of TextBlock objects with content and location information
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            fitz.FileDataError: If PDF file is corrupted or invalid
            PermissionError: If PDF is password protected
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        text_blocks = []
        
        try:
            # Open PDF document
            with fitz.open(pdf_path) as doc:
                logger.info(f"Processing PDF: {pdf_path.name} ({len(doc)} pages)")
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_blocks = self._extract_page_blocks(page, page_num + 1)
                    text_blocks.extend(page_blocks)
                    
                    logger.debug(f"Extracted {len(page_blocks)} blocks from page {page_num + 1}")
        
        except fitz.FileDataError as e:
            raise fitz.FileDataError(f"Invalid or corrupted PDF file: {e}")
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise
        
        # Filter and clean text blocks
        cleaned_blocks = self._filter_and_clean_blocks(text_blocks)
        
        logger.info(f"Extracted {len(cleaned_blocks)} valid text blocks from {pdf_path.name}")
        return cleaned_blocks
    
    def _extract_page_blocks(self, page: fitz.Page, page_number: int) -> List[TextBlock]:
        """
        Extract text blocks from a single page.
        
        Args:
            page: PyMuPDF page object
            page_number: 1-indexed page number
            
        Returns:
            List of TextBlock objects for this page
        """
        blocks = []
        
        try:
            # Get text blocks with positioning information
            text_dict = page.get_text("dict")
            
            block_index = 0
            for block in text_dict.get("blocks", []):
                if "lines" not in block:  # Skip image blocks
                    continue
                
                # Extract text from all lines in the block
                block_text = self._extract_text_from_block(block)
                
                if not block_text or len(block_text.strip()) < self.min_block_size:
                    continue
                
                # Get bounding box coordinates
                bbox = block.get("bbox")
                bounding_box = tuple(bbox) if bbox else None
                
                # Create TextBlock object
                text_block = TextBlock(
                    content=block_text,
                    page_number=page_number,
                    bounding_box=bounding_box,
                    block_index=block_index
                )
                
                blocks.append(text_block)
                block_index += 1
        
        except Exception as e:
            logger.warning(f"Error extracting blocks from page {page_number}: {e}")
        
        return blocks
    
    def _extract_text_from_block(self, block: Dict[str, Any]) -> str:
        """
        Extract and clean text from a PyMuPDF text block.
        
        Args:
            block: PyMuPDF block dictionary
            
        Returns:
            Cleaned text content
        """
        lines = []
        
        for line in block.get("lines", []):
            line_text = ""
            for span in line.get("spans", []):
                span_text = span.get("text", "")
                if span_text:
                    line_text += span_text
            
            if line_text.strip():
                lines.append(line_text.strip())
        
        # Join lines with proper spacing
        text = "\n".join(lines)
        
        # Clean up the text
        text = self._clean_extracted_text(text)
        
        return text
    
    def _fix_german_umlauts(self, text: str) -> str:
        """
        Fix corrupted German umlauts that appear as space + base letter.
        
        Args:
            text: Text with potentially corrupted umlauts
            
        Returns:
            Text with restored German umlauts
        """
        if not text:
            return ""
        
        
       # Replace '"a' with 'ä' and '"A' with 'Ä'
        #text = re.sub(r'"a', 'ä', text)
        text = re.sub(r'¨a', 'ä', text)
        text = re.sub(r'“a', 'ä', text)
        #text = re.sub(r'"A', 'Ä', text)
        text = re.sub(r'¨A', 'Ä', text)
        text = re.sub(r'“A', 'Ä', text)

        # Replace '"o' with 'ö' and '"O' with 'Ö'
        text = re.sub(r'"o', 'ö', text)
        text = re.sub(r'¨o', 'ö', text)
        text = re.sub(r'“o', 'ö', text)
        #text = re.sub(r'"O', 'Ö', text)
        text = re.sub(r'¨O', 'Ö', text)
        text = re.sub(r'“O', 'Ö', text)

        # Replace '"u' with 'ü' and '"U' with 'Ü'
        text = re.sub(r'"u', 'ü', text)
        text = re.sub(r'¨u', 'ü', text)
        text = re.sub(r'“u', 'ü', text)
        #text = re.sub(r'"U', 'Ü', text)
        text = re.sub(r'¨U', 'Ü', text)
        text = re.sub(r'“U', 'Ü', text)

        return text
    
    def _remove_line_break_hyphens(self, text: str) -> str:
        """
        Remove hyphens that were inserted at line breaks in German text.
        
        Args:
            text: Text with potential line-break hyphens
            
        Returns:
            Text with line-break hyphens removed
        """
        if not text:
            return ""
        
        # replace hyphens at the end of a line
        text = re.sub(r'-\n(?![ ,])', '', text)

        
        return text
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Step 1: Fix German umlaut corruption
        text = self._fix_german_umlauts(text)
        
        # Step 2: Remove line-break hyphens
        text = self._remove_line_break_hyphens(text)
        
        # Step 3: Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Step 4: Remove common PDF artifacts
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)  # Control characters
        
        # Step 5: Keep German characters and common punctuation
        # Updated regex to preserve German characters: äöüßÄÖÜ
        #text = re.sub(r'[^\w\s\.,;:!?()[\]{}"\'-äöüßÄÖÜ]', ' ', text)
        
        # Step 6: Fix common spacing issues
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)  # Remove space before punctuation

        # Protect URLs and email addresses to avoid inserting spaces within them
        protected = []
        def _mask(match):
            protected.append(match.group(0))
            return f"__PROTECTED_{len(protected)-1}__"
        url_email_pattern = r'\b(?:https?://\S+|www\.\S+|[\w\.-]+@[\w\.-]+\.\w+)\b'
        text = re.sub(url_email_pattern, _mask, text)

        # Ensure proper spacing after punctuation, but not between numbers (e.g., decimals or version numbers)
        def _ensure_space_after_punct(match):
            punct = match.group(1)
            start = match.start(1)
            end = match.end(1)
            prev_char = text[start-1] if start > 0 else ''
            next_char = text[end] if end < len(text) else ''
            # if punctuation is between two digits, leave it as-is
            if prev_char.isdigit() and next_char.isdigit():
                return punct
            return punct + ' '
        text = re.sub(r'([.,;:!?])\s*', _ensure_space_after_punct, text)

        # Restore protected URLs and emails
        for i, original in enumerate(protected):
            text = text.replace(f"__PROTECTED_{i}__", original)

        return text.strip()
    
    def _filter_and_clean_blocks(self, text_blocks: List[TextBlock]) -> List[TextBlock]:
        """
        Filter out irrelevant blocks and clean the remaining ones.
        
        Args:
            text_blocks: List of extracted text blocks
            
        Returns:
            Filtered and cleaned text blocks
        """
        filtered_blocks = []
        
        for block in text_blocks:
            # Skip very short blocks
            if len(block.content.strip()) < self.min_block_size:
                continue
            
            # Skip blocks that are likely headers, footers, or page numbers
            if self._is_header_footer_or_page_number(block.content):
                continue
            
            # Split large blocks if necessary
            if len(block.content) > self.max_block_size:
                split_blocks = self._split_large_block(block)
                filtered_blocks.extend(split_blocks)
            else:
                filtered_blocks.append(block)
        
        return filtered_blocks
    
    def _is_header_footer_or_page_number(self, text: str) -> bool:
        """
        Determine if text block is likely a header, footer, or page number.
        
        Args:
            text: Text content to check
            
        Returns:
            True if likely header/footer/page number
        """
        text_lower = text.lower().strip()
        
        # Check for page numbers (simple patterns)
        if re.match(r'^\d+$', text.strip()):
            return True
        
        if re.match(r'^page\s+\d+', text_lower):
            return True
        
        # Check for common header/footer patterns
        header_footer_patterns = [
            r'^\d+\s*$',  # Just numbers
            r'^chapter\s+\d+',  # Chapter headings
            r'^\d+\.\d+',  # Section numbers
            r'^table\s+of\s+contents',
            r'^references\s*$',
            r'^bibliography\s*$',
            r'^appendix',
        ]
        
        for pattern in header_footer_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Skip very short blocks that are likely not content
        if len(text.strip()) < 20 and not any(char.isalpha() for char in text):
            return True
        
        return False
    
    def _split_large_block(self, block: TextBlock) -> List[TextBlock]:
        """
        Split a large text block into smaller chunks.
        
        Args:
            block: TextBlock to split
            
        Returns:
            List of smaller TextBlock objects
        """
        text = block.content
        chunks = []
        
        # Try to split at sentence boundaries first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            if len(current_chunk + sentence) <= self.max_block_size:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    # Create new TextBlock for this chunk
                    chunk_block = TextBlock(
                        content=current_chunk.strip(),
                        page_number=block.page_number,
                        bounding_box=block.bounding_box,
                        block_index=f"{block.block_index}_{chunk_index}"
                    )
                    chunks.append(chunk_block)
                    chunk_index += 1
                
                current_chunk = sentence + " "
        
        # Add the remaining chunk
        if current_chunk.strip():
            chunk_block = TextBlock(
                content=current_chunk.strip(),
                page_number=block.page_number,
                bounding_box=block.bounding_box,
                block_index=f"{block.block_index}_{chunk_index}"
            )
            chunks.append(chunk_block)
        
        return chunks if chunks else [block]
    
    def extract_bibliography_section(self, pdf_path: str) -> Optional[str]:
        """
        Attempt to extract the bibliography/references section from the PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Bibliography text if found, None otherwise
        """
        try:
            with fitz.open(pdf_path) as doc:
                bibliography_text = ""
                found_bib_section = False
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_text = page.get_text()
                    page_text = self._clean_extracted_text(page_text)
                    
                    # Look for bibliography section headers
                    bib_headers = [
                        r'\b(?:references|bibliography|works\s+cited|sources)\b',
                        r'\b(?:literatur|literaturverzeichnis)\b',  # German
                        r'\b(?:références|bibliographie)\b',  # French
                    ]
                    
                    for header_pattern in bib_headers:
                        if re.search(header_pattern, page_text, re.IGNORECASE):
                            found_bib_section = True
                            bibliography_text += page_text + "\n"
                            break
                    
                    # If we found the bibliography section, continue collecting
                    if found_bib_section:
                        if not any(re.search(pattern, page_text, re.IGNORECASE) for pattern in bib_headers):
                            bibliography_text += page_text + "\n"
                
                return bibliography_text.strip() if bibliography_text else None
        
        except Exception as e:
            logger.warning(f"Error extracting bibliography section: {e}")
            return None
    
    def get_document_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract metadata from the PDF document.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing document metadata
        """
        try:
            with fitz.open(pdf_path) as doc:
                metadata = {
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'subject': doc.metadata.get('subject', ''),
                    'creator': doc.metadata.get('creator', ''),
                    'producer': doc.metadata.get('producer', ''),
                    'creation_date': doc.metadata.get('creationDate', ''),
                    'modification_date': doc.metadata.get('modDate', ''),
                    'page_count': len(doc),
                    'file_size': Path(pdf_path).stat().st_size,
                }
                return metadata
        
        except Exception as e:
            logger.warning(f"Error extracting PDF metadata: {e}")
            return {'page_count': 0, 'file_size': 0}


def create_test_pdf(output_path: str) -> str:
    """
    Create a simple test PDF for development and testing purposes.
    
    Args:
        output_path: Path where the test PDF should be created
        
    Returns:
        Path to the created PDF file
    """
    try:
        # Create a simple PDF with test content
        doc = fitz.open()  # Create new PDF
        
        # Add a page with sample thesis content
        page = doc.new_page()
        
        sample_text = """
        Bachelor Thesis: The Impact of Social Media on Academic Performance
        
        Abstract
        This study examines the relationship between social media usage and academic performance among university students. The research was conducted in 2024 with data from 500 participants.
        
        1. Introduction
        Social media platforms has become an integral part of students' daily lives. However, their impact on academic performance remains a topic of debate among educators and researchers.
        
        The study aims to investigate weather excessive social media use correlates with lower academic achievement.
        
        2. Methodology
        Data was collected through surveys and academic records. The participants was selected randomly from three universities.
        
        3. Results
        The results shows that students who spend more than 3 hours daily on social media tend to have lower GPA scores.
        
        4. Discussion
        These findings suggests that there is a negative correlation between social media usage and academic performance.
        
        References
        Smith, J. (2020). Social Media and Education. Journal of Educational Technology.
        Johnson, M. (2019) The Digital Generation: How Technology Affects Learning.
        """
        
        # Insert text into the page
        text_rect = fitz.Rect(72, 72, 500, 700)  # Text area
        try:
            page.insert_textbox(text_rect, sample_text, fontsize=11, fontname="helvetica")
        except Exception:
            # Fallback to default font if helvetica fails
            page.insert_textbox(text_rect, sample_text, fontsize=11)
        
        # Save the PDF
        doc.save(output_path)
        doc.close()
        
        logger.info(f"Created test PDF: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error creating test PDF: {e}")
        raise