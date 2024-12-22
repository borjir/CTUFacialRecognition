import sqlite3
import os

# Initialize the database if it doesn't exist
def init_database():
    if not os.path.exists("user_data.db"):
        conn = sqlite3.connect("user_data.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                ref_num TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                address TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone_num TEXT UNIQUE NOT NULL,
                gender TEXT NOT NULL,
                civil_status TEXT NOT NULL,
                guardian TEXT NOT NULL,
                dob TEXT NOT NULL,
                work_status TEXT NOT NULL,
                image_path TEXT NOT NULL,
                face_encoding BLOB UNIQUE NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
# Retrieve all face encodings from the database
def get_all_face_encodings():
    try:
        conn = sqlite3.connect("user_data.db")
        cursor = conn.cursor()
        query = "SELECT face_encoding FROM users"
        cursor.execute(query)
        encodings = cursor.fetchall()
        conn.close()
        return [row[0] for row in encodings]
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return []

# Check if a field value is unique
def check_unique_field(field, value):
    try:
        conn = sqlite3.connect("user_data.db")
        cursor = conn.cursor()
        query = f"SELECT 1 FROM users WHERE {field} = ?"
        cursor.execute(query, (value,))
        result = cursor.fetchone()
        conn.close()
        return result is None
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return False

# Insert a new user into the database
def insert_user(ref_num, full_name, address, email, phone_num, gender, civil_status, guardian, dob, work_status, image_path, face_encoding):
    try:
        conn = sqlite3.connect("user_data.db")
        cursor = conn.cursor()
        query = '''
            INSERT INTO users (ref_num, full_name, address, email, phone_num, gender, civil_status, guardian, dob, work_status, image_path, face_encoding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        cursor.execute(query, (ref_num, full_name, address, email, phone_num, gender, civil_status, guardian, dob, work_status, image_path, face_encoding))
        conn.commit()
        conn.close()
        print("User successfully registered.")
    except sqlite3.IntegrityError as e:
        print(f"Integrity error: {e}")
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")

# Fetch user data based on the face encoding
def get_user_data_by_encoding(encoding_bytes):
    try:
        conn = sqlite3.connect("user_data.db")
        cursor = conn.cursor()
        query = '''
            SELECT ref_num, full_name, address, email, phone_num, gender, civil_status, guardian, dob, work_status, image_path
            FROM users
            WHERE face_encoding = ?
        '''
        cursor.execute(query, (encoding_bytes,))
        user_data = cursor.fetchone()
        conn.close()
        return user_data
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return None


# Initialize the database at the start
init_database()
