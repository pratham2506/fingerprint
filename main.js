const express = require('express');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const jwt = require('jsonwebtoken');
const session = require('express-session');
const multer = require('multer');
const fs = require('fs');
const path = require('path');

const app = express();
const port = 3000;

// Middleware to parse JSON requests
app.use(bodyParser.json({ limit: '5mb' }));

// Use sessions for storing user data temporarily
app.use(session({
    secret: 'your_session_secret_key',
    resave: false,
    saveUninitialized: true,
    cookie: { secure: false, maxAge: 15 * 24 * 60 * 60 * 1000 } // 15 days
}));

// Configure Multer for image uploads
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadDir = './uploads';
        if (!fs.existsSync(uploadDir)){
            fs.mkdirSync(uploadDir);
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        cb(null, Date.now() + path.extname(file.originalname));
    }
});
const upload = multer({ storage: storage });

// SQLite database setup
const db = new sqlite3.Database('trialdb.db');

// Secret key for JWT
const JWT_SECRET = 'your_jwt_secret_key';

// Ensure tables exist or create them
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS fingerprints (
        username TEXT,
        password TEXT,
        droneid INTEGER,
        pilotid INTEGER PRIMARY KEY,
        address TEXT,
        fingerprint_image_path TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
});

// Example endpoint
app.get('/', (req, res) => {
    res.json({ message: 'Hello from JS API!' });
});

// User Signup endpoint
app.post('/api/signup', upload.single('fingerprint_image'), (req, res) => {
    const { username, password, droneid, pilotid, address } = req.body;
    const fingerprint_image_path = req.file ? req.file.path : null;

    db.run('INSERT INTO fingerprints (username, password, droneid, pilotid, address, fingerprint_image_path) VALUES (?, ?, ?, ?, ?, ?)',
        [username, password, droneid, pilotid, address, fingerprint_image_path],
        function (err) {
            if (err) {
                console.error('Error inserting fingerprint data:', err);
                if (err.message.includes('UNIQUE constraint failed')) {
                    res.status(400).json({ error: 'Duplicate entry. Username, Drone ID, or Pilot ID already exists.' });
                } else {
                    res.status(500).json({ error: 'Database error' });
                }
            } else {
                res.status(201).json({ message: 'Fingerprint inserted', id: this.lastID });
            }
        });
});

// User Signin endpoint
app.post('/api/signin', (req, res) => {
    const { username, password } = req.body;

    db.get('SELECT * FROM fingerprints WHERE username = ? AND password = ?', [username, password], (err, user) => {
        if (err) {
            console.error('Database error while retrieving user:', err);
            return res.status(500).json({ error: 'Database error' });
        }
        if (!user) {
            console.log('User not found:', username);
            return res.status(404).json({ error: 'User not found' });
        }

        // Generate JWT token valid for 15 days
        const token = jwt.sign({ fingerprint_image_path: user.fingerprint_image_path }, JWT_SECRET, { expiresIn: '15d' });

        // Store user data in session
        req.session.user = user;

        // Read the fingerprint image file
        fs.readFile(user.fingerprint_image_path, (err, data) => {
            if (err) {
                console.error('Error reading fingerprint image:', err);
                return res.status(500).json({ error: 'Error reading fingerprint image' });
            }

            const fingerprint_image_base64 = data.toString('base64');

            res.status(200).json({
                token: token,
                fingerprint_image: fingerprint_image_base64
            });
        });
    });
});

// User Logout endpoint
app.post('/api/logout', (req, res) => {
    // Clear the session
    req.session.destroy(err => {
        if (err) {
            return res.status(500).json({ error: 'Logout failed' });
        }
        res.status(200).json({ message: 'Logout successful' });
    });
});

// Endpoint to retrieve fingerprint data by ID
app.get('/api/fingerprint/retrieve/:pilotid', (req, res) => {
    const { pilotid } = req.params;
    db.get('SELECT * FROM fingerprints WHERE pilotid = ?', [pilotid], (err, row) => {
        if (err) {
            res.status(500).json({ error: 'Database error' });
        } else if (row) {
            res.status(200).json(row);
        } else {
            res.status(404).json({ error: 'Fingerprint not found' });
        }
    });
});

// Endpoint to insert new fingerprint data
app.post('/api/fingerprint/insert', upload.single('fingerprint_image'), (req, res) => {
    const { username, password, droneid, pilotid, address } = req.body;
    const fingerprint_image_path = req.file ? req.file.path : null;

    db.run('INSERT INTO fingerprints (username, password, droneid, pilotid, address, fingerprint_image_path) VALUES (?, ?, ?, ?, ?, ?)',
        [username, password, droneid, pilotid, address, fingerprint_image_path],
        function (err) {
            if (err) {
                console.error('Error inserting fingerprint data:', err);
                if (err.message.includes('UNIQUE constraint failed')) {
                    res.status(400).json({ error: 'Duplicate entry. Username, Drone ID, or Pilot ID already exists.' });
                } else {
                    res.status(500).json({ error: 'Database error' });
                }
            } else {
                res.status(201).json({ message: 'Fingerprint inserted', id: this.lastID });
            }
        });
});

// Endpoint to delete fingerprint data by ID
app.delete('/api/fingerprint/delete/:pilotid', (req, res) => {
    const { pilotid } = req.params;
    db.run('DELETE FROM fingerprints WHERE pilotid = ?', [pilotid], function (err) {
        if (err) {
            res.status(500).json({ error: 'Database error' });
        } else if (this.changes > 0) {
            res.status(200).json({ message: 'Fingerprint deleted' });
        } else {
            res.status(404).json({ error: 'Fingerprint not found' });
        }
    });
});

// Start the server
app.listen(port, () => {
    console.log(`JS API listening at http://localhost:${port}`);
});
