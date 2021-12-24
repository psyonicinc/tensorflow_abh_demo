import struct


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
