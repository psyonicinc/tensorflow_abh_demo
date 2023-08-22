import tkinter as tk
from PIL import ImageTk, Image
import cv2 
import pyautogui

window = tk.Tk()
window.attributes('-fullscreen', True)

show_webcam = False
wave_hand=True

dim = pyautogui.size()

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

def main_task():
    if show_webcam:
        print("webcam showed!")
    else:
        if wave_hand:
            print("insert handwave here")
        else:
            print("hands would be still in this situation")
    window.after(20, main_task)        

image = Image.open("default_img.jpg")
image = image.resize((dim[0], dim[1]))
photo_img_obj = ImageTk.PhotoImage(image)

print("here's image width: ", image.width)
print("here's image height: ", image.height)

#tk.Button(window, text="Quit", command=window.destroy).pack()

canv = tk.Canvas(window, bg="white", highlightthickness=0)
canv.pack(fill=tk.BOTH, expand=True)
canv.create_image(0, 0, anchor=tk.NW, image=photo_img_obj)

window.after(0, main_task)
window.mainloop()