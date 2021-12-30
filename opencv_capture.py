import cv2

tprev = cv2.getTickCount()

# For webcam input:
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FPS, 90)
fps = int(cap.get(5))
print("fps:",fps)

while cap.isOpened():

	ts = cv2.getTickCount()
	tdif = ts-tprev
	tprev = ts
	fps = cv2.getTickFrequency()/tdif
	
	success, image = cap.read()
	
	if not success:
		print("Ignoring empty camera frame.")
		# If loading a video, use 'break' instead of 'continue'.
		continue

	# To improve performance, optionally mark the image as not writeable to
	# pass by reference.
	image.flags.writeable = False
	#image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
	
	cv2.imshow('MediaPipe Hands', cv2.flip(image, 1))

	if cv2.waitKey(5) & 0xFF == 27:
		break
	
	print (fps)
		
cap.release()
