from abh_api_core import *
import binascii

testbuf = np.uint8(np.array([0x11]))

pos = np.int16((np.array([15.,16.,17.,18.,19.,-20.])*32767)/150)
rpm = np.int16((np.array([4,-5,6,-7,8,-9]))*4)


for ch in range(0,6):
	bytes = np.uint8(bytearray(struct.pack('<h',pos[ch])))
	testbuf = np.append(testbuf,bytes)
	bytes = np.uint8(bytearray(struct.pack('<h',rpm[ch])))
	testbuf = np.append(testbuf,bytes)	

# testbuf = np.append(testbuf, np.uint8(np.zeros(45)))
topackdata = np.uint8(np.array([100,64,6,45,49,35,12,208,75,106,185,75,54,112,94,43,34,207,158,49,32,168,204,50,187,20,0,1,32,0,3,64,0,5,96,0,1,32,0,3,64,0,5,96,0]))
testbuf = np.append(testbuf, topackdata)
testbuf = np.append(testbuf, np.uint8(np.zeros(1)))

signedbuf = np.int8(testbuf)
chk = np.uint8(np.sum(signedbuf))
testbuf = np.append(testbuf, chk)

b = testbuf.tobytes()

print(binascii.hexlify(b))
print(len(b))


p,i,v,fsr = parse_hand_data(b)
print(p)
print(i)
print(v)
print(fsr)

