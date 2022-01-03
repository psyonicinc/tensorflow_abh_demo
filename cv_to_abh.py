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
lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for the fps counter

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
			
		
		warr_fps = [0,0,0]
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
			
			#image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
						
			results = hands.process(image)
			
			
			# Draw the hand annotations on the image.
			#image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
			if results.multi_hand_landmarks:
				
				#log time for plotting
				t = time.time()
								
				abh.update(results, mp_hands)
				if port:
					# Write the finger array out over UART to the hand!
					msg = farr_to_barr(abh.fpos)
					ser.write(msg)
				
				#expose values to the plotting code
				yield t, abh.fpos[0], abh.fpos[1], abh.fpos[2], abh.fpos[3], abh.fpos[4], abh.fpos[5]
				
				if port:
					# Write the finger array out over UART to the hand!
					msg = farr_to_barr(abh.fpos)
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
