import serial
from serial.tools import list_ports
from abh_api_core import *
import math
import time
import numpy as np

import socket
import struct

udp_server_addr = ("192.168.29.251", 34345)
bufsize = 512

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(0)



		

buf = create_misc_msg(0x50, 0xC2) # cmd to enable upsampling of the thumb rotator
buf = bytearray(buf)
client_socket.sendto(buf, udp_server_addr)

fpos = [15., 15., 15., 15., 15., -15.]																									
try:
	while 1:
		
		for i in range(0, len(fpos)):
			ft = time.time()*3 + i*(2*np.pi)/12
			fpos[i] = (.5*math.sin(ft)+.5)*45+15
		fpos[5] = -fpos[5]
		
		msg = farr_to_barr(0x50, fpos)
		msg = bytearray(msg)
		client_socket.sendto(msg, udp_server_addr)
	
		time.sleep(.001)
			
except KeyboardInterrupt:
	pass
	