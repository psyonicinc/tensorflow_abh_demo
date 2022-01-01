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

""" 
	Find a serial com port.
"""
com_ports_list = list(list_ports.comports())
port = ""
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
lpf_sos = signal.iirfilter(2, Wn=3, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for sending the finger data over
lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for the fps counter

"""
	Program constants. Used for linear mapping offset/gain, etc.
"""
outp_fng = [5,100]
inp_fng = [20, 130]
outrange_fng = [5,110]

outp_tr = [-5,-70]
inp_tr = [-50, -75]
outrange_tr = [-5,-110]

outp_tf = [0,60]
inp_tf = [0,40]
outrange_tf = [10, 90]

"""
	Mediapipe setup/initialization
"""
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands


"""
	Figure/plotting initializiation
"""
fig,ax = plt.subplots()
plt.setp(ax,ylim = (-100,100))	#manually set axis y limits
bufwidth = 100
num_lines = 6
lines = []
xbuf = []
ybuf = []
#setup xy buffers to plot and axes
for i in range(num_lines):
	lines.append(ax.plot([],[])[0])
	xbuf.append([])
	ybuf.append([])
#initalize all xy buffers to 0
for i in range(0, num_lines):	
	for j in range(0,bufwidth):
		xbuf[i].append(0)
		ybuf[i].append(0)
#initialization function. needed for the 'blitting' option,
#which is the lowest latency plotting option
def init(): # required for blitting to give a clean slate.
	for line in lines:
		line.set_data([],[])
	return lines

"""
	Main program loop. 
	
	Does computer vision, angle extraction, filtering.
	For plotting to work, execute as the 'frames' function.
"""
def runcv():
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
			
		#initialize array used for writing out hand positions
		fpos = [15,15,15,15,15,-15]
		
		#initialize array used for filtering
		warr = []
		for f in fpos:
			warr.append([0,0,0])
		
		warr_fps = [0,0,0]
		
		#paramters for grip overload
		is_set_grip = 0
		grip_word = 0
		
		
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
				
				index_pip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP])
				middle_pip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP])
				ring_pip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.RING_FINGER_PIP])
				pinky_pip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.PINKY_PIP])
				
				index_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP])
				middle_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP])
				ring_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.RING_FINGER_TIP])
				pinky_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.PINKY_TIP])			
				
				thumb_tip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.THUMB_TIP])
				thumb_cmc = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.THUMB_CMC])
				thumb_mcp = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.THUMB_MCP])
				thumb_ip = to_vect(results.multi_hand_landmarks[0].landmark[mp_hands.HandLandmark.THUMB_IP])
				
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
				
				
				#compute all thumb vectors (to base)
				thumb_tip_b = hb_w.dot(v3_to_v4(thumb_tip))/scale		
				thumb_tip_b[3] = 1
				thumb_ip_b = hb_w.dot(v3_to_v4(thumb_ip))/scale
				thumb_ip_b[3] = 1
				thumb_mcp_b = hb_w.dot(v3_to_v4(thumb_mcp))/scale
				thumb_mcp_b[3] = 1
				thumb_cmc_b = hb_w.dot(v3_to_v4(thumb_cmc))/scale
				thumb_cmc_b[3] = 1
				
				ang_tr = np.arctan2(handed_sign*thumb_ip_b[2],-thumb_ip_b[1])*180/np.pi
				#mapthumb rotator
				fpos[5] = linmap(ang_tr, outp_tr, inp_tr)
				
				
				tip_to_ip_b = np.subtract(thumb_tip_b, thumb_ip_b)				
				ip_to_mcp_b = np.subtract(thumb_ip_b, thumb_mcp_b)
				ang_tf = vect_angle(tip_to_ip_b[0:3], ip_to_mcp_b[0:3])*180/np.pi
				#map thumb flexor
				fpos[4] = linmap(ang_tf, outp_tf, inp_tf)
				
				
				#compute all finger angles
				tips = [index_tip, middle_tip, ring_tip, pinky_tip]
				pips = [index_pip, middle_pip, ring_pip, pinky_pip]
				mcps = [index_mcp, middle_mcp, ring_mcp, pinky_mcp]
				dist_to_thumb = [0, 0, 0, 0, 0, 0]
				for i in range(0,4): 
					tip = tips[i]
					pip = pips[i]
					mcp = mcps[i]
										
					#get index angle
					tip_b = hb_w.dot(v3_to_v4(tip))/scale
					tip_b[3] = 1
					pip_b = hb_w.dot(v3_to_v4(pip))/scale
					pip_b[3] = 1
					mcp_b = hb_w.dot(v3_to_v4(mcp))/scale
					mcp_b[3] = 1

					tip_to_thumb_b = np.subtract(tip_b[0:3], thumb_tip_b[0:3])
					dist_to_thumb[i] = mag(tip_to_thumb_b)

					tip_pip_b = np.subtract(tip_b, pip_b)
					pip_mcp_b = np.subtract(pip_b, mcp_b)
					q1 = vect_angle(tip_pip_b, pip_mcp_b)
					q2 = vect_angle(pip_mcp_b, mcp_b)
					fng_ang = (q1+q2)*180/np.pi
					fpos[i] = linmap(fng_ang, outp_fng, inp_fng)
					#map fingers
								
				
				"""
					Override touching fingers with prebaked grips
				"""
				word = 0
				for i in range(0,4):
					word |= (dist_to_thumb[i] < 2.7) << i
				if word != 0 and is_set_grip == 0 and fpos[5] < -40:
					is_set_grip = 1
					grip_word = word
				elif word == 0:
					is_set_grip = 0
				if(is_set_grip):
					fpos = override_grip(fpos, grip_word)

				
				for i in range(len(fpos)):
					fpos[i], warr[i] = py_sos_iir(fpos[i], warr[i], lpf_sos[0])
								
				#expose values to the plotting code
				yield t, fpos[0], fpos[1], fpos[2], fpos[3], fpos[4], fpos[5]


				if port:
					# Write the finger array out over UART to the hand!
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
			
			fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
			print (fpsfilt)
			
	cap.release()
	if port:
		ser.close()

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
	ybuf[4].append(args[5])
	ybuf[5].append(args[6])

	ax.relim()
	ax.autoscale_view(scalex=True, scaley=False)
	for i, line in enumerate(lines):
		line.set_data(xbuf[i],ybuf[i])
	return lines
	
anim = animation.FuncAnimation(fig, animate, init_func=init, frames=runcv, interval=0, blit=True,  save_count = 50)
ax.legend(['idx','mid','rng','pnk','tf','tr'])
plt.show()
