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
bkst_ip = (get_bkst_ip_from_usr(), hand_port)

our_port = 1435
rx_offset = 1			#important! default behavior is for this to be ZERO, but you can split streams for multiprocess activity with a command line option on the bridge. A nonzero value (typically 1) should be loaded here to match setting on udp bridge
tx_skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tx_skt.settimeout(0)
tx_skt.bind(('0.0.0.0', (our_port))) #we could bind to anything here


rx_skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx_skt.settimeout(0)
if(rx_offset != 0):
	bindaddr = ('0.0.0.0', (our_port+rx_offset))
	rx_skt.bind( bindaddr )
	print("binding to "+bindaddr[0]+":"+str(bindaddr[1]))
else:
	rx_skt = tx_skt

print("dest="+bkst_ip[0]+":"+str(bkst_ip[1]))
target_addr = get_ip_of_targ(bkst_ip, tx_skt, rx_skt)
if(target_addr != ''):
	print("found target at "+target_addr[0]+":"+str(target_addr[1]))
else:
	target_addr = bkst_ip

rx_skt.close()	#IMPORTANT: unbind the receiver so the receiver process can successfully bind to that port

#note: if PPP stuffing is activated on the hand, this is likely unnecessary
hose_on_cmd = "activate_hose"
print("sending command: "+hose_on_cmd+" to: "+target_addr[0]+":"+str(target_addr[1]))
tx_skt.sendto(bytearray(hose_on_cmd,encoding="utf8"),target_addr)

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
		tx_skt.sendto(msg, target_addr)
		
		time.sleep(.001)
		
			
except KeyboardInterrupt:
	pass
	
	
hose_on_cmd = "deactivate_hose"
print("sending command: "+hose_on_cmd+" to: "+target_addr[0]+":"+str(target_addr[1]))
tx_skt.sendto(bytearray(hose_on_cmd,encoding="utf8"),target_addr)
