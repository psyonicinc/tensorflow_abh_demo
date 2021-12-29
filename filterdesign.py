"""
	Filter design experimentation with the scipy utility.
	
	NOTE: iirfilter produces EXACTLY the same results as fdatool. Tested with the following parameters:
		IIR
		butterworth
		specify order: 2
		Fs: 30 (same for both)
		Wn/Fc: .1 (same for both)
		
	Only difference is that matlab does not apply the gain in the numerator coefficients,
	while scipy does apply the gain in the numerator coefficients.
"""

from scipy import signal
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np


Fs= 30 #samples/s
wn = 0.1 	#normalized from 0-1, where 1 is the nyquist frequency (Fs/2)

#system = signal.iirdesign(wp, ws, gpass, gstop, analog=False, ftype='butter', output='sos', fs=Fs)
system = signal.iirfilter(2, Wn=wn, btype='lowpass', analog=False, ftype='butter', output='sos', fs=Fs)
print(len(system))
print (system)

w,h = signal.sosfreqz(system, worN=523, whole=False, fs=Fs)

fig, ax1 = plt.subplots()
ax1.set_title('Digital filter frequency response')
ax1.plot(w, 20 * np.log10(abs(h)), 'b')
ax1.set_ylabel('Amplitude [dB]', color='b')
ax1.set_xlabel('Frequency [rad/sample]')
ax1.grid()
#ax1.set_ylim([-120, 20])
ax1.relim()
ax1.autoscale_view()
ax2 = ax1.twinx()
angles = np.unwrap(np.angle(h))
ax2.plot(w, angles, 'g')
ax2.set_ylabel('Angle (radians)', color='g')
ax2.grid()
ax2.axis('tight')
ax2.relim()
ax2.autoscale_view()
nticks = 8
ax1.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(nticks))
ax2.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(nticks))
plt.show()