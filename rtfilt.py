""" 
	My implementation of second order IIR sections which can be used to compute 
	the filtered output of a signal. computed once per sample.
""" 
import numpy as np

""" 
	Scipy style coefficients. For mult-order sections, scipy 
	absorbs all gains into the numerator of the last section, as 
	opposed to matlab which spreads it out. Therefore scipy style
	SOS has no gain associated
""" 
def py_sos_iir(newsample, w, sos):
	b = sos[0:3] #b = NUMERATOR
	a = sos[3:6] #a = DENOMINATOR
	w[2] = w[1]
	w[1] = w[0]
	w[0] = newsample*a[0] - a[1]*w[1] - a[2]*w[2]	#note: a0 is always 1
	fout = b[0]*w[0] + b[1]*w[1] + b[2]*w[2]
	return fout, w

""" 
	Matlab style coefficients
""" 
def ml_sos_iir(newsample, w, sos, gain):
	b = sos[0:3] #b = NUMERATOR
	a = sos[3:6] #a = DENOMINATOR
	w[2] = w[1]
	w[1] = w[0]
	w[0] = newsample*a[0] - a[1]*w[1] - a[2]*w[2]	#note: a0 is always 1
	fout = gain*(b[0]*w[0] + b[1]*w[1] + b[2]*w[2])
	return fout, w
