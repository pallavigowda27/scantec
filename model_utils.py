import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2

def get_model():
    return "MockedModel"

import hashlib
import random

def predict_fracture(image):
    """
    Mock prediction based on image brightness. Darker images are more likely to be predicted as fractured.
    Preprocessing that changes brightness will affect the prediction.
    """
    # Calculate average brightness
    img_array = np.array(image)
    mean_brightness = img_array.mean()
    
    # If mean brightness < 120, predict fractured (darker images)
    # If > 120, normal
    # Add some randomness
    threshold = 120 + random.uniform(-10, 10)
    is_fractured = mean_brightness < threshold
    
    prediction = "Fractured" if is_fractured else "Normal (No Fracture Detected)"
    # Confidence based on distance from threshold
    distance = abs(mean_brightness - threshold)
    confidence = min(99.8, 75 + distance * 0.5)  # Higher confidence when farther from threshold
    confidence = round(confidence, 2)
    
    return prediction, confidence

def preprocess_image(image, target_size=(224, 224)):
    """
    Mock preprocessing. Returns standard PIL Image resized.
    """
    img = image.resize(target_size)
    return img

def enhance_image(image, brightness=1.0, contrast=1.0, apply_clahe=False, apply_blur=False, apply_sharpen=False):
    """
    Enhance the image with brightness, contrast, CLAHE, blur, and sharpen.
    """
    # Brightness and contrast
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(brightness)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(contrast)
    
    # Convert to OpenCV for CLAHE, blur, sharpen
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    if apply_clahe:
        lab = cv2.cvtColor(cv_image, cv2.COLOR_BGR2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        cv_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    if apply_blur:
        cv_image = cv2.GaussianBlur(cv_image, (5, 5), 0)
    
    if apply_sharpen:
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        cv_image = cv2.filter2D(cv_image, -1, kernel)
    
    # Convert back to PIL
    enhanced = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
    return enhanced
