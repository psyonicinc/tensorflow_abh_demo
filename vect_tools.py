import numpy as np
from mediapipe.framework.formats import landmark_pb2

"""
	Computes the inverse of the input matrix. Valid only
	for inputs which are homogeneous transformation matrices.
	Uses the property of rotation matrices where the inverse 
	is equal to the transpose for fast computation. 
"""
def ht_inverse(hin):
    hout = np.zeros((4,4))
    hout[0:3, 0:3] = np.transpose(hin[0:3,0:3])
    hout[0:3, 3] = -np.dot(hout[0:3,0:3], hin[0:3,3])
    return hout

"""
	Pads a 1 to the end of an numpy 3-vector.
	Input type must be an np.array of size at least 3
"""
def v3_to_v4(vin):
    vout = np.zeros(4)
    vout[0:3] = vin
    vout[3] = 1
    return vout

"""
	Computes the angle between two n-dimensional vectors by 
	computing the arccos of the normalized dot product.
	
	NOTE: This will produce an incorrect result if a 1-padded
	vector (i.e. the type used for homogeneous transformation 
	matrix multiplication) is used. Be sure to call on vect[0:3]
	if using a 1-padded 3 vector.
"""
def vect_angle(v1, v2):
	dp = np.dot(v1,v2)
	mp = np.sqrt(v1.dot(v1)) * np.sqrt(v2.dot(v2))
	cos_theta = dp/mp
	return np.arccos(cos_theta)

"""
	Returns a 4x4 homogeneous transformation matrix
	which is the principle rotation about X by the
	angle 'ang' (in radians).
"""	
def ht_rotx(ang):
	cth = np.cos(ang)
	sth = np.sin(ang)
	h = np.array([ [1, 0, 0, 0],
		[0, cth, -sth, 0],
		[0, sth, cth, 0],
		[0, 0, 0, 1]])
	return h


"""
	Returns a 4x4 homogeneous transformation matrix
	which is the principle rotation about the Z axis by the
	angle 'ang' (in radians).
"""	
def ht_rotz(ang):
	cth = np.cos(ang)
	sth = np.sin(ang)
	h = np.array([ [cth, -sth, 0, 0],
		[sth, cth, 0, 0],
		[0, 0, 1, 0],
		[0, 0, 0, 1]])
	return h

"""
	Returns a 4x4 homogeneous transformation matrix
	which is the principle rotation about the Y axis by the
	angle 'ang' (in radians).
"""	
def ht_roty(ang):
	cth = np.cos(ang)
	sth = np.sin(ang)
	h = np.array([ [cth, 0, sth, 0],
		[0, 1, 0, 0],
		[-sth, 0, cth, 0],
		[0, 0, 0, 1]])
	return h


def ht_from_2_vectors(vx, vyref, origin):
	ret = np.zeros((4,4))
	
	vz = np.cross(vx, vyref)
	vz = vz/mag(vz)
	vy = np.cross(vz, vx)
	vy = vy/mag(vy)
	ret[0:3, 0] = vx
	ret[0:3, 1] = vy
	ret[0:3, 2] = vz
	ret[0:3, 3] = origin
	ret[3, 0:4] = np.array([0,0,0,1])
	return ret

"""
	get xyz/rpy from a 4x4 homogeneous transformation matrix
"""
def get_xyz_rpy(R):
	yaw = np.arctan2(R[1][0],R[0][0])
	pitch = np.arctan2( -R[2][0], np.sqrt(R[2][1]**2+R[2][2]**2))
	roll = np.arctan2(R[2][1],R[2][2])
	rpy = np.array([roll,pitch,yaw])
	xyz = R[0:3,3]
	return xyz, rpy

"""
	get 4x4 homogeneous transformation matrix from xyz/rpy
"""
def get_ht4x4_from_xyz_rpy(xyz, rpy):
	Hyaw = ht_rotz(rpy[2])
	Hpitch = ht_roty(rpy[1])
	Hroll = ht_rotx(rpy[0])
	H = Hyaw.dot(Hpitch.dot(Hroll))
	H[0:3,3] = xyz
	return H

"""
	restrict val to lowerlim-upperlim
"""	
def clamp(val, lowerlim, upperlim):
	return max(min(upperlim,val),lowerlim)

"""
	fast computation of the vector magnitude of input v
"""	
def mag(v):
	return np.sqrt(v.dot(v))

"""
	linear mapping helper function
"""		
def linmap(v, p_out, p_in):
	return (v-p_in[0])*((p_out[1]-p_out[0])/(p_in[1]-p_in[0]))

"""
	mediapipe landmark helper function.
	
	Converts a mediapipe landmark_pb2 landmark
	to a numpy array 3-vector
"""	
def to_vect(v):
	return np.array([v.x, v.y, v.z])
	
"""
	mediapipe landmark helper function.
	
	Converts a numpy 3 vector (can be either
	a normal 3 vector or a 1-padded 3-vector)
	to a mediapipe normalized landmark. This 
	landmark can be entered into a list for 
	the mediapipe backend to draw as a landmark
	(red dot)
"""		
def v4_to_landmark(v):
	lm = landmark_pb2.NormalizedLandmark()
	lm.x = v[0]
	lm.y = v[1]
	lm.z = v[2]
	return lm
