import cv2
import numpy as np
from vect_tools import *
    
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

v1 = np.array([1,0,0,1])
v2 = np.array([0,1,0,1])
ang = vect_angle(v1[0:2],v2[0:2])

v1 = np.array([0,1,1,1])
hx = ht_rotx(90*np.pi/180)
v2 = hx.dot(v1)

tend = cv2.getTickCount()

#print(v2)
#print (hw_b)
#print (hb_w)
#print(base4)
#print(op_b)
#print(tend-tstart)



"""
	
	y cross z = x
	z cross x = y
	x cross y = z
	
	z cross y = -x
	x cross z = -y
	y cross x = -z
	
	
"""

x = np.array([1,0,0])
y = np.array([0,1,0])
z = np.array([0,0,1])
print(np.cross(y,z))
print(np.cross(z,x))
print(np.cross(x,y))

print(np.cross(z,y))
print(np.cross(x,z))
print(np.cross(y,x))


