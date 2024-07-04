import sqlite3

# Connect to the database
conn = sqlite3.connect('trialdb.db')
cursor = conn.cursor()

# Example: Select all rows from the users table where username is 'john_doe'
cursor.execute('SELECT username,password,droneid,pilotid,address,timestamp FROM fingerprints')
# cursor.execute('DROP TABLE fingerprints')
rows = cursor.fetchall()

# Print the retrieved data
for row in rows:
    print(row)

# Close the connection
conn.close()