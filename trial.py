import os
import json
import numpy as np
from matplotlib import pyplot as plt
import serial
import requests
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import base64
from io import BytesIO
import adafruit_fingerprint
import cv2

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
            
        # Check if there's an image URL in the response
        # if 'image_url' in response_data:
        #     download_image(response_data['image_url'], username)
            
    except Exception as e:
        messagebox.showerror("Error", f"Failed to connect to API: {str(e)}")

# Function to save Base64 encoded image
def save_base64_image(base64_string, username, download_dir="downloaded_images"):
    try:
        # Create download directory if it doesn't exist
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # Decode Base64 string to bytes
        image_data = base64.b64decode(base64_string)
        
        # Create PIL Image from bytes
        image = Image.open(BytesIO(image_data))
        
        # Save image locally in the download directory
        image_filename = os.path.join(download_dir, f"{username}_downloaded_image.png")
        image.save(image_filename)
        print(f"Fingerprint image saved as {image_filename}")
        
    except Exception as e:
        print(f"Error saving fingerprint image: {str(e)}")

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
        # print(f"API Response: {response_data}")  # Debugging print
        if response.status_code == 200:
            messagebox.showinfo("Success", "Signin successful!")
            
            # Check if there's a fingerprint image in the response
            if 'fingerprint_image' in response_data:
                save_base64_image(response_data['fingerprint_image'], username)
            
            # Save remaining data to JSON file
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
        if os.path.exists(f"{username}_fingerprint.png"):
                os.remove(f"{username}_fingerprint.png")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save fingerprint image: {str(e)}")

def load_image(path):
    """Load an image from the specified file path and convert it to grayscale."""
    image = cv2.imread(path)
    if image is None:
        raise FileNotFoundError(f"Image at path {path} not found.")
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray_image

def detect_and_compute(image):
    """Detect key points and compute descriptors using ORB."""
    orb = cv2.ORB_create(nfeatures=1500)
    keypoints, descriptors = orb.detectAndCompute(image, None)
    return keypoints, descriptors

def match_descriptors(descriptors1, descriptors2):
    """Match descriptors using BFMatcher with a ratio test."""
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(descriptors1, descriptors2, k=2)
    
    # Apply ratio test
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)
    return good_matches

def verify_fingerprints(image1, image2, min_match_count=10):
    """Verify if two fingerprint images match."""
    # Detect key points and compute descriptors
    keypoints1, descriptors1 = detect_and_compute(image1)
    keypoints2, descriptors2 = detect_and_compute(image2)
    
    if descriptors1 is None or descriptors2 is None:
        return False, 0
    
    # Match descriptors
    matches = match_descriptors(descriptors1, descriptors2)
    
    # Ensure there are enough matches
    if len(matches) > min_match_count:
        # Extract location of good matches
        src_pts = np.float32([keypoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # Compute homography using RANSAC
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        matches_mask = mask.ravel().tolist()
        
        # Verify the match using the homography matrix
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
    
    # Construct filename with username
    save_path = "match_fingerprint.png"
    
    plt.imsave(save_path, imgArray, cmap='gray')
    print(f"Fingerprint image saved as {save_path}")
    image1 = "match_fingerprint.png"
    image2 = "./downloaded_images/go_downloaded_image.png"
    matched_images = verify_fingerprints(image1,image2)
    if matched_images:
        print("Fingerprint verified success")
    else:
        print("Fingerprint do not match")


def logout_process():
    endpoint = "http://localhost:3000/api/logout"
    response = requests.post(endpoint)
    if response.status_code == 200:
        user_data = response.json()
        print(user_data)
        os.remove("remaining_data.json")
        os.remove("downloaded_images")
    else:
        print("Logout failed")

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
    
    button_signin = tk.Button(root, text="Signin", command=lambda: user_signin(username_entry, password_entry))
    button_signin.pack(pady=10)

    button_logout = tk.Button(root, text="Logout", command=lambda: logout_process())
    button_logout.pack(pady=10)

    button_verify_print = tk.Button(root, text="Verify print", command=lambda: user_fingerprint_authentication())
    button_verify_print.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    create_ui()
