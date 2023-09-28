import time
import socket

def scan_split_streams(bkst_ip, offset, target_port, bind_port):
	tx_skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	tx_skt.settimeout(0)
	tx_skt.bind(('0.0.0.0',bind_port))
	
	rx_skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	rx_skt.settimeout(0)
	if(offset != 0):
		bindaddr = ('0.0.0.0', (bind_port+offset))
		rx_skt.bind( bindaddr )	#bind to a new socket where the split stream destination will go
	else:
		rx_skt = tx_skt
	
	target_addr = get_ip_of_targ(bkst_ip, tx_skt, rx_skt)

	tx_skt.close()
	rx_skt.close()
	return target_addr
	


def get_bkst_ip_from_usr():
	hostname = socket.gethostname()
	# addr=socket.gethostbyname(hostname)
	hostname,aliaslist,addrlist=socket.gethostbyname_ex(hostname)

	print("Select an IP to use from list with a number (0,1,2,...)\r\n"+str(addrlist))
	usr_string_input = input()
	usr_input = int(usr_string_input)
	addr = addrlist[usr_input]
	addr = addr.split('.')
	addr[3] = '255'
	addr = '.'.join(addr)
	return addr

"""
	Make sure the bkst_ip has both ip addr and port
"""
def get_ip_of_targ(bkst_ip, tx_skt, rx_skt):
	found = 0
	start_time = time.time()
	tx_skt.sendto(bytearray("marco",encoding='utf8'),bkst_ip)
	addr = ''
	while(time.time()-start_time < 3):
		try:
			pkt,addr = rx_skt.recvfrom(512)
			if(len(pkt) > 0):
				found = 1
				break
		except BlockingIOError:
			pass
	if(found):
		return addr
	else:
		return ''
	
	

"""
kind of dumb function which interacts with locate_server_from_bkst_query
"""
def get_hostip_idx_from_usr():
	hostname = socket.gethostname()
	# addr=socket.gethostbyname(hostname)
	hostname,aliaslist,addrlist=socket.gethostbyname_ex(hostname)

	print("Select an IP to use from list with a number (0,1,2,...)\r\n"+str(addrlist))
	usr_string_input = input()
	usr_input = int(usr_string_input)
	
	return usr_input

"""
	Sends query out to server and waits until timeout for a response
	
"""
def locate_server_from_bkst_query(port, addrlist_idx=None, use_loopback=False,):

	
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
			if( addrlist_idx != None):
				usr_input = addrlist_idx
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
				return str(addr[0]), 1, addrlist[usr_input]
		except:
			pass
	if(found == 0):
		return str(addrmod), 0, addrlist[usr_input]
