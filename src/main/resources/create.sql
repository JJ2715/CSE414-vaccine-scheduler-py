CREATE TABLE Patients (
    Username varchar(255) PRIMARY KEY,
    Salt BINARY(16),
    Hash BINARY(16)
);

CREATE TABLE Caregivers (
    Username varchar(255) PRIMARY KEY,
    Salt BINARY(16),
    Hash BINARY(16)
);

CREATE TABLE Availabilities (
    Time DATE,
    Username varchar(255) REFERENCES Caregivers(Username),
    Reserved BIT DEFAULT 0,
    PRIMARY KEY (Time, Username)
);

CREATE TABLE Vaccines (
    Name varchar(255) PRIMARY KEY,
    Doses INT
);

CREATE TABLE Appointments (
    Appointment_ID INT IDENTITY(1,1) PRIMARY KEY,
    Patient_Username VARCHAR(255) NOT NULL REFERENCES Patients(Username),
    Caregiver_Username VARCHAR(255) NOT NULL REFERENCES Caregivers(Username),
    Vaccine_Name VARCHAR(255) NOT NULL REFERENCES Vaccines(Name),
    Date DATE NOT NULL,
    FOREIGN KEY (Date, Caregiver_Username) REFERENCES Availabilities(Time, Username)
);