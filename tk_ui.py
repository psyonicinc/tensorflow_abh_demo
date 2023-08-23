import tkinter as tk
from PIL import ImageTk, Image
import cv2 
import pyautogui
import mediapipe as mp
import numpy as np
import argparse
import serial
from serial.tools import list_ports

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
        self.use_grip_cmds: bool = use_grip_cmds
        self.CP210x_only: bool = CP210x_only
        self.no_input: bool = no_input
        self.reverse: bool = reverse
        self.camera_capture = camera_capture
        self.fade_rate = fade_rate
        self.input_listener = None # meant to be a serial object

        self.dim = pyautogui.size()
        self.screen_saver = ImageTk.PhotoImage(Image.open("default_img.jpg").resize(self.dim[0], self.dim[1]))
        self.black_img = np.zeros((dim[0], dim[1]))

        self.label = tk.Label(self)
        self.label.pack()

        self.show_webcam = False
        self.wave_hand = True

        self.bind('q', self.close_window)
        self.bind('a', self.switch_img)
        self.bind('x', self.switch_handwave)

        # Find all serial ports
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

        if self.reverse:
            self.slist.reverse()


    def handwave(self, fpos):
        pass
    
    # event handlers
    def close_window(self, e):
        pass

    def switch_img(self, e):
        pass

    def switch_handwave(self, e):
        pass

    # the function called in our mainloop
    def update(self):
        # here's what mainloop calls
        pass


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

window.after(0, main_task)
window.mainloop()