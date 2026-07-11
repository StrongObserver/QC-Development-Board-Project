import os
import cv2

for name in sorted(os.listdir("inputs")):
    path = os.path.join("inputs", name)
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is not None:
        print(f"{path}: {img.shape[1]}x{img.shape[0]}")
