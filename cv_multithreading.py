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
import threading

"""
	Mediapipe setup/initialization
"""
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands


"""globals"""
exit = 0
processing_done = 1
image_ready = 0
image = []


"""
	Processing thread.
	
	Slave to the image thread. Image thread is the provider of data for us to process.
"""
def process_thread():
	global exit
	global processing_done
	global image_ready
	global image

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
	
	
	with mp_hands.Hands(
		max_num_hands=1,
		model_complexity=0,
		min_detection_confidence=0.5,
		min_tracking_confidence=0.33) as hands:
		
		abh = AbilityHandBridge()
	
		while not exit:
			
			while(image_ready == 0):	#spin until we have image data to act on.
				pass # do nothing
					
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
				
			processing_done = 1
	if port:
		ser.close()
	print("Processing Stop")
		
def image_thread():
	global exit
	global processing_done
	global image_ready
	global image

	# For webcam input:
	cap = cv2.VideoCapture(0)
	cap.set(cv2.CAP_PROP_FPS, 90)
	fps = int(cap.get(5))
	print("fps:",fps)
	
	tprev = 0
	warr_fps = [0,0,0]
	lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for the fps counter

	
	while not exit:
			
			
			#fps counter
			ts = cv2.getTickCount()
			tdif = ts-tprev
			tprev = ts
			fps = cv2.getTickFrequency()/tdif

			#filter and print fps count
			fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
			print (fpsfilt)


			#get new frame
			success, image2 = cap.read()
			if not success:
				print("Ignoring empty camera frame.")
				exit = 1
				image_ready = 1
				# If loading a video, use 'break' instead of 'continue'.
				continue

			#spin with timeout to wait for processing to finish
			tstart = cv2.getTickCount()
			while processing_done == 0:
				t = (cv2.getTickCount()-tstart)/cv2.getTickFrequency()
				if(t > 1.1):
					break;

			image=image2	#report image out to the process thread. double buffer needed to prevent race condition
			processing_done = 0		#image is a 'master' thread. process is a 'slave'. We clear processing flag just before we allow it to run again
			image_ready = 1
	
	exit = 1
	image_ready = 1
	
	cap.release()
	print("Capture Stop")

def kill_thread():
	global exit
	global processing_done
	global image_ready
	global image

	input()
	exit = 1

	print("Exit signal sent")
	
if __name__ == "__main__":
	
	t1 = threading.Thread(target=process_thread, args=())
	t2 = threading.Thread(target=image_thread,args=())
	t3 = threading.Thread(target=kill_thread, args=())
	
	t1.start()
	t2.start()
	t3.start()
	
	t1.join()
	t2.join()
	t3.join()
	
	
	