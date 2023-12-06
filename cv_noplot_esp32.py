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
from PPP_stuffing import *

if __name__ == "__main__":
		
	parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
	parser.add_argument('--do_grip_cmds' , help="Include flag for using grip commands for grip recognitions", action='store_true')
	parser.add_argument('--camera_capture', type=int, help="opencv capture number", default=0)
	parser.add_argument('--no_pinch_lock', help="disallow the grip/pinch locking", action='store_true')
	parser.add_argument('--no_filter', help="remove lpf for raw", action='store_true')
	parser.add_argument('--no_hose',help="refrain from sending hose activation command",action='store_true')
	parser.add_argument('--sel_ip',help="manually select desired LAN IP if multiple network adapters are present",action='store_true')
	parser.add_argument('--parse_reply',help="activate reply parsing",action='store_true')
	parser.add_argument('--loopback',help="flag to indicate looping back all udp traffic",action='store_true')
	parser.add_argument('--stuff', help="byte stuff outgoing data", action='store_true')
	parser.add_argument('--showfps', help="enable fps printing", action='store_true')
	parser.add_argument('--swapports', help="swap the ports, thereby swapping the left-right hand map without having to do it physically", action='store_true')
	parser.add_argument('--hpos_ip', help="set specific ip to send the hand data to. For sending to windows for virtual hand control",default='')
	args = parser.parse_args()
	
	use_grip_cmds = args.do_grip_cmds
	if(use_grip_cmds):
		print("Using grip commmands")
	else:
		print("Using hardloaded commands")
	
	
	usr_idx = None
	if(args.sel_ip):
		usr_idx = get_hostip_idx_from_usr()
	
	
	"""
		Obtain addresses of the ESP32 UART forwarding devices via broadcast-reply method
	"""
	addrs = []
	ports = [34345,23234]
	if(args.loopback == False):
		scanport = 7134
		bkst_ip = get_bkst_ip_from_usr()
		for port in ports:
			targ_addr = scan_split_streams( (bkst_ip,port), 1, port, 7134)	#use a random port to scan with, which avoids collisions with any plotting software that might be monitoring the RX port/split traffic
			if(targ_addr != ''):
				addrs.append(targ_addr)
	else:
		addrs = [('127.0.0.1',ports[0]),('127.0.0.1',ports[1])]	#hardload addrs in case of loopback request
	if(len(addrs) == 0):
		addrs = [('127.0.0.1',ports[0]),('127.0.0.1',ports[1])]	#hardload addrs in case of loopback request
	elif(len(addrs) == 1):
		addrs.append(('127.0.0.1',ports[1]))	#add a looped back address 
	
	if (args.swapports):
		tmp = addrs[0]
		addrs[0] = addrs[1]
		addrs[1] = tmp

	for addr in addrs:
		print("Found: "+addr[0]+":"+str(addr[1]))
	
	#number of hands
	n = len(addrs)
	
	"""
		Create sockets to use for transmistting to the ESP32s. bind to a different set of ports. Important to ensure they aren't +1, because
		configuration of the ESP32's in the hands should be +1 port offset for split port configuration
	"""
	our_port_to_bind_to = [1435,1437]	#configure both as +1, 1435 is us so receiver is 1436, 1437 is us so receiver is 1438
	client_sockets = []
	for i in range(0,n):
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		client_socket.settimeout(0)
		bindip = ('0.0.0.0', our_port_to_bind_to[i])
		print("binding socket "+str(i)+" to "+bindip[0]+":"+str(bindip[1]))
		client_socket.bind(bindip)
		client_sockets.append(client_socket)
	
	
	
	handpos_ip_addr = '127.0.0.1'
	if(args.hpos_ip != ''):
		handpos_ip_addr = args.hpos_ip
		print("Using: "+handpos_ip_addr)
	lhpos_soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	lhpos_soc.settimeout(0)
	lhpos_soc.bind(('0.0.0.0', 7239))	#bind to random ass port
	rhpos_soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	rhpos_soc.settimeout(0)
	rhpos_soc.bind(('0.0.0.0', 7241))	#bind to random ass port
	hpsoc = []
	hpsoc.append(lhpos_soc)
	hpsoc.append(rhpos_soc)
	hps_targs = [(handpos_ip_addr, 7240), (handpos_ip_addr, 7242)]
	
	
	print("using "+str(len(addrs))+" sockets:")
	for a in addrs:
		print(a)
	
	if(n != 0):
	
		if(args.no_hose == False):
			#note: if PPP stuffing is activated on the hand, this is likely unnecessary
			hose_on_cmd = "activate_hose"
			for i in range(0,len(addrs)):
				addr = addrs[i]
				print("sending command: "+hose_on_cmd+" to: "+str(addr[0])+":"+str(addr[1]))		
				client_sockets[i].sendto(bytearray(hose_on_cmd,encoding="utf8"),addr)

		
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
				abh.lock_pinch = (not args.no_pinch_lock) or args.do_grip_cmds
				if(args.no_filter == True):
					abh.filter_fpos = False
				abhlist.append(abh)
			
			send_upsampling_msg_ts = 0
			send_hose_ts = 0
			
			barr = np.uint8(np.zeros(15)).tobytes()
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
				
				t_seconds = ts/cv2.getTickFrequency()

				if (t_seconds > send_hose_ts):
					send_hose_ts = t_seconds + 5
					print("hose")
					hose_on_cmd = "activate_hose"
					client_sockets[i].sendto(bytearray(hose_on_cmd,encoding='utf8'), addrs[i])

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
						abhlist[ser_idx].update(mp_hands, results.multi_hand_landmarks[idx].landmark, results.multi_handedness[idx].classification[0].index)
						#if port:
						
						

						if(abhlist[ser_idx].is_set_grip == 1 and (abhlist[ser_idx].grip_word == 1 or abhlist[ser_idx].grip_word == 3) and use_grip_cmds == 1):
							grip = 0x00
							if(abhlist[ser_idx].grip_word == 1):
								grip = 0x3
							elif(abhlist[ser_idx].grip_word == 3):
								grip = 0x4
							if(prev_cmd_was_grip[ser_idx] == 0):
								msg = bytearray(send_grip_cmd(0x50, grip, 0xFF))
								# slist[ser_idx].write(msg)
								client_sockets[ser_idx].sendto(msg, addrs[ser_idx])
								time.sleep(0.01)
								msg = bytearray(send_grip_cmd(0x50, 0x00, 0xFF))
								# slist[ser_idx].write(msg)
								client_sockets[ser_idx].sendto(msg, addrs[ser_idx])
								time.sleep(0.01)
								prev_cmd_was_grip[ser_idx] = 1
							msg = send_grip_cmd(0x50, grip, 0xFF)
							barr = bytearray(msg)
						else:						
							prev_cmd_was_grip[ser_idx] = 0
							# Write the finger array out over UART to the hand!
							msg = farr_to_dposition(0x50, np.float32(abhlist[ser_idx].fpos), 1)
							if(args.stuff == False):
								barr = bytearray(msg)
							else:
								barr = PPP_stuff(bytearray(msg))
						


						txbuf = bytearray([])
						for r in range(0,4):
							for c in range(0,4):
								fv = abhlist[ser_idx].hw_b[r][c]
								bv = struct.pack('<f', fv)
								txbuf = txbuf + bv
						# print(txbuf.hex())
						# print("hpos: "+str(abhlist[ser_idx].hw_b[0][3])+", "+str(abhlist[ser_idx].hw_b[1][3])+", "+str(abhlist[ser_idx].hw_b[2][3]))
						xyz,rpy = get_xyz_rpy(abhlist[ser_idx].hw_b[0:3][0:3])
						# print("rpy= "+str(rpy[0])+", "+str(rpy[1])+", "+str(rpy[2]))
						hpsoc[ser_idx].sendto(txbuf, hps_targs[ser_idx])
						
						
							
		
						#loopback. Server (subscriber) expectes straight up floating point with a 32 bit checksum. checksum eval not required
						# dgram = bytearray(udp_pkt(abhlist[0].fpos))	#publish only 1 hand at a time in this context. 
						# print("sending ", dgram)
						# print(bytes(barr).hex())
						client_sockets[ser_idx].sendto(barr, addrs[ser_idx])
						if(args.loopback == False):
							client_sockets[ser_idx].sendto(barr, ('127.0.0.1', addrs[ser_idx][1]))

						if(args.parse_reply):
							try:
								pkt,addr = client_sockets[ser_idx].recvfrom(512)
								if(len(pkt) != 0):
									rPos,rI,rV,rFSR = parse_hand_data(pkt)		
									tlen = rPos.size + rI.size + rV.size + rFSR.size
									if(tlen != 0):
										print(str(np.int16(rPos))+str(rI)+str(np.int16(rV))+str(rFSR))
									else:
										print(pkt)
							except BlockingIOError:	#ignore nonblocking read errors
								pass


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
				else:
					if(args.loopback == False):
						for i in range(0,len(client_sockets)):	#continue sending the last data frame out, even if the hand is out of frame
							client_sockets[i].sendto(barr, addrs[i])

					
				# Flip the image horizontally for a selfie-view display.
				cv2.namedWindow('MediaPipe Hands', cv2.WINDOW_FREERATIO)
				cv2.setWindowProperty('MediaPipe Hands',  cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_FREERATIO)
				cv2.imshow('MediaPipe Hands', cv2.flip(image, 1))

				if cv2.waitKey(1) & 0xFF == 27:
					break

				if(args.loopback == False):
					if(t_seconds > send_upsampling_msg_ts):
						send_upsampling_msg_ts = t_seconds + 10
						for i in range(0,n):
							msg = create_misc_msg(0x50, 0xC2)
							print("sending: ", [ hex(b) for b in msg ], "to ser device ", i)
							filter_msg = bytearray(msg)
							client_sockets[i].sendto(filter_msg, addrs[i])
							# slist[i].write(msg)


				fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
				if(args.showfps):
					print (fpsfilt)
		
		for i in range(0,len(addrs)):
			addr = addrs[i]
			client_socket.sendto(bytearray("deactivate_hose",encoding="utf8"),addr)
		
		cap.release()