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
		hand.serialWrite(1)
		
		sum, data = hand.getRawData()
		sum2, pos, press, sbits = hand.getProcessedData()
		
		print("Sums: " + str(sum) + "  " + str(sum2))
		print(data.hex())
		print("Pos: " + str(pos))
		print("Psr: " + str(press))
		print("Bits: " + str(sbits))

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