"""
database.py  -  Data Access Layer (Back-End)
Hotel Management System | 22AIE303 DBMS

Every SQL statement used by the application lives here.
The GUI (app.py) never writes SQL directly - it calls these functions.
"""

import hashlib
import mysql.connector
from mysql.connector import Error
from db_config import DB_CONFIG


# ----------------------------------------------------------------------
# CONNECTION HANDLING
# ----------------------------------------------------------------------
def get_connection():
    """Open a new MySQL connection. Raises Error if it fails."""
    return mysql.connector.connect(**DB_CONFIG)


def run_query(sql, params=None, fetch=False, fetchone=False):
    """
    Generic executor.
      fetch=True     -> returns list of rows
      fetchone=True  -> returns a single row
      otherwise      -> commits and returns lastrowid / rowcount
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        if fetchone:
            result = cur.fetchone()
        elif fetch:
            result = cur.fetchall()
        else:
            conn.commit()
            result = cur.lastrowid if cur.lastrowid else cur.rowcount
        return result
    finally:
        cur.close()
        conn.close()


def test_connection():
    """Used by app.py at start-up to show a friendly error."""
    try:
        conn = get_connection()
        conn.close()
        return True, "Connected"
    except Error as e:
        return False, str(e)


# ----------------------------------------------------------------------
# 1. AUTHENTICATION
# ----------------------------------------------------------------------
def hash_password(plain):
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def authenticate(username, password):
    """Returns (user_id, username, role) or None."""
    sql = "SELECT user_id, username, role FROM users WHERE username=%s AND password=%s"
    return run_query(sql, (username, hash_password(password)), fetchone=True)


def add_user(username, password, role):
    sql = "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)"
    return run_query(sql, (username, hash_password(password), role))


def get_users():
    return run_query(
        "SELECT user_id, username, role, created_at FROM users ORDER BY user_id",
        fetch=True)


# ----------------------------------------------------------------------
# 2. ROOM TYPES  (CRUD)
# ----------------------------------------------------------------------
def get_room_types():
    return run_query(
        "SELECT room_type_id, room_type_name, capacity, price_per_night "
        "FROM room_types ORDER BY room_type_id", fetch=True)


def add_room_type(name, capacity, price):
    sql = ("INSERT INTO room_types (room_type_name, capacity, price_per_night) "
           "VALUES (%s, %s, %s)")
    return run_query(sql, (name, capacity, price))


def update_room_type(rtid, name, capacity, price):
    sql = ("UPDATE room_types SET room_type_name=%s, capacity=%s, price_per_night=%s "
           "WHERE room_type_id=%s")
    return run_query(sql, (name, capacity, price, rtid))


def delete_room_type(rtid):
    return run_query("DELETE FROM room_types WHERE room_type_id=%s", (rtid,))


# ----------------------------------------------------------------------
# 3. ROOMS  (CRUD)
# ----------------------------------------------------------------------
def get_rooms():
    """JOIN of rooms and room_types."""
    sql = ("SELECT r.room_id, r.room_number, rt.room_type_name, r.floor, "
           "rt.price_per_night, r.status "
           "FROM rooms r JOIN room_types rt ON r.room_type_id = rt.room_type_id "
           "ORDER BY r.room_number")
    return run_query(sql, fetch=True)


def add_room(room_number, room_type_id, floor, status):
    sql = ("INSERT INTO rooms (room_number, room_type_id, floor, status) "
           "VALUES (%s, %s, %s, %s)")
    return run_query(sql, (room_number, room_type_id, floor, status))


def update_room(room_id, room_number, room_type_id, floor, status):
    sql = ("UPDATE rooms SET room_number=%s, room_type_id=%s, floor=%s, status=%s "
           "WHERE room_id=%s")
    return run_query(sql, (room_number, room_type_id, floor, status, room_id))


def delete_room(room_id):
    return run_query("DELETE FROM rooms WHERE room_id=%s", (room_id,))


def get_available_rooms(check_in, check_out):
    """
    Rooms that are NOT under maintenance and have NO overlapping active booking.
    Classic overlap test:  existing.check_in < new.check_out
                       AND existing.check_out > new.check_in
    """
    sql = ("SELECT r.room_id, r.room_number, rt.room_type_name, rt.price_per_night "
           "FROM rooms r JOIN room_types rt ON r.room_type_id = rt.room_type_id "
           "WHERE r.status <> 'Maintenance' "
           "AND r.room_id NOT IN ( "
           "    SELECT b.room_id FROM bookings b "
           "    WHERE b.booking_status IN ('Booked','Checked-In') "
           "    AND b.check_in_date < %s AND b.check_out_date > %s ) "
           "ORDER BY r.room_number")
    return run_query(sql, (check_out, check_in), fetch=True)


def is_room_free(room_id, check_in, check_out, exclude_booking=None):
    sql = ("SELECT COUNT(*) FROM bookings "
           "WHERE room_id=%s AND booking_status IN ('Booked','Checked-In') "
           "AND check_in_date < %s AND check_out_date > %s")
    params = [room_id, check_out, check_in]
    if exclude_booking:
        sql += " AND booking_id <> %s"
        params.append(exclude_booking)
    row = run_query(sql, tuple(params), fetchone=True)
    return row[0] == 0


# ----------------------------------------------------------------------
# 4. GUESTS  (CRUD + SEARCH)
# ----------------------------------------------------------------------
GUEST_COLS = ("guest_id, first_name, last_name, gender, phone, email, "
              "address, id_proof, id_number")


def get_guests():
    return run_query(f"SELECT {GUEST_COLS} FROM guests ORDER BY guest_id", fetch=True)


def search_guests(keyword):
    like = f"%{keyword}%"
    sql = (f"SELECT {GUEST_COLS} FROM guests "
           "WHERE first_name LIKE %s OR last_name LIKE %s "
           "OR phone LIKE %s OR email LIKE %s OR id_number LIKE %s "
           "ORDER BY guest_id")
    return run_query(sql, (like, like, like, like, like), fetch=True)


def add_guest(fn, ln, gender, phone, email, address, id_proof, id_number):
    sql = ("INSERT INTO guests (first_name,last_name,gender,phone,email,"
           "address,id_proof,id_number) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)")
    return run_query(sql, (fn, ln, gender, phone, email, address, id_proof, id_number))


def update_guest(gid, fn, ln, gender, phone, email, address, id_proof, id_number):
    sql = ("UPDATE guests SET first_name=%s,last_name=%s,gender=%s,phone=%s,"
           "email=%s,address=%s,id_proof=%s,id_number=%s WHERE guest_id=%s")
    return run_query(sql, (fn, ln, gender, phone, email, address,
                           id_proof, id_number, gid))


def delete_guest(gid):
    return run_query("DELETE FROM guests WHERE guest_id=%s", (gid,))


def get_guest_choices():
    sql = ("SELECT guest_id, CONCAT(first_name,' ',IFNULL(last_name,''),"
           "' (',phone,')') FROM guests ORDER BY first_name")
    return run_query(sql, fetch=True)


# ----------------------------------------------------------------------
# 5. BOOKINGS  (CRUD)
# ----------------------------------------------------------------------
def get_bookings():
    """Three-table JOIN + computed nights and amount."""
    sql = ("SELECT b.booking_id, "
           "CONCAT(g.first_name,' ',IFNULL(g.last_name,'')) AS guest_name, "
           "r.room_number, rt.room_type_name, b.check_in_date, b.check_out_date, "
           "DATEDIFF(b.check_out_date,b.check_in_date) AS nights, "
           "(DATEDIFF(b.check_out_date,b.check_in_date)*rt.price_per_night) AS amount, "
           "b.number_of_guests, b.booking_status "
           "FROM bookings b "
           "JOIN guests g ON b.guest_id = g.guest_id "
           "JOIN rooms r ON b.room_id = r.room_id "
           "JOIN room_types rt ON r.room_type_id = rt.room_type_id "
           "ORDER BY b.booking_id DESC")
    return run_query(sql, fetch=True)


def search_bookings(keyword):
    like = f"%{keyword}%"
    sql = ("SELECT b.booking_id, "
           "CONCAT(g.first_name,' ',IFNULL(g.last_name,'')) AS guest_name, "
           "r.room_number, rt.room_type_name, b.check_in_date, b.check_out_date, "
           "DATEDIFF(b.check_out_date,b.check_in_date) AS nights, "
           "(DATEDIFF(b.check_out_date,b.check_in_date)*rt.price_per_night) AS amount, "
           "b.number_of_guests, b.booking_status "
           "FROM bookings b "
           "JOIN guests g ON b.guest_id = g.guest_id "
           "JOIN rooms r ON b.room_id = r.room_id "
           "JOIN room_types rt ON r.room_type_id = rt.room_type_id "
           "WHERE g.first_name LIKE %s OR g.last_name LIKE %s "
           "OR r.room_number LIKE %s OR b.booking_status LIKE %s "
           "ORDER BY b.booking_id DESC")
    return run_query(sql, (like, like, like, like), fetch=True)


def add_booking(guest_id, room_id, cin, cout, pax, bdate, status):
    sql = ("INSERT INTO bookings (guest_id,room_id,check_in_date,check_out_date,"
           "number_of_guests,booking_date,booking_status) "
           "VALUES (%s,%s,%s,%s,%s,%s,%s)")
    return run_query(sql, (guest_id, room_id, cin, cout, pax, bdate, status))


def update_booking(bid, guest_id, room_id, cin, cout, pax, status):
    sql = ("UPDATE bookings SET guest_id=%s, room_id=%s, check_in_date=%s, "
           "check_out_date=%s, number_of_guests=%s, booking_status=%s "
           "WHERE booking_id=%s")
    return run_query(sql, (guest_id, room_id, cin, cout, pax, status, bid))


def set_booking_status(bid, status):
    return run_query("UPDATE bookings SET booking_status=%s WHERE booking_id=%s",
                     (status, bid))


def delete_booking(bid):
    return run_query("DELETE FROM bookings WHERE booking_id=%s", (bid,))


def get_booking_amount(bid):
    sql = ("SELECT DATEDIFF(b.check_out_date,b.check_in_date)*rt.price_per_night "
           "FROM bookings b JOIN rooms r ON b.room_id=r.room_id "
           "JOIN room_types rt ON r.room_type_id=rt.room_type_id "
           "WHERE b.booking_id=%s")
    row = run_query(sql, (bid,), fetchone=True)
    return row[0] if row else 0


def get_booking_choices():
    sql = ("SELECT b.booking_id, CONCAT('#',b.booking_id,' - ',g.first_name,"
           "' - Room ',r.room_number) "
           "FROM bookings b JOIN guests g ON b.guest_id=g.guest_id "
           "JOIN rooms r ON b.room_id=r.room_id ORDER BY b.booking_id DESC")
    return run_query(sql, fetch=True)


# ----------------------------------------------------------------------
# 6. PAYMENTS  (CRUD)
# ----------------------------------------------------------------------
def get_payments():
    sql = ("SELECT p.payment_id, p.booking_id, "
           "CONCAT(g.first_name,' ',IFNULL(g.last_name,'')) AS guest_name, "
           "p.amount, p.payment_method, p.payment_date, p.payment_status "
           "FROM payments p "
           "JOIN bookings b ON p.booking_id = b.booking_id "
           "JOIN guests g ON b.guest_id = g.guest_id "
           "ORDER BY p.payment_id DESC")
    return run_query(sql, fetch=True)


def add_payment(booking_id, amount, method, pdate, status):
    sql = ("INSERT INTO payments (booking_id,amount,payment_method,payment_date,"
           "payment_status) VALUES (%s,%s,%s,%s,%s)")
    return run_query(sql, (booking_id, amount, method, pdate, status))


def update_payment(pid, booking_id, amount, method, pdate, status):
    sql = ("UPDATE payments SET booking_id=%s, amount=%s, payment_method=%s, "
           "payment_date=%s, payment_status=%s WHERE payment_id=%s")
    return run_query(sql, (booking_id, amount, method, pdate, status, pid))


def delete_payment(pid):
    return run_query("DELETE FROM payments WHERE payment_id=%s", (pid,))


# ----------------------------------------------------------------------
# 7. REPORTS  (aggregate functions / GROUP BY / HAVING)
# ----------------------------------------------------------------------
def report_room_availability():
    sql = ("SELECT rt.room_type_name, COUNT(*) AS total, "
           "SUM(CASE WHEN r.status='Available' THEN 1 ELSE 0 END) AS available, "
           "SUM(CASE WHEN r.status='Occupied' THEN 1 ELSE 0 END) AS occupied, "
           "SUM(CASE WHEN r.status='Maintenance' THEN 1 ELSE 0 END) AS maintenance "
           "FROM rooms r JOIN room_types rt ON r.room_type_id=rt.room_type_id "
           "GROUP BY rt.room_type_name ORDER BY rt.room_type_name")
    return run_query(sql, fetch=True)


def report_revenue_by_method():
    sql = ("SELECT payment_method, COUNT(*) AS txn_count, SUM(amount) AS total, "
           "ROUND(AVG(amount),2) AS avg_amount "
           "FROM payments WHERE payment_status='Paid' "
           "GROUP BY payment_method ORDER BY total DESC")
    return run_query(sql, fetch=True)


def report_top_guests():
    """GROUP BY + HAVING + ORDER BY."""
    sql = ("SELECT CONCAT(g.first_name,' ',IFNULL(g.last_name,'')) AS guest_name, "
           "g.phone, COUNT(b.booking_id) AS bookings, "
           "SUM(DATEDIFF(b.check_out_date,b.check_in_date)) AS total_nights "
           "FROM guests g JOIN bookings b ON g.guest_id=b.guest_id "
           "GROUP BY g.guest_id, guest_name, g.phone "
           "HAVING COUNT(b.booking_id) >= 1 "
           "ORDER BY bookings DESC, total_nights DESC")
    return run_query(sql, fetch=True)


def report_pending_payments():
    sql = ("SELECT p.payment_id, p.booking_id, "
           "CONCAT(g.first_name,' ',IFNULL(g.last_name,'')) AS guest_name, "
           "p.amount, p.payment_date "
           "FROM payments p JOIN bookings b ON p.booking_id=b.booking_id "
           "JOIN guests g ON b.guest_id=g.guest_id "
           "WHERE p.payment_status='Pending' ORDER BY p.amount DESC")
    return run_query(sql, fetch=True)


def dashboard_stats():
    stats = {}
    stats["rooms"] = run_query("SELECT COUNT(*) FROM rooms", fetchone=True)[0]
    stats["available"] = run_query(
        "SELECT COUNT(*) FROM rooms WHERE status='Available'", fetchone=True)[0]
    stats["guests"] = run_query("SELECT COUNT(*) FROM guests", fetchone=True)[0]
    stats["active"] = run_query(
        "SELECT COUNT(*) FROM bookings WHERE booking_status IN "
        "('Booked','Checked-In')", fetchone=True)[0]
    stats["revenue"] = run_query(
        "SELECT IFNULL(SUM(amount),0) FROM payments WHERE payment_status='Paid'",
        fetchone=True)[0]
    stats["pending"] = run_query(
        "SELECT IFNULL(SUM(amount),0) FROM payments WHERE payment_status='Pending'",
        fetchone=True)[0]
    return stats
