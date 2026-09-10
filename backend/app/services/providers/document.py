import os
from abc import ABC, abstractmethod
from google import genai

class DocumentProcessor(ABC):
    @abstractmethod
    async def process_full_pdf(self, file_path: str, mime_type: str = "application/pdf") -> str:
        pass

class GeminiDocumentProcessor(DocumentProcessor):
    def __init__(self):
        # We can use the LLM key for vision tasks as well
        api_key = os.getenv("GEMINI_LLM_API_KEY") or os.getenv("GEMINI_EMBEDDING_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    async def process_full_pdf(self, file_path: str, mime_type: str = "application/pdf") -> str:
        import asyncio
        import json
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                uploaded_file = self.client.files.upload(file=file_path, config={'mime_type': mime_type})
                
                prompt = """
                Extract all text from this legal document exactly as it appears. 
                Maintain the original language (English, Gujarati, Hindi, etc).
                If there are handwritten annotations, include them if readable.
                IMPORTANT: You must prefix the text of EVERY single page with the exact text: "--- PAGE X ---" where X is the page number.
                Do not summarize. Just provide the exact extracted text exactly as written.
                """
                
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[uploaded_file, prompt]
                )
                
                return response.text
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"Error cause 429 (Attempt {attempt+1}/{max_retries})...")
                    await asyncio.sleep(30)
                else:
                    print(f"Error OCRing PDF with Gemini: {e}")
                    return ""
        return ""

class NvidiaDocumentProcessor(DocumentProcessor):
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    async def process_full_pdf(self, file_path: str, mime_type: str = "application/pdf") -> str:
        if not self.api_key:
            print("NVIDIA_API_KEY is not set.")
            return ""

        import fitz
        import base64
        import asyncio
        import aiohttp
        
        doc = fitz.open(file_path)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        async def fetch_page(session, i, b64_img):
            prompt = "Extract all text from this page exactly as it appears. Do not summarize. Output ONLY the raw text from the page."
            payload = {
                "model": "meta/llama-3.2-11b-vision-instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                "frequency_penalty": 0,
                "max_tokens": 512,
                "presence_penalty": 0,
                "temperature": 1,
                "top_p": 1
            }
            
            for attempt in range(3):
                try:
                    async with session.post(self.invoke_url, headers=headers, json=payload) as response:
                        if response.status == 429:
                            print(f"Nvidia Rate Limit on page {i+1}. Retrying...")
                            await asyncio.sleep(5)
                            continue
                        if response.status != 200:
                            err_text = await response.text()
                            raise Exception(f"API Error {response.status}: {err_text}")
                        
                        data = await response.json()
                        text = data['choices'][0]['message']['content']
                        return i, text
                except asyncio.CancelledError:
                    print(f"Task cancelled on page {i+1}")
                    raise
                except Exception as e:
                    print(f"Error on page {i+1} attempt {attempt+1}: {type(e).__name__} - {str(e)}")
                    await asyncio.sleep(2)
            return i, ""
            
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = []
            # Semaphore to limit concurrent requests to 1 to prevent NIM Free Tier timeout
            sem = asyncio.Semaphore(1)
            
            async def bounded_fetch(i, b64_img):
                async with sem:
                    return await fetch_page(session, i, b64_img)

            for i in range(len(doc)):
                page = doc[i]
                pix = page.get_pixmap(dpi=72) # Lower DPI to save tokens/bandwidth
                img_data = pix.tobytes("jpeg")
                b64_img = base64.b64encode(img_data).decode("utf-8")
                tasks.append(bounded_fetch(i, b64_img))
                
            results = await asyncio.gather(*tasks)
            
        # Sort results by page number to ensure correct order
        results.sort(key=lambda x: x[0])
        
        full_text = ""
        return full_text

class HybridLocalDocumentProcessor(DocumentProcessor):
    def __init__(self):
        pass

    async def process_full_pdf(self, file_path: str, mime_type: str = "application/pdf") -> str:
        # We will use process_pdf_to_chunks directly instead
        return ""
        
    async def process_pdf_to_chunks(self, file_path: str, document_id: str) -> list:
        import pymupdf
        import pytesseract
        import base64
        import asyncio
        from PIL import Image
        import io
        import re
        import time

        t_load_start = time.perf_counter()
        doc = pymupdf.open(file_path)
        t_load_end = time.perf_counter()
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF] PDF page loading: {t_load_end - t_load_start:.2f}s" + "\n")
        print(f"[PERF] PDF page loading: {t_load_end - t_load_start:.2f}s")
        
        chunks = []
        
        total_pages = len(doc)
        native_pages = 0
        tesseract_pages = 0
        vision_pages = 0
        
        t_native_total = 0.0
        t_tesseract_total = 0.0
        t_vision_total = 0.0
        
        slowest_tesseract_time = 0.0
        slowest_tesseract_page = 0
        
        for i in range(len(doc)):
            page_num = i + 1
            page = doc.load_page(i)
            
            # 1. Native Extraction
            t_nat_start = time.perf_counter()
            native_text = page.get_text()
            t_nat_end = time.perf_counter()
            t_native_total += (t_nat_end - t_nat_start)
            
            # Check if text is usable (e.g., > 50 characters of actual alphanumeric text)
            alphanumeric_count = sum(c.isalnum() for c in native_text)
            
            if alphanumeric_count > 50:
                chunks.append({
                    "document_id": document_id,
                    "page_number": page_num,
                    "page_numbers": [page_num],
                    "text": native_text.strip(),
                    "language": "auto",
                    "extraction_method": "native_pdf",
                    "ocr_status": "success"
                })
                native_pages += 1
                continue
                
            # 2. Tesseract OCR
            t_tess_start = time.perf_counter()
            try:
                # Point pytesseract to the default Windows installation path
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                
                # Get high res image for OCR
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Use Hindi + Gujarati + English
                ocr_text = pytesseract.image_to_string(img, lang="eng+hin+guj")
                alphanumeric_count_ocr = sum(c.isalnum() for c in ocr_text)
                
                t_tess_end = time.perf_counter()
                t_tess = t_tess_end - t_tess_start
                t_tesseract_total += t_tess
                if t_tess > slowest_tesseract_time:
                    slowest_tesseract_time = t_tess
                    slowest_tesseract_page = page_num
                
                if alphanumeric_count_ocr > 50:
                    chunks.append({
                        "document_id": document_id,
                        "page_number": page_num,
                        "page_numbers": [page_num],
                        "text": ocr_text.strip(),
                        "language": "mixed",
                        "extraction_method": "tesseract_ocr",
                        "ocr_status": "success"
                    })
                    tesseract_pages += 1
                    continue
            except Exception as e:
                t_tess_end = time.perf_counter()
                t_tess = t_tess_end - t_tess_start
                t_tesseract_total += t_tess
                if t_tess > slowest_tesseract_time:
                    slowest_tesseract_time = t_tess
                    slowest_tesseract_page = page_num
                print(f"Tesseract failed on page {page_num}: {e}")
                
            # 3. Nvidia Vision Fallback (only for difficult pages)
            t_vis_start = time.perf_counter()
            try:
                import requests
                import base64
                
                pix = page.get_pixmap(dpi=72)
                img_data = pix.tobytes("jpeg")
                b64_img = base64.b64encode(img_data).decode("utf-8")
                
                nvidia_key = os.getenv("NVIDIA_API_KEY")
                if not nvidia_key:
                    raise Exception("NVIDIA_API_KEY not set")
                    
                headers = {
                    "Authorization": f"Bearer {nvidia_key}",
                    "Accept": "application/json"
                }
                
                payload = {
                    "model": "meta/llama-3.2-11b-vision-instruct",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                                {"type": "text", "text": "Extract all text exactly as written. Maintain language. Output ONLY the raw text."}
                            ]
                        }
                    ],
                    "frequency_penalty": 0,
                    "max_tokens": 512,
                    "presence_penalty": 0,
                    "temperature": 1,
                    "top_p": 1
                }
                
                response = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload)
                if response.status_code == 200:
                    nvidia_text = response.json()['choices'][0]['message']['content']
                else:
                    raise Exception(f"Nvidia API returned {response.status_code}: {response.text}")
                
                chunks.append({
                    "document_id": document_id,
                    "page_number": page_num,
                    "page_numbers": [page_num],
                    "text": nvidia_text.strip() if nvidia_text else "",
                    "language": "auto",
                    "extraction_method": "nvidia_vision",
                    "ocr_status": "success" if nvidia_text else "failed"
                })
                vision_pages += 1
            except Exception as e:
                print(f"Nvidia Fallback failed on page {page_num}: {e}")
                chunks.append({
                    "document_id": document_id,
                    "page_number": page_num,
                    "page_numbers": [page_num],
                    "text": "",
                    "language": "auto",
                    "extraction_method": "failed",
                    "ocr_status": "failed"
                })
            finally:
                t_vis_end = time.perf_counter()
                t_vision_total += (t_vis_end - t_vis_start)

        with open("perf.log", "a") as f_log: f_log.write(f"[PERF] PyMuPDF native extraction total: {t_native_total:.2f}s" + "\n")
        print(f"[PERF] PyMuPDF native extraction total: {t_native_total:.2f}s")
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF] Tesseract OCR total: {t_tesseract_total:.2f}s" + "\n")
        print(f"[PERF] Tesseract OCR total: {t_tesseract_total:.2f}s")
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF] NVIDIA Vision fallback total: {t_vision_total:.2f}s" + "\n")
        print(f"[PERF] NVIDIA Vision fallback total: {t_vision_total:.2f}s")
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF] OCR Stats: total pages: {total_pages}, native-text pages: {native_pages}, Tesseract pages: {tesseract_pages}, NVIDIA Vision fallback pages: {vision_pages}" + "\n")
        print(f"[PERF] OCR Stats: total pages: {total_pages}, native-text pages: {native_pages}, Tesseract pages: {tesseract_pages}, NVIDIA Vision fallback pages: {vision_pages}")
        if tesseract_pages > 0:
            with open("perf.log", "a") as f_log: f_log.write(f"[PERF] average Tesseract time/page: {t_tesseract_total / tesseract_pages:.2f}s" + "\n")
            print(f"[PERF] average Tesseract time/page: {t_tesseract_total / tesseract_pages:.2f}s")
        if slowest_tesseract_page > 0:
            with open("perf.log", "a") as f_log: f_log.write(f"[PERF] slowest Tesseract page: {slowest_tesseract_page} ({slowest_tesseract_time:.2f}s)" + "\n")
            print(f"[PERF] slowest Tesseract page: {slowest_tesseract_page} ({slowest_tesseract_time:.2f}s)")
        if vision_pages > 0:
            with open("perf.log", "a") as f_log: f_log.write(f"[PERF] average Vision time/page: {t_vision_total / vision_pages:.2f}s" + "\n")
            print(f"[PERF] average Vision time/page: {t_vision_total / vision_pages:.2f}s")

        return chunks


