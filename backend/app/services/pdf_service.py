import os
import pymupdf
from typing import List

class PdfService:
    def extract_pages_as_images(self, pdf_path: str, output_dir: str) -> List[dict]:
        """
        Extracts each page of a PDF as a PNG image.
        Returns a list of dicts with page_number and image_path.
        """
        os.makedirs(output_dir, exist_ok=True)
        doc = pymupdf.open(pdf_path)
        pages_info = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Use high resolution for better OCR (e.g. 300 DPI -> zoom factor ~4)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
            
            image_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
            pix.save(image_path)
            
            pages_info.append({
                "page_number": page_num + 1,
                "image_path": image_path
            })
            
        return pages_info

    def extract_text_page_by_page(self, pdf_path: str) -> List[dict]:
        """
        Extracts text locally from each page of a PDF using PyMuPDF.
        Returns a list of dicts with page_number and text.
        """
        doc = pymupdf.open(pdf_path)
        pages_info = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                pages_info.append({
                    "page_number": page_num + 1,
                    "text": text
                })
                
        return pages_info

pdf_service = PdfService()
