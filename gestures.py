
pinch = [
	[67.6, 1],	#index
	[0, 0],		#middle
	[0, 0],		#ring	
	[0, 0],		#pinky
	[65.38, 1],		#tflexor
	[-65.53, 1]]		#trotator

chuck = [
	[64, 1],	#index
	[64, 1],		#middle
	[0, 0],		#ring	
	[0, 0],		#pinky
	[50, 1],		#tflexor
	[-80, 1]]		#trotator

middletouch = [
	[0, 0],	#index
	[59.6, 1],		#middle
	[0, 0],		#ring	
	[0, 0],		#pinky
	[55.38, 1],		#tflexor
	[-85.53, 1]]		#trotator


def override_grip(fpos, word):
	grip = []
	if word == 1:
		grip = pinch
	if word == 3:
		grip = chuck
	if word == 2:
		grip = middletouch
	
	
	if grip:
		for i in range(len(grip)):
			if grip[i][1]:
				fpos[i] = grip[i][0]
	return fpos