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

        
        # Find all serial ports
        slist = []
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
                    slist.append(ser)
                    print ("connected!", p)

            except Exception:
                print("Failed to connect. here's traceback: ")
                print(traceback.format_exc())

        print("found ", len(slist), "ports")
        for s in slist:
            buf = create_misc_msg(0x50, 0xC2)
            print("writing thumb filter message on com port: ", s)
            s.write(buf)
        
        if not (len(slist) > 0 and len(slist) <= 2): # check if any serial ports are connected
            raise RuntimeError("no serial ports connected")
        else:
            self.n = len(slist)
        #setup complete. setup mediapipe with 

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

        finally:
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, old_settings)

    def run(self):
        """main loop that runs"""
        lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for the fps counter
        prev_cmd_was_grip = [0,0]

        pass

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
    parser.add_argument('--do_grip_cmds' , help="Include flag for using grip commands for grip recognitions", action='store_true')
    parser.add_argument('--CP210x_only', help="for aadeel's bad computer", action='store_true')
    parser.add_argument('--camera_capture', type=int, help="opencv capture number", default=0)
    args = parser.parse_args()
    
    displayer = Displayer(use_grip_cmds=args.do_grip_cmds, CP210x_only=args.CP210x_only, camera_capture=args.camera_capture)
    displayer.run()
	