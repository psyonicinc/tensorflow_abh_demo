import cv2
import mediapipe as mp
import time
import numpy as np
import math
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

# process 5/3
import subprocess
import pyautogui

def get_screen_resolution():
    output = subprocess.Popen('xrandr | grep "\*" | cut -d" " -f4',shell=True, stdout=subprocess.PIPE).communicate()[0]
    resolution = output.split()[0].split(b'x')
    return {'width': resolution[0], 'height': resolution[1]}

class SerialDisplayer:
    def __init__(self, use_grip_cmds, CP210x_only, camera_capture=0):
        self.use_grip_cmds = use_grip_cmds
        self.CP210x_only = CP210x_only
        self.camera_capture = camera_capture
        self.input_listener = None # meant to be a serial object
        
        self.pressed = ''
        self.screen_saver = cv2.imread("default_img.jpg", cv2.IMREAD_COLOR) 
        self.dim = pyautogui.size()

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
                if( (self.CP210x_only == False) or  (self.CP210x_only == True and p[1].find('CP210x') != -1) ):
                    ser = (serial.Serial(p[0],'460800', timeout = 1))
                    self.slist.append(ser)
                    print ("connected!", p)

            except Exception:
                print("Failed to connect. here's traceback: ")
                print(traceback.format_exc())

        print("found ", len(self.slist), "ports")

        start_time = time.time()
        print("connecting input handler...")
        while(time.time() - start_time < 5):
            for i in range(len(self.slist)):
                if (self.slist[i].inWaiting() > 0):
                    self.input_listener = self.slist[i]
                    self.slist.pop(i)
                    start_time -= 40 # we're connected. let's not wait this long
                    break

        if not self.input_listener:
            print("warning: no input handler found")
            # raise RuntimeError("No switch found. Cannot launch program")

        for s in self.slist:
            buf = create_misc_msg(0x50, 0xC2)
            print("writing thumb filter message on com port: ", s)
            s.write(buf)
        
        if not (len(self.slist) > 0 and len(self.slist) <= 2): # check if any serial ports are connected
            raise RuntimeError("no serial ports connected")
        else:
            self.n = len(self.slist)

    def wave_hand(self, fpos):
        """helper function to run handwave"""
        try:
            for i in range(len(fpos)):
                ft = time.time()*1.5 + i*(2*np.pi)/12
                fpos[i] = (0.5*math.sin(ft)+0.5)*45 + 15
            fpos[5] = -fpos[5]

            msg = farr_to_barr(0x50, fpos)
            self.slist[0].write(msg)
        except:
            pass 
        
        try:
            for i in range(len(fpos)):
                ft = time.time()*3 + (i + 6)*(2*np.pi)/12
                fpos[i] = (0.5*math.sin(ft)+0.5)*45+15
            fpos[5] = -fpos[5]
            msg = farr_to_barr(0x50, fpos)
            self.slist[1].write(msg)
        except:
            pass


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
        
        with mp_hands.Hands(
				max_num_hands=self.n,
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

            show_webcam = False
            wave_hand = False

            fpos = [15., 15., 15., 15., 15., -15.]	# for the slow hand wave

            while True:
                if self.input_listener:
                    data_char = self.input_listener.read(self.input_listener.inWaiting()).decode('ascii') # get our input
                    if data_char == 'A':
                        show_webcam = True
                    elif data_char == 'X':
                        show_webcam = False
                    elif data_char == 'Y' and not show_webcam:
                        wave_hand = True
                    elif data_char == 'U' and not show_webcam:
                        wave_hand = False

                if show_webcam:
                    if not cap.isOpened():
                        raise RuntimeError("could not open webcam. cap.isOpened() return 'False' in run()")
                    ts = cv2.getTickCount()
                    tdif = ts - tprev
                    tprev = ts
                    fps = cv2.getTickFrequency()/tdif
                    success, image = cap.read()

                    if not success:
                        print("ignoring empty frame")
                        continue
                    
                    image.flags.writeable = False
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) 
                    results = hands.process(image)
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) # uncomment if color output looks funny
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
                                    time.sleep(0.01)
                                    msg = send_grip_cmd(0x50, 0x00, 0xFF)
                                    self.slist[ser_idx].write(msg)
                                    time.sleep(0.01)
                                    prev_cmd_was_grip[ser_idx] = 1
                                msg = send_grip_cmd(0x50, grip, 0xFF)
                            else:
                                prev_cmd_was_grip[idx] = 0
                                # Write the finger array out over UART to the hand!
                                msg = farr_to_barr(0x50, abhlist[idx].fpos)
                            
                            self.slist[ser_idx].write(msg)

                            # draw landmarks of the hand we found
                            hand_landmarks = results.multi_hand_landmarks[idx]
                            mp_drawing.draw_landmarks(
                                image,
                                hand_landmarks,
                                mp_hands.HAND_CONNECTIONS,
                                mp_drawing_styles.get_default_hand_landmarks_style(),
                                mp_drawing_styles.get_default_hand_connections_style()
                            )

                            # Render a static point in the base frame of the model. Visualization of the position-orientation accuracy.
                            # Point should be just in front of the palm. Compensated for handedness
                            static_point_b = np.array([4.16, 1.05, -1.47*abhlist[idx].handed_sign, 1])*abhlist[idx].scale
                            static_point_b[3] = 1 # remove scaling that wasapplied to the immutable '1'
                            neutral_thumb_w = abhlist[idx].hw_b.dot(static_point_b) # get dot position in world coordinates for a visual tag/reference
                            l_list = landmark_pb2.NormalizedLandmarkList(
                                landmark=[
                                    v4_to_landmark(neutral_thumb_w)
                                ]
                            )
                            mp_drawing.draw_landmarks(
                                image,
                                l_list,
                                [],
                                mp_drawing_styles.get_default_hand_landmarks_style(),
                                mp_drawing_styles.get_default_hand_connections_style()
                            )

                    t_seconds = ts/cv2.getTickFrequency()
                    if (t_seconds > send_unsampling_msg_ts):
                        send_unsampling_msg_ts = t_seconds + 10
                        for i in range(self.n):
                            msg = create_misc_msg(0x50, 0xC2)
                            print("sending: ", [ hex(b) for b in msg ], "to ser device ", i)
                            self.slist[i].write(msg)

                    fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
                    print(fpsfilt)
                    image = cv2.flip(image, 1)
                
                else:
                    if (wave_hand):
                        self.wave_hand(fpos)

                    image = self.screen_saver

                    # time.sleep(0.001) # not sure if we need this so much so I commented it out

                # Flip the image horizontally for selfie-view display
                cv2.namedWindow('MediaPipe Hands', cv2.WINDOW_NORMAL)
                cv2.setWindowProperty('MediaPipe Hands',  cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                
                (x, y, windowWidth, windowHeight) = cv2.getWindowImageRect('MediaPipe Hands')
                ydiv = np.floor(windowHeight/image.shape[0])
                xdiv = np.floor(windowWidth/image.shape[1])
                uniform_mult = np.max([1,np.min([xdiv,ydiv])])
                
                yrem = (windowHeight - image.shape[0]*uniform_mult)
                xrem = (windowWidth - image.shape[1]*uniform_mult)
                top = int(np.max([0, yrem/2]))
                bottom = top
                left = int(np.max([0,xrem/2]))
                right = left
                
                # Pick which 'imgresized' will give you the right fullscreen you want
                # imgresized = cv2.resize(image, (int(image.shape[1]*uniform_mult),int(image.shape[0]*uniform_mult)), interpolation=cv2.INTER_AREA)
                imgresized = cv2.resize(image, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
                dst = cv2.copyMakeBorder(imgresized,top,bottom,left,right, cv2.BORDER_CONSTANT, None, value = 0)
                cv2.imshow('MediaPipe Hands', dst)
                
                key = cv2.waitKey(1) & 0xFF 
                if key == ord('q'):
                    break
                if key == ord('a'):
                    show_webcam = not show_webcam
                
                if key == ord('x') and not show_webcam:
                    wave_hand = not wave_hand
                
        cap.release()
        for s in self.slist:
            s.close()
        
        if self.input_listener:
            self.input_listener.close()

    cv2.destroyAllWindows()

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
    parser.add_argument('--do_grip_cmds' , help="Include flag for using grip commands for grip recognitions", action='store_true')
    parser.add_argument('--CP210x_only', help="for aadeel's bad computer", action='store_true')
    parser.add_argument('--camera_capture', type=int, help="opencv capture number", default=0)
    args = parser.parse_args()
    
    displayer = SerialDisplayer(use_grip_cmds=args.do_grip_cmds, CP210x_only=args.CP210x_only, camera_capture=args.camera_capture)
    displayer.run()
