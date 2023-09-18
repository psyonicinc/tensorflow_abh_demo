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
from udp_bkst_query import *

if __name__ == "__main__":
		
	parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
	parser.add_argument('--do_grip_cmds' , help="Include flag for using grip commands for grip recognitions", action='store_true')
	parser.add_argument('--camera_capture', type=int, help="opencv capture number", default=0)
	parser.add_argument('--no_pinch_lock', help="disallow the grip/pinch locking", action='store_true')
	parser.add_argument('--no_filter', help="remove lpf for raw", action='store_true')
	parser.add_argument('--no_hose',help="refrain from sending hose activation command",action='store_true')
	parser.add_argument('--sel_ip',help="manually select desired LAN IP if multiple network adapters are present",action='store_true')
	args = parser.parse_args()
	
	use_grip_cmds = args.do_grip_cmds
	if(use_grip_cmds):
		print("Using grip commmands")
	else:
		print("Using hardloaded commands")
	
	
	usr_idx = None
	if(args.sel_ip):
		usr_idx = get_hostip_idx_from_usr()
	
	addrs = []
	#"left"
	hand_port = 34345
	string_address,connected = locate_server_from_bkst_query(hand_port,usr_idx)
	print("piping commands to: "+str(string_address)+" on port: "+str(hand_port))
	udp_server_addr_tmp = (string_address,  hand_port)
	if(connected):
		addrs.append(udp_server_addr_tmp)
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	client_socket.settimeout(0)
		
	#"right"
	hand_port = 23234
	string_address,connected = locate_server_from_bkst_query(hand_port,usr_idx)
	print("piping commands to: "+str(string_address)+" on port: "+str(hand_port))
	udp_server_addr_tmp = (string_address,  hand_port)
	if(connected):
		addrs.append(udp_server_addr_tmp)
	
	#number of hands
	n = len(addrs)
	
	print("using "+str(len(addrs))+" sockets:")
	for a in addrs:
		print(a)
	
	if(n != 0):
	
		if(args.no_hose == False):
			#note: if PPP stuffing is activated on the hand, this is likely unnecessary
			hose_on_cmd = "activate_hose"
			for addr in addrs:
				print("sending command: "+hose_on_cmd+" to: "+str(addr[0])+":"+str(addr[1]))		
				client_socket.sendto(bytearray(hose_on_cmd,encoding="utf8"),addr)

		
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
		#print("fps:",fps)

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
						ser_idx = results.multi_handedness[idx].classification[0].index	#can be 0 or 1
						if(n == 1):
							ser_idx = 0		#default to 0 if there's only one device connected
						#args.no_pinch_lock
						
						#fpos, warr, hw_b, hb_w, handed_sign, scale, dist_to_thumb = get_fpos(results, mp_hands, fpos, warr)
						abhlist[ser_idx].update(mp_hands, results.multi_hand_landmarks[idx].landmark, ser_idx)
						#if port:
						
						# Write the finger array out over UART to the hand!
						msg = farr_to_barr(0x50, abhlist[ser_idx].fpos)
						barr = bytearray(msg)
						
						#loopback. Server (subscriber) expectes straight up floating point with a 32 bit checksum. checksum eval not required
						# dgram = bytearray(udp_pkt(abhlist[0].fpos))	#publish only 1 hand at a time in this context. 
						# print("sending ", dgram)
						client_socket.sendto(barr, addrs[ser_idx])

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
						static_point_b = np.array([4.16, 1.05, -1.47*abhlist[ser_idx].handed_sign, 1])*abhlist[ser_idx].scale			
						static_point_b[3] = 1	#remove scaling that was applied to the immutable '1'
						neutral_thumb_w = abhlist[ser_idx].hw_b.dot(static_point_b)	#get dot position in world coordinates for a visual tag/reference				
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

				t_seconds = ts/cv2.getTickFrequency()
				if(t_seconds > send_upsampling_msg_ts):
					send_upsampling_msg_ts = t_seconds + 10
					for i in range(0,n):
						msg = create_misc_msg(0x50, 0xC2)
						print("sending: ", [ hex(b) for b in msg ], "to ser device ", i)
						barr = bytearray(msg)
						client_socket.sendto(barr, addrs[i])
						# slist[i].write(msg)


				fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
				# print (fpsfilt)
		
		for addr in addrs:
			client_socket.sendto(bytearray("deactivate_hose",encoding="utf8"),addr)
		
		cap.release()