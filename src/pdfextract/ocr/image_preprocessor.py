from __future__ import annotations

import logging
from PIL import Image, ImageFilter, ImageOps
import numpy as np

from pdfextract.core.config import OCRConfig

logger = logging.getLogger(__name__)


def convert_to_grayscale(img: Image.Image) -> Image.Image:
    """Convert image to grayscale."""
    if img.mode == 'L':
        return img
    return img.convert('L')


def resize_to_dpi(img: Image.Image, current_dpi: int = 72, target_dpi: int = 300) -> Image.Image:
    """Resize image to target DPI."""
    if current_dpi >= target_dpi:
        return img
    scale_factor = target_dpi / current_dpi
    new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def adaptive_threshold(img: Image.Image) -> Image.Image:
    """Simple contrast enhancement / adaptive thresholding."""
    gray = convert_to_grayscale(img)
    img_arr = np.array(gray)
    mean_val = float(np.mean(img_arr))
    threshold = max(80.0, min(210.0, mean_val * 0.9))
    binarized = np.where(img_arr > threshold, 255, 0).astype(np.uint8)
    return Image.fromarray(binarized)


def denoise(img: Image.Image) -> Image.Image:
    """Basic denoising using median filter."""
    return img.filter(ImageFilter.MedianFilter(size=3))


def deskew(img: Image.Image) -> Image.Image:
    """Deskew detection and correction using projection profile."""
    gray = convert_to_grayscale(img)
    img_arr = np.array(gray)
    inverted = 255 - img_arr
    
    # Subsample for speed
    step = max(1, min(img_arr.shape[0] // 500, img_arr.shape[1] // 500))
    sample = inverted[::step, ::step]
    
    angles = np.arange(-3.0, 3.5, 0.5)
    best_angle = 0.0
    max_variance = 0.0
    
    sample_img = Image.fromarray(sample)
    for angle in angles:
        if abs(angle) < 0.01:
            rot_arr = sample
        else:
            rotated = sample_img.rotate(float(angle), resample=Image.Resampling.NEAREST, fillcolor=0)
            rot_arr = np.array(rotated)
        row_sums = np.sum(rot_arr, axis=1)
        variance = float(np.var(row_sums))
        if variance > max_variance:
            max_variance = variance
            best_angle = float(angle)
            
    if abs(best_angle) >= 0.5:
        logger.info(f"Deskewing image by {best_angle}°")
        # Rotate in place without expanding to preserve aspect ratio and coordinates
        return img.rotate(best_angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255)
    return img


def preprocess_image(image: Image.Image, config: OCRConfig | dict | None = None) -> Image.Image:
    """
    Main preprocessing pipeline conditioned on config settings.
    """
    processed = image
    
    use_grayscale = True
    use_threshold = False
    use_deskew = False
    
    if config is not None:
        if isinstance(config, dict):
            use_grayscale = config.get("grayscale", True)
            use_threshold = config.get("adaptive_threshold", False)
            use_deskew = config.get("deskew", False)
        else:
            use_grayscale = getattr(config, "grayscale", True)
            use_threshold = getattr(config, "adaptive_threshold", False)
            use_deskew = getattr(config, "deskew", False)
            
    if use_grayscale:
        processed = convert_to_grayscale(processed)
        
    if use_deskew:
        processed = deskew(processed)
        
    if use_threshold:
        processed = adaptive_threshold(processed)
        
    return processed
