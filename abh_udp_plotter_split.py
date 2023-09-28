import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import serial
import socket
import struct 
import threading
from abh_get_fpos import *
from abh_api_core import *
import argparse


parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
parser.add_argument('--bind_port', type=int, help="Port for the software to bind to", default=-1)
args = parser.parse_args()


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

soc = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
soc.settimeout(0)
if(args.bind_port == -1):
	port = input("What port are we gonna bind to?: ")
	port = int(port)
	print("Binding to port: "+str(port))
	soc.bind(('0.0.0.0',port))
else:
	print("Binding to port: "+str(args.bind_port))
	soc.bind(('0.0.0.0',args.bind_port))
	

def animate(data):
	global xbuf
	global ybuf
	global lines


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

def newframe():
	global soc
	
	d = np.zeros(num_lines+1)
	
	while(1):
		
		try:
			t = time.time()-start_time
			d[0] = t		

			pkt,addr = soc.recvfrom(512)
			if(len(pkt) != 0):
				rPos,rI,rV,rFSR = parse_hand_data(pkt)		
				tlen = rPos.size + rI.size + rV.size + rFSR.size
				if(tlen != 0):
					# print(str(np.int16(rPos))+str(rI)+str(np.int16(rV))+str(rFSR))
					d[1:len(d)] = rFSR
					yield d				

		except BlockingIOError:	#ignore nonblocking read errors
			pass
		
	

ani = animation.FuncAnimation(
	fig, animate, frames=newframe, init_func=None, interval=1, blit=True, save_count=None, cache_frame_data=False,repeat=False)

# To save the animation, use e.g.
#
# ani.save("movie.mp4")
#
# or
#
# from matplotlib.animation import FFMpegWriter
# writer = FFMpegWriter(fps=15, metadata=dict(artist='Me'), bitrate=1800)
# ani.save("movie.mp4", writer=writer)

plt.show()

