import serial
from abh_api_core import farr_to_barr
import math

ser = serial.Serial('COM3','460800', timeout = 1)

#define fpos
fpos = [15., 15., 15., 15., 15., -15.]

msg = farr_to_barr(fpos)
print(msg)
ser.write(msg)

ser.close()