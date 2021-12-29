import cv2
import mediapipe as mp
import time
import numpy as np
from matplotlib import animation
from matplotlib import pyplot as plt
from mediapipe.framework.formats import landmark_pb2
from ht_matrix import *

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands




fig,ax = plt.subplots()
plt.setp(ax,ylim = (-np.pi,np.pi))

bufwidth = 100
num_lines = 4
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

def to_vect(v):
	return np.array([v.x, v.y, v.z])
	
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

				base = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.WRIST])
				
				index_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP])
				middle_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP])
				ring_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.RING_FINGER_MCP])
				pinky_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.PINKY_MCP])
								
				index_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP])
				thumb_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.THUMB_TIP])
				thumb_cmc = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.THUMB_CMC])
			
				#get scale. scale is equal to the distance (in 0-1 generalized pixel coordinates) 
				# between the base/wrist position and the MCP position of the index finger
				# we use scale to make mapped hand positions robust to relative pixel distances
				#b2idx_mcp = np.subtract(index_mcp, base)
				#scale = np.sqrt(b2idx_mcp.dot(b2idx_mcp))
				v1 = np.subtract(index_mcp, middle_mcp)
				v2 = np.subtract(middle_mcp, ring_mcp)
				v3 = np.subtract(ring_mcp, pinky_mcp)
				scale = (np.sqrt(v1.dot(v1)) + np.sqrt(v2.dot(v2)) + np.sqrt(v3.dot(v3)))/3
			
				hw_b = np.zeros((4,4))
				vx = np.subtract(index_mcp, base)
				vx = vx/np.sqrt(vx.dot(vx))				
				vyref = np.subtract(pinky_mcp,base)
				vyref = vyref/np.sqrt(vyref.dot(vyref))
				vz = np.cross(vx, vyref)
				vz = vz/np.sqrt(vz.dot(vz))
				vy = np.cross(vz, vx)
				vy = vy/np.sqrt(vy.dot(vy))

				hw_b[0:3, 0] = vx
				hw_b[0:3, 1] = vy
				hw_b[0:3, 2] = vz
				hw_b[0:3, 3] = base
				hw_b[3, 0:4] = np.array([0,0,0,1])
				hb_w = ht_inverse(hw_b)
				
							
				#obtain index mcp angle
				mcp2tip = np.subtract(index_tip,index_mcp)
				norm_idx_mcp = np.sqrt(mcp2tip.dot(mcp2tip))/scale
				fpos[0] = norm_idx_mcp*90+15
				
				
				thumb_tip_b = hb_w.dot(v3_to_v4(thumb_tip))/scale				
				fpos[5] = np.arctan2(thumb_tip_b[2],thumb_tip_b[1])
				
				
				yield t, scale, fpos[0], fpos[5], fpos[4]
								
				#for hand_landmarks in results.multi_hand_landmarks:
				hand_landmarks = results.multi_hand_landmarks[0]
				mp_drawing.draw_landmarks(
					image,
					hand_landmarks,
					mp_hands.HAND_CONNECTIONS,
					mp_drawing_styles.get_default_hand_landmarks_style(),
					mp_drawing_styles.get_default_hand_connections_style())
				
						
				lm = landmark_pb2.NormalizedLandmark()
				lm.x = .5
				lm.y = .5
				lm.z = 0
				l_list = landmark_pb2.NormalizedLandmarkList(
					landmark = [
						lm
					]
				)
				mp_drawing.draw_landmarks(
					image,
					l_list,
					[],
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
	ybuf[2].append(args[3])
	ybuf[3].append(args[4])
	ax.relim()
	ax.autoscale_view(scalex=True, scaley=False)
	for i, line in enumerate(lines):
		line.set_data(xbuf[i],ybuf[i])
	return lines
	
anim = animation.FuncAnimation(fig, animate, init_func=init, frames=runcv, interval=0, blit=True,  save_count = 50)
ax.legend(['scale','idx','tr','tf'])
plt.show()