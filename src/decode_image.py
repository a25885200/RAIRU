import base64
import torch
import numpy as np
import cv2
from PIL import Image

def decode_image_with_gpu(screen_data):
    # Decode the base64 image data
    image_data = base64.b64decode(screen_data['image'])
    
    # Convert the image data to a tensor on the GPU
    image_tensor = torch.tensor(list(image_data), dtype=torch.uint8).cuda()
    
    # Transfer the tensor back to CPU and convert to numpy array
    image_array = image_tensor.cpu().numpy()
    
    # Decode the image using OpenCV
    image = cv2.imdecode(np.frombuffer(image_array, dtype=np.uint8), cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Convert to PIL Image
    pil_img = Image.fromarray(image)
    