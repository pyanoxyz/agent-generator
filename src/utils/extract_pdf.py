import io
# import fitz
from typing import Optional, Dict, List
import pdfplumber

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

     
def extract_paragraphs_from_pdf(pdf_bytes: bytes) -> List[str]:
    """
    Extract text from a PDF file while ignoring images.

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        str: Extracted text from the PDF
    """
    full_text = []
    pdf_file = io.BytesIO(pdf_bytes)
    try:
        # Open the PDF file
        with pdfplumber.open(pdf_file) as pdf:
            # Iterate through all pages
            for page in pdf.pages:
                # Extract text from the current page
                text = page.extract_text()
                if text:
                    full_text.append(text)

        # Join all the text with newlines
        return full_text

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None