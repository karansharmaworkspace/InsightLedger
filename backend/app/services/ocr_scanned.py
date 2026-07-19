"""
Scanned Document OCR Service
Handles Tesseract OCR for scanned PDFs and images.
"""
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract
from PIL import Image
import pdfplumber


@dataclass
class OCRPageResult:
    page_number: int
    text: str
    confidence: float
    word_count: int


@dataclass
class OCRDocumentResult:
    document_id: str
    filename: str
    text: str
    confidence: float
    page_results: List[OCRPageResult]
    is_scanned: bool
    processing_time: float


class ScannedDocumentOCR:
    """OCR service for scanned documents using Tesseract."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR accuracy."""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return binary

    def deskew(self, img: np.ndarray) -> np.ndarray:
        """Correct document skew."""
        coords = np.column_stack(np.where(img > 0))
        if len(coords) < 100:
            return img

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.5:
            return img

        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    def ocr_image(self, img: np.ndarray) -> Dict[str, Any]:
        """Run OCR on a single image."""
        processed = self.preprocess_image(img)
        processed = self.deskew(processed)

        pil_img = Image.fromarray(processed)

        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(pil_img)

        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        word_count = len([w for w in data["text"] if w.strip()])

        return {
            "text": text.strip(),
            "confidence": avg_confidence,
            "word_count": word_count,
        }

    def is_scanned_pdf(self, pdf_path: str) -> bool:
        """Detect if a PDF is scanned (image-based) vs text-based."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                if text and len(text.strip()) > 50:
                    return False
                return True
        except Exception:
            return True

    def ocr_pdf(self, pdf_path: str, document_id: str, filename: str) -> OCRDocumentResult:
        """Process a scanned PDF with OCR."""
        import time
        import fitz  # PyMuPDF

        start_time = time.time()
        page_results = []
        all_text = []

        doc = fitz.open(pdf_path)

        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=300)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 1:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

            result = self.ocr_image(img)

            page_result = OCRPageResult(
                page_number=i + 1,
                text=result["text"],
                confidence=result["confidence"],
                word_count=result["word_count"],
            )
            page_results.append(page_result)
            all_text.append(result["text"])

        doc.close()

        total_confidence = (
            sum(p.confidence for p in page_results) / len(page_results)
            if page_results else 0
        )

        return OCRDocumentResult(
            document_id=document_id,
            filename=filename,
            text="\n\n".join(all_text),
            confidence=total_confidence,
            page_results=page_results,
            is_scanned=True,
            processing_time=time.time() - start_time,
        )

    def ocr_image_file(self, image_path: str, document_id: str, filename: str) -> OCRDocumentResult:
        """Process a single image file with OCR."""
        import time

        start_time = time.time()
        img = cv2.imread(image_path)

        if img is None:
            raise ValueError(f"Could not read image: {image_path}")

        result = self.ocr_image(img)
        elapsed = time.time() - start_time

        page_result = OCRPageResult(
            page_number=1,
            text=result["text"],
            confidence=result["confidence"],
            word_count=result["word_count"],
        )

        return OCRDocumentResult(
            document_id=document_id,
            filename=filename,
            text=result["text"],
            confidence=result["confidence"],
            page_results=[page_result],
            is_scanned=True,
            processing_time=elapsed,
        )
