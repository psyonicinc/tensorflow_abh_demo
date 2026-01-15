import time
from math import pi, sin
import math
from ah_wrapper.ah_serial_client import AHSerialClient
import numpy as np
from serial.tools import list_ports
import cv2
import serial
import argparse
# import pyautogui
import threading
from ah_wrapper.ah_serial_client import AHSerialClient
import Hand_thread

# Shared data for each thread
poses = [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
]

locks = [threading.Lock() for _ in poses]
stop_events = [threading.Event() for _ in poses]

threads = []

for i in range(len(poses)):
    t = threading.Thread(target=Hand_thread.position_sender,
                         args=(poses[i], locks[i], stop_events[i]))
    threads.append(t)
    t.start()

ithread = 0

class SerialDisplayer:
    def __init__(self, use_grip_cmds, CP210x_only, no_input=False, reverse=False, camera_capture=0, fade_rate=20):
        self.use_grip_cmds = use_grip_cmds
        self.CP210x_only = CP210x_only
        self.no_input = no_input
        self.reverse = reverse
        self.camera_capture = camera_capture
        self.fade_rate = fade_rate
        self.input_listener = None # meant to be a serial object

        # self.dim = pyautogui.size()
        # self.screen_saver = cv2.imread("default_img.jpg", cv2.IMREAD_COLOR)
        # self.original_shape = self.screen_saver.shape
        # self.screen_saver = cv2.resize(self.screen_saver, (self.dim[0], self.dim[1]), interpolation=cv2.INTER_CUBIC)
        # self.black_img = np.zeros_like(self.screen_saver)

        # # Find all serial ports
        self.slist = []
        com_ports_list = list(list_ports.comports())
        port = []

        for i in range(len(poses)):
            t = threading.Thread(target=Hand_thread.position_sender,
                                args=(poses[i], locks[i], stop_events[i]))
            threads.append(t)
            t.start()

        for p in com_ports_list:
            if(p):
                port.append(p)
                print("Found: ", p)

        if not port:
            print("no port found")

        for p in com_ports_list:
            if p:
                try:
                    # Connect based on CP210x_only flag
                    if (not self.CP210x_only) or (self.CP210x_only and 'FT232R' in p[1]):
                        client = AHSerialClient(write_thread=False, baud_rate=460800)
                        self.slist.append(client)

                        # Add a new thread for position_sender if needed
                        t = threading.Thread(target=Hand_thread.position_sender, args=(poses[ithread], locks[ithread], stop_events[ithread], client))
                        threads.append(t)
                        t.start()
                        print("Connected to:", p)
                        ithread += 1

                    elif not self.no_input and (not self.CP210x_only or (self.CP210x_only and 'CP210' in p[1])):
                        print("Connecting input handler...")
                        self.input_listener = serial.Serial(p[0], '460800', timeout=1)
                        print("Connected input handler:", p)
                except Exception:
                    print("Failed to connect to", p)

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
            
        

        if self.reverse:
            self.slist.reverse()

    def wave_hand(self, fpos):
        """helper function to run handwave"""

        for i in range(len(poses)):
            with locks[i]:

                try:
                    for k in range(len(fpos)):
                        ft = time.time()*0.905 + i*(2*np.pi)/12
                        fpos[k] = (0.5*math.sin(ft)+0.5)*45 + 15
                    fpos[5] = -fpos[5]   
                    poses[i] = fpos.copy() # update the global pose list    

                except:
                    pass 

    def relax_hand(self,fpos):
        """helper function to run handwave"""
        for i in range(len(poses)):
            with locks[i]:
                try:
                    for k in range(len(fpos)):
                        poses[i][k] = 0  

                except:
                    pass 
        
    def close_conn(self):
        """close all connections"""
        # Stop thread
        for event in stop_events:
            event.set()

        for thread in threads:
            thread.join()



# client = AHSerialClient(write_thread=False, baud_rate=460800)
# client2 = AHSerialClient(write_thread=False, baud_rate=460800)
"""
Since write_thread == False we will need to issue send_command after every 
set_position command since the while loop is acting as our write thread.  One
could alternatively generate a message using the api and use that as an argument
for the send_command() method.  Using set_position allows you to update the 
hands targets, which is useful for in the loop control.
"""

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
    fpos = [0,0,0,0,0,0]
    try:
        while True:    
            displayer.wave_hand(fpos)
                

    except KeyboardInterrupt:
        pass
    finally:
        displayer.close_conn()
