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
import os

def get_screen_resolution():
    output = subprocess.Popen('xrandr | grep "\*" | cut -d" " -f4',shell=True, stdout=subprocess.PIPE).communicate()[0]
    resolution = output.split()[0].split(b'x')
    return {'width': resolution[0], 'height': resolution[1]}    

class SerialDisplayer:
    def __init__(self, use_grip_cmds, CP210x_only, no_input=False, reverse=False, camera_capture=0, fade_rate=20):
        self.use_grip_cmds = use_grip_cmds
        self.CP210x_only = CP210x_only
        self.no_input = no_input
        self.reverse = reverse
        self.camera_capture = camera_capture
        self.fade_rate = fade_rate
        self.input_listener = None # meant to be a serial object

        self.dim = pyautogui.size()
        self.screen_saver = cv2.imread("default_img.jpg", cv2.IMREAD_COLOR)
        self.original_shape = self.screen_saver.shape
        self.screen_saver = cv2.resize(self.screen_saver, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
        self.black_img = np.zeros_like(self.screen_saver)

        # Find all serial ports
        self.slist = []
        com_ports_list = list(list_ports.comports())
        port = []

        for p in com_ports_list:
            if(p):
                port.append(p)
                print("Found: ", p)

        if not port:
            print("no port found")

        for p in port:
            try:
                ser = []
                if ( (not self.CP210x_only) or (self.CP210x_only == True and (p[1].find('FT232R') != -1)) ):
                    ser = (serial.Serial(p[0], '460800', timeout=1))
                    self.slist.append(ser)
                    print("connected!", p)

                # TODO: IR sensor input listeners 
                elif not self.no_input and ( (not self.CP210x_only) or (self.CP210x_only == True and (p[1].find('CP210') != -1) ) ):
                    print("connecting input handler...")
                    self.input_listener = (serial.Serial(p[0], '460800', timeout=1))

            except Exception:
                print("Failed to connect. here's traceback: ")
                print(traceback.format_exc)

        print("found ", len(self.slist), " ports")

        if not (len(self.slist) > 0 and len(self.slist) <= 2): # check number of available hands
            raise RuntimeError("no serial ports connected")
        else:
            self.n = len(self.slist)


        if not self.input_listener:
            print("warning: no input handler found")
            # raise RuntimeError("No switch found. Cannot launch program")
        else:
            ir_port = self.input_listener.port
            self.input_listener.close()
            self.input_listener = serial.Serial(ir_port,'500000', timeout=1)

        for s in self.slist:
            buf = create_misc_msg(0x50, 0xC2)
            print("writing thumb filter message on com port: ", s)
            s.write(buf)
        

        if self.reverse:
            self.slist.reverse()

    def wave_hand(self, fpos):
        """helper function to run handwave"""
        for serial in self.slist:
            try:
                for i in range(len(fpos)):
                    ft = time.time()*1.25 + i*(2*np.pi)/12
                    fpos[i] = (0.5*math.sin(ft)+0.5)*45 + 15
                fpos[5] = -fpos[5]

                msg = farr_to_barr(0x50, fpos)
                serial.write(msg)

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
        fourcc = cv2.VideoWriter_fourcc('M','J','P','G')
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        cap.set(cv2.CAP_PROP_FPS, 90)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(1920*720/1080))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(1080*720/1080))

        fps = int(cap.get(5))
        print("fps: ", fps)
        
        with mp_hands.Hands(
				max_num_hands=self.n,
				model_complexity=0,
				min_detection_confidence=0.33,
				min_tracking_confidence=0.66) as hands:
            
            tprev = cv2.getTickCount()
            warr_fps = [0,0,0]
            
            # params for grip overload
            abhlist = []
            for i in range(self.n):
                abh = AbilityHandBridge()
                abhlist.append(abh)
            
            #abhlist.reverse()

            send_unsampling_msg_ts = 0

            show_webcam = False
            wave_hand = True
            transition_count = 100

            fpos = [15., 15., 15., 15., 15., -15.]	# for the slow hand wave

            while True:
                if self.input_listener:
                    #data_char = self.input_listener.read(self.input_listener.inWaiting())
                    data_char = set(self.input_listener.read(self.input_listener.inWaiting()).decode('ascii')) # get our input
                    
                    if 'A' in data_char:
                        show_webcam = True
                        transition_count = 0

                    elif 'X' in data_char:
                        show_webcam = False
                        transition_count = 0

                    elif 'Y' in data_char and not show_webcam:
                        wave_hand = not wave_hand

                    elif 'U' in data_char and not show_webcam:
                        wave_hand = not wave_hand

                if show_webcam:
                    """
                    mediapipe hand detection
                    """
                    if cap.isOpened():
                        ts = cv2.getTickCount()
                        tdif = ts - tprev
                        tprev = ts
                        fps = cv2.getTickFrequency()/tdif
                        success, image = cap.read()
                        #print("webcam image shape: ", image.shape)

                        if not success:
                            print("ignoring empty frame")
                            continue
                        
                        image.flags.writeable = False
                        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) 
                        results = hands.process(image)
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) # comment/uncomment if color output looks funny
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
                        imgresized = cv2.resize(image, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
                        if (transition_count < self.fade_rate):
                            fadein = transition_count/float(self.fade_rate)
                            imgresized = cv2.addWeighted(self.black_img, 1-fadein, imgresized, fadein, 0)
                            transition_count += 1
         
                else:
                    if (wave_hand):
                        self.wave_hand(fpos)

                    image = self.screen_saver

                    if (transition_count < float(self.fade_rate) and cap.isOpened()):
                        _, webcam_img = cap.read()
                        webcam_img = cv2.flip(webcam_img, 1)
                        webcam_img = cv2.resize(webcam_img, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
                        fadein = transition_count/float(self.fade_rate)
                        imgresized = cv2.addWeighted(self.black_img, 1-fadein, self.screen_saver, fadein, 0)
                        transition_count += 1
                    else:
                        imgresized = image
                    # time.sleep(0.001) # not sure if we need this so much so I commented it out

                # Flip the image horizontally for selfie-view display
                cv2.namedWindow('MediaPipe Hands', cv2.WINDOW_NORMAL)
                cv2.setWindowProperty('MediaPipe Hands',  cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                
                (x, y, windowWidth, windowHeight) = cv2.getWindowImageRect('MediaPipe Hands')
                ydiv = np.floor(windowHeight/imgresized.shape[0])
                xdiv = np.floor(windowWidth/imgresized.shape[1])
                uniform_mult = np.max([1,np.min([xdiv,ydiv])])
                
                yrem = (windowHeight - imgresized.shape[0]*uniform_mult)
                xrem = (windowWidth - imgresized.shape[1]*uniform_mult)
                top = int(np.max([0, yrem/2]))
                bottom = top
                left = int(np.max([0,xrem/2]))
                right = left
                
                # Pick which 'imgresized' will give you the right fullscreen you want
                # imgresized = cv2.resize(image, (int(image.shape[1]*uniform_mult),int(image.shape[0]*uniform_mult)), interpolation=cv2.INTER_AREA)
                dst = cv2.copyMakeBorder(imgresized,top,bottom,left,right, cv2.BORDER_CONSTANT, None, value = 0)
                if (show_webcam):
                    self.freeze_pic = cv2.resize(dst, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
                cv2.imshow('MediaPipe Hands', dst)
                
                key = cv2.waitKey(1) & 0xFF 
                if key == ord('q'):
                    break
                if key == ord('a'):
                    show_webcam = not show_webcam
                    transition_count = 0
                
                if key == ord('x') and not show_webcam:
                    wave_hand = not wave_hand
                
        cap.release()
        for s in self.slist:
            s.close()
        
        if self.input_listener:
            self.input_listener.close()

    cv2.destroyAllWindows()
    #os.system("killall -9 unclutter")

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
    parser.add_argument('--do_grip_cmds' , help="Include flag for using grip commands for grip recognitions", action='store_true')
    parser.add_argument('--CP210x_only', help="for aadeel's bad computer", action='store_true')
    parser.add_argument('--no_input', help="No input handler? Skip input reading step", action='store_true')
    parser.add_argument('--reverse', help="reverse the order of the hands in order to map detections properly", action='store_true')
    parser.add_argument('--camera_capture', type=int, help="opencv capture number", default=0)
    parser.add_argument('--fade_rate', type=int, help="fade transition speed", default=20)
    args = parser.parse_args()
    
    displayer = SerialDisplayer(use_grip_cmds=args.do_grip_cmds, CP210x_only=args.CP210x_only, no_input=args.no_input, reverse=args.reverse, camera_capture=args.camera_capture, fade_rate=args.fade_rate)
    displayer.run()
