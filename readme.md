
# Pilot fingerprint authentication system (InDrones)

API code is in main.js. For any modification in API, refer main.js.
It uses http://localhost:3000 port by default.


For main application code, refer main.py. 


secret.key contains the key used for encryption and decryption of data. 


downloaded_images folder and remaining_data.json file are created at user login.


Library used for this project is Adafruit Fingerprint. Fingerprint sensor used in the project is AS608 with a ttl for serial communication over USB.


generatekey.py is used for the generation of secret.key file that contains the key.


If you want to test the fingerprint matching algorithm or need sample fingerprints, use collect_fingerprint.py. 


Use erase_sensor_memory.py to flush the sensor menory in case.


image_match.py contains the logic for fingerprint matching (prototype).




