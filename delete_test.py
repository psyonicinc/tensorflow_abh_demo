import numpy as np

hw_b = np.zeros((4,4))

vx = np.array([1,.5,0])
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




print (hw_b)