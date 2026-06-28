import requests
import cv2
import numpy as np

try:
    response = requests.get("http://127.0.0.1:8001/api/modules")
    print("GET /api/modules:", response.status_code)
    
    # Generate a valid dummy JPEG image
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (250, 250), (0, 255, 0), -1)
    _, img_encoded = cv2.imencode('.jpg', img)
    img_bytes = img_encoded.tobytes()
    
    files = {'file': ('custom_test.jpg', img_bytes, 'image/jpeg')}
    response = requests.post("http://127.0.0.1:8001/api/inference/pointpillars", files=files)
    print("POST /api/inference/pointpillars:", response.status_code)
    try:
        print(response.json())
    except:
        print(response.text)
except Exception as e:
    print("Error:", e)
