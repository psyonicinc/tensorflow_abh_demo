import serial
from serial.tools import list_ports
from abh_api_core import *
import math
import time
import numpy as np
from udp_bkst_query import *
import socket
import struct


hand_port = 34345
addr = locate_server_from_bkst_query(hand_port)	
print("piping commands to: "+str(addr)+" on port: "+str(hand_port))
udp_server_addr = (addr,  hand_port)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(0)
bufsize = 512

#note: if PPP stuffing is activated on the hand, this is likely unnecessary
hose_on_cmd = "deactivate_hose"
print("sending command: "+hose_on_cmd+" to: "+str(addr))
client_socket.sendto(bytearray(hose_on_cmd,encoding="utf8"),udp_server_addr)


buf = create_misc_msg(0x50, 0xC2) # cmd to enable upsampling of the thumb rotator
buf = bytearray(buf)
client_socket.sendto(buf, udp_server_addr)

fpos = [15., 15., 15., 15., 15., -15.]																									
try:
	rPos = np.array([])
	rI = np.array([])
	rV = np.array([])
	rFSR = np.array([])

	while 1:
		
		for i in range(0, len(fpos)):
			ft = time.time()*3 + i*(2*np.pi)/12
			fpos[i] = (.5*math.sin(ft)+.5)*45+15
		fpos[5] = -fpos[5]
		
		msg = bytearray(farr_to_dposition(0x50, fpos, 1))
		client_socket.sendto(msg, udp_server_addr)

		try:
			pkt,addr = client_socket.recvfrom(bufsize)
			if(len(pkt) != 0):
				rPos,rI,rV,rFSR = parse_hand_data(pkt)		
				tlen = rPos.size + rI.size + rV.size + rFSR.size
				if(tlen != 0):
					print(str(np.int16(rPos))+str(rI)+str(np.int16(rV))+str(rFSR))
				else:
					print(pkt)
		except:	#ignore errors, cuz nonblocking read always throws an exception
			pass

		time.sleep(.001)
			
except KeyboardInterrupt:
	pass
	