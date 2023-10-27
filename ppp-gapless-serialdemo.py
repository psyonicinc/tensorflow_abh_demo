import serial
from serial.tools import list_ports
from abh_api_core import *
import math
import time
import numpy as np
from PPP_stuffing import *
import binascii

#ser = serial.Serial('COM4','460800', timeout = 1)
""" 
	Find a serial com port.
"""
com_ports_list = list(list_ports.comports())
port = []
slist = []
for p in com_ports_list:
	if(p):
		pstr = ""
		pstr = p
		port.append(pstr)
		print("Found:", pstr)
if not port:
	print("No port found")

for p in port:
	try:
		ser = []
		ser = (serial.Serial(p[0],'460800', timeout = 0, write_timeout = 0))
		slist.append(ser)
		print ("connected!", p)
		# print ("found: ", p)
	except:
		print("failded.")
		pass
print( "found ", len(slist), "ports.")
		
		

# for s in slist:
	# buf = create_misc_msg(0x50, 0xC2) # cmd to enable upsampling of the thumb rotator
	# print ("writing thumb filter message on com port: ", s)
	# s.write(buf)

fpos = [15., 15., 15., 15., 15., -15.]																									
try:
	rPos = np.array([])
	rI = np.array([])
	rV = np.array([])
	rFSR = np.array([])
	
	stuff_buffer = np.array([])

	while 1:
		
		
		for i in range(0, len(fpos)):
			ft = time.time()*3 + i*(2*np.pi)/12
			fpos[i] = (.5*math.sin(ft)+.5)*45+15
		fpos[5] = -fpos[5]
		
		msg = farr_to_dposition(0x50, fpos, 1)
		slist[0].write(PPP_stuff(bytearray(msg)))
		# slist[0].write(msg)
		
		time.sleep(.001)	#this is necessary because the hand needs IDLE time before issuing a reply
		
		while(slist[0].in_waiting != 0):	#dump all the data
			bytes = slist[0].read(512)	#gigantic read size with nonblocking
			if(len(bytes) != 0): #redundant, but fine to keep
				npbytes = np.frombuffer(bytes, np.uint8)
				# npbytes = np.append(npbytes, np.uint8(0))
				# npbytes = np.insert(npbytes, 0, 0)
				# print(npbytes.tobytes().hex())
				for b in npbytes:
					payload, stuff_buffer = unstuff_PPP_stream(b,stuff_buffer)
					if(len(payload) != 0):
						rPos,rI,rV,rFSR = parse_hand_data(payload)
						if( (rPos.size + rI.size + rV.size + rFSR.size) != 0):
							pass
							# slist[0].write(bytearray('match',encoding='utf8'))
							# print("Pass, "+str(len(payload)))
							# print(str(np.int16(rPos))+str(rI)+str(np.int16(rV))+str(rFSR))
						else:	
							print("Fail, "+str(len(payload)))

		
		
except KeyboardInterrupt:
	pass
	
for s in slist:
	s.close()