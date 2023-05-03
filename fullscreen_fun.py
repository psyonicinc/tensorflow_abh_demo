import cv2
import numpy as np


image = cv2.imread("default_img.jpg", cv2.IMREAD_COLOR)

# Flip the image horizontally for selfie-view display
cv2.namedWindow('MediaPipe Hands', cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty('MediaPipe Hands',  cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

(x, y, windowWidth, windowHeight) = cv2.getWindowImageRect('MediaPipe Hands')
ydiv = np.floor(windowHeight/image.shape[0])
xdiv = np.floor(windowWidth/image.shape[1])
uniform_mult = np.max([1,np.min([xdiv,ydiv])])

yrem = (windowHeight - image.shape[0]*uniform_mult)
xrem = (windowWidth - image.shape[1]*uniform_mult)
top = int(np.max([0, yrem/2]))
bottom = top
left = int(np.max([0,xrem/2]))
right = left

imgresized = cv2.resize(image, (int(image.shape[1]*uniform_mult),int(image.shape[0]*uniform_mult)), interpolation=cv2.INTER_AREA)
dst = cv2.copyMakeBorder(imgresized,top,bottom,left,right, cv2.BORDER_CONSTANT, None, value = 0)
cv2.imshow('MediaPipe Hands', dst)

cv2.waitKey(0)
cv2.destroyAllWindows()