import numpy as np

def ht_inverse(hin):
    hout = np.zeros((4,4))
    hout[0:3, 0:3] = np.transpose(hin[0:3,0:3])
    hout[0:3, 3] = -np.dot(hout[0:3,0:3], hin[0:3,3])
    return hout

def v3_to_v4(vin):
    vout = np.zeros(4)
    vout[0:3] = vin
    vout[3] = 1
    return vout

def vect_angle(v1, v2):
	dp = np.dot(v1,v2)
	mp = np.sqrt(v1.dot(v1)) * np.sqrt(v2.dot(v2))
	cos_theta = dp/mp
	return np.arccos(cos_theta)
	
def ht_rotx(ang):
	cth = np.cos(ang)
	sth = np.sin(ang)
	h = np.array([ [1, 0, 0, 0],
		[0, cth, -sth, 0],
		[0, sth, cth, 0],
		[0, 0, 0, 1]])
	return h
	
def clamp(val, lowerlim, upperlim):
	return max(min(upperlim,val),lowerlim)

def mag(v):
	return np.sqrt(v.dot(v))
	
def linmap(v, outmax,outmin, inmax,inmin):
	return (v-inmin)*((outmax-outmin)/(inmax-inmin))
