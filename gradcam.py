import cv2
import numpy as np

def generate_mock_gradcam(image, alpha=0.4):
    """
    Generates a mock Grad-CAM heatmap using OpenCV since we are bypassing TF.
    It highlights the edges and high-contrast areas to simulate an ROL.
    """
    # Convert PIL to CV2
    img_cv = np.array(image)
    if img_cv.ndim == 2:
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_GRAY2RGB)
    elif img_cv.shape[2] == 4:
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGBA2RGB)
        
    # Create a simple synthetic heatmap based on edges
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # Thicken edges and blur heavily to look like GradCAM blobs
    kernel = np.ones((15,15), np.uint8)
    dilated_edges = cv2.dilate(edges, kernel, iterations=3)
    heatmap = cv2.GaussianBlur(dilated_edges, (51, 51), 0)
    
    # Normalize heatmap 0-255
    heatmap = cv2.normalize(heatmap, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    # Apply colormap
    heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    
    # Superimpose the heatmap on original image
    superimposed_img = cv2.addWeighted(heatmap_colored, alpha, img_cv, 1 - alpha, 0)
    
    return superimposed_img
