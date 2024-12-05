import sys
sys.path.append("../util/*")
sys.path.append("../db/*")
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql


class Caregiver:
    def __init__(self, username, password=None, salt=None, hash=None):
        self.username = username
        self.password = password
        self.salt = salt
        self.hash = hash

    @staticmethod
    def create_caregiver(username, password):
        # Generate a salt and hash for the password
        salt = Util.generate_salt()
        hash = Util.generate_hash(password, salt)

        # Create the Caregiver object
        caregiver = Caregiver(username, salt=salt, hash=hash)

        # Save to the database
        try:
            caregiver.save_to_db()
        except pymssql.Error as e:
            print("Error occurred while creating caregiver.")
            raise e

    # Method to authenticate caregiver login
    @staticmethod
    def login_caregiver(username, password):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor(as_dict=True)

        get_caregiver_details = "SELECT Salt, Hash FROM Caregivers WHERE Username = %s"
        try:
            cursor.execute(get_caregiver_details, username)
            result = cursor.fetchone()

            if not result:
                # Username does not exist
                return False

            stored_salt = result['Salt']
            stored_hash = result['Hash']
            calculated_hash = Util.generate_hash(password, stored_salt)

            # Compare calculated hash with stored hash
            return calculated_hash == stored_hash
        except pymssql.Error as e:
            print("Database error occurred:", e)
            return False
        finally:
            cm.close_connection()

    # Get caregiver object
    def get(self):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor(as_dict=True)

        get_caregiver_details = "SELECT Salt, Hash FROM Caregivers WHERE Username = %s"
        try:
            cursor.execute(get_caregiver_details, self.username)
            for row in cursor:
                curr_salt = row['Salt']
                curr_hash = row['Hash']
                calculated_hash = Util.generate_hash(self.password, curr_salt)
                if not curr_hash == calculated_hash:
                    cm.close_connection()
                    return None
                else:
                    self.salt = curr_salt
                    self.hash = calculated_hash
                    cm.close_connection()
                    return self
        except pymssql.Error as e:
            raise e
        finally:
            cm.close_connection()
        return None

    # Getters
    def get_username(self):
        return self.username

    def get_salt(self):
        return self.salt

    def get_hash(self):
        return self.hash

    # Save caregiver to the database
    def save_to_db(self):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()

        add_caregivers = "INSERT INTO Caregivers VALUES (%s, %s, %s)"
        try:
            cursor.execute(add_caregivers, (self.username, self.salt, self.hash))
            conn.commit()
        except pymssql.Error:
            raise
        finally:
            cm.close_connection()

    # Insert availability with parameter date d
    def upload_availability(self, d):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()

        add_availability = "INSERT INTO Availabilities VALUES (%s , %s)"
        try:
            cursor.execute(add_availability, (d, self.username))
            conn.commit()
        except pymssql.Error:
            raise
        finally:
            cm.close_connection()
