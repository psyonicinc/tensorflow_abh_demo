import serial
from serial.tools import list_ports
from abh_api_core import farr_to_barr
from abh_api_core import create_misc_msg
import math
import time
import platform
import sys
from threading import Lock, Thread
from dataclasses import dataclass
import copy


class AbilityHand:
	
	def __init__(self):
		self.positionLock = Lock()
		self.dataLock = Lock()
		self.position = [15., 15., 15., 15., 15., -15.]
		self.checkSum = 1
		self.data = 0
		
	def setPositions(self, pos):
		self.positionLock.acquire()
		self.position = pos.copy()
		self.positionLock.release()
		return
		
	def getPositions(self):
		self.positionLock.acquire()
		ret = self.position.copy()
		self.positionLock.release()
		return ret
		
	def setData(self, checkSum, data):
		self.dataLock.acquire()
		self.checkSum = copy.copy(checkSum)
		self.data = copy.deepcopy(data)
		self.dataLock.release()
		return
		
		
	def getData(self):
		self.dataLock.acquire()
		ret_cs = copy.copy(self.checkSum)
		ret_data = copy.deepcopy(self.data)
		self.dataLock.release()
		return ret_cs, ret_data
		
	
def handCommunication(hand, loopsToDo):

	## Set Up Serial
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

	## Run
	count = 0
	timeouts = 0
	badChecksums = 0
	while count < loopsToDo:
		count += 1
		print("Run: " + str(count))
		sum = 0
		msg = farr_to_barr(hand.getPositions())
		ser.write(msg)
		data = ser.read(71)
		if len(data) == 71:
			for byte in data:
				sum = (sum + byte)%256
				
			if sum != 0:
				badChecksums+=1
				ser.reset_input_buffer()
		else:
			timeouts+=1
			ser.reset_input_buffer()
		hand.setData(sum, data)
		
	print("Total Number of Runs: " + str(count))
	print("Timeouts: " + str(timeouts))
	print("Checksum failures: " + str(badChecksums))
		

	
def main():
	print("Starting...")
	hand = AbilityHand()
	fpos = hand.getPositions()
	t1 = Thread(target=handCommunication, args=(hand, 10000,))
	t1.start()
	while(t1.is_alive()):
		print("Calc Data")
		for i in range(0, len(fpos)):
			ft = time.time()*3 + i
			fpos[i] = (.5*math.sin(ft)+.5)*45+15
		fpos[5] = -fpos[5]
		hand.setPositions(fpos)
	
	print("Done!")
	


if __name__ == "__main__":
	main()

	