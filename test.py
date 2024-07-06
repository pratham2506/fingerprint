import os
import json
import numpy as np
from matplotlib import pyplot as plt
import serial
import serial.tools.list_ports  # Add this line
import requests
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from PIL import Image
import base64
from io import BytesIO
import adafruit_fingerprint
import cv2
import shutil

uart = serial.Serial("COM4", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

def get_fingerprint_photo(username, com_port, save_path=""):
    uart = serial.Serial(com_port, baudrate=57600, timeout=1)
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

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
    
    if not save_path:
        save_path = f"{username}_fingerprint.png"
    
    plt.imsave(save_path, imgArray, cmap='gray')
    print(f"Fingerprint image saved as {save_path}")
    
    return save_path


def send_fingerprint_to_api(username, password, droneid, pilotid, address, fingerprint_image_path):
    api_url = 'http://localhost:3000/api/fingerprint/insert'
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

def save_base64_image(base64_string, username, download_dir="downloaded_images"):
    try:
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        image_data = base64.b64decode(base64_string)
        
        image = Image.open(BytesIO(image_data))
        
        image_filename = os.path.join(download_dir, f"{username}_downloaded_image.png")
        image.save(image_filename)
        print(f"Fingerprint image saved as {image_filename}")
        
    except Exception as e:
        print(f"Error saving fingerprint image: {str(e)}")

def user_signin(username_entry, password_entry):
    username = username_entry.get()
    password = password_entry.get()
    
    print(f"Signing in with Username: {username}, Password: {password}")
    
    api_url = 'http://localhost:3000/api/signin'
    data = {
        'username': username,
        'password': password
    }
    try:
        response = requests.post(api_url, json=data)
        response_data = response.json()
        if response.status_code == 200:
            messagebox.showinfo("Success", "Signin successful!")
            
            if 'fingerprint_image' in response_data:
                save_base64_image(response_data['fingerprint_image'], username)
            
            remaining_data = {
                'username': username,
                'droneid': response_data.get('droneid', ''),
                'pilotid': response_data.get('pilotid', ''),
                'address': response_data.get('address', ''),
                'timestamp': response_data.get('timestamp', '')
            }
            with open('remaining_data.json', 'w') as f:
                json.dump(remaining_data, f, indent=4)
        else:
            messagebox.showerror("Error", f"Signin failed: {response_data['error']}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect to API: {str(e)}")

def save_fingerprint_image(username_entry, password_entry, droneid_entry, pilotid_entry, address_entry, com_port):
    try:
        username = username_entry.get()
        password = password_entry.get()
        droneid = int(droneid_entry.get())
        pilotid = int(pilotid_entry.get())
        address = address_entry.get()
        
        fingerprint_image_path = get_fingerprint_photo(username, com_port)
        
        send_fingerprint_to_api(username, password, droneid, pilotid, address, fingerprint_image_path)
        if os.path.exists(f"{username}_fingerprint.png"):
            os.remove(f"{username}_fingerprint.png")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save fingerprint image: {str(e)}")

def load_image(path):
    image = cv2.imread(path)
    if image is None:
        raise FileNotFoundError(f"Image at path {path} not found.")
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray_image

def detect_and_compute(image):
    orb = cv2.ORB_create(nfeatures=1500)
    keypoints, descriptors = orb.detectAndCompute(image, None)
    return keypoints, descriptors

def match_descriptors(descriptors1, descriptors2):
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(descriptors1, descriptors2, k=2)
    
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)
    return good_matches

def verify_fingerprints(image1_path, image2_path, min_match_count=10):
    image1 = load_image(image1_path)
    image2 = load_image(image2_path)
    
    keypoints1, descriptors1 = detect_and_compute(image1)
    keypoints2, descriptors2 = detect_and_compute(image2)
    
    if descriptors1 is None or descriptors2 is None:
        return False, 0
    
    matches = match_descriptors(descriptors1, descriptors2)
    out = cv2.drawMatches(image1, keypoints1, image2, keypoints2, matches, None)
    plt.imshow(out)
    plt.show()
    if len(matches) > min_match_count:
        src_pts = np.float32([keypoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        matches_mask = mask.ravel().tolist()
        
        if M is not None and sum(matches_mask) > min_match_count:
            out = cv2.drawMatches(image1, keypoints1, image2, keypoints2, matches, None, 
                                  matchesMask=matches_mask, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
            plt.imshow(out)
            plt.show()
            return True, sum(matches_mask)
    return False, 0

def user_fingerprint_authentication():
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
    
    save_path = "match_fingerprint.png"
    
    plt.imsave(save_path, imgArray, cmap='gray')
    print(f"Fingerprint image saved as {save_path}")
    
    matched = False
    match_count = 0
    downloaded_images_dir = "./downloaded_images"
    
    for image_file in os.listdir(downloaded_images_dir):
        if image_file.endswith("_downloaded_image.png"):
            image2_path = os.path.join(downloaded_images_dir, image_file)
            match_result, count = verify_fingerprints(save_path, image2_path)
            if match_result:
                matched = True
                match_count = count
                break
    
    if matched:
        messagebox.showinfo("Success", f"Fingerprint verified successfully! Match count: {match_count}")
    else:
        messagebox.showerror("Error", f"Fingerprint verification failed. Match count: {match_count}")


def logout_process():
    endpoint = "http://localhost:3000/api/logout"
    response = requests.post(endpoint)
    if response.status_code == 200:
        user_data = response.json()
        print(user_data)
        if os.path.exists("match_fingerprint.png"):
            os.remove("match_fingerprint.png")
        os.remove("remaining_data.json")
        shutil.rmtree("downloaded_images")
    else:
        print("Logout failed")

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Main Window")
        self.geometry("1000x600+0+0")
        self.configure(bg="#f0f0f0")

        self.frames = {}
        for F in (HomeScreen, SignupScreen, SigninScreen, FingerprintMatchScreen, LogoutScreen):
            page_name = F.__name__
            frame = F(parent=self, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("HomeScreen")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

class HomeScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        tk.Label(self, text="Welcome", font=("Helvetica", 20), bg="#f0f0f0").pack(pady=20)

        # Dropdown to select COM port dynamically
        tk.Label(self, text="Select COM Port:", bg="#f0f0f0", font=('Helvetica', 12)).pack(pady=10)
        self.com_port_var = tk.StringVar(self)
        self.com_ports_dropdown = ttk.Combobox(self, textvariable=self.com_port_var, state="readonly")
        self.com_ports_dropdown.pack(pady=10)
        self.update_com_ports_dropdown()

        ttk.Button(self, text="Signup", command=lambda: controller.show_frame("SignupScreen")).pack(pady=10)
        ttk.Button(self, text="Signin", command=lambda: controller.show_frame("SigninScreen")).pack(pady=10)
        ttk.Button(self, text="Fingerprint Match", command=lambda: controller.show_frame("FingerprintMatchScreen")).pack(pady=10)
        ttk.Button(self, text="Logout", command=lambda: controller.show_frame("LogoutScreen")).pack(pady=10)

    def update_com_ports_dropdown(self):
        ports = serial.tools.list_ports.comports()
        com_ports = [port.device for port in ports]
        self.com_ports_dropdown["values"] = com_ports
        if com_ports:
            self.com_ports_dropdown.current(0)  # Select the first port by default

class SignupScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        tk.Label(self, text="Signup", font=("Helvetica", 16), bg="#f0f0f0").pack(pady=10)

        frame = tk.Frame(self, bg="#f0f0f0")
        frame.pack(pady=10)

        tk.Label(frame, text="Username:", bg="#f0f0f0", font=('Helvetica', 12)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        username_entry = tk.Entry(frame, font=('Helvetica', 12), width=30)
        username_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(frame, text="Password:", bg="#f0f0f0", font=('Helvetica', 12)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        password_entry = tk.Entry(frame, show="*", font=('Helvetica', 12), width=30)
        password_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(frame, text="Drone ID:", bg="#f0f0f0", font=('Helvetica', 12)).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        droneid_entry = tk.Entry(frame, font=('Helvetica', 12), width=30)
        droneid_entry.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(frame, text="Pilot ID:", bg="#f0f0f0", font=('Helvetica', 12)).grid(row=3, column=0, padx=10, pady=5, sticky="w")
        pilotid_entry = tk.Entry(frame, font=('Helvetica', 12), width=30)
        pilotid_entry.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(frame, text="Address:", bg="#f0f0f0", font=('Helvetica', 12)).grid(row=4, column=0, padx=10, pady=5, sticky="w")
        address_entry = tk.Entry(frame, font=('Helvetica', 12), width=30)
        address_entry.grid(row=4, column=1, padx=10, pady=5)

        tk.Button(self, text="Save Fingerprint", font=('Helvetica', 12), command=lambda: save_fingerprint_image(
            username_entry, password_entry, droneid_entry, pilotid_entry, address_entry, self.com_port_var.get())).pack(pady=10)
        
        tk.Button(self, text="Close", font=('Helvetica', 12), command=lambda: controller.show_frame("HomeScreen")).pack(pady=10)

class SigninScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        tk.Label(self, text="Signin", font=("Helvetica", 16), bg="#f0f0f0").pack(pady=10)

        frame = tk.Frame(self, bg="#f0f0f0")
        frame.pack(pady=10)

        tk.Label(frame, text="Username:", bg="#f0f0f0", font=('Helvetica', 12)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        username_entry = tk.Entry(frame, font=('Helvetica', 12), width=30)
        username_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(frame, text="Password:", bg="#f0f0f0", font=('Helvetica', 12)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        password_entry = tk.Entry(frame, show="*", font=('Helvetica', 12), width=30)
        password_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Button(self, text="Signin", font=('Helvetica', 12), command=lambda: user_signin(username_entry, password_entry)).pack(pady=10)
        
        tk.Button(self, text="Close", font=('Helvetica', 12), command=lambda: controller.show_frame("HomeScreen")).pack(pady=10)

class FingerprintMatchScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        tk.Label(self, text="Fingerprint Match", font=("Helvetica", 16), bg="#f0f0f0").pack(pady=10)

        tk.Button(self, text="Start Matching", font=('Helvetica', 12), command=user_fingerprint_authentication).pack(pady=10)
        
        tk.Button(self, text="Close", font=('Helvetica', 12), command=lambda: controller.show_frame("HomeScreen")).pack(pady=10)

class LogoutScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(bg="#f0f0f0")

        tk.Label(self, text="Logout", font=("Helvetica", 16), bg="#f0f0f0").pack(pady=10)

        tk.Button(self, text="Logout", font=('Helvetica', 12), command=logout_process).pack(pady=10)
        
        tk.Button(self, text="Close", font=('Helvetica', 12), command=lambda: controller.show_frame("HomeScreen")).pack(pady=10)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
