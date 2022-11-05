import serial
from serial.tools import list_ports
from abh_api_core import *
import math
import time
import numpy as np

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
		ser = (serial.Serial(p[0],'460800', timeout = 1))
		slist.append(ser)
		print ("connected!", p)
		# print ("found: ", p)
	except:
		print("failded.")
		pass
print( "found ", len(slist), "ports.")
		
		

for s in slist:
	buf = create_misc_msg(0xC2) # cmd to enable upsampling of the thumb rotator
	print ("writing thumb filter message on com port: ", s)
	s.write(buf)

fpos = [15., 15., 15., 15., 15., -15.]																									
try:
	while 1:
		
		try:
			for i in range(0, len(fpos)):
				ft = time.time()*3 + i*(2*np.pi)/12
				fpos[i] = (.5*math.sin(ft)+.5)*45+15
			fpos[5] = -fpos[5]
			
			msg = farr_to_barr(fpos)
			slist[0].write(msg)
		except:
			pass
		
		try:		
			for i in range(0, len(fpos)):
				ft = time.time()*3 + (i+6)*(2*np.pi)/12
				fpos[i] = (.5*math.sin(ft)+.5)*45+15
			fpos[5] = -fpos[5]
			
			msg = farr_to_barr(fpos)
			slist[1].write(msg)
		except:
			pass
	
		time.sleep(.001)
		
		
except KeyboardInterrupt:
	pass
	
for s in slist:
	s.close()
