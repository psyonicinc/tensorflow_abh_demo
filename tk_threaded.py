import tkinter as tk
import cv2 
from PIL import ImageTk, Image
import pyautogui
import mediapipe as mp
import numpy as np
import argparse
import serial
from serial.tools import list_ports
import math
from threading import Thread
# debug
import traceback

# local imports
from abh_api_core import *
from rtfilt import *
from gestures import *
from abh_get_fpos import *
from vect_tools import *

class TKThreaded(tk.Tk):
    def __init__(self, use_grip_cmds, CP210x_only, no_input=False, reverse=False, camera_capture=0, fade_rate=20):
        super().__init__()
        self.attributes('-fullscreen', True)
        self.config(cursor='none')

        self.use_grip_cmds: bool = use_grip_cmds
        self.CP210x_only: bool = CP210x_only
        self.no_input: bool = no_input
        self.reverse: bool = reverse
        self.camera_capture = camera_capture
        self.fade_rate = fade_rate
        self.input_listener = None # meant to be a serial object

        self.dim = pyautogui.size()
        self.screen_saver = cv2.imread("default_img.jpg")
        self.screen_saver = cv2.resize(self.screen_saver, (self.dim[0], self.dim[1]))
        self.black_img = np.zeros_like(self.screen_saver)

        self.label = tk.Label(self)
        self.label.pack()

        self.show_webcam = False
        self.wave_hand = True
        self.transition_count = 100 # when transitioning between screensaver and webcam

        self.cam_thread = Thread(target=self.run)

        # key bindings
        self.bind('q', self.close_window)
        self.bind('a', self.switch_img)
        self.bind('x', self.switch_handwave)

        # webcam
        fourcc = cv2.VideoWriter_fourcc('M','J','P','G')
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.cap.set(cv2.CAP_PROP_FPS, 90)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(1920*720/1080))
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(1080*720/1080))

        if not self.cap.isOpened():
            print("WARNING: cap.isOpened() returned false in __init__()")

        # Find all serial ports for self.slist
        self.slist = []
        com_ports_list = list(list_ports.comports())
        port = []

        for p in com_ports_list:
            if (p):
                port.append(p)
                print("Found: ", p)
        
        if not port:
            print("no port found")

        for p in port:
            try:
                ser = []
                if ( (not self.CP210x_only) or  (self.CP210x_only == True and ( (p[1].find('CP210') != -1) or (p[1].find('FT232R') != -1) )) ):
                    ser = (serial.Serial(p[0], '460800', timeout=1))
                    self.slist.append(ser)
                    print("connected!", p)
            except Exception:
                print("Failed to connect. here's traceback: ")
                print(traceback.format_exc)

        # TODO: IR sensor input listeners 
        if not self.no_input:
            start_time = time.time()
            print("connecting input handler...")
            while (time.time() - start_time < 5):
                for i in range(len(self.slist)):
                    if (self.slist[i].inWaiting() > 0):
                        self.input_listener = self.slist.pop(i)
                        start_time -= 40 # we're connected. let's not wait this long
                        break

        self.n = len(self.slist)
        if not (self.n > 0 and self.n <= 2): # if 0 < self.n <= 2 is false. For 2 hands
            raise RuntimeError("no serial ports connected. here's self.n: ", self.n)
        
        print("found ", len(self.slist), " ports" )

        # TODO: control initialization
        self.fpos = [15., 15., 15., 15., 15., -15.]
        self.send_unsampling_msg_ts = 0
        self.lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)	#filter for the fps counter
        self.prev_cmd_was_grip = [0,0]
        self.warr_fps = [0,0,0]
        self.abhlist = []
        for i in range(self.n):
            abh = AbilityHandBridge()
            self.abhlist.append(abh)
        
        if self.reverse:
            self.slist.reverse()

        fps = int(self.cap.get(5))
        print("fps: ", fps)

        # mediapipe detection initialization
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_hands = mp.solutions.hands
        self.hand_detector = self.mp_hands.Hands(max_num_hands=self.n,
            model_complexity=0,
            min_detection_confidence=0.33,
            min_tracking_confidence=0.66)

        self.tprev = cv2.getTickCount()

    def run(self):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
    parser.add_argument('--do_grip_cmds' , help="Include flag for using grip commands for grip recognitions", action='store_true')
    parser.add_argument('--CP210x_only', help="for aadeel's bad computer", action='store_true')
    parser.add_argument('--no_input', help="No input handler? Skip input reading step", action='store_true')
    parser.add_argument('--reverse', help="reverse the order of the hands in order to map detections properly", action='store_true')
    parser.add_argument('--camera_capture', type=int, help="opencv capture number", default=0)
    parser.add_argument('--fade_rate', type=int, help="fade transition speed", default=20)
    args = parser.parse_args()

    app = TKThreaded(use_grip_cmds=args.do_grip_cmds, CP210x_only=args.CP210x_only, no_input=args.no_input, reverse=args.reverse, camera_capture=args.camera_capture, fade_rate=args.fade_rate)
    app.after(10, app.updater)
    app.mainloop()