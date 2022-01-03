import cv2
import mediapipe as mp
import time
import numpy as np
from vect_tools import *
from rtfilt import *
from abh_api_core import *
from scipy import signal
import serial
from serial.tools import list_ports
from gestures import *


class AbilityHandBridge:
	def __init__(self):
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
		self.lpf_sos = signal.iirfilter(2, Wn=3, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for sending the finger data over
		"""
			Program constants. Used for linear mapping offset/gain, etc.
		"""
		self.outp_fng = [5,100]
		self.inp_fng = [20, 130]
		self.outrange_fng = [5,110]

		self.outp_tr = [-5,-70]
		self.inp_tr = [-50, -75]
		self.outrange_tr = [-500, -5]

		self.outp_tf = [0,60]
		self.inp_tf = [15,-40]
		self.outrange_tf = [10, 90]

		#initialize array used for writing out hand positions
		self.fpos = [15,15,15,15,15,-15]
		
		#initialize array used for filtering
		self.warr = []
		for f in self.fpos:
			self.warr.append([0,0,0])
		
		self.hw_b = np.zeros((4,4))
		self.hb_w = np.zeros((4,4))
		self.hb_ip = np.zeros((4,4))
		self.hip_b = np.zeros((4,4))
		
		self.handed_sign = 1
		self.scale = 1
		self.dist_to_thumb = 1
		
		self.grip_word = 0
		self.is_set_grip = 0
		
	def update(self, results, mp_hands):

		#get the handedness
		#index is 1/"Right", 0/"Left". This has something to do with the image being flipped, but we're just gonna flip the label association here
		if(results.multi_handedness[0].classification[0].index == 1):	
			self.handed_sign = 1 #1 for left, -1 for right. Apply to Z component when doing arctan2
		else:
			self.handed_sign = -1

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
		self.scale = (mag(v1) + mag(v2) + mag(v3))/3

		#obtain hw_b and hb_w
		self.hw_b = np.zeros((4,4))
		vx = np.subtract(index_mcp, base)
		vx = vx/mag(vx)
		vyref = np.subtract(pinky_mcp,base)
		vyref = vyref/mag(vyref)
		vz = np.cross(vx, vyref)
		vz = vz/mag(vz)
		vy = np.cross(vz, vx)
		vy = vy/mag(vy)
		self.hw_b[0:3, 0] = vx
		self.hw_b[0:3, 1] = vy
		self.hw_b[0:3, 2] = vz
		self.hw_b[0:3, 3] = base
		self.hw_b[3, 0:4] = np.array([0,0,0,1])
		self.hb_w = ht_inverse(self.hw_b)


		#compute all thumb vectors (to base)
		thumb_tip_b = self.hb_w.dot(v3_to_v4(thumb_tip))/self.scale		
		thumb_tip_b[3] = 1
		thumb_ip_b = self.hb_w.dot(v3_to_v4(thumb_ip))/self.scale
		thumb_ip_b[3] = 1
		thumb_mcp_b = self.hb_w.dot(v3_to_v4(thumb_mcp))/self.scale
		thumb_mcp_b[3] = 1
		thumb_cmc_b = self.hb_w.dot(v3_to_v4(thumb_cmc))/self.scale
		thumb_cmc_b[3] = 1

		ang_tr = np.arctan2(self.handed_sign*thumb_ip_b[2],-thumb_ip_b[1])*180/np.pi
		#mapthumb rotator
		self.fpos[5] = linmap(ang_tr, self.outp_tr, self.inp_tr)
		self.fpos[5] = clamp(self.fpos[5], self.outrange_tr[0], self.outrange_tr[1])

		#tip_to_ip_b = np.subtract(thumb_tip_b, thumb_ip_b)				
		#ip_to_mcp_b = np.subtract(thumb_ip_b, thumb_mcp_b)
		#ang_tf_dp = vect_angle(tip_to_ip_b[0:3], ip_to_mcp_b[0:3])*180/np.pi
		vx = np.subtract(thumb_ip_b, thumb_mcp_b)
		vx = vx[0:3]
		vx = vx / mag(vx)
		vyref = thumb_cmc_b	# multiple options here. might be the best one
		vyref = vyref[0:3]
		vyref = vyref/mag(vyref)
		self.hb_ip = ht_from_2_vectors(vx,vyref,thumb_ip_b[0:3])
		self.hip_b = ht_inverse(self.hb_ip)
		thumb_tip_ip = self.hip_b.dot(thumb_tip_b)
		ang_tf = np.arctan2(thumb_tip_ip[1], thumb_tip_ip[0])*180/np.pi
		#map thumb flexor
		self.fpos[4] = linmap(ang_tf, self.outp_tf, self.inp_tf)
		#self.fpos[4] = ang_tf


		#compute all finger angles
		tips = [index_tip, middle_tip, ring_tip, pinky_tip]
		pips = [index_pip, middle_pip, ring_pip, pinky_pip]
		mcps = [index_mcp, middle_mcp, ring_mcp, pinky_mcp]
		self.dist_to_thumb = [0, 0, 0, 0, 0, 0]
		for i in range(0,4): 
			tip = tips[i]
			pip = pips[i]
			mcp = mcps[i]
								
			#get index angle
			tip_b = self.hb_w.dot(v3_to_v4(tip))/self.scale
			tip_b[3] = 1
			pip_b = self.hb_w.dot(v3_to_v4(pip))/self.scale
			pip_b[3] = 1
			mcp_b = self.hb_w.dot(v3_to_v4(mcp))/self.scale
			mcp_b[3] = 1

			tip_to_thumb_b = np.subtract(tip_b[0:3], thumb_tip_b[0:3])
			self.dist_to_thumb[i] = mag(tip_to_thumb_b)

			tip_pip_b = np.subtract(tip_b, pip_b)
			pip_mcp_b = np.subtract(pip_b, mcp_b)
			q1 = vect_angle(tip_pip_b, pip_mcp_b)
			q2 = vect_angle(pip_mcp_b, mcp_b)
			fng_ang = (q1+q2)*180/np.pi
			self.fpos[i] = linmap(fng_ang, self.outp_fng, self.inp_fng)
			#map fingers
						
		for i in range(len(self.fpos)):
			self.fpos[i], self.warr[i] = py_sos_iir(self.fpos[i], self.warr[i], self.lpf_sos[0])
		
		"""
			Override touching fingers with prebaked grips
		"""
		word = 0
		for i in range(0,4):
			word |= (self.dist_to_thumb[i] < 2.7) << i	#get the binary word representing thresholded fingertip-thumb distance
		if word != 0 and self.is_set_grip == 0 and self.fpos[5] < -30:
			self.is_set_grip = 1
			self.grip_word = word
		elif word == 0:
			self.is_set_grip = 0
		if(self.is_set_grip):
			self.fpos = override_grip(self.fpos, self.grip_word)


