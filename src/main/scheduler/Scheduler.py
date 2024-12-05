from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime
import re


session = {
    "logged_in": False,
    "username": None,
    "role": None  # "patient" or "caregiver"
}

def is_strong_password(password):
    # Check for password strength
    if (len(password) >= 8 and
        re.search(r'[A-Z]', password) and
        re.search(r'[a-z]', password) and
        re.search(r'[0-9]', password) and
        re.search(r'[!@#?]', password)):
        return True
    return False

def create_patient(tokens):
    if len(tokens) != 3:
        print("Invalid arguments. Usage: create_patient <username> <password>")
        return

    username, password = tokens[1], tokens[2]

    if not is_strong_password(password):
        print("Password must be at least 8 characters long, contain uppercase and lowercase letters, "
              "include numbers, and at least one special character (!, @, #, ?).")
        return

    try:
        Patient.create_patient(username, password)
        print(f"Created user {username}")
    except Exception as e:
        print(e)
        print("Failed to create user.")


def create_caregiver(tokens):
    if len(tokens) != 3:
        print("Invalid arguments. Usage: create_caregiver <username> <password>")
        return

    username, password = tokens[1], tokens[2]

    if not is_strong_password(password):
        print("Password must be at least 8 characters long, contain uppercase and lowercase letters, "
              "include numbers, and at least one special character (!, @, #, ?).")
        return

    try:
        Caregiver.create_caregiver(username, password)
        print(f"Created user {username}")
    except Exception as e:
        print(e)
        print("Failed to create user.")




def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
    
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def login_patient(tokens):
    if len(tokens) != 3:
        print("Invalid arguments. Usage: login_patient <username> <password>")
        return

    if session["logged_in"]:
        print("User already logged in.")
        return

    username, password = tokens[1], tokens[2]
    if Patient.login_patient(username, password):
        session["logged_in"] = True
        session["username"] = username
        session["role"] = "patient"
        print(f"Logged in as: {username}")
    else:
        print("Login failed.")



def login_caregiver(tokens):
    if len(tokens) != 3:
        print("Invalid arguments. Usage: login_caregiver <username> <password>")
        return

    if session["logged_in"]:
        print("User already logged in.")
        return

    username, password = tokens[1], tokens[2]
    if Caregiver.login_caregiver(username, password):
        session["logged_in"] = True
        session["username"] = username
        session["role"] = "caregiver"
        print(f"Logged in as: {username}")
    else:
        print("Login failed.")



def search_caregiver_schedule(tokens):
    if not session["logged_in"]:
        print("Please login first!")
        return

    if len(tokens) != 2:
        print("Invalid arguments. Usage: search_caregiver_schedule <date>")
        return

    date = tokens[1]
    try:
        datetime.datetime.strptime(date, "%m-%d-%Y")
    except ValueError:
        print("Invalid date format. Use MM-DD-YYYY.")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()

    query = """
        SELECT Availabilities.Username, Vaccines.Name, Vaccines.Doses
        FROM Availabilities
        LEFT JOIN Vaccines ON 1=1
        WHERE Availabilities.Time = %s
        ORDER BY Availabilities.Username;
    """
    try:
        cursor.execute(query, date)
        rows = cursor.fetchall()
        if not rows:
            print("No caregivers available on this date.")
        for row in rows:
            print(f"{row[0]} {row[1]} {row[2]}")
    except pymssql.Error as e:
        print("Please try again!")
        print("Db-Error:", e)
    finally:
        cm.close_connection()



def reserve(tokens):
    if not session["logged_in"] or session["role"] != "patient":
        print("Please login as a patient!")
        return

    if len(tokens) != 3:
        print("Invalid arguments. Usage: reserve <date> <vaccine>")
        return

    date, vaccine_name = tokens[1], tokens[2]
    try:
        parsed_date = datetime.datetime.strptime(date, "%m-%d-%Y").date()
    except ValueError:
        print("Invalid date format. Use MM-DD-YYYY.")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()

    try:

        # 1. Find caregiver
        check_availability = """
            SELECT Username 
            FROM Availabilities
            WHERE Time = %s AND Reserved = 0
            ORDER BY Username;
        """
        cursor.execute(check_availability, (parsed_date,))
        caregiver_row = cursor.fetchone()
        if not caregiver_row:
            print("No Caregiver is available!")
            return
        caregiver_username = caregiver_row[0]
        print(f"Selected Caregiver: {caregiver_username}")

        # 2. Check vaccine availability
        check_vaccine = """
            SELECT Doses 
            FROM Vaccines
            WHERE Name = %s;
        """
        cursor.execute(check_vaccine, (vaccine_name,))
        vaccine_row = cursor.fetchone()
        if not vaccine_row or vaccine_row[0] <= 0:
            print("Not enough available doses!")
            return
        print(f"Available Doses for {vaccine_name}: {vaccine_row[0]}")

        # 3. Create appointment
        appointment_query = """
            INSERT INTO Appointments (
                Patient_Username, 
                Caregiver_Username, 
                Vaccine_Name, 
                Date
            ) VALUES (%s, %s, %s, %s);
        """
        cursor.execute(appointment_query, 
                     (session["username"], caregiver_username, vaccine_name, parsed_date))

        # 4. Update vaccine count
        update_vaccine = """
            UPDATE Vaccines 
            SET Doses = Doses - 1 
            WHERE Name = %s;
        """
        cursor.execute(update_vaccine, (vaccine_name,))

        # 5. Mark availability as reserved
        update_availability = """
            UPDATE Availabilities 
            SET Reserved = 1
            WHERE Time = %s AND Username = %s;
        """
        cursor.execute(update_availability, (parsed_date, caregiver_username))

        # Commit all changes
        conn.commit()

        print(f"Appointment ID: {cursor.lastrowid}, Caregiver username: {caregiver_username}")

    except pymssql.Error as e:
        print(f"Failed to complete reservation: {e}")
        conn.rollback()
    finally:
        cm.close_connection()


def upload_availability(tokens):
    if not session["logged_in"] or session["role"] != "caregiver":
        print("Please login as a caregiver first!")
        return

    if len(tokens) != 2:
        print("Invalid arguments. Usage: upload_availability <date>")
        return

    date = tokens[1]
    try:
        parsed_date = datetime.datetime.strptime(date, "%m-%d-%Y").date()
    except ValueError:
        print("Invalid date format. Use MM-DD-YYYY.")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()

    add_availability_query = "INSERT INTO Availabilities (Time, Username) VALUES (%s, %s)"
    try:
        cursor.execute(add_availability_query, (parsed_date, session["username"]))
        conn.commit()
        print("Availability uploaded!")
    except pymssql.Error as e:
        print("Error occurred while uploading availability. Please try again!")
        print("Db-Error:", e)
    finally:
        cm.close_connection()




def cancel(tokens):
    if len(tokens) != 2:
        print("Invalid arguments. Usage: cancel <appointment_id>")
        return

    if not session["logged_in"]:
        print("Please login first!")
        return

    try:
        appointment_id = int(tokens[1])
    except ValueError:
        print("Appointment ID must be a number.")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    cursor = conn.cursor()

    try:

        # Fetch appointment details
        appointment_query = """
            SELECT Vaccine_Name, Date, Caregiver_Username
            FROM Appointments
            WHERE Appointment_ID = %s;
        """
        cursor.execute(appointment_query, (appointment_id,))
        appointment = cursor.fetchone()

        if not appointment:
            print("No such appointment exists.")
            return

        vaccine_name, appointment_date, caregiver_username = appointment

        # Remove appointment
        delete_appointment_query = """
            DELETE FROM Appointments
            WHERE Appointment_ID = %s;
        """
        cursor.execute(delete_appointment_query, (appointment_id,))

        # Restore caregiver availability
        update_availability_query = """
            UPDATE Availabilities
            SET Reserved = 0
            WHERE Time = %s AND Username = %s;
        """
        cursor.execute(update_availability_query, (appointment_date, caregiver_username))

        # Increment vaccine doses
        update_vaccine_query = """
            UPDATE Vaccines
            SET Doses = Doses + 1
            WHERE Name = %s;
        """
        cursor.execute(update_vaccine_query, (vaccine_name,))

        # Commit the changes
        conn.commit()
        print(f"Appointment ID {appointment_id} has been canceled.")
    except pymssql.Error as e:
        print(f"Error canceling appointment: {e}")
        conn.rollback()
    finally:
        cm.close_connection()


def add_doses(tokens):
    if not session["logged_in"] or session["role"] != "caregiver":
        print("Please login as a caregiver first!")
        return

    if len(tokens) != 3:
        print("Invalid arguments. Usage: add_doses <vaccine> <number>")
        return

    vaccine_name = tokens[1]
    try:
        doses = int(tokens[2])
        if doses <= 0:
            print("Number of doses must be positive!")
            return
    except ValueError:
        print("Invalid number of doses!")
        return

    vaccine = Vaccine(vaccine_name, doses)
    try:
        existing_vaccine = vaccine.get()
        if existing_vaccine:
            existing_vaccine.increase_available_doses(doses)
        else:
            vaccine.save_to_db()
        print("Doses updated!")
    except Exception as e:
        print(f"Failed to add doses: {e}")



def show_appointments(tokens):
    if not session["logged_in"]:
        print("Please login first!")
        return

    cm = ConnectionManager()
    conn = cm.create_connection()
    
    try:
        
        cursor = conn.cursor()
        
        if session["role"] == "patient":
            query = """
                SELECT Appointment_ID, Vaccine_Name, Date, Caregiver_Username
                FROM Appointments
                WHERE Patient_Username = %s
                ORDER BY Appointment_ID;
            """
            cursor.execute(query, (session['username'],))
            
        elif session["role"] == "caregiver":
            query = """
                SELECT Appointment_ID, Vaccine_Name, Date, Patient_Username
                FROM Appointments
                WHERE Caregiver_Username = %s
                ORDER BY Appointment_ID;
            """
            cursor.execute(query, (session["username"],))

        rows = cursor.fetchall()
        
        if not rows:
            print("No appointments found.")
        else:
            for row in rows:
                date_str = row[2].strftime('%Y-%m-%d') if row[2] else 'N/A'
                print(f"Appointment ID: {row[0]}, "
                      f"Vaccine: {row[1]}, "
                      f"Date: {date_str}, "
                      f"Related User: {row[3]}")
    except pymssql.Error as e:
        print(f"Error retrieving appointments: {e}")
    finally:
        cm.close_connection()





def logout(tokens):
    if not session["logged_in"]:
        print("You are not logged in!")
        return

    session["logged_in"] = False
    session["username"] = None
    session["role"] = None
    print("Successfully logged out!")



def start():
    while True:
        print()
        print(" *** Please enter one of the following commands *** ")
        print("> create_patient <username> <password>")
        print("> create_caregiver <username> <password>")
        print("> login_patient <username> <password>")
        print("> login_caregiver <username> <password>")
        print("> search_caregiver_schedule <date>")
        print("> reserve <date> <vaccine>")
        print("> upload_availability <date>")
        print("> cancel <appointment_id>")
        print("> add_doses <vaccine> <number>")
        print("> show_appointments")
        print("> logout")
        print("> Quit")
        print()

        try:
            response = input("> ").strip()
            tokens = response.split()
            if not tokens:
                print("No command entered. Please try again!")
                continue

            operation = tokens[0].lower()

            if operation == "create_patient":
                create_patient(tokens)
            elif operation == "create_caregiver":
                create_caregiver(tokens)
            elif operation == "login_patient":
                login_patient(tokens)
            elif operation == "login_caregiver":
                login_caregiver(tokens)
            elif operation == "search_caregiver_schedule":
                search_caregiver_schedule(tokens)
            elif operation == "reserve":
                reserve(tokens)
            elif operation == "upload_availability":
                upload_availability(tokens)
            elif operation == "cancel":
                cancel(tokens)
            elif operation == "add_doses":
                add_doses(tokens)
            elif operation == "show_appointments":
                show_appointments(tokens)
            elif operation == "logout":
                logout(tokens)
            elif operation == "quit":
                print("Bye!")
                break
            else:
                print("Invalid operation name! Please try again.")
        except ValueError as ve:
            print(f"Input error: {ve}. Please try again.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Please try again.")



if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''
    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")
    start()
