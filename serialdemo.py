import serial
from serial.tools import list_ports
from abh_api_core import farr_to_barr
from abh_api_core import create_misc_msg
import math
import time
import platform
import sys


printFailures = True #True - will print out every error that happens and run it happens on. False, only print totals at end

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
		if platform.system() == 'Windows':
			ser = serial.Serial('COM5','460800', timeout = 0.005) #, inter_byte_timeout=0.001)
		elif plaform.system() == 'Linux':
			ser = serial.Serial('/dev/ttyUSB0','460800', timeout = 0.005, inter_byte_timeout=0.001)
		else:
			raise Exception("Unknown OS, supports Windows and Linux")
			 
		print ("connected!")
		ser.reset_input_buffer()
		buf = create_misc_msg(0xC2) # cmd to enable upsampling of the thumb rotator
		ser.write(buf)
		time.sleep(0.001)
		ser.reset_input_buffer()
	except Exception as e:
		port = ""
		print(str(e))
		print("failed to connect")


fpos = [15., 15., 15., 15., 15., -15.]
try:
	loops = 1000
	if len(sys.argv) > 1:
		loops = int(sys.argv[1])

	count = 0
	timeouts = 0
	badChecksums = 0
	consecutiveChecksums = 0
	start = time.perf_counter()
	print("Start at: " + str(start))
	while count < loops:
		count+=1
		loopStart =  time.perf_counter_ns()
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
				if printFailures:
					print(str(count) +": " +"Check Sum Fail: " + str(sum))
				badChecksums+=1
				ser.reset_input_buffer()
		else:
			if printFailures:
				print(str(count) +": "+"Timeout!! "+ str(len(data)))
			timeouts+=1
			ser.reset_input_buffer()
		
		#while  time.perf_counter_ns() < (loopStart + 1000000):
		#	pass
		#time.sleep(0.0004)  #windows sleep is not precise enough for this

		
	end = time.perf_counter()
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