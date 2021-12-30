import cv2
import mediapipe as mp
import time
import numpy as np
from matplotlib import animation
from matplotlib import pyplot as plt
from vect_tools import *
from rtfilt import *
from abh_api_core import *
from scipy import signal
import serial

"""
	Design the low pass filter we will use on the angle outputs.
	NOTE:
		1. fs is entered here. This is the estimated update frequency of our loop.
			might not be accurate! depends on our actual FPS. Hz
		2. Cutoff is entered here as Wn. Units are in Hz (bc. fs is in hz also)
		
		N must be 2 for this filter to be valid. N greater than 2 yields 2 sections, 
		and we're only doing 1 section.
		
	Higher values of Wn -> less aggressive filtering.
	Lower values of Wn -> more aggressive filtering.
	Wn must be greater than 0 and less than nyquist (Fs/2).
"""
lpf_sos = signal.iirfilter(2, Wn=3, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)

"""
	Program constants. Used for linear mapping offset/gain, etc.
"""
max_fng = 95
min_fng = 10
max_fng_rad = 2.85
min_fng_rad = .1
max_tr = -5
min_tr = -100
max_tr_rad = -.8
min_tr_rad = -2.4
max_tf = 110
min_tf = 10
max_tf_rad = 3.15
min_tf_rad = 2.5

"""
	Mediapipe setup/initialization
"""
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

"""
	Main program loop. 
	
	Does computer vision, angle extraction, filtering.
	For plotting to work, execute as the 'frames' function.
"""

# For webcam input:
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FPS, 90)
fps = int(cap.get(5))
print("fps:",fps)

#open serial port! 
ser = serial.Serial('COM4','460800', timeout = 1)

with mp_hands.Hands(
		max_num_hands=1,
		model_complexity=0,
		min_detection_confidence=0.5,
		min_tracking_confidence=0.33) as hands:
		
	tprev = cv2.getTickCount()	
	fpos = [15,15,15,15,15,-15]
	warr = []
	for f in fpos:
		warr.append([0,0,0])
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
			
			#log time for plotting
			t = time.time()

			#get the handedness
			#index is 1/"Right", 0/"Left". This has something to do with the image being flipped, but we're just gonna flip the label association here
			if(results.multi_handedness[0].classification[0].index == 1):	
				handed_sign = 1 #1 for left, -1 for right. Apply to Z component when doing arctan2
			else:
				handed_sign = -1
			
			#load landmarks into np.arrays, so we can use np to perform vectorized math operations
			base = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.WRIST])
			index_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP])
			middle_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP])
			ring_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.RING_FINGER_MCP])
			pinky_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.PINKY_MCP])
			index_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP])
			middle_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP])
			ring_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.RING_FINGER_TIP])
			pinky_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.PINKY_TIP])			
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
			scale = (mag(v1) + mag(v2) + mag(v3))/3

			#obtain hw_b and hb_w
			hw_b = np.zeros((4,4))
			vx = np.subtract(index_mcp, base)
			vx = vx/mag(vx)
			vyref = np.subtract(pinky_mcp,base)
			vyref = vyref/mag(vyref)
			vz = np.cross(vx, vyref)
			vz = vz/mag(vz)
			vy = np.cross(vz, vx)
			vy = vy/mag(vy)
			hw_b[0:3, 0] = vx
			hw_b[0:3, 1] = vy
			hw_b[0:3, 2] = vz
			hw_b[0:3, 3] = base
			hw_b[3, 0:4] = np.array([0,0,0,1])
			hb_w = ht_inverse(hw_b)
			
			#compute all finger angles
			fngs = [index_tip, middle_tip, ring_tip, pinky_tip]
			mcps = [index_mcp, middle_mcp, ring_mcp, pinky_mcp]
			for i in range(0,4): 
				tip = fngs[i]
				mcp = mcps[i]
				#get index angle
				tip_b = hb_w.dot(v3_to_v4(tip))/scale
				tip_b[3] = 1
				mcp_b = hb_w.dot(v3_to_v4(mcp))/scale
				mcp_b[3] = 1
				o_tip_b = np.subtract(tip_b[0:3], mcp_b[0:3])
				ang = np.arctan2(-handed_sign*o_tip_b[2],o_tip_b[0])
				#map fingers
				fpos[i] = (ang-min_fng_rad)*((max_fng-min_fng)/(max_fng_rad-min_fng_rad))
				fpos[i] = clamp(fpos[i], min_fng, max_fng)
			
			#compute and map thumb angles
			thumb_tip_b = hb_w.dot(v3_to_v4(thumb_tip))/scale		
			thumb_tip_b[3] = 1
			ang_tr = np.arctan2(handed_sign*thumb_tip_b[2],-thumb_tip_b[1])
			ang_tf = np.arctan2(-handed_sign*thumb_tip_b[2],-thumb_tip_b[0])
			#mapthumb flexor
			fpos[5] = (ang_tr - max_tr_rad)*((min_tr-max_tr)/(min_tr_rad-max_tr_rad))
			fpos[5] = clamp(fpos[5], min_tr,max_tr)
			#map thumb rotator
			fpos[4] = (ang_tf-min_tf_rad)*((max_tf-min_tf)/(max_tf_rad-min_tf_rad))
			fpos[4] = clamp(fpos[4],min_tf,max_tf)
			
			
			for i in range(len(fpos)):
				fpos[i], warr[i] = py_sos_iir(fpos[i], warr[i], lpf_sos[0])
			
			msg = farr_to_barr(fpos)
			ser.write(msg)


			#draw landmarks of the hand we found
			hand_landmarks = results.multi_hand_landmarks[0]
			mp_drawing.draw_landmarks(
				image,
				hand_landmarks,
				mp_hands.HAND_CONNECTIONS,
				mp_drawing_styles.get_default_hand_landmarks_style(),
				mp_drawing_styles.get_default_hand_connections_style())

			#render a static point in the base frame of the model. Visualization of the position-orientation accuracy.
			#Point should be just in front of the palm. Compensated for handedness
			static_point_b = np.array([4.16, 1.05, -1.47*handed_sign, 1])*scale			
			static_point_b[3] = 1	#remove scaling that was applied to the immutable '1'
			neutral_thumb_w = hw_b.dot(static_point_b)	#get dot position in world coordinates for a visual tag/reference				
			l_list = landmark_pb2.NormalizedLandmarkList(
				landmark = [
					v4_to_landmark(neutral_thumb_w)
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

		if cv2.waitKey(1) & 0xFF == 27:
			break
		
		#print (fps)
		#print(fps, fpos[0], fpos[1], fpos[2], fpos[3], fpos[4], fpos[5])
		
		
		
cap.release()
ser.close()