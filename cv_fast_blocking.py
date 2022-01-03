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
		min_detection_confidence=0.5,
		min_tracking_confidence=0.33) as hands:
		
	tprev = cv2.getTickCount()	
			
	warr_fps = [0,0,0]
	
	#paramters for grip overload
	abh = AbilityHandBridge()
	
	try:
		while cap.isOpened():
			
			#fps counter
			ts = cv2.getTickCount()
			tdif = ts-tprev
			tprev = ts
			fps = cv2.getTickFrequency()/tdif

			#get new frame
			success, image = cap.read()
			if not success:
				print("Ignoring empty camera frame.")
				# If loading a video, use 'break' instead of 'continue'.
				continue
	
			#process hands
			image.flags.writeable = False	#improves performance
			#image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
			results = hands.process(image)
			
			#convert positions if hand is found
			if results.multi_hand_landmarks:
				
				#log time for plotting
				t = time.time()
				
				#get finger positions. write to uart
				abh.update(results, mp_hands)
				if port:
					# Write the finger array out over UART to the hand!
					msg = farr_to_barr(abh.fpos)
					ser.write(msg)
			
			
			#filter and print fps count
			fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
			print (fpsfilt)
					
	except KeyboardInterrupt:
		print("Stopping...")
		pass
cap.release()
if port:
	ser.close()