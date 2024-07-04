from tkinter import Tk, Button, StringVar, OptionMenu, Entry, Label, Toplevel, messagebox, Text, Scrollbar, END
from tkinter import ttk
import requests
from serial.tools.list_ports import comports
import serial
import adafruit_fingerprint
import time
import base64
from cryptography.fernet import Fernet
import json
import os

# Load encryption key
with open("secret.key", "rb") as key_file:
    key = key_file.read()
cipher_suite = Fernet(key)

# API base URL
API_BASE_URL = "http://localhost:3000/api"

# Global variable for fingerprint sensor
finger = None

# Initialize UART and fingerprint sensor dynamically
def initialize_uart(com_port):
    global finger
    try:
        uart = serial.Serial(com_port, baudrate=57600, timeout=2)
        time.sleep(1)
        finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
        return True
    except serial.SerialException as e:
        update_status(f"Error initializing UART on {com_port}: {e}")
        return False

# Function to encrypt data
def encrypt_data(data):
    encrypted_data = cipher_suite.encrypt(bytes(data))
    return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')

def decrypt_data(encrypted_data):
    decrypted_data = cipher_suite.decrypt(base64.urlsafe_b64decode(encrypted_data))
    return decrypted_data

# Function to insert fingerprint data into database via API
def insert_fingerprint_data(username, password, droneid, pilotid, address, fingerprint_data, fingerprint_image):
    endpoint = f"{API_BASE_URL}/fingerprint/insert"
    files = {'fingerprint_image': open(fingerprint_image, 'rb')}
    data = {
        'username': username,
        'password': password,
        'droneid': droneid,
        'pilotid': pilotid,
        'address': address,
        'fingerprint_data': fingerprint_data,
    }
    response = requests.post(endpoint, files=files, data=data)
    if response.status_code == 201:
        update_status("Fingerprint data and image stored using API.")
    else:
        update_status(f"Error storing fingerprint data and image: {response.text}")
# Function to enroll fingerprint and store in database
def enroll_finger(username, password, droneid, pilotid, address):
    global finger
    if not finger:
        update_status("Fingerprint sensor not initialized.")
        return False
    
    for fingerimg in range(1, 3):
        if fingerimg == 1:
            update_status("Place finger on sensor...")
        else:
            update_status("Place same finger again...")

        while True:
            i = finger.get_image()
            if i == adafruit_fingerprint.OK:
                update_status("Image taken")
                break
            if i == adafruit_fingerprint.NOFINGER:
                update_status(".")
            elif i == adafruit_fingerprint.IMAGEFAIL:
                update_status("Imaging error")
                return False
            else:
                update_status("Other error")
                return False

        update_status("Templating...")
        i = finger.image_2_tz(fingerimg)
        if i == adafruit_fingerprint.OK:
            update_status("Templated")
        else:
            if i == adafruit_fingerprint.IMAGEMESS:
                update_status("Image too messy")
            elif i == adafruit_fingerprint.FEATUREFAIL:
                update_status("Could not identify features")
            elif i == adafruit_fingerprint.INVALIDIMAGE:
                update_status("Image invalid")
            else:
                update_status("Other error")
            return False

        if fingerimg == 1:
            update_status("Remove finger")
            time.sleep(1)
            while i != adafruit_fingerprint.NOFINGER:
                i = finger.get_image()

    update_status("Creating model...")
    i = finger.create_model()
    if i == adafruit_fingerprint.OK:
        update_status("Created")
        # Store fingerprint image locally
        fingerprint_image_path = f"finger_{username}_{pilotid}.bmp"
        finger.download_image(0x01, fingerprint_image_path)
        
        # Encrypt fingerprint image data
        with open(fingerprint_image_path, 'rb') as img_file:
            image_data = img_file.read()
            encrypted_image_data = encrypt_data(image_data)

        # Store fingerprint data and encrypted image in database via API
        insert_fingerprint_data(username, password, droneid, pilotid, address, encrypted_image_data, fingerprint_image_path)
        os.remove(fingerprint_image_path)  # Remove local image after upload

    else:
        if i == adafruit_fingerprint.ENROLLMISMATCH:
            update_status("Prints did not match")
        else:
            update_status("Other error")
        return False

    return True

# Function to fetch available COM ports
def fetch_com_ports():
    ports = [port.device for port in comports()]
    return ports

# Function to handle COM port selection change
def com_port_changed(*args):
    selected_port = selected_com_port.get()
    if initialize_uart(selected_port):
        update_status(f"Initialized UART on {selected_port}")
    else:
        update_status(f"Failed to initialize UART on {selected_port}")

# Function to handle Signup process
def signup_process():
    clear_frame()
    
    Label(main_frame, text="Username:").grid(row=0, column=0, padx=10, pady=5)
    username_entry = Entry(main_frame)
    username_entry.grid(row=0, column=1, padx=10, pady=5)

    Label(main_frame, text="Password:").grid(row=1, column=0, padx=10, pady=5)
    password_entry = Entry(main_frame, show='*')
    password_entry.grid(row=1, column=1, padx=10, pady=5)

    Label(main_frame, text="Drone ID:").grid(row=2, column=0, padx=10, pady=5)
    droneid_entry = Entry(main_frame)
    droneid_entry.grid(row=2, column=1, padx=10, pady=5)

    Label(main_frame, text="Pilot ID:").grid(row=3, column=0, padx=10, pady=5)
    pilotid_entry = Entry(main_frame)
    pilotid_entry.grid(row=3, column=1, padx=10, pady=5)

    Label(main_frame, text="Address:").grid(row=4, column=0, padx=10, pady=5)
    address_entry = Entry(main_frame)
    address_entry.grid(row=4, column=1, padx=10, pady=5)

    def enroll_fingerprint():
        username = username_entry.get()
        password = password_entry.get()
        droneid = int(droneid_entry.get())
        pilotid = int(pilotid_entry.get())
        address = address_entry.get()

        if enroll_finger(username, password, droneid, pilotid, address):
            messagebox.showinfo("Success", "Fingerprint enrolled and data stored successfully.")
            show_main_buttons()
        else:
            messagebox.showerror("Error", "Fingerprint enrollment failed. Please try again.")

    Button(main_frame, text="Enroll Fingerprint", command=enroll_fingerprint).grid(row=5, column=0, columnspan=2, padx=10, pady=10)

# Function to handle Signin process
def signin_process():
    clear_frame()

    Label(main_frame, text="Username:").grid(row=0, column=0, padx=10, pady=5)
    username_entry = Entry(main_frame)
    username_entry.grid(row=0, column=1, padx=10, pady=5)

    Label(main_frame, text="Password:").grid(row=1, column=0, padx=10, pady=5)
    password_entry = Entry(main_frame, show='*')
    password_entry.grid(row=1, column=1, padx=10, pady=5)

    def signin():
        username = username_entry.get()
        password = password_entry.get()

        # Authenticate user via API
        endpoint = f"{API_BASE_URL}/signin"
        data = {'username': username, 'password': password}
        response = requests.post(endpoint, json=data)

        if response.status_code == 200:
            try:
                user_data = response.json()
                token = user_data.get('token')
                with open("token.txt", "w") as token_file:
                    token_file.write(token)
                update_status("Authentication successful. Token stored in local storage.")
                store_user_data_locally(user_data)
                show_user_dashboard()
            except ValueError:
                messagebox.showerror("Error", "Invalid JSON format received from server.")
        else:
            messagebox.showerror("Error", "Invalid username or password. Please try again.")

    Button(main_frame, text="Signin", command=signin).grid(row=2, column=0, columnspan=2, padx=10, pady=10)

# Function to open the user dashboard after successful login
def show_user_dashboard():
    clear_frame()
    
    verify_button = Button(main_frame, text="Verify Fingerprint", command=verify_fingerprint_process)
    verify_button.pack(pady=10)
    
    logout_button = Button(main_frame, text="Logout", command=logout_process)
    logout_button.pack(pady=10)

def read_from_json():
    global finger  # Assuming `finger` is initialized somewhere else
    
    if not finger:
        update_status("Fingerprint sensor not initialized.")
        return False
    
    try:
        with open('user_data.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            fetch_fingerprint = jsondata['user']['fingerprint_data']['data']
            fingerprint_bytes = fetch_fingerprint
        
        if finger.send_fpdata(fingerprint_bytes,"char",10):
            print("Stored on sensor")
        else:
            print("Not stored on sensor")
            
    except FileNotFoundError:
        print("JSON file not found.")
    except KeyError:
        print("JSON file format incorrect.")
    except Exception as e:
        print(f"Error: {e}")


# Function to handle Fingerprint Verification process
def verify_fingerprint_process():
    global finger
    if not finger:
        update_status("Fingerprint sensor not initialized.")
        return False
    for fingerimg in range(1, 3):
        if fingerimg == 1:
            update_status("Place finger on sensor...")
        else:
            update_status("Place same finger again...")

        while True:
            i = finger.get_image()
            if i == adafruit_fingerprint.OK:
                update_status("Image taken")
                break
            if i == adafruit_fingerprint.NOFINGER:
                update_status(".")
            elif i == adafruit_fingerprint.IMAGEFAIL:
                update_status("Imaging error")
                return False
            else:
                update_status("Other error")
                return False

        update_status("Templating...")
        i = finger.image_2_tz(fingerimg)
        if i == adafruit_fingerprint.OK:
            update_status("Templated")
        else:
            if i == adafruit_fingerprint.IMAGEMESS:
                update_status("Image too messy")
            elif i == adafruit_fingerprint.FEATUREFAIL:
                update_status("Could not identify features")
            elif i == adafruit_fingerprint.INVALIDIMAGE:
                update_status("Image invalid")
            else:
                update_status("Other error")
            return False

        if fingerimg == 1:
            update_status("Remove finger")
            time.sleep(1)
            while i != adafruit_fingerprint.NOFINGER:
                i = finger.get_image()

    update_status("Creating model...")
    i = finger.create_model()
    if i == adafruit_fingerprint.OK:
        update_status("Created")
        # Store fingerprint data in database
        fingerprint_data = finger.get_fpdata("image")
    
    #     filename = "fingerprint_data.json"
    #     with open(filename, "w") as json_file:
    #         json.dump(fingerprint_data, json_file, indent=4)
    #         update_status(f"Fingerprint data saved to {filename}")
        
    #     return True
    # else:
    #     update_status("Model creation failed")
    #     return False

    # update_status("Place finger on sensor...")
    # while finger.get_image() != adafruit_fingerprint.OK:
    #     pass
    # update_status("Image taken")
    
    # update_status("Templating...")
    # templated_fingerprint = finger.image_2_tz(1)
    # if templated_fingerprint != adafruit_fingerprint.OK:
    #     update_status("Templating failed")
    #     return False

    update_status("Searching...")
    if finger.match_fingerprint_from_json('user_data.json') == fingerprint_data:
        update_status("Fingerprint matched!")
        messagebox.showinfo("Success", "Fingerprint matched successfully.")
    else:
        update_status("Fingerprint did not match")
        messagebox.showerror("Error", "Fingerprint did not match.")

# Function to store user data locally
def store_user_data_locally(user_data):
    with open("user_data.json", "w") as file:
        json.dump(user_data, file)
    update_status("User data stored locally.")

# Function to handle Logout process
def logout_process():
    if os.path.exists("token.txt"):
        os.remove("token.txt")
    if os.path.exists("user_data.json"):
        os.remove("user_data.json")
    update_status("Logged out successfully.")
    messagebox.showinfo("Logout", "Logged out successfully.")
    clear_frame()
    show_main_buttons()

# Function to update status messages
def update_status(message):
    status_text.config(state="normal")
    status_text.insert(END, message + "\n")
    status_text.config(state="disabled")
    status_text.yview(END)

# Function to clear main frame
def clear_frame():
    for widget in main_frame.winfo_children():
        widget.destroy()

# Function to show main buttons
def show_main_buttons():
    clear_frame()
    signup_button = Button(main_frame, text="Signup", command=signup_process)
    signup_button.pack(pady=10)

    signin_button = Button(main_frame, text="Signin", command=signin_process)
    signin_button.pack(pady=10)

    check_login_status()  # Check login status when showing main buttons

# Function to check login status
def check_login_status():
    if os.path.exists("token.txt"):
        show_user_dashboard()  # If token exists, user is logged in, show dashboard

# Initialize Tkinter main window
root = Tk()
root.title("Fingerprint Authentication System")

# Main frame
main_frame = ttk.Frame(root, padding="10")
main_frame.pack(fill="both", expand=True)

# Status text box
status_text = Text(root, height=10, state="disabled", wrap="word")
status_text.pack(fill="x")
scrollbar = Scrollbar(root, command=status_text.yview)
scrollbar.pack(side="right", fill="y")
status_text["yscrollcommand"] = scrollbar.set

# Fetch and populate COM ports
selected_com_port = StringVar()
selected_com_port.set("Select COM port")
ports = fetch_com_ports()
if ports:
    selected_com_port.set(ports[0])  # Set the first available port as default
port_menu = OptionMenu(root, selected_com_port, *ports)
port_menu.pack(pady=10)
selected_com_port.trace("w", com_port_changed)

# Show main buttons initially
show_main_buttons()

# Start Tkinter main loop
root.mainloop()