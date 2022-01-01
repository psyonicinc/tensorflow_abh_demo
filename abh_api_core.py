import struct

"""
	Sends the array farr (which should have only 6 elements, or the hand won't do anything)
	Byte positions:
		0th: 0x50 
		1st: AD (control mode)
		payload: farr as the payload (4 bytes per value),
		last: checksum
	Must be 27 total bytes for the hand to do anything in response.
"""
def farr_to_barr(farr):
	barr = [];
	barr.append( (struct.pack('<B',0x50))[0] );	#device ID
	barr.append( (struct.pack('<B',0xAD))[0] );	#control mode
	#following block of code converts fpos into a floating point byte array and 
	#loads it into barr bytewise
	for fp in farr:
		b4 = struct.pack('<f',fp)
		for b in b4:
			barr.append(b)
	# last step: calculate the checksum and load it into the final byte
	sum = 0
	for b in barr:
		sum = sum + b
	chksum = (-sum) & 0xFF;
	barr.append(chksum)
	return barr

"""
	Sends a 3 byte payload.
	0th is device id
	1st is the misc. command
	2nd is the checksum!
"""
def create_misc_msg(cmd):
	barr = []
	barr.append( (struct.pack('<B',0x50))[0] );	#device ID
	barr.append( (struct.pack('<B', cmd))[0] );	#command!
	sum = 0
	for b in barr:
		sum = sum + b
	chksum = (-sum) & 0xFF;
	barr.append(chksum)
	return barr
