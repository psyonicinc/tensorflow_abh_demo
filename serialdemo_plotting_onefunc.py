import serial
from serial.tools import list_ports
from abh_api_core import *
import math
import time
import numpy as np
from PPP_stuffing import *
import binascii
import matplotlib.pyplot as plt
import matplotlib.animation as animation

#ser = serial.Serial('COM4','460800', timeout = 1)
""" 
	Find a serial com port.
"""
com_ports_list = list(list_ports.comports())
port = []
slist = []
for p in com_ports_list:
	if(p):
		pstr = ""
		pstr = p
		port.append(pstr)
		print("Found:", pstr)
if not port:
	print("No port found")

for p in port:
	try:
		ser = []
		ser = (serial.Serial(p[0],'460800', timeout = 0))
		slist.append(ser)
		print ("connected!", p)
		# print ("found: ", p)
	except:
		print("failded.")
		pass
print( "found ", len(slist), "ports.")
		
		

for s in slist:
	buf = create_misc_msg(0x50, 0xC2) # cmd to enable upsampling of the thumb rotator
	print ("writing thumb filter message on com port: ", s)
	s.write(buf)


"""
Plotting STuff
"""
start_time = time.time()
ylower = -2
yupper = 2
bufwidth = 200
num_lines = 30
fig, ax = plt.subplots()
ax.set_ylim(ylower,yupper)
lines = []
for i in range(num_lines):
	lines.append(ax.plot([],[])[0])
xbuf = np.zeros(bufwidth)
ybuf = np.zeros((num_lines, bufwidth))


stuff_buffer = np.array([])
data = np.zeros(num_lines+1)

def animate(unused):
	global xbuf
	global ybuf
	global lines
	global slist
	global start_time
	global stuff_buffer
	global data
	
	# fpos = np.zeros(num_lines)
	
	t = time.time() - start_time
	data[0] = t
	
	
	# for i in range(0, len(fpos)):
		# ft = t*3 + i*(2*np.pi)/12
		# fpos[i] = (.5*np.sin(ft)+.5)*45+15
	# fpos[5] = -fpos[5]
	
	
	# msg = farr_to_dposition(0x50, fpos, 1)
	# slist[0].write(msg)

	time.sleep(.01)

	while(slist[0].in_waiting != 0):	#dump all the data
		bytes = slist[0].read(1024)	#gigantic read size with nonblocking
		if(len(bytes) != 0): #redundant, but fine to keep
			npbytes = np.frombuffer(bytes, np.uint8)
			# npbytes = np.append(npbytes, np.uint8(0))
			# npbytes = np.insert(npbytes, 0, 0)
			# print(npbytes.tobytes().hex())
			for b in npbytes:
				payload, stuff_buffer = unstuff_PPP_stream(b,stuff_buffer)
				if(len(payload) != 0):
					rPos,rI,rV,rFSR = parse_hand_data(payload)
					if( (rPos.size + rI.size + rV.size + rFSR.size) != 0):
						# print("Pass, "+str(len(payload)))
						print(str(np.int16(rPos))+str(rI)+str(np.int16(rV))+str(rFSR))
						# data[1:len(data)] = rPos
						data[1:len(data)] = rFSR

					else:	
						pass
						# print("Fail, "+str(len(payload)))



	xbuf = np.roll(xbuf,1)	#roll xbuf by 1
	xbuf[0] = data[0]	#load in new value
	
	
	for i in range(0,num_lines):
		ybuf[i] = np.roll(ybuf[i],1) #roll 1
		ybuf[i][0] = data[i+1]
		# ybuf[i][0] = udp_pkt[i+1]	#load new value

	xmin = np.min(xbuf)
	xmax = np.max(xbuf)
	plt.setp(ax,xlim = (xmin,xmax))
	plt.setp(ax,ylim = (np.min(ybuf),np.max(ybuf)))
	
	ax.relim()
	ax.autoscale_view(scalex=False, scaley=False)

	for i, line in enumerate(lines):
		line.set_data(xbuf,ybuf[i])
   
	return lines




		

	

ani = animation.FuncAnimation(
	fig, animate, init_func=None, interval=1, blit=True, save_count=None, cache_frame_data=False,repeat=False)

plt.show()
	
for s in slist:
	s.close()
