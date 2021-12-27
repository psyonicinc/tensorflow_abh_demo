import cv2
import mediapipe as mp
import time
from matplotlib import animation
from matplotlib import pyplot as plt

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

fig,ax = plt.subplots()

bufwidth = 100
num_lines = 2
lines = []
xbuf = []
ybuf = []

for i in range(num_lines):
	lines.append(ax.plot([],[])[0])
	xbuf.append([])
	ybuf.append([])

for i in range(0, num_lines):	
    for j in range(0,bufwidth):
        xbuf[i].append(0)
        ybuf[i].append(0)

def init(): # required for blitting to give a clean slate.
	for line in lines:
		line.set_data([],[])
	return lines
	
def runcv():
	# For webcam input:
	cap = cv2.VideoCapture(0)
	with mp_hands.Hands(
			max_num_hands=1,
			model_complexity=0,
			min_detection_confidence=0.5,
			min_tracking_confidence=0.33) as hands:
			
		tprev = cv2.getTickCount()	
		fpos = [15,15,15,15,15,-15]
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
			
			
			results = hands.process(image)
			
			
			# Draw the hand annotations on the image.
			#image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
			if results.multi_hand_landmarks:
									
				t = time.time()
				v = results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
				x = v.x
				y = v.y
				z = v.z 
				yield t, x, y

				#for hand_landmarks in results.multi_hand_landmarks:
				hand_landmarks = results.multi_hand_landmarks[0]
				mp_drawing.draw_landmarks(
					image,
					hand_landmarks,
					mp_hands.HAND_CONNECTIONS,
					mp_drawing_styles.get_default_hand_landmarks_style(),
					mp_drawing_styles.get_default_hand_connections_style())

			# Flip the image horizontally for a selfie-view display.
			cv2.imshow('MediaPipe Hands', cv2.flip(image, 1))

			if cv2.waitKey(5) & 0xFF == 27:
				break
			
			print (fps)
			
	cap.release()


x = []
y = []
def animate(args):
	for i in range(0,num_lines):
		del xbuf[i][0]
		del ybuf[i][0]
		xbuf[i].append(args[0])
	ybuf[0].append(args[1])
	ybuf[1].append(args[2])
	ax.relim()
	ax.autoscale_view()
	for i, line in enumerate(lines):
		line.set_data(xbuf[i],ybuf[i])
	return lines
	
anim = animation.FuncAnimation(fig, animate, init_func=init, frames=runcv, interval=0, blit=True,  save_count = 50)
plt.show()