import time
import socket

"""
	Sends query out to server and waits until timeout for a response
	
"""
def locate_server_from_bkst_query(port, use_loopback=False, kbrd_ip_select=False):

	hostname = socket.gethostname()
	# addr=socket.gethostbyname(hostname)
	hostname,aliaslist,addrlist=socket.gethostbyname_ex(hostname)
	usr_string_input = ''
	usr_input = 0
	udp_server_addr = ("127.0.0.1",port)
	addrmod = "127.0.0.1"
	client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	client_socket.settimeout(0.0) #make non blocking

	if(use_loopback == False):
		if(len(addrlist) > 1):
			if( kbrd_ip_select == True):
				print("Select an IP to use from list with a number (0,1,2,...)\r\n"+str(addrlist))
				usr_string_input = input()
				usr_input = int(usr_string_input)
			else:
				usr_input = len(addrlist)-1
		if(usr_input >= 0 and usr_input < len(addrlist)):
			addr=str(addrlist[usr_input])
			print("Host IP Addr: "+addr)
			addrmod = addr.split('.')
			addrmod[3] = '255'
			addrmod = '.'.join(addrmod)
			print("Using: "+addrmod+" on port: ",port)
			udp_server_addr = (addrmod, port)
			bufsize = 512

	start_time = time.time()
	try:
		print("dest="+udp_server_addr[0]+", "+str(udp_server_addr[1]))
		barr = bytearray("marco",encoding='utf8')
		client_socket.sendto(barr,udp_server_addr)		
	except KeyboardInterrupt:
		print("some fkn error")

	found = 0
	while(time.time()-start_time < 3):
		try:
			pkt,addr = client_socket.recvfrom(bufsize)
			if(len(pkt) > 0):
				print("received" + str(pkt)+" from: ",str(addr[0]))
				found = 1
				return str(addr[0]), 1
		except:
			pass
	if(found == 0):
		return str(addrmod), 0
