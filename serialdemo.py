import serial
import struct

ser = serial.Serial('COM3','460800', timeout = 1)

#define fpos
fpos = [15., 15., 15., 15., 15., -15.]

barr = [];
barr.append( (struct.pack('<B',0x50))[0] );	#device ID
barr.append( (struct.pack('<B',0xAD))[0] );	#control mode
#following block of code converts fpos into a floating point byte array and 
#loads it into barr bytewise
for fp in fpos:
	b4 = struct.pack('<f',fp)
	for b in b4:
		barr.append(b)
# last step: calculate the checksum and load it into the final byte



print(barr)
ser.write(barr);

ser.close()