import tkinter as tk
from PIL import ImageTk, Image


window = tk.Tk()
window.attributes('-fullscreen', True)

def close_win(e):
    window.destroy()
window.bind('q', close_win)

image = Image.open("default_img.jpg")
photo_img_obj = ImageTk.PhotoImage(image)

tk.Button(window, text="Quit", command=window.destroy).pack()

canv = tk.Canvas(window, bg="white", highlightthickness=0)
canv.pack(fill=tk.BOTH, expand=True)
canv.create_image(0, 0, anchor=tk.NW, image=photo_img_obj)

window.mainloop()