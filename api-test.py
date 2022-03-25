import serial
from serial.tools import list_ports
from abh_api_core import *
import math
import time

#ser = serial.Serial('COM4','460800', timeout = 1)
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


fpos = [15., 15., 15., 15., 15., -15.]
try:
	while 1:
		
		#fpos = [15., 15., 15., 15., 15., -15.]
		for i in range(0, len(fpos)):
			ft = time.time()*3 + i
			fpos[i] = (.5*math.sin(ft)+.5)*45+15
		fpos[5] = -fpos[5]
		
		#msg = farr_to_barr(fpos)
		msg = farr_to_dposition(fpos, 2)
		ser.write(msg)
		time.sleep(.001)
except KeyboardInterrupt:
	pass

ser.close()