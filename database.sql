-- USERS
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin','principal','student','warden','guardian')),
    college TEXT,
    approved INTEGER DEFAULT 0,
    id_card TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HOSTELS
CREATE TABLE hostels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    college TEXT,
    warden_id INTEGER,
    total_rooms INTEGER,
    available_rooms INTEGER,
    FOREIGN KEY (warden_id) REFERENCES users(id)
);

-- ROOMS
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostel_id INTEGER,
    room_number TEXT,
    is_allocated INTEGER DEFAULT 0,
    student_id INTEGER,
    FOREIGN KEY (hostel_id) REFERENCES hostels(id),
    FOREIGN KEY (student_id) REFERENCES users(id)
);

-- APPLICATIONS
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    hostel_id INTEGER,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (hostel_id) REFERENCES hostels(id)
);

-- ATTENDANCE
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    warden_id INTEGER,
    date TEXT,
    status TEXT,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (warden_id) REFERENCES users(id)
);

-- ROOM PHOTOS
CREATE TABLE room_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostel_id INTEGER,
    warden_id INTEGER,
    filename TEXT,
    FOREIGN KEY (hostel_id) REFERENCES hostels(id),
    FOREIGN KEY (warden_id) REFERENCES users(id)
);