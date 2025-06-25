from PIL import Image

def take_photo() -> Image.Image:
    image = Image.open("cardinal.jpg")
    return image

# import cv2
# def take_photo() -> Image.Image:
#     cap = cv2.VideoCapture(0)
#     ret, frame = cap.read()
#     cap.release()
#     return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
