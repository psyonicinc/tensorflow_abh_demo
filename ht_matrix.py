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
