import tkinter as tk
from PIL import ImageTk, Image

window = tk.Tk()
image = Image.open("default_img.jpg")
photo_img_obj = ImageTk.PhotoImage(image)


canv = tk.Canvas(window, bg="white")
canv.grid(row=2, column=3)
canv.create_image(20, 20, anchor=tk.NW, image=photo_img_obj)

window.mainloop()
