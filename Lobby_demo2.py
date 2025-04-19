import cv2
import mediapipe as mp
import time
import numpy as np
import math
from matplotlib import animation
from matplotlib import pyplot as plt
from vect_tools import *
from rtfilt import *
from scipy import signal
import serial
from serial.tools import list_ports
from gestures import *
from abh_get_fpos import *
import argparse
from ability_hand_api.python.ah_wrapper.ah_serial_client import AHSerialClient
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
        self.input_listener = None

        self.dim = pyautogui.size()
        self.screen_saver = cv2.imread("default_img.jpg", cv2.IMREAD_COLOR)
        self.original_shape = self.screen_saver.shape
        self.screen_saver = cv2.resize(self.screen_saver, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
        self.black_img = np.zeros_like(self.screen_saver)

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
                if (not self.CP210x_only or (self.CP210x_only and ('FT232R' in p[1]))):
                    client = AHSerialClient()
                    self.slist.append(client)
                    print("Connected to Ability Hand on: ", p)

                elif not self.no_input and (not self.CP210x_only or (self.CP210x_only and ('CP210' in p[1]))):
                    print("connecting input handler...")
                    self.input_listener = serial.Serial(p[0], '460800', timeout=1)
                    print("connected input handler: ", p)

            except Exception:
                print("Failed to connect. Traceback:")
                print(traceback.format_exc())

        if not (len(self.slist) > 0 and len(self.slist) <= 2):
            raise RuntimeError("No serial ports connected")
        else:
            self.n = len(self.slist)

        if not self.input_listener:
            print("Warning: no input handler found")
        else:
            ir_port = self.input_listener.port
            self.input_listener.close()
            self.input_listener = serial.Serial(ir_port, '500000', timeout=1)

        if self.reverse:
            self.slist.reverse()

    def wave_hand(self, fpos):
        for client in self.slist:
            try:
                for i in range(len(fpos)):
                    ft = time.time()*0.905 + i*(2*np.pi)/12
                    fpos[i] = (0.5*math.sin(ft)+0.5)*45 + 15
                fpos[5] = -fpos[5]
                client.set_position(fpos)
            except:
                pass 

    def relax_hand(self, fpos):
        for client in self.slist:
            try:
                fpos = [1]*6
                client.set_position(fpos)
            except:
                pass 

    def run(self):
        lpf_fps_sos = signal.iirfilter(2, Wn=0.7, btype='lowpass', analog=False, ftype='butter', output='sos', fs=30)
        prev_cmd_was_grip = [0, 0]

        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles
        mp_hands = mp.solutions.hands

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
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

            from abh_api_core import AbilityHandBridge
            abhlist = [AbilityHandBridge() for _ in range(self.n)]

            show_webcam = False
            wave_hand = True
            Relax_H = False
            transition_count = 100
            fpos = [15., 15., 15., 15., 15., -15.]

            while True:
                if self.input_listener:
                    data_char = set(self.input_listener.read(self.input_listener.inWaiting()).decode('ascii'))
                    if 'A' in data_char or 'X' in data_char:
                        show_webcam = not show_webcam
                        transition_count = 0
                    elif ('Y' in data_char or 'U' in data_char) and not show_webcam:
                        wave_hand = not wave_hand

                if show_webcam:
                    Relax_H = False
                    if cap.isOpened():
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
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                        if results.multi_hand_landmarks:
                            num_writes = 1
                            if len(results.multi_hand_landmarks) == 2 and results.multi_handedness[0].classification[0].index != results.multi_handedness[1].classification[0].index:
                                num_writes = 2
                            for idx in range(num_writes):
                                t = time.time()
                                ser_idx = results.multi_handedness[idx].classification[0].index
                                if self.n == 1:
                                    ser_idx = 0

                                abhlist[idx].update(mp_hands, results.multi_hand_landmarks[idx].landmark, results.multi_handedness[idx].classification[0].index)

                                if abhlist[idx].is_set_grip == 1 and (abhlist[idx].grip_word in [1, 3]) and self.use_grip_cmds:
                                    grip = 0x3 if abhlist[idx].grip_word == 1 else 0x4
                                    if prev_cmd_was_grip[ser_idx] == 0:
                                        self.slist[ser_idx].set_grip(grip)
                                        time.sleep(0.01)
                                        self.slist[ser_idx].set_grip(0x00)
                                        time.sleep(0.01)
                                        prev_cmd_was_grip[ser_idx] = 1
                                    self.slist[ser_idx].set_grip(grip)
                                else:
                                    prev_cmd_was_grip[idx] = 0
                                    self.slist[ser_idx].set_position(abhlist[idx].fpos)

                                hand_landmarks = results.multi_hand_landmarks[idx]
                                mp_drawing.draw_landmarks(
                                    image,
                                    hand_landmarks,
                                    mp_hands.HAND_CONNECTIONS,
                                    mp_drawing_styles.get_default_hand_landmarks_style(),
                                    mp_drawing_styles.get_default_hand_connections_style()
                                )

                        fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, lpf_fps_sos[0])
                        print(fpsfilt)
                        image = cv2.flip(image, 1)
                        imgresized = cv2.resize(image, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
                        if transition_count < self.fade_rate:
                            fadein = transition_count / float(self.fade_rate)
                            imgresized = cv2.addWeighted(self.black_img, 1 - fadein, imgresized, fadein, 0)
                            transition_count += 1
                else:
                    if wave_hand:
                        Relax_H = False
                        self.wave_hand(fpos)
                    else:
                        if not Relax_H:
                            self.relax_hand(fpos)

                    imgresized = self.screen_saver

                    if transition_count < float(self.fade_rate) and cap.isOpened():
                        _, webcam_img = cap.read()
                        webcam_img = cv2.flip(webcam_img, 1)
                        webcam_img = cv2.resize(webcam_img, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
                        fadein = transition_count / float(self.fade_rate)
                        imgresized = cv2.addWeighted(self.black_img, 1 - fadein, self.screen_saver, fadein, 0)
                        transition_count += 1

                cv2.namedWindow('MediaPipe Hands', cv2.WINDOW_NORMAL)
                cv2.setWindowProperty('MediaPipe Hands',  cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                dst = cv2.resize(imgresized, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hand CV Demo Parser')
    parser.add_argument('--do_grip_cmds', action='store_true')
    parser.add_argument('--CP210x_only', action='store_true')
    parser.add_argument('--no_input', action='store_true')
    parser.add_argument('--reverse', action='store_true')
    parser.add_argument('--camera_capture', type=int, default=0)
    parser.add_argument('--fade_rate', type=int, default=20)
    args = parser.parse_args()

    displayer = SerialDisplayer(
        use_grip_cmds=args.do_grip_cmds,
        CP210x_only=args.CP210x_only,
        no_input=args.no_input,
        reverse=args.reverse,
        camera_capture=args.camera_capture,
        fade_rate=args.fade_rate
    )
    displayer.run()
