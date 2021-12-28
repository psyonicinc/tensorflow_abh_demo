import cv2
import numpy as np
from ht_matrix import *
    
tstart = cv2.getTickCount()

hw_b = np.zeros((4,4))
hb_w = np.zeros((4,4))

vx = np.array([1,.5,-4])
vx = vx/np.sqrt(vx.dot(vx))

vyref = np.array([0,1,0])
vyref = vyref/np.sqrt(vyref.dot(vyref))

vz = np.cross(vx, vyref)
vz = vz/np.sqrt(vz.dot(vz))

vy = np.cross(vz, vx)
vy = vy/np.sqrt(vy.dot(vy))


base = np.array([10,11,12])

hw_b[0:3, 0] = vx
hw_b[0:3, 1] = vy
hw_b[0:3, 2] = vz
hw_b[0:3, 3] = base
hw_b[3, 0:4] = np.array([0,0,0,1])

hb_w = ht_inverse(hw_b)
base4 = v3_to_v4(base)
op_b = hb_w.dot(base4)  #NOTE: this is the way to multiply a 4x4 matrix by a 4x1 array!!! use dot

tend = cv2.getTickCount()

print (hw_b)
print (hb_w)
#print(base4)
print(op_b)
print(tend-tstart)


