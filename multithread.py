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
from AbilityHand import AbilityHand
		

	
def main():
	hand = []
	t1 = []
	try:
		print("Starting...")
		ser = []
		try: 
			ser = serial.Serial('COM5')
		except Exception as e:
			print(str(e))
			print("Failed to connect")
		serialLock = Lock()
		hand = AbilityHand(ser, serialLock)
		fpos = hand.getPositions()
		t1 = Thread(target=hand.serialWrite, args=(1000,))
		t1.start()
		positions = []
		while(t1.is_alive()):
			#print("Calc Data")
			for i in range(0, len(fpos)):
				ft = time.time()*3 + i
				fpos[i] = (.5*math.sin(ft)+.5)*45+15
			fpos[5] = -fpos[5]
			hand.setPositions(fpos)
			sum, data = hand.getRawData()
			if sum !=0:
				#print("Checksum or timeout")
				positions.append(0.0)
			else:
				position = struct.unpack('f', data[0:4])
				#positions.append(position)
				#print("First position is: " + str(position))
			time.sleep(0.001)

		hand.runStats()
		print("Done!")
		#print(str(positions))
	except KeyboardInterrupt: 
		hand.stop()
		t1.join()
		hand.runStats()
		print("Keyboard Interupt, Done")
		
	
	



if __name__ == "__main__":
	main()


# 0 degrees open