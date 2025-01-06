import io
import fitz
from typing import Optional, Dict, List

async def extract_paragraphs_from_pdf(content: bytes) -> List[str]:
    """
    Extract text content from PDF using PyMuPDF (fitz) with decoding support
    
    Args:
        content: PDF file content as bytes
    
    Returns:
        List of paragraphs with cleaned text
    """
    try:
        # Create stream from bytes
        stream = io.BytesIO(content)
        doc = fitz.open(stream=stream, filetype="pdf")
        
        paragraphs = []
        
        for page in doc:
            # Get the blocks of text
            blocks = page.get_text("blocks")
            
            for block in blocks:
                text = block[4].strip()
                
                # Skip short lines and page numbers
                if len(text) < 30 or re.match(r'^\d+$', text):
                    continue
                    
                # Check if text is encoded (common patterns in the cipher text)
                if '_' in text or text.count('r') > text.count('s'):
                    # Skip encoded version, as we have the decoded version
                    continue
                
                # Clean up text
                text = text.replace('\n', ' ')
                text = re.sub(r'\s+', ' ', text)
                
                if text:
                    paragraphs.append(text)
        
        doc.close()
        return paragraphs
        
    except Exception as e:
        print(f"Error extracting PDF content: {str(e)}")
        return []