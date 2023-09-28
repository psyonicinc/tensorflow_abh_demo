import socket


soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
soc.settimeout(.01)


hostname = socket.gethostname()
hostname,aliaslist,addrlist=socket.gethostbyname_ex(hostname)

port = 34345
for addr in addrlist:
	try:
		bkst_addr = addr.split('.')
		bkst_addr[3] = '255'
		bkst_addr = ('.'.join(bkst_addr)	, port)
		# print("dest="+bkst_addr[0]+":"+str(bkst_addr[1]))
		soc.sendto( bytearray('deactivate_hose',encoding='utf8'),bkst_addr )
	except:
		print("error sending to "+bkst_addr[0]+":"+str(bkst_addr[1]))