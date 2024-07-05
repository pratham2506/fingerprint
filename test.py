import numpy as np
from matplotlib import pyplot as plt
import serial
import requests
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import adafruit_fingerprint

uart = serial.Serial("COM4", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

# Function to get and save fingerprint image locally
def get_fingerprint_photo(username, save_path=""):
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
    
    # Construct filename with username
    if not save_path:
        save_path = f"{username}_fingerprint.png"
    
    plt.imsave(save_path, imgArray, cmap='gray')
    print(f"Fingerprint image saved as {save_path}")
    
    # Return the path where the image is saved
    return save_path

# Function to send fingerprint image and data to API
def send_fingerprint_to_api(username, password, droneid, pilotid, address, fingerprint_image_path):
    api_url = 'http://localhost:3000/api/fingerprint/insert'  # Adjust URL if needed
    files = {'fingerprint_image': open(fingerprint_image_path, 'rb')}
    data = {
        'username': username,
        'password': password,
        'droneid': droneid,
        'pilotid': pilotid,
        'address': address
    }
    try:
        response = requests.post(api_url, files=files, data=data)
        response_data = response.json()
        if response.status_code == 201:
            messagebox.showinfo("Success", "Fingerprint image and data saved successfully!")
        else:
            messagebox.showerror("Error", f"Failed to save fingerprint image and data: {response_data['error']}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect to API: {str(e)}")

# Function to handle user sign-in
def user_signin(username_entry, password_entry):
    username = username_entry.get()
    password = password_entry.get()
    
    print(f"Signing in with Username: {username}, Password: {password}")  # Debugging print
    
    api_url = 'http://localhost:3000/api/signin'  # Adjust URL if needed
    data = {
        'username': username,
        'password': password
    }
    try:
        response = requests.post(api_url, json=data)
        response_data = response.json()
        print(f"API Response: {response_data}")  # Debugging print
        if response.status_code == 200:
            messagebox.showinfo("Success", "Signin successful!")
        else:
            messagebox.showerror("Error", f"Signin failed: {response_data['error']}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect to API: {str(e)}")

# Callback function to save fingerprint image and send to API
def save_fingerprint_image(username_entry, password_entry, droneid_entry, pilotid_entry, address_entry):
    try:
        # Fetch user inputs
        username = username_entry.get()
        password = password_entry.get()
        droneid = int(droneid_entry.get())
        pilotid = int(pilotid_entry.get())
        address = address_entry.get()
        
        fingerprint_image_path = get_fingerprint_photo(username)
        
        send_fingerprint_to_api(username, password, droneid, pilotid, address, fingerprint_image_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save fingerprint image: {str(e)}")

# Create the main UI function
def create_ui():
    root = tk.Tk()
    root.title("Fingerprint Image Capture")
    
    # Entry fields
    tk.Label(root, text="Username:").pack()
    username_entry = tk.Entry(root)
    username_entry.pack()
    
    tk.Label(root, text="Password:").pack()
    password_entry = tk.Entry(root, show="*")
    password_entry.pack()
    
    tk.Label(root, text="Drone ID:").pack()
    droneid_entry = tk.Entry(root)
    droneid_entry.pack()
    
    tk.Label(root, text="Pilot ID:").pack()
    pilotid_entry = tk.Entry(root)
    pilotid_entry.pack()
    
    tk.Label(root, text="Address:").pack()
    address_entry = tk.Entry(root)
    address_entry.pack()
    
    button_save = tk.Button(root, text="Save Fingerprint Image", command=lambda: save_fingerprint_image(username_entry, password_entry, droneid_entry, pilotid_entry, address_entry))
    button_save.pack(pady=20)
    
    button_signin = tk.Button(root, text="Signin", command=lambda: open_signin_window())
    button_signin.pack(pady=10)
    
    root.mainloop()

# Create the signin UI function
def open_signin_window():
    signin_window = tk.Toplevel()
    signin_window.title("User Signin")
    
    tk.Label(signin_window, text="Username:").pack()
    username_entry = tk.Entry(signin_window)
    username_entry.pack()
    
    tk.Label(signin_window, text="Password:").pack()
    password_entry = tk.Entry(signin_window, show="*")
    password_entry.pack()
    
    button_signin = tk.Button(signin_window, text="Signin", command=lambda: user_signin(username_entry, password_entry))
    button_signin.pack(pady=20)
    
if __name__ == "__main__":
    create_ui()
