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
from serial.tools import list_ports
from gestures import *
from abh_get_fpos import *

""" 
	Find a serial com port.
"""
com_ports_list = list(list_ports.comports())
port = ""
ser = []
for p in com_ports_list:
	if(p):
		port = p
		print("Found:", port)
		break
if not port:
	print("No port found")

if(port):
	try:
		ser = serial.Serial(port[0],'460800', timeout = 1)
		print ("connected!")
		buf = create_misc_msg(0xC2) # cmd to enable upsampling of the thumb rotator
		ser.write(buf)
	except:
		port = ""
		print("failed to connect")


lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for the fps counter

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

with mp_hands.Hands(
		max_num_hands=1,
		model_complexity=0,
		min_detection_confidence=0.66,
		min_tracking_confidence=0.66) as hands:
		
	tprev = cv2.getTickCount()	
			
	warr_fps = [0,0,0]
	
	#paramters for grip overload
	abh = AbilityHandBridge()
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
		
		image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
					
		results = hands.process(image)
		

		# Draw the hand annotations on the image.
		image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
		if results.multi_hand_landmarks:
			
			#log time for plotting
			t = time.time()
			
			#fpos, warr, hw_b, hb_w, handed_sign, scale, dist_to_thumb = get_fpos(results, mp_hands, fpos, warr)
			abh.update(results, mp_hands)
			if port:
				# Write the finger array out over UART to the hand!
				msg = farr_to_barr(abh.fpos)
				ser.write(msg)
			#print(abh.fpos[4])
			
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
			static_point_b = np.array([4.16, 1.05, -1.47*abh.handed_sign, 1])*abh.scale			
			static_point_b[3] = 1	#remove scaling that was applied to the immutable '1'
			neutral_thumb_w = abh.hw_b.dot(static_point_b)	#get dot position in world coordinates for a visual tag/reference				
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
		
		fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
		print (fpsfilt)
		
cap.release()
if port:
	ser.close()