import time
import socket

def locate_server_from_bkst_query(port):
	hostname = socket.gethostname()
	addr=socket.gethostbyname(hostname)
	print("Host IP Addr: "+addr)
	addrmod = addr
	dotidx = len(addrmod)-1
	for i in range(len(addrmod)-1,0, -1):
		if(addrmod[i] == '.'):
			dotidx = i
			break
	lastoctet = addrmod[dotidx+1:len(addrmod)]
	addrmod = addrmod.replace(lastoctet,"255")
	print("Using: "+addrmod+" on port: ",port)
	udp_server_addr = (addrmod, port)
	bufsize = 512
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	client_socket.settimeout(0.0) #make non blocking

	start_time = time.time()

	try:
		barr = bytearray("marco",encoding='utf8')
		client_socket.sendto(barr,udp_server_addr)		
	except KeyboardInterrupt:
		print("some fkn error")

	found = 0
	while(time.time()-start_time < 3):
		try:
			pkt,addr = client_socket.recvfrom(bufsize)
			if(len(pkt) > 0):
				print("received response from: ",str(addr[0]))
				found = 1
				return str(addr[0])
		except:
			pass
	if(found == 0):
		return str(addrmod)
