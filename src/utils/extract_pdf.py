import io
# import fitz
from typing import Optional, Dict, List
import pdfplumber
import re
# async def extract_paragraphs_from_pdf(content: bytes) -> List[str]:
#     """
#     Extract text content from PDF using PyMuPDF (fitz) with decoding support
    
#     Args:
#         content: PDF file content as bytes
    
#     Returns:
#         List of paragraphs with cleaned text
#     """
#     try:
#         # Create stream from bytes
#         stream = io.BytesIO(content)
#         doc = fitz.open(stream=stream, filetype="pdf")
        
#         paragraphs = []
        
#         for page in doc:
#             # Get the blocks of text
#             blocks = page.get_text("blocks")
            
#             for block in blocks:
#                 text = block[4].strip()
                
#                 # Skip short lines and page numbers
#                 if len(text) < 30 or re.match(r'^\d+$', text):
#                     continue
                    
#                 # Check if text is encoded (common patterns in the cipher text)
#                 if '_' in text or text.count('r') > text.count('s'):
#                     # Skip encoded version, as we have the decoded version
#                     continue
                
#                 # Clean up text
#                 text = text.replace('\n', ' ')
#                 text = re.sub(r'\s+', ' ', text)
                
#                 if text:
#                     paragraphs.append(text)
        
#         doc.close()
#         return paragraphs
        
#     except Exception as e:
#         print(f"Error extracting PDF content: {str(e)}")
#         return []


def clean_text(text: str) -> str:
    """
    Clean and format the extracted text.
    """
    # Split words that are incorrectly joined (camel case separation)
    text = re.sub(r'(?<!^)(?=[A-Z][a-z])', ' ', text)
    
    # Fix common spacing issues
    text = re.sub(r'(?<=\w)\.(?=\w)', '. ', text)  # Add space after period
    text = re.sub(r'(?<=\w),(?=\w)', ', ', text)   # Add space after comma
    text = re.sub(r'\s+', ' ', text)               # Remove multiple spaces
    
    # Fix specific patterns in your text
    text = text.replace('(cid:', ' (cid:')
    text = text.replace('github.', 'github.')
    
    # Split joined words
    def split_words(match):
        word = match.group(0)
        return ' '.join(re.findall('[A-Z][a-z]*', word))
    
    text = re.sub(r'[A-Z][a-z]+(?=[A-Z])', split_words, text)
    
    return text.strip()

def extract_paragraphs_from_pdf(pdf_bytes: bytes) -> List[str]:
    """
    Extract text from a PDF file while preserving proper formatting.
    """
    full_text = []
    pdf_file = io.BytesIO(pdf_bytes)
    
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                # Extract text with custom settings
                text = page.extract_text(
                    layout=True,
                    x_tolerance=2,
                    y_tolerance=2
                )
                
                if text:
                    # Clean and format the text
                    cleaned_text = clean_text(text)
                    
                    # Additional formatting for specific patterns in your resume
                    cleaned_text = re.sub(r'(?<=\d)–(?=\d)', ' – ', cleaned_text)  # Fix date ranges
                    cleaned_text = re.sub(r'(?<=\w)•(?=\w)', ' • ', cleaned_text)  # Fix bullet points
                    
                    full_text.append(cleaned_text)
            
            return full_text
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None