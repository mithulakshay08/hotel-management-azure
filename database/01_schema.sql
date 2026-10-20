-- ============================================================
--  HOTEL MANAGEMENT SYSTEM  |  22AIE303 DBMS Project
--  Backend Schema  :  MySQL 8.0
--  Run with        :  mysql -u root -p < 01_schema.sql
-- ============================================================

DROP DATABASE IF EXISTS hotel_db;
CREATE DATABASE hotel_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hotel_db;

-- ------------------------------------------------------------
-- 1. USERS  (staff logins / authentication)
-- ------------------------------------------------------------
CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password      VARCHAR(64)  NOT NULL,              -- SHA-256 hex digest
    role          ENUM('Admin','Receptionist') NOT NULL DEFAULT 'Receptionist',
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 2. ROOM_TYPES  (Standard / Deluxe / Suite ...)
-- ------------------------------------------------------------
CREATE TABLE room_types (
    room_type_id     INT AUTO_INCREMENT PRIMARY KEY,
    room_type_name   VARCHAR(40)   NOT NULL UNIQUE,
    capacity         INT           NOT NULL,
    price_per_night  DECIMAL(10,2) NOT NULL,
    CONSTRAINT chk_capacity CHECK (capacity BETWEEN 1 AND 10),
    CONSTRAINT chk_price    CHECK (price_per_night > 0)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 3. ROOMS
-- ------------------------------------------------------------
CREATE TABLE rooms (
    room_id       INT AUTO_INCREMENT PRIMARY KEY,
    room_number   VARCHAR(10) NOT NULL UNIQUE,
    room_type_id  INT         NOT NULL,
    floor         INT         NOT NULL,
    status        ENUM('Available','Occupied','Maintenance') NOT NULL DEFAULT 'Available',
    CONSTRAINT fk_room_type FOREIGN KEY (room_type_id)
        REFERENCES room_types(room_type_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_floor CHECK (floor BETWEEN 0 AND 50)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 4. GUESTS
-- ------------------------------------------------------------
CREATE TABLE guests (
    guest_id    INT AUTO_INCREMENT PRIMARY KEY,
    first_name  VARCHAR(50) NOT NULL,
    last_name   VARCHAR(50),
    gender      ENUM('Male','Female','Other') NOT NULL,
    phone       VARCHAR(15) NOT NULL UNIQUE,
    email       VARCHAR(80),
    address     VARCHAR(150),
    id_proof    ENUM('Aadhaar','Passport','Driving License','Voter ID') NOT NULL,
    id_number   VARCHAR(40) NOT NULL,
    CONSTRAINT uq_guest_id_doc UNIQUE (id_proof, id_number)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 5. BOOKINGS
-- ------------------------------------------------------------
CREATE TABLE bookings (
    booking_id      INT AUTO_INCREMENT PRIMARY KEY,
    guest_id        INT  NOT NULL,
    room_id         INT  NOT NULL,
    check_in_date   DATE NOT NULL,
    check_out_date  DATE NOT NULL,
    number_of_guests INT NOT NULL DEFAULT 1,
    booking_date    DATE NOT NULL,
    booking_status  ENUM('Booked','Checked-In','Checked-Out','Cancelled')
                    NOT NULL DEFAULT 'Booked',
    CONSTRAINT fk_booking_guest FOREIGN KEY (guest_id)
        REFERENCES guests(guest_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_booking_room  FOREIGN KEY (room_id)
        REFERENCES rooms(room_id)  ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_dates  CHECK (check_out_date > check_in_date),
    CONSTRAINT chk_pax    CHECK (number_of_guests BETWEEN 1 AND 10)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 6. PAYMENTS
-- ------------------------------------------------------------
CREATE TABLE payments (
    payment_id      INT AUTO_INCREMENT PRIMARY KEY,
    booking_id      INT NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    payment_method  ENUM('Cash','Card','UPI','Net Banking') NOT NULL,
    payment_date    DATE NOT NULL,
    payment_status  ENUM('Paid','Pending','Refunded') NOT NULL DEFAULT 'Pending',
    CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id)
        REFERENCES bookings(booking_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_amount CHECK (amount >= 0)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- INDEXES  (query optimisation)
-- ------------------------------------------------------------
CREATE INDEX idx_booking_dates  ON bookings(check_in_date, check_out_date);
CREATE INDEX idx_booking_status ON bookings(booking_status);
CREATE INDEX idx_guest_name     ON guests(first_name, last_name);
CREATE INDEX idx_room_status    ON rooms(status);

-- ------------------------------------------------------------
-- VIEWS
-- ------------------------------------------------------------
CREATE VIEW vw_room_availability AS
SELECT r.room_id, r.room_number, rt.room_type_name, r.floor,
       rt.capacity, rt.price_per_night, r.status
FROM rooms r
JOIN room_types rt ON r.room_type_id = rt.room_type_id;

CREATE VIEW vw_booking_details AS
SELECT b.booking_id,
       CONCAT(g.first_name,' ',IFNULL(g.last_name,'')) AS guest_name,
       g.phone, r.room_number, rt.room_type_name,
       b.check_in_date, b.check_out_date,
       DATEDIFF(b.check_out_date, b.check_in_date) AS nights,
       (DATEDIFF(b.check_out_date, b.check_in_date) * rt.price_per_night) AS total_amount,
       b.booking_status
FROM bookings b
JOIN guests     g  ON b.guest_id     = g.guest_id
JOIN rooms      r  ON b.room_id      = r.room_id
JOIN room_types rt ON r.room_type_id = rt.room_type_id;

CREATE VIEW vw_payment_summary AS
SELECT p.payment_id, p.booking_id,
       CONCAT(g.first_name,' ',IFNULL(g.last_name,'')) AS guest_name,
       p.amount, p.payment_method, p.payment_date, p.payment_status
FROM payments p
JOIN bookings b ON p.booking_id = b.booking_id
JOIN guests   g ON b.guest_id   = g.guest_id;

-- ------------------------------------------------------------
-- TRIGGERS  (automatic room-status maintenance)
-- ------------------------------------------------------------
DELIMITER $$

CREATE TRIGGER trg_after_booking_insert
AFTER INSERT ON bookings
FOR EACH ROW
BEGIN
    IF NEW.booking_status IN ('Booked','Checked-In') THEN
        UPDATE rooms SET status = 'Occupied' WHERE room_id = NEW.room_id;
    END IF;
END$$

CREATE TRIGGER trg_after_booking_update
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF NEW.booking_status IN ('Checked-Out','Cancelled') THEN
        UPDATE rooms SET status = 'Available' WHERE room_id = NEW.room_id;
    ELSEIF NEW.booking_status IN ('Booked','Checked-In') THEN
        UPDATE rooms SET status = 'Occupied' WHERE room_id = NEW.room_id;
    END IF;
END$$

-- ------------------------------------------------------------
-- STORED PROCEDURE  (bill generation)
-- ------------------------------------------------------------
CREATE PROCEDURE sp_generate_bill(IN p_booking_id INT)
BEGIN
    SELECT b.booking_id,
           CONCAT(g.first_name,' ',IFNULL(g.last_name,'')) AS guest_name,
           r.room_number, rt.room_type_name, rt.price_per_night,
           DATEDIFF(b.check_out_date, b.check_in_date) AS nights,
           (DATEDIFF(b.check_out_date, b.check_in_date) * rt.price_per_night) AS total_amount
    FROM bookings b
    JOIN guests     g  ON b.guest_id     = g.guest_id
    JOIN rooms      r  ON b.room_id      = r.room_id
    JOIN room_types rt ON r.room_type_id = rt.room_type_id
    WHERE b.booking_id = p_booking_id;
END$$

DELIMITER ;

-- ============================================================
--  SAMPLE DATA
-- ============================================================

-- password for BOTH users below is:  admin123   (SHA-256 hex)
INSERT INTO users (username, password, role) VALUES
('admin',    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Admin'),
('reception','240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Receptionist');

INSERT INTO room_types (room_type_name, capacity, price_per_night) VALUES
('Standard',       2, 1800.00),
('Deluxe',         3, 3200.00),
('Executive Suite',4, 5500.00),
('Family Room',    5, 4200.00);

INSERT INTO rooms (room_number, room_type_id, floor, status) VALUES
('101',1,1,'Available'), ('102',1,1,'Available'), ('103',1,1,'Maintenance'),
('201',2,2,'Available'), ('202',2,2,'Available'),
('301',3,3,'Available'), ('302',3,3,'Available'),
('401',4,4,'Available'), ('402',4,4,'Available'), ('403',1,4,'Available');

INSERT INTO guests (first_name,last_name,gender,phone,email,address,id_proof,id_number) VALUES
('Arjun','Menon','Male','9876543210','arjun.m@example.com','12 Anna Nagar, Chennai','Aadhaar','4321-8765-1098'),
('Priya','Raghavan','Female','9812345678','priya.r@example.com','5 RS Puram, Coimbatore','Aadhaar','1122-3344-5566'),
('Karthik','Subramanian','Male','9791122334','karthik.s@example.com','88 Besant Nagar, Chennai','Driving License','TN0920190001'),
('Sneha','Iyer','Female','9445566778','sneha.i@example.com','23 Mylapore, Chennai','Passport','P1234567'),
('Rahul','Verma','Male','9900112233','rahul.v@example.com','7 Koramangala, Bengaluru','Voter ID','ABC1234567');

INSERT INTO bookings (guest_id,room_id,check_in_date,check_out_date,number_of_guests,booking_date,booking_status) VALUES
(1,1,'2026-08-12','2026-08-15',2,'2026-08-10','Checked-In'),
(2,4,'2026-08-13','2026-08-16',3,'2026-08-10','Booked'),
(3,6,'2026-08-01','2026-08-04',2,'2026-07-28','Checked-Out'),
(4,8,'2026-08-14','2026-08-18',4,'2026-08-11','Booked'),
(5,2,'2026-07-20','2026-07-22',1,'2026-07-18','Checked-Out');

INSERT INTO payments (booking_id,amount,payment_method,payment_date,payment_status) VALUES
(1, 5400.00,'UPI',        '2026-08-12','Paid'),
(2, 9600.00,'Card',       '2026-08-13','Pending'),
(3,16500.00,'Net Banking','2026-08-04','Paid'),
(4,16800.00,'Cash',       '2026-08-14','Pending'),
(5, 3600.00,'UPI',        '2026-07-22','Paid');

-- Verify
SELECT 'Database created successfully' AS status;
SELECT COUNT(*) AS total_rooms FROM rooms;
SELECT COUNT(*) AS total_bookings FROM bookings;
