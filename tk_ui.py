import tkinter as tk
from PIL import ImageTk, Image
import cv2 
import pyautogui
import mediapipe as mp
import numpy as np
import argparse
import serial
from serial.tools import list_ports
import math
# debug
import traceback

# local imports
from abh_api_core import *
from rtfilt import *
from gestures import *
from abh_get_fpos import *
from vect_tools import *

class TKUI(tk.Tk):
    def __init__(self, use_grip_cmds, CP210x_only, no_input=False, reverse=False, camera_capture=0, fade_rate=20):
        super().__init__(self)
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
        self.black_img = np.zeros((self.dim[0], self.dim[1]))

        self.label = tk.Label(self)
        self.label.pack()

        self.show_webcam = False
        self.wave_hand = True
        self.transition_count = 100 # when transitioning between screensaver and webcam

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
        
        self.n = len(self.slist)
        if not (self.n > 0 and self.n <= 2): # if 0 < self.n <= 2 is false
            raise RuntimeError("no serial ports connected")
        
        print("found ", len(self.slist), " ports" )
        
        # TODO: IR sensor input listeners 


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

        fps = int(cap.get(5))
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

    def handwave(self, fpos):
        for serial in self.slist:
            try:
                for i in range(len(fpos)):
                    ft = time.time()*1.25 + i*(2*np.pi)/12
                    fpos[i] = (0.5*math.sin(ft)+0.5)
                fpos[5] = -fpos[5]

                msg = farr_to_barr(0x50, fpos)
                serial.write(msg)
            except:
                pass
    
    # event handlers
    def close_window(self, e):
        self.cap.release()
        for s in self.slist:
            s.close()
        
        if self.input_listener: # TODO: implement input listener part
            self.input_listener.close()

        cv2.destroyAllWindows()
        self.destroy()

    def switch_img(self, e):
        self.transition_count = 0
        self.show_webcam = not self.show_webcam

    def switch_handwave(self, e):
        self.wave_hand = not self.wave_hand

    # the function called in our mainloop
    def update(self):
        # here's what mainloop calls

        if self.input_listener:
            # TODO: implement input listener
            pass
        
        if show_webcam:
            """
            mediapipe hand detection
            """
            if self.cap.isOpened():
                ts = cv2.getTickCount()
                tdif = ts - self.tprev
                self.tprev = ts
                fps = cv2.getTickGrequency()/tdif
                success, image = self.cap.read()

                if not success:
                    print("ignoring empty frame")
                    return

                image.flags.writeable = False
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                results = self.hand_detector.process(image)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) # comment/uncomment if color output looks funny
                
                if results.multi_hand_landmarks:
                    num_writes = 1
                    if (len(results.multi_hand_landmarks) == 2 and results.multi_handedness[0].classification[0].index != results.multi_handedness[1].classification[0].index):
                        num_writes = 2
                    for idx in range(num_writes):
                        t = time.time()
                        ser_idx = results.multi_handedness[idx].classification[0].index
                        if (self.n == 1):
                            ser_idx = 0
                        
                        self.abhlist[idx].update(self.mp_hands, results.multi_hand_landmarks[idx].landmark, results.multi_handedness[idx].classification[0].index)
                        
                        if self.abhlist[idx].is_set_grip == 1 and (self.abhlist[idx].grip_word == 1 or self.abhlist[idx].grip_word == 3) and self.use_grip_cmds == 1:
                            grip = 0x00
                            if (self.abhlist[idx].grip_word == 1):
                                grip = 0x3
                            elif (self.abhlist[idx].grip_word == 3):
                                grip = 0x4
                            if (self.prev_cmd_was_grip[ser_idx] == 0):
                                msg = send_grip_cmd(0x50, grip, 0xFF) 
                                self.slist[ser_idx].wrie(msg)
                                time.sleep(0.01)
                                msg=send_grip_cmd(0x50, 0x00, 0xFF)
                                self.slist[ser_idx].write(msg)
                                time.sleep(0.01)
                                self.prev_cmd_was_grip[ser_idx] = 1
                            msg = send_grip_cmd(0x50, grip, 0xFF)

                        else:
                            self.prev_cmd_was_grip[idx] = 0
                            # Write the finger array out over UART to the hand!
                            msg = farr_to_barr(0x50, self.abhlist[idx].fpos)

                        self.slist[ser_idx].write(msg)

                        # draw landmarks of the hand we found
                        hand_landmarks = results.multi_hand_landmarks[idx]
                        self.mp_drawing.draw_landmarks(
                            image,
                            hand_landmarks,
                            self.mp_hands.HAND_CONNECTIONS,
                            self.mp_drawing_styles.get_default_hand_landmarks_style(),
                            self.mp_drawing_styles.get_default_hand_connections_style()
                        )

                        # Render a static point in the base frame of the model. Visualization of the position-orientation accuracy.
                        # Point should be just in front of the palm. Compensated for handedness
                        static_point_b = np.array([4.16, 1.05, -1.47*self.abhlist[idx].handed_sign, 1])*self.abhlist[idx].scale
                        static_point_b[3] = 1 # remove scaling that wasapplied to the immutable '1'
                        neutral_thumb_w = self.abhlist[idx].hw_b.dot(static_point_b) # get dot position in world coordinates for a visual tag/reference
                        l_list = landmark_pb2.NormalizedLandmarkList(
                            landmark=[
                                v4_to_landmark(neutral_thumb_w)
                            ]
                        )
                        self.mp_drawing.draw_landmarks(
                            image,
                            l_list,
                            [],
                            self.mp_drawing_styles.get_default_hand_landmarks_style(),
                            self.mp_drawing_styles.get_default_hand_landmarks_style()
                        )

                t_seconds = ts/cv2.getTickFrequency()
                if (t_seconds > self.send_unsampling_msg_ts):
                    self.send_unsampling_msg_ts = t_seconds + 10
                    for i in range(self.n):
                        msg = create_misc_msg(0x50, 0xC2)
                        print("sending: ", [ hex(b) for b in msg ], "to ser device ", i)
                        self.slist[i].write(msg)

                fpsfilt, warr_fps = py_sos_iir(fps, warr_fps, self.lpf_fps_sos[0])
                print(fpsfilt)
                image = cv2.flip(image, 1)
                imgresized = cv2.resize(image, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
                if (self.transition_count < self.fade_rate):
                    fadein = self.transition_count/float(self.fade_rate)
                    imgresized = cv2.addWeighted(self.black_img, 1-fadein, imgresized, fadein, 0)
                    self.transition_count += 1


        else:
            if (self.wave_hand):
                self.handwave(self.fpos)

            image = self.screen_saver

            if (self.transition_count < float(self.fade_rate) and cap.isOpened()):
                _, webcam_img = self.cap.read()
                webcam_img = cv2.flip(webcam_img, 1)
                webcam_img = cv2.resize(webcam_img, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
                fadein = self.transition_count/float(self.fade_rate)
                imgresized = cv2.addWeighted(self.black_img, 1-fadein, self.screen_saver, fadein, 0)
                self.transition_count += 1

            else:
                imgresized = image

        tk_img = ImageTk.PhotoImage(image=Image.fromarray(imgresized))
        self.label.photo_image = tk_img
        self.label.config(image=tk_img)

window = tk.Tk()
window.attributes('-fullscreen', True)
window.config(cursor="none")
image_label = tk.Label(window)
image_label.pack()

show_webcam = False
wave_hand = True

dim = pyautogui.size()

# webcam input
fourcc = cv2.VideoWriter_fourcc('M','J','P','G')
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FOURCC, fourcc)
cap.set(cv2.CAP_PROP_FPS, 90)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(1920*720/1080))
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(1080*720/1080))


if not cap.isOpened():
    raise RuntimeError("cap.isOpened() returned false")

# event handlers:
def close_win(e):
    window.destroy()

def switch_img(e):
    global show_webcam # Declare the global flag first before changing it
    show_webcam = not show_webcam
    print("here's flag: ", show_webcam)

def switch_handwave(e):
    global wave_hand
    wave_hand = not wave_hand
    print("here's wave_hand: ", wave_hand)

window.bind('q', close_win)
window.bind('a', switch_img)
window.bind('x', switch_handwave)

screen_saver = Image.open("default_img.jpg")
screen_saver = screen_saver.resize((dim[0], dim[1]))
screen_saver_img_obj = ImageTk.PhotoImage(screen_saver)


def main_task():
    global cap
    global screen_saver_img_obj
    if show_webcam:
        success, frame = cap.read()
        opencv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        captured_image = Image.fromarray(opencv_image).resize((dim[0], dim[1]))
        photo_img = ImageTk.PhotoImage(image=captured_image)
        image_label.photo_image = photo_img
        image_label.config(image=photo_img)

    else:
        image_label.config(image=screen_saver_img_obj)
        if wave_hand:
            print("insert handwave here")
        else:
            print("hands would be still in this situation")
    window.after(10, main_task)


# tk.Button(window, text="Quit", command=window.destroy).pack()

# canv = tk.Canvas(window, bg="white", highlightthickness=0)
# canv.pack(fill=tk.BOTH, expand=True)
# canv.create_image(0, 0, anchor=tk.NW, image=photo_img_obj)

window.after(10, main_task)
window.mainloop()