import tkinter as tk
from PIL import ImageTk, Image
import cv2 
import pyautogui

window = tk.Tk()
window.attributes('-fullscreen', True)

image_label = tk.Label(window)
image_label.pack()

show_webcam = False
wave_hand=True

dim = pyautogui.size()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, dim[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, dim[1])

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
        print("webcam showed!")
        _, frame = cap.read()
        opencv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        captured_image = Image.fromarray(opencv_image).resize((dim[0], dim[1]))
        photo_img = ImageTk.PhotoImage(image=captured_image)
        image_label.config(image=photo_img)

    else:
        image_label.config(image=screen_saver_img_obj)
        if wave_hand:
            print("insert handwave here")
        else:
            print("hands would be still in this situation")
    window.after(20, main_task)


# tk.Button(window, text="Quit", command=window.destroy).pack()

# canv = tk.Canvas(window, bg="white", highlightthickness=0)
# canv.pack(fill=tk.BOTH, expand=True)
# canv.create_image(0, 0, anchor=tk.NW, image=photo_img_obj)

window.after(0, main_task)
window.mainloop()