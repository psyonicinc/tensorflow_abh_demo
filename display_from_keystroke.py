import cv2
import mediapipe as mp
import time
import numpy as np
from matplotlib import animation
from matplotlib import pyplot as plt
from vect_tools import *
from rtfilt import *
from abh_api_core import *
from scipy import signal
import serial
from serial.tools import list_ports
from gestures import *
from abh_get_fpos import *
import argparse

# debugging. please remove after done
import traceback

# keystroke listening
import sys
import termios
import tty
from threading import Thread

class Displayer:
    def __init__(self, use_grip_cmds, CP210x_only, camera_capture=0):
        self.use_grip_cmds = use_grip_cmds
        self.CP210x_only = CP210x_only
        self.camera_capture = camera_capture
        
        self.pressed = ''
        self.listener = Thread(target=self.get_key)
        self.screen_saver = cv2.imread("default_img.jpg", cv2.IMREAD_COLOR) 
        self.img = self.screen_saver
        
        # Find all serial ports
        self.slist = []
        com_ports_list = list(list_ports.comports())
        port = []

        for p in com_ports_list:
            if(p):
                pstr = ""
                pstr = p
                port.append(pstr)
                print("Found: ", pstr)

        if not port:
                print("no port found")

        for p in port:
            try:
                ser = []
                if( (args.CP210x_only == False) or  (args.CP210x_only == True and p[1].find('CP210x') != -1) ):
                    ser = (serial.Serial(p[0],'460800', timeout = 1))
                    self.slist.append(ser)
                    print ("connected!", p)

            except Exception:
                print("Failed to connect. here's traceback: ")
                print(traceback.format_exc())

        print("found ", len(self.slist), "ports")
        for s in self.slist:
            buf = create_misc_msg(0x50, 0xC2)
            print("writing thumb filter message on com port: ", s)
            s.write(buf)
        
        if not (len(self.slist) > 0 and len(self.slist) <= 2): # check if any serial ports are connected
            raise RuntimeError("no serial ports connected")
        else:
            self.n = len(self.slist)
        
    def get_key(self):
        file_descriptor = sys.stdin.fileno()
        old_settings = termios.tcgetattr(file_descriptor)
        try:
            tty.setcbreak(file_descriptor)
            while True:
                # Listen for keyboard input
                key = sys.stdin.read(1)
                if (key == 'a' or key =='s' or key == 'q'):
                    self.pressed = key
                    if key is 'q':
                        break

        finally:
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, old_settings)
    


    def run(self):
        """main loop that runs"""
        lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for the fps counter
        prev_cmd_was_grip = [0,0]

        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles
        mp_hands = mp.solutions.hands

        # webcam input
        cap = cv2.VideoCapture(self.camera_capture)
        cap.set(cv2.CAP_PROP_FPS, 90)
        fps = int(cap.get(5))
        print("fps: ", fps)

        self.listener.start() # thread listens to keystrokes 
        
        with mp_hands.Hands(
				max_num_hands=n,
				model_complexity=0,
				min_detection_confidence=0.66,
				min_tracking_confidence=0.66) as hands:
            
            tprev = cv2.getTickCount()
            warr_fps = [0,0,0]
            
            # params for grip overload
            abhlist = []
            for i in range(self.n):
                abh = AbilityHandBridge()
                abhlist.append(abh)

            send_unsampling_msg_ts = 0
            while cap.isOpened():
                ts = cv2.getTickCount()
                tdif = ts - tprev
                tprev = ts
                fps = cv2.getTickFrequency()/tdif
                success, image = cap.read()

                if not success:
                    print("ignoring empty frame")
                    continue
                
                image.flags.writeable = False
                image = cv2.cvtColor(image, cv2.colorBGR2RGB)
                results = hands.process(image)
                if results.multi_hand_landmarks:
                    num_writes = 1
                    if(len(results.multi_hand_landmarks) == 2 and results.multi_handedness[0].classification[0].index != results.multi_handedness[1].classification[0].index):
                        num_writes = 2
                    for idx in range(num_writes):
                        # log time for plotting
                        t = time.time()
                        ser_idx = results.multi_handedness[idx].classification[0].index
                        if (self.n == 1):
                            ser_idx = 0

                        abhlist[idx].update(mp_hands, results.multi_hand_landmarks[idx].landmark, results.multi_handedness[idx].classification[0].index)

                        if abhlist[idx].is_set_grip == 1 and (abhlist[idx].grip_word == 1 or abhlist[idx].grip_word == 3) and self.use_grip_cmds == 1:
                            grip = 0x00
                            if (abhlist[idx].grip_word == 1):
                                grip = 0x3
                            elif (abhlist[idx].grip_word ==3):
                                grip = 0x4
                            if (prev_cmd_was_grip[ser_idx] == 0):
                                msg = send_grip_cmd(0x50, grip, 0xFF)
                                self.slist[ser_idx].write(msg)
                
                #TODO: CONTINUE FROM HERE

            """OTHER IDEA. PLEASE EXCUSE THIS BLOCK"""
            show_webcam = False # webcam flag
            while (cap.isOpened()):
                if (self.pressed == 'a'):
                    show_webcam = not show_webcam
                    self.pressed = ''
                    
                if (show_webcam):
                    pass
                else:
                    self.img

                cv2.waitKey(0)

    cv2.destroyAllWindows()

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
    parser.add_argument('--do_grip_cmds' , help="Include flag for using grip commands for grip recognitions", action='store_true')
    parser.add_argument('--CP210x_only', help="for aadeel's bad computer", action='store_true')
    parser.add_argument('--camera_capture', type=int, help="opencv capture number", default=0)
    args = parser.parse_args()
    
    displayer = Displayer(use_grip_cmds=args.do_grip_cmds, CP210x_only=args.CP210x_only, camera_capture=args.camera_capture)
    displayer.run()
	