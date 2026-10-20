"""
app.py  -  Front-End (Tkinter GUI)
Hotel Management System | 22AIE303 DBMS Project

Run:  python app.py
Login: admin / admin123
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

import database as db

# ---------------------------------------------------------------- theme
BG = "#f4f6f8"
CARD = "#ffffff"
PRIMARY = "#1f3a5f"
ACCENT = "#c8a165"
TEXT = "#22303f"
MUTED = "#6b7c8f"

FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")
FONT_H = ("Segoe UI", 16, "bold")
FONT_XL = ("Segoe UI", 22, "bold")


def valid_date(s):
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


# ======================================================================
#  LOGIN WINDOW
# ======================================================================
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hotel Management System - Login")
        self.geometry("420x360")
        self.configure(bg=PRIMARY)
        self.resizable(False, False)
        self.user = None

        tk.Label(self, text="HOTEL", font=("Segoe UI", 26, "bold"),
                 bg=PRIMARY, fg="white").pack(pady=(45, 0))
        tk.Label(self, text="MANAGEMENT SYSTEM", font=("Segoe UI", 11),
                 bg=PRIMARY, fg=ACCENT).pack()

        box = tk.Frame(self, bg=CARD, padx=25, pady=20)
        box.pack(pady=25, padx=40, fill="x")

        tk.Label(box, text="Username", font=FONT_B, bg=CARD, fg=TEXT).pack(anchor="w")
        self.e_user = tk.Entry(box, font=FONT, width=28)
        self.e_user.pack(pady=(2, 10))
        self.e_user.insert(0, "admin")

        tk.Label(box, text="Password", font=FONT_B, bg=CARD, fg=TEXT).pack(anchor="w")
        self.e_pass = tk.Entry(box, font=FONT, width=28, show="*")
        self.e_pass.pack(pady=(2, 14))
        self.e_pass.bind("<Return>", lambda e: self.login())

        tk.Button(box, text="LOGIN", font=FONT_B, bg=PRIMARY, fg="white",
                  relief="flat", width=24, pady=6,
                  command=self.login).pack()

        self.status = tk.Label(self, text="", bg=PRIMARY, fg="#ffb4b4", font=FONT)
        self.status.pack()

        self.after(200, self.check_db)

    def check_db(self):
        ok, msg = db.test_connection()
        if not ok:
            messagebox.showerror(
                "Database Error",
                "Cannot connect to MySQL.\n\n"
                f"{msg}\n\nCheck db_config.py and make sure MySQL is running "
                "and 01_schema.sql has been executed.")

    def login(self):
        u = self.e_user.get().strip()
        p = self.e_pass.get().strip()
        if not u or not p:
            self.status.config(text="Enter username and password")
            return
        try:
            row = db.authenticate(u, p)
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            return
        if row:
            self.user = {"id": row[0], "name": row[1], "role": row[2]}
            self.destroy()
            MainApp(self.user).mainloop()
        else:
            self.status.config(text="Invalid username or password")


# ======================================================================
#  MAIN APPLICATION
# ======================================================================
class MainApp(tk.Tk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.title(f"Hotel Management System  -  {user['name']} ({user['role']})")
        self.geometry("1180x680")
        self.configure(bg=BG)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", font=FONT_B, padding=(18, 9),
                        background="#dde3e9", foreground=TEXT)
        style.map("TNotebook.Tab", background=[("selected", PRIMARY)],
                  foreground=[("selected", "white")])
        style.configure("Treeview", font=FONT, rowheight=26,
                        fieldbackground=CARD, background=CARD)
        style.configure("Treeview.Heading", font=FONT_B,
                        background=PRIMARY, foreground="white")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, font=FONT)
        style.configure("TButton", font=FONT_B, padding=5)

        header = tk.Frame(self, bg=PRIMARY, height=52)
        header.pack(fill="x")
        tk.Label(header, text="  HOTEL MANAGEMENT SYSTEM", bg=PRIMARY, fg="white",
                 font=("Segoe UI", 14, "bold")).pack(side="left", pady=12)
        tk.Button(header, text="Logout", bg=ACCENT, fg="white", relief="flat",
                  font=FONT_B, padx=14, command=self.logout).pack(side="right", padx=12)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_dash = DashboardTab(self.nb)
        self.tab_rt = RoomTypeTab(self.nb)
        self.tab_room = RoomTab(self.nb)
        self.tab_guest = GuestTab(self.nb)
        self.tab_book = BookingTab(self.nb)
        self.tab_pay = PaymentTab(self.nb)
        self.tab_rep = ReportTab(self.nb)

        for tab, name in [(self.tab_dash, "Dashboard"), (self.tab_rt, "Room Types"),
                          (self.tab_room, "Rooms"), (self.tab_guest, "Guests"),
                          (self.tab_book, "Bookings"), (self.tab_pay, "Payments"),
                          (self.tab_rep, "Reports")]:
            self.nb.add(tab, text=name)

        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_change)

    def on_tab_change(self, _):
        current = self.nb.nametowidget(self.nb.select())
        if hasattr(current, "refresh"):
            try:
                current.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def logout(self):
        if messagebox.askyesno("Logout", "Do you want to logout?"):
            self.destroy()
            LoginWindow().mainloop()


# ======================================================================
#  BASE TAB  -  shared form + table helpers
# ======================================================================
class BaseTab(ttk.Frame):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.selected_id = None
        tk.Label(self, text=title, font=FONT_H, bg=BG, fg=PRIMARY).pack(
            anchor="w", padx=14, pady=(10, 4))

        self.form = tk.Frame(self, bg=CARD, padx=14, pady=12,
                             highlightbackground="#d5dde5", highlightthickness=1)
        self.form.pack(fill="x", padx=14)

        self.btnbar = tk.Frame(self, bg=BG)
        self.btnbar.pack(fill="x", padx=14, pady=8)

        self.table_frame = tk.Frame(self, bg=BG)
        self.table_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    # ---------- form widgets ----------
    def entry(self, r, c, label, width=20):
        tk.Label(self.form, text=label, font=FONT_B, bg=CARD, fg=TEXT).grid(
            row=r, column=c * 2, sticky="w", padx=(0, 6), pady=5)
        e = tk.Entry(self.form, font=FONT, width=width)
        e.grid(row=r, column=c * 2 + 1, sticky="w", padx=(0, 22), pady=5)
        return e

    def combo(self, r, c, label, values, width=18):
        tk.Label(self.form, text=label, font=FONT_B, bg=CARD, fg=TEXT).grid(
            row=r, column=c * 2, sticky="w", padx=(0, 6), pady=5)
        cb = ttk.Combobox(self.form, values=values, font=FONT,
                          width=width, state="readonly")
        cb.grid(row=r, column=c * 2 + 1, sticky="w", padx=(0, 22), pady=5)
        return cb

    def buttons(self, specs):
        for text, cmd, color in specs:
            tk.Button(self.btnbar, text=text, command=cmd, bg=color, fg="white",
                      font=FONT_B, relief="flat", padx=16, pady=6).pack(
                side="left", padx=(0, 8))

    def make_table(self, columns, widths):
        wrap = tk.Frame(self.table_frame, bg=BG)
        wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(wrap, columns=columns, show="headings")
        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def fill(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=r)

    def current_row(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0])["values"] if sel else None

    def on_select(self, _):
        pass

    def guard(self, cond, msg):
        if not cond:
            messagebox.showwarning("Validation", msg)
        return cond

    def ok(self, msg):
        messagebox.showinfo("Success", msg)


# ======================================================================
#  DASHBOARD
# ======================================================================
class DashboardTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        tk.Label(self, text="Dashboard", font=FONT_H, bg=BG, fg=PRIMARY).pack(
            anchor="w", padx=14, pady=(12, 10))
        self.grid_frame = tk.Frame(self, bg=BG)
        self.grid_frame.pack(fill="x", padx=14)
        self.cards = {}
        specs = [("Total Rooms", "rooms"), ("Available Rooms", "available"),
                 ("Registered Guests", "guests"), ("Active Bookings", "active"),
                 ("Revenue Collected", "revenue"), ("Payments Pending", "pending")]
        for i, (label, key) in enumerate(specs):
            card = tk.Frame(self.grid_frame, bg=CARD, padx=20, pady=18,
                            highlightbackground="#d5dde5", highlightthickness=1)
            card.grid(row=i // 3, column=i % 3, padx=8, pady=8, sticky="nsew")
            self.grid_frame.grid_columnconfigure(i % 3, weight=1)
            val = tk.Label(card, text="-", font=FONT_XL, bg=CARD, fg=PRIMARY)
            val.pack(anchor="w")
            tk.Label(card, text=label, font=FONT, bg=CARD, fg=MUTED).pack(anchor="w")
            self.cards[key] = val

        tk.Label(self, text="Today's Check-ins / Check-outs", font=FONT_B,
                 bg=BG, fg=TEXT).pack(anchor="w", padx=22, pady=(18, 6))
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="both", expand=True, padx=22, pady=(0, 14))
        cols = ("ID", "Guest", "Room", "Check-In", "Check-Out", "Status")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=6)
        for c, w in zip(cols, (60, 200, 90, 120, 120, 120)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True)

    def refresh(self):
        s = db.dashboard_stats()
        for k, lbl in self.cards.items():
            v = s[k]
            lbl.config(text=f"Rs {v:,.0f}" if k in ("revenue", "pending") else str(v))
        today = date.today()
        rows = [b for b in db.get_bookings()
                if str(b[4]) == str(today) or str(b[5]) == str(today)]
        self.tree.delete(*self.tree.get_children())
        for b in rows:
            self.tree.insert("", "end", values=(b[0], b[1], b[2], b[4], b[5], b[9]))


# ======================================================================
#  ROOM TYPES
# ======================================================================
class RoomTypeTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "Room Type Management")
        self.e_name = self.entry(0, 0, "Type Name")
        self.e_cap = self.entry(0, 1, "Capacity", 10)
        self.e_price = self.entry(0, 2, "Price / Night", 12)
        self.buttons([("Add", self.add, "#2e7d32"), ("Update", self.update, "#1565c0"),
                      ("Delete", self.delete, "#c62828"),
                      ("Clear", self.clear, MUTED), ("Refresh", self.refresh, PRIMARY)])
        self.make_table(("ID", "Room Type", "Capacity", "Price/Night"),
                        (70, 260, 120, 140))
        self.refresh()

    def refresh(self):
        self.fill(db.get_room_types())

    def on_select(self, _):
        r = self.current_row()
        if not r:
            return
        self.selected_id = r[0]
        self.e_name.delete(0, "end"); self.e_name.insert(0, r[1])
        self.e_cap.delete(0, "end"); self.e_cap.insert(0, r[2])
        self.e_price.delete(0, "end"); self.e_price.insert(0, r[3])

    def clear(self):
        self.selected_id = None
        for e in (self.e_name, self.e_cap, self.e_price):
            e.delete(0, "end")

    def read(self):
        name = self.e_name.get().strip()
        if not self.guard(name, "Type name is required"):
            return None
        try:
            cap = int(self.e_cap.get())
            price = float(self.e_price.get())
        except ValueError:
            self.guard(False, "Capacity must be a whole number and price a number")
            return None
        if not self.guard(cap > 0 and price > 0, "Capacity and price must be positive"):
            return None
        return name, cap, price

    def add(self):
        v = self.read()
        if not v:
            return
        try:
            db.add_room_type(*v)
            self.ok("Room type added"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update(self):
        if not self.guard(self.selected_id, "Select a row first"):
            return
        v = self.read()
        if not v:
            return
        try:
            db.update_room_type(self.selected_id, *v)
            self.ok("Room type updated"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if not self.guard(self.selected_id, "Select a row first"):
            return
        if messagebox.askyesno("Confirm", "Delete this room type?"):
            try:
                db.delete_room_type(self.selected_id)
                self.ok("Deleted"); self.clear(); self.refresh()
            except Exception as e:
                messagebox.showerror(
                    "Error", "Cannot delete - rooms of this type exist.\n\n" + str(e))


# ======================================================================
#  ROOMS
# ======================================================================
class RoomTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "Room Management")
        self.e_num = self.entry(0, 0, "Room Number", 14)
        self.cb_type = self.combo(0, 1, "Room Type", [])
        self.e_floor = self.entry(0, 2, "Floor", 8)
        self.cb_status = self.combo(0, 3, "Status",
                                    ["Available", "Occupied", "Maintenance"], 14)
        self.buttons([("Add", self.add, "#2e7d32"), ("Update", self.update, "#1565c0"),
                      ("Delete", self.delete, "#c62828"),
                      ("Clear", self.clear, MUTED), ("Refresh", self.refresh, PRIMARY)])
        self.make_table(("ID", "Room No", "Type", "Floor", "Price", "Status"),
                        (60, 110, 200, 80, 120, 130))
        self.types = {}
        self.refresh()

    def refresh(self):
        self.types = {t[1]: t[0] for t in db.get_room_types()}
        self.cb_type["values"] = list(self.types.keys())
        self.fill(db.get_rooms())

    def on_select(self, _):
        r = self.current_row()
        if not r:
            return
        self.selected_id = r[0]
        self.e_num.delete(0, "end"); self.e_num.insert(0, r[1])
        self.cb_type.set(r[2])
        self.e_floor.delete(0, "end"); self.e_floor.insert(0, r[3])
        self.cb_status.set(r[5])

    def clear(self):
        self.selected_id = None
        self.e_num.delete(0, "end"); self.e_floor.delete(0, "end")
        self.cb_type.set(""); self.cb_status.set("")

    def read(self):
        num = self.e_num.get().strip()
        tname = self.cb_type.get()
        status = self.cb_status.get()
        if not self.guard(num and tname and status,
                          "Room number, type and status are required"):
            return None
        try:
            floor = int(self.e_floor.get())
        except ValueError:
            self.guard(False, "Floor must be a number")
            return None
        return num, self.types[tname], floor, status

    def add(self):
        v = self.read()
        if not v:
            return
        try:
            db.add_room(*v); self.ok("Room added"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", "Room number may already exist.\n\n" + str(e))

    def update(self):
        if not self.guard(self.selected_id, "Select a row first"):
            return
        v = self.read()
        if not v:
            return
        try:
            db.update_room(self.selected_id, *v)
            self.ok("Room updated"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if not self.guard(self.selected_id, "Select a row first"):
            return
        if messagebox.askyesno("Confirm", "Delete this room?"):
            try:
                db.delete_room(self.selected_id)
                self.ok("Deleted"); self.clear(); self.refresh()
            except Exception as e:
                messagebox.showerror(
                    "Error", "Cannot delete - bookings reference this room.\n\n" + str(e))


# ======================================================================
#  GUESTS
# ======================================================================
class GuestTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "Guest Management")
        self.e_fn = self.entry(0, 0, "First Name")
        self.e_ln = self.entry(0, 1, "Last Name")
        self.cb_gender = self.combo(0, 2, "Gender", ["Male", "Female", "Other"], 12)
        self.e_phone = self.entry(1, 0, "Phone")
        self.e_email = self.entry(1, 1, "Email")
        self.cb_idp = self.combo(1, 2, "ID Proof",
                                 ["Aadhaar", "Passport", "Driving License", "Voter ID"], 16)
        self.e_addr = self.entry(2, 0, "Address", 40)
        self.e_idn = self.entry(2, 1, "ID Number")

        search = tk.Frame(self.btnbar, bg=BG)
        self.buttons([("Add", self.add, "#2e7d32"), ("Update", self.update, "#1565c0"),
                      ("Delete", self.delete, "#c62828"),
                      ("Clear", self.clear, MUTED), ("Refresh", self.refresh, PRIMARY)])
        search.pack(side="right")
        tk.Label(search, text="Search:", font=FONT_B, bg=BG).pack(side="left")
        self.e_search = tk.Entry(search, font=FONT, width=22)
        self.e_search.pack(side="left", padx=6)
        self.e_search.bind("<KeyRelease>", lambda e: self.do_search())

        self.make_table(("ID", "First Name", "Last Name", "Gender", "Phone",
                         "Email", "Address", "ID Proof", "ID Number"),
                        (50, 110, 110, 80, 110, 170, 200, 110, 130))
        self.refresh()

    def refresh(self):
        self.fill(db.get_guests())

    def do_search(self):
        kw = self.e_search.get().strip()
        self.fill(db.search_guests(kw) if kw else db.get_guests())

    def on_select(self, _):
        r = self.current_row()
        if not r:
            return
        self.selected_id = r[0]
        vals = [self.e_fn, self.e_ln, None, self.e_phone, self.e_email,
                self.e_addr, None, self.e_idn]
        data = [r[1], r[2], None, r[4], r[5], r[6], None, r[8]]
        for w, v in zip(vals, data):
            if w is not None:
                w.delete(0, "end"); w.insert(0, "" if v is None else v)
        self.cb_gender.set(r[3])
        self.cb_idp.set(r[7])

    def clear(self):
        self.selected_id = None
        for e in (self.e_fn, self.e_ln, self.e_phone, self.e_email,
                  self.e_addr, self.e_idn):
            e.delete(0, "end")
        self.cb_gender.set(""); self.cb_idp.set("")

    def read(self):
        fn = self.e_fn.get().strip()
        phone = self.e_phone.get().strip()
        gender = self.cb_gender.get()
        idp = self.cb_idp.get()
        idn = self.e_idn.get().strip()
        if not self.guard(fn and phone and gender and idp and idn,
                          "First name, gender, phone, ID proof and ID number "
                          "are required"):
            return None
        if not self.guard(phone.isdigit() and len(phone) == 10,
                          "Phone must be exactly 10 digits"):
            return None
        email = self.e_email.get().strip()
        if email and not self.guard("@" in email and "." in email,
                                    "Enter a valid email address"):
            return None
        return (fn, self.e_ln.get().strip(), gender, phone, email,
                self.e_addr.get().strip(), idp, idn)

    def add(self):
        v = self.read()
        if not v:
            return
        try:
            db.add_guest(*v); self.ok("Guest registered"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", "Phone or ID may already exist.\n\n" + str(e))

    def update(self):
        if not self.guard(self.selected_id, "Select a row first"):
            return
        v = self.read()
        if not v:
            return
        try:
            db.update_guest(self.selected_id, *v)
            self.ok("Guest updated"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if not self.guard(self.selected_id, "Select a row first"):
            return
        if messagebox.askyesno("Confirm",
                               "Delete this guest? Their bookings will also be removed."):
            try:
                db.delete_guest(self.selected_id)
                self.ok("Deleted"); self.clear(); self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))


# ======================================================================
#  BOOKINGS
# ======================================================================
class BookingTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "Booking Management")
        self.cb_guest = self.combo(0, 0, "Guest", [], 22)
        self.e_cin = self.entry(0, 1, "Check-In (YYYY-MM-DD)", 14)
        self.e_cout = self.entry(0, 2, "Check-Out (YYYY-MM-DD)", 14)
        self.cb_room = self.combo(1, 0, "Room", [], 22)
        self.e_pax = self.entry(1, 1, "No. of Guests", 8)
        self.cb_status = self.combo(1, 2, "Status",
                                    ["Booked", "Checked-In", "Checked-Out",
                                     "Cancelled"], 14)
        tk.Button(self.form, text="Find Available Rooms", bg=ACCENT, fg="white",
                  font=FONT_B, relief="flat", padx=12, pady=4,
                  command=self.find_rooms).grid(row=2, column=1, sticky="w",
                                                pady=(6, 2))

        self.e_cin.insert(0, str(date.today()))
        self.e_cout.insert(0, str(date.today()))
        self.e_pax.insert(0, "1")
        self.cb_status.set("Booked")

        self.buttons([("Book", self.add, "#2e7d32"),
                      ("Update", self.update, "#1565c0"),
                      ("Check-In", lambda: self.status("Checked-In"), "#00838f"),
                      ("Check-Out", lambda: self.status("Checked-Out"), "#6a1b9a"),
                      ("Cancel", lambda: self.status("Cancelled"), "#ef6c00"),
                      ("Delete", self.delete, "#c62828"),
                      ("Clear", self.clear, MUTED)])

        search = tk.Frame(self.btnbar, bg=BG)
        search.pack(side="right")
        tk.Label(search, text="Search:", font=FONT_B, bg=BG).pack(side="left")
        self.e_search = tk.Entry(search, font=FONT, width=20)
        self.e_search.pack(side="left", padx=6)
        self.e_search.bind("<KeyRelease>", lambda e: self.do_search())

        self.make_table(("ID", "Guest", "Room", "Type", "Check-In", "Check-Out",
                         "Nights", "Amount", "Pax", "Status"),
                        (55, 170, 80, 140, 110, 110, 70, 110, 60, 110))
        self.guests, self.rooms = {}, {}
        self.refresh()

    def refresh(self):
        self.guests = {label: gid for gid, label in db.get_guest_choices()}
        self.cb_guest["values"] = list(self.guests.keys())
        self.rooms = {f"{r[1]} - {r[2]}": r[0] for r in db.get_rooms()}
        self.cb_room["values"] = list(self.rooms.keys())
        self.fill(db.get_bookings())

    def do_search(self):
        kw = self.e_search.get().strip()
        self.fill(db.search_bookings(kw) if kw else db.get_bookings())

    def find_rooms(self):
        cin, cout = valid_date(self.e_cin.get()), valid_date(self.e_cout.get())
        if not self.guard(cin and cout, "Enter valid dates as YYYY-MM-DD"):
            return
        if not self.guard(cout > cin, "Check-out must be after check-in"):
            return
        free = db.get_available_rooms(cin, cout)
        if not free:
            messagebox.showinfo("No Rooms", "No rooms are free for these dates.")
            return
        self.rooms = {f"{r[1]} - {r[2]}": r[0] for r in free}
        self.cb_room["values"] = list(self.rooms.keys())
        self.cb_room.set(list(self.rooms.keys())[0])
        messagebox.showinfo("Available Rooms",
                            f"{len(free)} room(s) available for these dates.")

    def on_select(self, _):
        r = self.current_row()
        if not r:
            return
        self.selected_id = r[0]
        for label in self.guests:
            if label.startswith(str(r[1]).strip()):
                self.cb_guest.set(label); break
        for label, rid in self.rooms.items():
            if label.startswith(str(r[2])):
                self.cb_room.set(label); break
        self.e_cin.delete(0, "end"); self.e_cin.insert(0, r[4])
        self.e_cout.delete(0, "end"); self.e_cout.insert(0, r[5])
        self.e_pax.delete(0, "end"); self.e_pax.insert(0, r[8])
        self.cb_status.set(r[9])

    def clear(self):
        self.selected_id = None
        self.cb_guest.set(""); self.cb_room.set("")
        self.e_cin.delete(0, "end"); self.e_cin.insert(0, str(date.today()))
        self.e_cout.delete(0, "end"); self.e_cout.insert(0, str(date.today()))
        self.e_pax.delete(0, "end"); self.e_pax.insert(0, "1")
        self.cb_status.set("Booked")
        self.refresh()

    def read(self):
        g, rm = self.cb_guest.get(), self.cb_room.get()
        if not self.guard(g and rm, "Select a guest and a room"):
            return None
        cin, cout = valid_date(self.e_cin.get()), valid_date(self.e_cout.get())
        if not self.guard(cin and cout, "Dates must be in YYYY-MM-DD format"):
            return None
        if not self.guard(cout > cin, "Check-out must be after check-in"):
            return None
        try:
            pax = int(self.e_pax.get())
        except ValueError:
            self.guard(False, "Number of guests must be a whole number")
            return None
        if not self.guard(pax > 0, "Number of guests must be at least 1"):
            return None
        status = self.cb_status.get() or "Booked"
        return self.guests[g], self.rooms[rm], cin, cout, pax, status

    def add(self):
        v = self.read()
        if not v:
            return
        gid, rid, cin, cout, pax, status = v
        if not db.is_room_free(rid, cin, cout):
            messagebox.showerror("Room Not Free",
                                 "This room is already booked for the selected dates.")
            return
        try:
            bid = db.add_booking(gid, rid, cin, cout, pax, date.today(), status)
            amount = db.get_booking_amount(bid)
            self.ok(f"Booking #{bid} created.\nTotal payable: Rs {amount:,.2f}")
            self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update(self):
        if not self.guard(self.selected_id, "Select a booking first"):
            return
        v = self.read()
        if not v:
            return
        gid, rid, cin, cout, pax, status = v
        if not db.is_room_free(rid, cin, cout, exclude_booking=self.selected_id):
            messagebox.showerror("Room Not Free",
                                 "This room is already booked for the selected dates.")
            return
        try:
            db.update_booking(self.selected_id, gid, rid, cin, cout, pax, status)
            self.ok("Booking updated"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def status(self, new_status):
        if not self.guard(self.selected_id, "Select a booking first"):
            return
        try:
            db.set_booking_status(self.selected_id, new_status)
            self.ok(f"Booking marked as {new_status}")
            self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if not self.guard(self.selected_id, "Select a booking first"):
            return
        if messagebox.askyesno("Confirm", "Delete this booking and its payments?"):
            try:
                db.delete_booking(self.selected_id)
                self.ok("Deleted"); self.clear(); self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))


# ======================================================================
#  PAYMENTS
# ======================================================================
class PaymentTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "Payment Management")
        self.cb_book = self.combo(0, 0, "Booking", [], 22)
        self.e_amt = self.entry(0, 1, "Amount", 14)
        self.cb_method = self.combo(0, 2, "Method",
                                    ["Cash", "Card", "UPI", "Net Banking"], 14)
        self.e_date = self.entry(1, 0, "Payment Date", 22)
        self.cb_status = self.combo(1, 1, "Status", ["Paid", "Pending", "Refunded"], 14)
        tk.Button(self.form, text="Auto-Calculate Bill", bg=ACCENT, fg="white",
                  font=FONT_B, relief="flat", padx=12, pady=4,
                  command=self.auto_bill).grid(row=1, column=5, sticky="w")
        self.e_date.insert(0, str(date.today()))
        self.cb_status.set("Paid")

        self.buttons([("Add", self.add, "#2e7d32"), ("Update", self.update, "#1565c0"),
                      ("Delete", self.delete, "#c62828"),
                      ("Clear", self.clear, MUTED), ("Refresh", self.refresh, PRIMARY)])
        self.make_table(("ID", "Booking ID", "Guest", "Amount", "Method",
                         "Date", "Status"), (60, 100, 200, 120, 130, 120, 110))
        self.bookings = {}
        self.refresh()

    def refresh(self):
        self.bookings = {label: bid for bid, label in db.get_booking_choices()}
        self.cb_book["values"] = list(self.bookings.keys())
        self.fill(db.get_payments())

    def auto_bill(self):
        b = self.cb_book.get()
        if not self.guard(b, "Select a booking first"):
            return
        amt = db.get_booking_amount(self.bookings[b])
        self.e_amt.delete(0, "end"); self.e_amt.insert(0, f"{amt:.2f}")

    def on_select(self, _):
        r = self.current_row()
        if not r:
            return
        self.selected_id = r[0]
        for label, bid in self.bookings.items():
            if str(bid) == str(r[1]):
                self.cb_book.set(label); break
        self.e_amt.delete(0, "end"); self.e_amt.insert(0, r[3])
        self.cb_method.set(r[4])
        self.e_date.delete(0, "end"); self.e_date.insert(0, r[5])
        self.cb_status.set(r[6])

    def clear(self):
        self.selected_id = None
        self.cb_book.set(""); self.cb_method.set("")
        self.e_amt.delete(0, "end")
        self.e_date.delete(0, "end"); self.e_date.insert(0, str(date.today()))
        self.cb_status.set("Paid")

    def read(self):
        b, m, s = self.cb_book.get(), self.cb_method.get(), self.cb_status.get()
        if not self.guard(b and m and s, "Booking, method and status are required"):
            return None
        try:
            amt = float(self.e_amt.get())
        except ValueError:
            self.guard(False, "Amount must be a number")
            return None
        if not self.guard(amt >= 0, "Amount cannot be negative"):
            return None
        d = valid_date(self.e_date.get())
        if not self.guard(d, "Date must be YYYY-MM-DD"):
            return None
        return self.bookings[b], amt, m, d, s

    def add(self):
        v = self.read()
        if not v:
            return
        try:
            db.add_payment(*v); self.ok("Payment recorded"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update(self):
        if not self.guard(self.selected_id, "Select a row first"):
            return
        v = self.read()
        if not v:
            return
        try:
            db.update_payment(self.selected_id, *v)
            self.ok("Payment updated"); self.clear(); self.refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if not self.guard(self.selected_id, "Select a row first"):
            return
        if messagebox.askyesno("Confirm", "Delete this payment?"):
            try:
                db.delete_payment(self.selected_id)
                self.ok("Deleted"); self.clear(); self.refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e))


# ======================================================================
#  REPORTS
# ======================================================================
class ReportTab(ttk.Frame):
    REPORTS = {
        "Room Availability by Type":
            (db.report_room_availability,
             ("Room Type", "Total", "Available", "Occupied", "Maintenance")),
        "Revenue by Payment Method":
            (db.report_revenue_by_method,
             ("Method", "Transactions", "Total Collected", "Average")),
        "Guest Booking Summary":
            (db.report_top_guests,
             ("Guest", "Phone", "Bookings", "Total Nights")),
        "Pending Payments":
            (db.report_pending_payments,
             ("Payment ID", "Booking ID", "Guest", "Amount", "Date")),
    }

    def __init__(self, parent):
        super().__init__(parent)
        tk.Label(self, text="Reports", font=FONT_H, bg=BG, fg=PRIMARY).pack(
            anchor="w", padx=14, pady=(12, 8))
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=14)
        tk.Label(bar, text="Select report:", font=FONT_B, bg=BG).pack(side="left")
        self.cb = ttk.Combobox(bar, values=list(self.REPORTS.keys()), font=FONT,
                               width=34, state="readonly")
        self.cb.pack(side="left", padx=8)
        self.cb.current(0)
        tk.Button(bar, text="Generate", bg=PRIMARY, fg="white", font=FONT_B,
                  relief="flat", padx=16, pady=5,
                  command=self.generate).pack(side="left")

        self.wrap = tk.Frame(self, bg=BG)
        self.wrap.pack(fill="both", expand=True, padx=14, pady=12)
        self.tree = None

    def generate(self):
        name = self.cb.get()
        func, cols = self.REPORTS[name]
        if self.tree:
            self.tree.destroy()
        self.tree = ttk.Treeview(self.wrap, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=180, anchor="w")
        self.tree.pack(fill="both", expand=True)
        try:
            for row in func():
                self.tree.insert("", "end", values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh(self):
        pass


# ======================================================================
if __name__ == "__main__":
    LoginWindow().mainloop()
