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
import argparse
import socket

if __name__ == "__main__":
		
	parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
	parser.add_argument('--do_grip_cmds' , help="Include flag for using grip commands for grip recognitions", action='store_true')
	parser.add_argument('--camera_capture', type=int, help="opencv capture number", default=0)
	parser.add_argument('--no_pinch_lock', help="disallow the grip/pinch locking", action='store_true')
	parser.add_argument('--no_filter', help="remove lpf for raw", action='store_true')
	args = parser.parse_args()
	
	use_grip_cmds = args.do_grip_cmds
	if(use_grip_cmds):
		print("Using grip commmands")
	else:
		print("Using hardloaded commands")
	
	udp_server_addr = ("192.168.29.255", 50134)
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	client_socket.settimeout(1.0)

	#number of hands
	n = 1
	
	lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for the fps counter


	prev_cmd_was_grip = [0,0]
	
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
	cap = cv2.VideoCapture(args.camera_capture)
	cap.set(cv2.CAP_PROP_FPS, 90)
	fps = int(cap.get(5))
	print("fps:",fps)

	with mp_hands.Hands(
			max_num_hands=n,
			model_complexity=0,
			min_detection_confidence=0.66,
			min_tracking_confidence=0.66) as hands:
			
		tprev = cv2.getTickCount()	
				
		warr_fps = [0,0,0]
		
		#paramters for grip overload
		abhlist = []
		for i in range(0,n):
			abh = AbilityHandBridge()
			abh.lock_pinch = False
			if(args.no_filter == True):
				abh.filter_fpos = False
			abhlist.append(abh)
		
		send_upsampling_msg_ts = 0
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
				
				num_writes = 1
				if(len(results.multi_hand_landmarks) == 2 and results.multi_handedness[0].classification[0].index != results.multi_handedness[1].classification[0].index):
					num_writes = 2
				for idx in range(0 , num_writes):
					#log time for plotting
					t = time.time()
					ser_idx = results.multi_handedness[idx].classification[0].index
					if(n == 1):
						ser_idx = 0		#default to 0 if there's only one device connected
					#args.no_pinch_lock
					
					#fpos, warr, hw_b, hb_w, handed_sign, scale, dist_to_thumb = get_fpos(results, mp_hands, fpos, warr)
					abhlist[idx].update(mp_hands, results.multi_hand_landmarks[idx].landmark, results.multi_handedness[idx].classification[0].index)
					#if port:
					
					# Write the finger array out over UART to the hand!
					msg = udp_pkt(abhlist[idx].fpos)
					barr = bytearray(msg)					
					client_socket.sendto(barr, udp_server_addr)
					

					#draw landmarks of the hand we found
					hand_landmarks = results.multi_hand_landmarks[idx]
					mp_drawing.draw_landmarks(
						image,
						hand_landmarks,
						mp_hands.HAND_CONNECTIONS,
						mp_drawing_styles.get_default_hand_landmarks_style(),
						mp_drawing_styles.get_default_hand_connections_style())

					#render a static point in the base frame of the model. Visualization of the position-orientation accuracy.
					#Point should be just in front of the palm. Compensated for handedness
					static_point_b = np.array([4.16, 1.05, -1.47*abhlist[idx].handed_sign, 1])*abhlist[idx].scale			
					static_point_b[3] = 1	#remove scaling that was applied to the immutable '1'
					neutral_thumb_w = abhlist[idx].hw_b.dot(static_point_b)	#get dot position in world coordinates for a visual tag/reference				
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
			cv2.namedWindow('MediaPipe Hands', cv2.WINDOW_FREERATIO)
			cv2.setWindowProperty('MediaPipe Hands',  cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_FREERATIO)
			cv2.imshow('MediaPipe Hands', cv2.flip(image, 1))

			if cv2.waitKey(1) & 0xFF == 27:
				break

			fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
			print (fpsfilt)

	cap.release()