from scheduler.db.ConnectionManager import ConnectionManager
import hashlib, os
import pymssql

class Patient:
    def __init__(self, username, salt=None, hash_value=None):
        self.username = username
        self.salt = salt
        self.hash = hash_value

    @staticmethod
    def create_patient(username, password):
        # Generate a salt and hash for the password
        salt = os.urandom(16)
        hash_value = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt, 100000, dklen=16
        )

        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()

        try:
            insert_patient = """
                INSERT INTO Patients (Username, Salt, Hash) VALUES (%s, %s, %s)
            """
            cursor.execute(insert_patient, (username, salt, hash_value))
            conn.commit()
            return True  # Just return True/False, don't print
        except pymssql.Error as e:
            if "PRIMARY KEY" in str(e):
                return False
            return False
        finally:
            cm.close_connection()

    @staticmethod
    def login_patient(username, password):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()

        try:
            get_user = """
                SELECT Salt, Hash FROM Patients WHERE Username = %s
            """
            cursor.execute(get_user, username)
            result = cursor.fetchone()

            if not result:
                return False

            salt, stored_hash = result
            input_hash = hashlib.pbkdf2_hmac(
                'sha256', password.encode('utf-8'), salt, 100000, dklen=16
            )

            return input_hash == stored_hash
        except pymssql.Error:
            return False
        finally:
            cm.close_connection()
