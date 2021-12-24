import serial
from abh_api_core import farr_to_barr
import math
import time

ser = serial.Serial('COM3','460800', timeout = 1)

fpos = [15., 15., 15., 15., 15., -15.]
try:
	while 1:
		
		#fpos = [15., 15., 15., 15., 15., -15.]
		for i in range(0, len(fpos)):
			ft = time.time()*3 + i
			fpos[i] = (.5*math.sin(ft)+.5)*45+15
		fpos[5] = -fpos[5]
		
		msg = farr_to_barr(fpos)
		ser.write(msg)
		time.sleep(.001)
except KeyboardInterrupt:
	pass

ser.close()