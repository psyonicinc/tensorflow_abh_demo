import serial
from serial.tools import list_ports
from abh_api_core import farr_to_barr
import math
import time
import ctypes

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
		print("IGNORE USING COM5---Found:", port)
		break
if not port:
	print("No port found")

if(port):
	try:
		ser = serial.Serial("COM5",'460800', timeout = 0.002, inter_byte_timeout=0.0001)
		print ("connected!")
		buf = create_misc_msg(0xC2) # cmd to enable upsampling of the thumb rotator
		ser.write(buf)
	except:
		port = ""
		print("failed to connect")


fpos = [15., 15., 15., 15., 15., -15.]
try:
	start = time.process_time()
	print("Start at: " + str(start))
	count = 0
	timeouts = 0
	badChecksums = 0
	while count < 1000:
		count+=1
		#print(str(count) +": ", end='')
		#fpos = [15., 15., 15., 15., 15., -15.]
		for i in range(0, len(fpos)):
			ft = time.time()*3 + i
			fpos[i] = (.5*math.sin(ft)+.5)*45+15
		fpos[5] = -fpos[5]
		msg = farr_to_barr(fpos)
		ser.write(msg)
		data = ser.read(71)
		if len(data) == 71:
			sum = 0;
			for byte in data:
				sum = (sum + byte)%256
				
			if sum != 0:
				print(str(count) +": " +"Check Sum Fail: " + str(sum))
				badChecksums+=1
		else:
			print(str(count) +": "+"Timeout!! "+ str(len(data)))
			timeouts+=1
		
		i = 0
		#while i < 500000:
		#	i += 1
		#while time.process_time_ns() < (startTime + 50):
		#	pass
		time.sleep(0.001)
		
	end = time.process_time()
	elapsed = end - start
	print("End at: " + str(end))
	print("Total Number of Runs: " + str(count))
	print("Timeouts: " + str(timeouts))
	print("Checksum failures: " + str(badChecksums))
	print("Elapsed Time(s): " + str(elapsed))
except KeyboardInterrupt:
	print("Total Number of Runs: " + str(count))
	pass

ser.close()