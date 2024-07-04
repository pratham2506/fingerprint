import time
import numpy as np
from matplotlib import pyplot as plt
import serial
import adafruit_fingerprint
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

uart = serial.Serial("COM4", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

def get_fingerprint_photo(save_path="fingerprint_image.png"):
    """Get and save fingerprint image to a file"""
    print("Waiting for image...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Got image...Transferring image data...")
    imgList = finger.get_fpdata("image", 2)
    imgArray = np.zeros(73728, np.uint8)
    for i, val in enumerate(imgList):
        imgArray[(i * 2)] = val & 240
        imgArray[(i * 2) + 1] = (val & 15) * 16
    imgArray = np.reshape(imgArray, (288, 256))
    plt.imsave(save_path, imgArray, cmap='gray')
    print(f"Fingerprint image saved as {save_path}")

def save_fingerprint_image():
    """Callback function to save fingerprint image when button is clicked"""
    try:
        get_fingerprint_photo(save_path="fingerprint_image.png")
        messagebox.showinfo("Saved", "Fingerprint image saved successfully as fingerprint_image.png")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save fingerprint image: {str(e)}")

def create_ui():
    """Create a simple UI with a button to save fingerprint image"""
    root = tk.Tk()
    root.title("Fingerprint Image Capture")
    
    button_save = tk.Button(root, text="Save Fingerprint Image", command=save_fingerprint_image)
    button_save.pack(pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    create_ui()
