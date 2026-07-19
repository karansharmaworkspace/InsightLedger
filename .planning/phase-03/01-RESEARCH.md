# Research: Phase 3 — OCR & Scanned Document Processing

## OCR Libraries

### Tesseract OCR
- Open source, most popular
- Good accuracy for clean scans
- Supports 100+ languages
- Python wrapper: pytesseract

### EasyOCR
- Deep learning based
- Better for noisy images
- Supports 80+ languages
- Slower than Tesseract

### PaddleOCR
- Chinese company (Baidu)
- Very accurate
- Good for Asian languages
- Newer, less community support

### Recommendation
- **Tesseract** for most cases (fast, reliable)
- **EasyOCR** for noisy/low-quality scans

## Image Preprocessing

### Common Techniques
1. **Grayscale**: Convert to single channel
2. **Binarization**: Black and white (Otsu's method)
3. **Noise reduction**: Gaussian blur, median filter
4. **Deskewing**: Correct rotation
5. **Contrast enhancement**: CLAHE

### OpenCV Functions
- `cv2.cvtColor()` - Color conversion
- `cv2.threshold()` - Binarization
- `cv2.GaussianBlur()` - Noise reduction
- `cv2.warpAffine()` - Rotation

## Confidence Scoring

### Tesseract Confidence
- Per-character confidence (0-100)
- Average per word/page/document
- Low confidence = need manual review

### Thresholds
- > 90%: High quality
- 70-90%: Acceptable
- < 70%: Review needed

## Common Pitfalls

1. **Low DPI scans**: Need 300+ DPI for good OCR
2. **Skewed images**: Deskew before OCR
3. **Background noise**: Clean images first
4. **Multiple fonts**: May confuse OCR
5. **Handwriting**: Tesseract struggles with cursive
