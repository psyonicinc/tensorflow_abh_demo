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
import struct

class AbilityHand:

	def __init__(self, ser, serLock):
		self._posLock = Lock()
		self._dataLock = Lock()
		self._serLock = serLock
		self._setPosition = [15., 15., 15., 15., 15., -15.]
		self._checkSum = -1
		self._data = 0
		self.newData = False
		self._runs = 0
		self._timeouts = 0
		self._checksumFails = 0
		self._ser = ser
		self._stop = False
		self._serLock.acquire()
		self._setupSerial()
		buf = create_misc_msg(0xC2) # cmd to enable upsampling of the thumb rotator
		self._ser.write(buf)
		time.sleep(0.001)
		self._ser.reset_input_buffer()
		self._serLock.release()
	
	def setPositions(self, pos):
		self._posLock.acquire()
		for i in range(0,6):
			self._setPosition[i] = float(pos[i])
		self._posLock.release()
	
	
	def getPositions(self):
		self._posLock.acquire()
		ret = self._setPosition.copy()
		self._posLock.release()
		return ret
	
	
	def _setData(self, timeout, badChecksum, checksum, data):
		self._dataLock.acquire()
		self.newData = True
		self._checkSum = checksum
		self._data = data
		self._dataLock.release()
		if badChecksum:
			self._checksumFails += 1
		if timeout:
			self._timeouts += 1
		return
		
		
	def getRawData(self):
		self._dataLock.acquire()
		ret_cs = copy.copy(self._checkSum)
		ret_data = copy.deepcopy(self._data)
		self.newData = False
		self._dataLock.release()
		return ret_cs, ret_data
		
		
	def getProcessedData(self):
		positions = [-1.0] * 6
		safetyBits = [True] * 6
		fingerPressure = [0] * 30
		cs, data = self.getRawData()
		if cs == 0:
			# Finger position and safety bits
			for i in range(0, 6):
				positions[i] = struct.unpack('f', data[(4*i):(4*i + 4)])
				if (data[70] & (1 << i)) == 0:
					safetyBits[i] = False
			
			for i in range(0, 15):
				dualData = data[24+(i*3):24+((i*3)+3)]
				data1 = struct.unpack('H', dualData[0:2])[0] & 0x0FFF
				data2 = (struct.unpack('H', dualData[1:3])[0] & 0xFFF0) >> 4
				fingerPressure[2*i] = int(data1)
				fingerPressure[(2*i)+1] = int(data2)
				
		return cs, positions, fingerPressure, safetyBits
		
	## ONLY CALL WHEN YOU HAVE ACQUIRED self._serLock()!!
	def _setupSerial(self):
		self._ser.timeout=0.05
		self._ser.baudrate='460800'
		if platform.system() != 'Windows':
			self._ser.inter_byte_timeout=0.001
		self._ser.reset_input_buffer()
		return
	
	## ONLY CALL WHEN YOU HAVE ACQUIRED self._serLock()!!
	def _serialWrite(self):
		self._runs +=1
		sum = 0
		badSum = False
		hadTimeout = False
		msg = farr_to_barr(self.getPositions())
		self._ser.write(msg)
		data = self._ser.read(71)
		if len(data) == 71:
			for byte in data: 
				sum = (sum + byte)%256
			
			if sum != 0:
				badSum = True
		else:
			hadTimeout = True
			sum = -1
		
		if hadTimeout or badSum:
			self._ser.reset_input_buffer()
		self._setData(hadTimeout, badSum, sum, data)
		return (hadTimeout or badSum)
		
		
	def serialWrite(self, count):
		startTime = time.perf_counter();
		self._serLock.acquire()
		self._setupSerial()
		runCount = 0
		while (runCount < count) and (not self._stop):
			self._serialWrite()
			runCount+=1
			
		self._serLock.release()
		endTime = time.perf_counter();
		self._stop = False
		print("Run Time: " + str(endTime-startTime))
		
		
	def serialWriteForever(self):
		self._serLock.acquire()
		self._setupSerial()
		while not self._stop:
			self._serialWrite()
		self._stop = False
		self._serLock.release()
		
	def stop(self):
		self._stop = True
		
	def runStats(self):
		print("Total Runs: " + str(self._runs))
		print("Check Sum Failures: " + str(self._checksumFails))
		print("Response Timeouts: " + str(self._timeouts))

		
		