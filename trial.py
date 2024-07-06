import tkinter as tk
from tkinter import messagebox

# Dummy function for signup and signin (replace with actual functionality)
def signup():
    username = username_entry.get()
    password = password_entry.get()
    # Implement your signup logic here
    messagebox.showinfo("Signup", f"Signup successful for {username}")

def signin():
    username = username_entry.get()
    password = password_entry.get()
    # Implement your signin logic here
    messagebox.showinfo("Signin", f"Welcome back, {username}")

# Main window
root = tk.Tk()
root.title("User Authentication App")

# Labels
tk.Label(root, text="Username:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.E)
tk.Label(root, text="Password:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.E)

# Entries
username_entry = tk.Entry(root, width=30)
username_entry.grid(row=0, column=1, padx=10, pady=5)
password_entry = tk.Entry(root, show="*", width=30)
password_entry.grid(row=1, column=1, padx=10, pady=5)

# Buttons
signup_button = tk.Button(root, text="Signup", command=signup)
signup_button.grid(row=2, column=0, columnspan=2, pady=10)
signin_button = tk.Button(root, text="Signin", command=signin)
signin_button.grid(row=3, column=0, columnspan=2, pady=10)

root.mainloop()
