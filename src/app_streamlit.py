"""
app_streamlit.py  -  Front-End (Streamlit web UI)
Hotel Management System | 22AIE303 DBMS Project

Run:   streamlit run app_streamlit.py
Login: admin / admin123

Note: this file replaces app.py only. database.py and the MySQL schema
are unchanged - the same data-access layer serves both front ends.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from decimal import Decimal

import database as db

# ======================================================================
#  PALETTES
# ======================================================================
PALETTES = {
    "Eucalyptus & Oat": {
        "bg":      "#F2F4F0",   # barely-green off white  (page)
        "surface": "#FFFFFF",   # cards
        "tint":    "#DDE7DF",   # pastel block            (headers, chips)
        "ink":     "#22403A",   # deep eucalyptus         (text, nav)
        "ink_sub": "#5C7169",   # muted text
        "accent":  "#B08344",   # warm brass              (primary action)
        "line":    "#D3DCD5",
    },
    "Wisteria & Chalk": {
        "bg":      "#F4F2F7",
        "surface": "#FFFFFF",
        "tint":    "#E2DDEC",
        "ink":     "#332B4A",
        "ink_sub": "#6B6382",
        "accent":  "#7C6BA8",
        "line":    "#DAD4E4",
    },
    "Harbour & Sand": {
        "bg":      "#F3F1EC",
        "surface": "#FFFFFF",
        "tint":    "#DCE4E8",
        "ink":     "#1F3D4C",
        "ink_sub": "#5E7683",
        "accent":  "#C0714B",
        "line":    "#D6DBD9",
    },
}

# Status colours are deliberately OUTSIDE the palette - they must mean
# the same thing whichever theme is selected.
STATUS = {
    "Available":   ("#E4F0E4", "#2F6B3F"),
    "Occupied":    ("#FBE9E4", "#A8452F"),
    "Maintenance": ("#FBF1DC", "#8A6416"),
    "Booked":      ("#E6EEF7", "#2A557F"),
    "Checked-In":  ("#E4F0E4", "#2F6B3F"),
    "Checked-Out": ("#EDEDED", "#5A5A5A"),
    "Cancelled":   ("#FBE9E4", "#A8452F"),
    "Paid":        ("#E4F0E4", "#2F6B3F"),
    "Pending":     ("#FBF1DC", "#8A6416"),
    "Refunded":    ("#EDEDED", "#5A5A5A"),
    "Admin":       ("#E6EEF7", "#2A557F"),
    "Receptionist":("#EDEDED", "#5A5A5A"),
}


def css(P):
    return f"""
<style>
  .stApp {{ background:{P['bg']}; }}
  section[data-testid="stSidebar"] {{ background:{P['ink']}; }}
  section[data-testid="stSidebar"] * {{ color:#FFFFFF !important; }}
  section[data-testid="stSidebar"] .stRadio label {{
      font-size:0.95rem; padding:2px 0; }}

  h1,h2,h3 {{ color:{P['ink']} !important; font-weight:700;
      letter-spacing:-0.01em; }}
  .stApp, .stApp p, .stApp label, .stApp div {{ color:{P['ink']}; }}

  .page-head {{ font-size:1.9rem; font-weight:700; color:{P['ink']};
      margin:0 0 .1rem 0; }}
  .page-sub  {{ font-size:.92rem; color:{P['ink_sub']}; margin:0 0 1.1rem 0; }}

  .card {{ background:{P['surface']}; border:1px solid {P['line']};
      border-radius:10px; padding:16px 18px; }}
  .metric {{ background:{P['surface']}; border:1px solid {P['line']};
      border-radius:10px; padding:16px 18px; height:100%; }}
  .metric .v {{ font-size:1.85rem; font-weight:700; color:{P['ink']};
      line-height:1.15; }}
  .metric .l {{ font-size:.8rem; color:{P['ink_sub']};
      text-transform:uppercase; letter-spacing:.06em; margin-top:2px; }}
  .metric .b {{ height:3px; width:34px; background:{P['accent']};
      border-radius:2px; margin-bottom:10px; }}

  .sect {{ background:{P['tint']}; border-radius:8px; padding:8px 14px;
      font-weight:700; color:{P['ink']}; font-size:.95rem;
      margin:.2rem 0 .8rem 0; }}

  .stButton>button {{ background:{P['accent']}; color:#FFFFFF;
      border:none; border-radius:7px; font-weight:600; padding:.45rem 1.1rem; }}
  .stButton>button:hover {{ filter:brightness(.92); color:#FFFFFF; }}
  .stFormSubmitButton>button {{ background:{P['accent']}; color:#FFFFFF;
      border:none; border-radius:7px; font-weight:600; }}
  .stFormSubmitButton>button:hover {{ filter:brightness(.92); color:#FFFFFF; }}

  div[data-testid="stDataFrame"] {{ border:1px solid {P['line']};
      border-radius:8px; }}
  .stTextInput input, .stNumberInput input, .stDateInput input {{
      border-radius:6px; }}
  header[data-testid="stHeader"] {{ background:transparent; }}
  div[data-testid="stToolbar"], div[data-testid="stDecoration"],
  #MainMenu, footer {{ display:none !important; }}
  .block-container {{ padding-top:2.2rem; max-width:1250px; }}
</style>
"""


def head(title, sub=""):
    st.markdown(f'<div class="page-head">{title}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="page-sub">{sub}</div>', unsafe_allow_html=True)


def sect(text):
    st.markdown(f'<div class="sect">{text}</div>', unsafe_allow_html=True)


def badge_html(v):
    bg, fg = STATUS.get(str(v), ("#EDEDED", "#5A5A5A"))
    return (f'<span style="background:{bg};color:{fg};padding:2px 9px;'
            f'border-radius:11px;font-size:.78rem;font-weight:600;">{v}</span>')


def table(rows, cols, status_col=None, money_cols=()):
    """Render rows as a styled dataframe."""
    if not rows:
        st.info("No records yet.")
        return None
    df = pd.DataFrame(rows, columns=cols)
    for c in money_cols:
        if c in df.columns:
            df[c] = df[c].apply(lambda v: f"Rs {float(v):,.2f}")
    st.dataframe(df, use_container_width=True, hide_index=True)
    return df


def ok(msg):
    st.session_state["_flash"] = ("success", msg)


def err(msg):
    st.session_state["_flash"] = ("error", msg)


def show_flash():
    f = st.session_state.pop("_flash", None)
    if f:
        (st.success if f[0] == "success" else st.error)(f[1])


# ======================================================================
#  LOGIN
# ======================================================================
def login_page(P):
    st.markdown(
        f"""<div style="max-width:420px;margin:6vh auto 0 auto;text-align:center">
          <div style="font-size:2.4rem;font-weight:800;color:{P['ink']};
               letter-spacing:-.02em">Hotel Management</div>
          <div style="font-size:.9rem;color:{P['ink_sub']};
               text-transform:uppercase;letter-spacing:.22em;margin-top:2px">
               22AIE303 &nbsp;&middot;&nbsp; DBMS</div>
          <div style="height:3px;width:52px;background:{P['accent']};
               border-radius:2px;margin:18px auto 0 auto"></div>
        </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.write("")
        with st.form("login", clear_on_submit=False):
            u = st.text_input("Username", value="admin")
            p = st.text_input("Password", type="password")
            go = st.form_submit_button("Sign in", use_container_width=True)
        if go:
            if not u or not p:
                st.error("Enter both username and password.")
            else:
                try:
                    row = db.authenticate(u.strip(), p.strip())
                except Exception as e:
                    st.error(f"Cannot reach the database. {e}")
                    return
                if row:
                    st.session_state.user = {"id": row[0], "name": row[1],
                                             "role": row[2]}
                    st.rerun()
                else:
                    st.error("Username or password is incorrect.")
        st.caption("Demo accounts — admin / admin123 · reception / admin123")


# ======================================================================
#  DASHBOARD
# ======================================================================
def page_dashboard():
    head("Dashboard", "Live figures, each from an aggregate query")
    s = db.dashboard_stats()
    cards = [("Total rooms", s["rooms"]), ("Available now", s["available"]),
             ("Registered guests", s["guests"]), ("Active bookings", s["active"]),
             ("Revenue collected", f"Rs {float(s['revenue']):,.0f}"),
             ("Payments pending", f"Rs {float(s['pending']):,.0f}")]
    for r in range(2):
        for col, (label, val) in zip(st.columns(3), cards[r * 3:r * 3 + 3]):
            col.markdown(
                f'<div class="metric"><div class="b"></div>'
                f'<div class="v">{val}</div><div class="l">{label}</div></div>',
                unsafe_allow_html=True)
        st.write("")

    st.write("")
    sect("Arrivals and departures today")
    today = str(date.today())
    rows = [b for b in db.get_bookings()
            if str(b[4]) == today or str(b[5]) == today]
    if rows:
        table([(b[0], b[1], b[2], b[4], b[5], b[9]) for b in rows],
              ["ID", "Guest", "Room", "Check-in", "Check-out", "Status"])
    else:
        st.info("Nothing scheduled for today.")

    sect("Occupancy by room type")
    ra = db.report_room_availability()
    if ra:
        df = pd.DataFrame(ra, columns=["Room type", "Total", "Available",
                                       "Occupied", "Maintenance"])
        st.bar_chart(df.set_index("Room type")[["Available", "Occupied"]],
                     height=260, color=["#8CBF9A", "#D99B86"])


# ======================================================================
#  ROOM TYPES
# ======================================================================
def page_room_types():
    head("Room types", "Tariff lives here once, not on every room — this is what keeps the schema in 3NF")
    show_flash()
    rows = db.get_room_types()

    sect("Add a room type")
    with st.form("rt_add", clear_on_submit=True):
        c = st.columns([2, 1, 1, 1])
        name = c[0].text_input("Type name")
        cap = c[1].number_input("Capacity", 1, 10, 2)
        price = c[2].number_input("Price per night", 1.0, 100000.0, 1800.0,
                                  step=100.0)
        c[3].write("")
        c[3].write("")
        if c[3].form_submit_button("Add type", use_container_width=True):
            if not name.strip():
                err("Type name is required.")
            else:
                try:
                    db.add_room_type(name.strip(), int(cap), float(price))
                    ok(f"Added room type “{name.strip()}”.")
                except Exception as e:
                    err(f"Could not add. A type with that name may already exist. ({e})")
            st.rerun()

    sect("All room types")
    table(rows, ["ID", "Room type", "Capacity", "Price per night"],
          money_cols=["Price per night"])

    if rows:
        sect("Edit or remove")
        labels = {f"{r[1]}  (ID {r[0]})": r for r in rows}
        pick = st.selectbox("Select a room type", list(labels), key="rt_pick")
        r = labels[pick]
        c = st.columns([2, 1, 1, 1, 1])
        n2 = c[0].text_input("Type name", value=r[1], key="rt_n")
        c2 = c[1].number_input("Capacity", 1, 10, int(r[2]), key="rt_c")
        p2 = c[2].number_input("Price per night", 1.0, 100000.0,
                               float(r[3]), step=100.0, key="rt_p")
        c[3].write("")
        c[3].write("")
        c[4].write("")
        c[4].write("")
        if c[3].button("Save changes", use_container_width=True):
            try:
                db.update_room_type(r[0], n2.strip(), int(c2), float(p2))
                ok("Room type updated.")
            except Exception as e:
                err(f"Could not update. ({e})")
            st.rerun()
        if c[4].button("Delete", use_container_width=True):
            try:
                db.delete_room_type(r[0])
                ok("Room type deleted.")
            except Exception as e:
                err("Cannot delete — rooms of this type still exist. "
                    "That is the ON DELETE RESTRICT foreign key doing its job.")
            st.rerun()


# ======================================================================
#  ROOMS
# ======================================================================
def page_rooms():
    head("Rooms", "Room inventory and current status")
    show_flash()
    types = {t[1]: t[0] for t in db.get_room_types()}
    rows = db.get_rooms()

    if not types:
        st.warning("Add at least one room type first.")
        return

    sect("Add a room")
    with st.form("rm_add", clear_on_submit=True):
        c = st.columns([1, 1.4, 1, 1.2, 1])
        num = c[0].text_input("Room number")
        tname = c[1].selectbox("Room type", list(types))
        floor = c[2].number_input("Floor", 0, 50, 1)
        status = c[3].selectbox("Status", ["Available", "Occupied", "Maintenance"])
        c[4].write("")
        c[4].write("")
        if c[4].form_submit_button("Add room", use_container_width=True):
            if not num.strip():
                err("Room number is required.")
            else:
                try:
                    db.add_room(num.strip(), types[tname], int(floor), status)
                    ok(f"Added room {num.strip()}.")
                except Exception as e:
                    err("Could not add — that room number already exists. "
                        "The UNIQUE constraint blocked it.")
            st.rerun()

    sect("All rooms")
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Room", "Type", "Floor",
                                         "Price", "Status"])
        df["Price"] = df["Price"].apply(lambda v: f"Rs {float(v):,.0f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        sect("Edit or remove")
        labels = {f"Room {r[1]}  ·  {r[2]}": r for r in rows}
        pick = st.selectbox("Select a room", list(labels), key="rm_pick")
        r = labels[pick]
        c = st.columns([1, 1.4, 1, 1.2, .9, .9])
        n2 = c[0].text_input("Room number", value=r[1], key="rm_n")
        t2 = c[1].selectbox("Room type", list(types),
                            index=list(types).index(r[2]) if r[2] in types else 0,
                            key="rm_t")
        f2 = c[2].number_input("Floor", 0, 50, int(r[3]), key="rm_f")
        s2 = c[3].selectbox("Status", ["Available", "Occupied", "Maintenance"],
                            index=["Available", "Occupied",
                                   "Maintenance"].index(r[5]), key="rm_s")
        for i in (4, 5):
            c[i].write("")
            c[i].write("")
        if c[4].button("Save", use_container_width=True):
            try:
                db.update_room(r[0], n2.strip(), types[t2], int(f2), s2)
                ok("Room updated.")
            except Exception as e:
                err(f"Could not update. ({e})")
            st.rerun()
        if c[5].button("Delete", use_container_width=True):
            try:
                db.delete_room(r[0])
                ok("Room deleted.")
            except Exception:
                err("Cannot delete — bookings reference this room.")
            st.rerun()


# ======================================================================
#  GUESTS
# ======================================================================
def page_guests():
    head("Guests", "Guest register with search")
    show_flash()

    sect("Register a guest")
    with st.form("g_add", clear_on_submit=True):
        c = st.columns(3)
        fn = c[0].text_input("First name")
        ln = c[1].text_input("Last name")
        gender = c[2].selectbox("Gender", ["Male", "Female", "Other"])
        c = st.columns(3)
        phone = c[0].text_input("Phone (10 digits)")
        email = c[1].text_input("Email")
        idp = c[2].selectbox("ID proof", ["Aadhaar", "Passport",
                                          "Driving License", "Voter ID"])
        c = st.columns([2, 1, 1])
        addr = c[0].text_input("Address")
        idn = c[1].text_input("ID number")
        c[2].write("")
        c[2].write("")
        if c[2].form_submit_button("Register guest", use_container_width=True):
            if not fn.strip() or not phone.strip() or not idn.strip():
                err("First name, phone and ID number are required.")
            elif not (phone.strip().isdigit() and len(phone.strip()) == 10):
                err("Phone must be exactly 10 digits.")
            elif email.strip() and ("@" not in email or "." not in email):
                err("That email address does not look valid.")
            else:
                try:
                    db.add_guest(fn.strip(), ln.strip(), gender, phone.strip(),
                                 email.strip(), addr.strip(), idp, idn.strip())
                    ok(f"Registered {fn.strip()} {ln.strip()}.")
                except Exception:
                    err("Could not register — that phone number or ID is "
                        "already on file. The UNIQUE constraint blocked it.")
            st.rerun()

    sect("Guest register")
    q = st.text_input("Search by name, phone, email or ID number",
                      placeholder="Start typing…", key="g_q")
    rows = db.search_guests(q.strip()) if q.strip() else db.get_guests()
    if q.strip():
        st.caption(f"{len(rows)} match(es) — SELECT … WHERE … LIKE across five columns")
    table(rows, ["ID", "First name", "Last name", "Gender", "Phone",
                 "Email", "Address", "ID proof", "ID number"])

    if rows:
        sect("Edit or remove")
        labels = {f"{r[1]} {r[2]}  ·  {r[4]}": r for r in rows}
        pick = st.selectbox("Select a guest", list(labels), key="g_pick")
        r = labels[pick]
        c = st.columns(3)
        fn2 = c[0].text_input("First name", value=r[1], key="g_fn")
        ln2 = c[1].text_input("Last name", value=r[2] or "", key="g_ln")
        gd2 = c[2].selectbox("Gender", ["Male", "Female", "Other"],
                             index=["Male", "Female", "Other"].index(r[3]),
                             key="g_gd")
        c = st.columns(3)
        ph2 = c[0].text_input("Phone", value=r[4], key="g_ph")
        em2 = c[1].text_input("Email", value=r[5] or "", key="g_em")
        ip2 = c[2].selectbox("ID proof", ["Aadhaar", "Passport",
                                          "Driving License", "Voter ID"],
                             index=["Aadhaar", "Passport", "Driving License",
                                    "Voter ID"].index(r[7]), key="g_ip")
        c = st.columns([2, 1, .8, .8])
        ad2 = c[0].text_input("Address", value=r[6] or "", key="g_ad")
        in2 = c[1].text_input("ID number", value=r[8], key="g_in")
        for i in (2, 3):
            c[i].write("")
            c[i].write("")
        if c[2].button("Save", use_container_width=True):
            try:
                db.update_guest(r[0], fn2.strip(), ln2.strip(), gd2, ph2.strip(),
                                em2.strip(), ad2.strip(), ip2, in2.strip())
                ok("Guest updated.")
            except Exception as e:
                err(f"Could not update. ({e})")
            st.rerun()
        if c[3].button("Delete", use_container_width=True):
            try:
                db.delete_guest(r[0])
                ok("Guest deleted, along with their bookings (ON DELETE CASCADE).")
            except Exception as e:
                err(f"Could not delete. ({e})")
            st.rerun()


# ======================================================================
#  BOOKINGS
# ======================================================================
def page_bookings():
    head("Bookings", "Availability is checked with a date-overlap subquery before anything is saved")
    show_flash()

    guests = {lbl: gid for gid, lbl in db.get_guest_choices()}
    if not guests:
        st.warning("Register a guest first.")
        return

    sect("New booking")
    c = st.columns([2, 1, 1, 1])
    gpick = c[0].selectbox("Guest", list(guests), key="b_g")
    cin = c[1].date_input("Check-in", value=date.today(), key="b_ci")
    cout = c[2].date_input("Check-out", value=date.today() + timedelta(days=1),
                           key="b_co")
    pax = c[3].number_input("Guests", 1, 10, 1, key="b_px")

    if cout <= cin:
        st.error("Check-out must be after check-in. The CHECK constraint on the "
                 "table enforces this at the database level too.")
        return

    free = db.get_available_rooms(cin, cout)
    if not free:
        st.warning("No rooms are free for those dates.")
        return

    nights = (cout - cin).days
    fl = {f"Room {r[1]}  ·  {r[2]}  ·  Rs {float(r[3]):,.0f}/night": r
          for r in free}
    c = st.columns([2, 1, 1])
    rpick = c[0].selectbox(f"Available rooms ({len(free)} free for these dates)",
                           list(fl), key="b_r")
    room = fl[rpick]
    total = nights * float(room[3])
    c[1].markdown(f'<div class="metric"><div class="b"></div>'
                  f'<div class="v">{nights}</div><div class="l">Nights</div></div>',
                  unsafe_allow_html=True)
    c[2].markdown(f'<div class="metric"><div class="b"></div>'
                  f'<div class="v">Rs {total:,.0f}</div>'
                  f'<div class="l">Amount payable</div></div>',
                  unsafe_allow_html=True)
    st.write("")
    if st.button("Confirm booking"):
        if not db.is_room_free(room[0], cin, cout):
            err("That room was taken for those dates. Nothing was saved.")
        else:
            try:
                bid = db.add_booking(guests[gpick], room[0], cin, cout,
                                     int(pax), date.today(), "Booked")
                ok(f"Booking #{bid} confirmed — Rs {total:,.2f} payable.")
            except Exception as e:
                err(f"Could not save the booking. ({e})")
        st.rerun()

    sect("All bookings")
    q = st.text_input("Search by guest, room or status", key="b_q",
                      placeholder="Start typing…")
    rows = db.search_bookings(q.strip()) if q.strip() else db.get_bookings()
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Guest", "Room", "Type",
                                         "Check-in", "Check-out", "Nights",
                                         "Amount", "Pax", "Status"])
        df["Amount"] = df["Amount"].apply(lambda v: f"Rs {float(v):,.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        sect("Manage a booking")
        labels = {f"#{r[0]}  ·  {r[1]}  ·  Room {r[2]}  ·  {r[9]}": r
                  for r in rows}
        pick = st.selectbox("Select a booking", list(labels), key="b_pick")
        r = labels[pick]
        c = st.columns(5)
        for i in range(5):
            c[i].write("")
        if c[0].button("Check in", use_container_width=True):
            db.set_booking_status(r[0], "Checked-In")
            ok(f"Booking #{r[0]} checked in. A trigger set the room to Occupied.")
            st.rerun()
        if c[1].button("Check out", use_container_width=True):
            db.set_booking_status(r[0], "Checked-Out")
            ok(f"Booking #{r[0]} checked out. A trigger released the room.")
            st.rerun()
        if c[2].button("Cancel", use_container_width=True):
            db.set_booking_status(r[0], "Cancelled")
            ok(f"Booking #{r[0]} cancelled.")
            st.rerun()
        if c[3].button("Delete", use_container_width=True):
            try:
                db.delete_booking(r[0])
                ok("Booking deleted, along with its payments.")
            except Exception as e:
                err(f"Could not delete. ({e})")
            st.rerun()


# ======================================================================
#  PAYMENTS
# ======================================================================
def page_payments():
    head("Payments", "Bill amount is computed by a three-table join, not typed in by hand")
    show_flash()

    bookings = {lbl: bid for bid, lbl in db.get_booking_choices()}
    if not bookings:
        st.warning("Create a booking first.")
        return

    sect("Record a payment")
    c = st.columns([2, 1, 1])
    bpick = c[0].selectbox("Booking", list(bookings), key="p_b")
    suggested = float(db.get_booking_amount(bookings[bpick]) or 0)
    amt = c[1].number_input("Amount", 0.0, 1000000.0, suggested, step=100.0,
                            key="p_a")
    method = c[2].selectbox("Method", ["Cash", "Card", "UPI", "Net Banking"],
                            key="p_m")
    c = st.columns([1, 1, 2])
    pdate = c[0].date_input("Payment date", value=date.today(), key="p_d")
    pstat = c[1].selectbox("Status", ["Paid", "Pending", "Refunded"], key="p_s")
    st.caption(f"Bill for this booking is Rs {suggested:,.2f} "
               f"(nights × price per night, from the join).")
    if st.button("Record payment"):
        try:
            db.add_payment(bookings[bpick], float(amt), method, pdate, pstat)
            ok(f"Payment of Rs {float(amt):,.2f} recorded.")
        except Exception as e:
            err(f"Could not record the payment. ({e})")
        st.rerun()

    sect("All payments")
    rows = db.get_payments()
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Booking", "Guest", "Amount",
                                         "Method", "Date", "Status"])
        df["Amount"] = df["Amount"].apply(lambda v: f"Rs {float(v):,.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

        sect("Edit or remove")
        labels = {f"#{r[0]}  ·  {r[2]}  ·  Rs {float(r[3]):,.0f}  ·  {r[6]}": r
                  for r in rows}
        pick = st.selectbox("Select a payment", list(labels), key="p_pick")
        r = labels[pick]
        c = st.columns([1, 1.2, 1, .8, .8])
        a2 = c[0].number_input("Amount", 0.0, 1000000.0, float(r[3]),
                               step=100.0, key="p_a2")
        m2 = c[1].selectbox("Method", ["Cash", "Card", "UPI", "Net Banking"],
                            index=["Cash", "Card", "UPI",
                                   "Net Banking"].index(r[4]), key="p_m2")
        s2 = c[2].selectbox("Status", ["Paid", "Pending", "Refunded"],
                            index=["Paid", "Pending",
                                   "Refunded"].index(r[6]), key="p_s2")
        for i in (3, 4):
            c[i].write("")
            c[i].write("")
        if c[3].button("Save", use_container_width=True):
            try:
                db.update_payment(r[0], r[1], float(a2), m2, r[5], s2)
                ok("Payment updated.")
            except Exception as e:
                err(f"Could not update. ({e})")
            st.rerun()
        if c[4].button("Delete", use_container_width=True):
            try:
                db.delete_payment(r[0])
                ok("Payment deleted.")
            except Exception as e:
                err(f"Could not delete. ({e})")
            st.rerun()


# ======================================================================
#  REPORTS
# ======================================================================
REPORTS = {
    "Occupancy by room type": (
        db.report_room_availability,
        ["Room type", "Total", "Available", "Occupied", "Maintenance"],
        "COUNT with SUM(CASE …) grouped by room type."),
    "Revenue by payment method": (
        db.report_revenue_by_method,
        ["Method", "Transactions", "Total collected", "Average"],
        "COUNT, SUM and AVG grouped by payment method, filtered to Paid."),
    "Guest booking summary": (
        db.report_top_guests,
        ["Guest", "Phone", "Bookings", "Total nights"],
        "GROUP BY with HAVING, ordered by booking count."),
    "Pending payments": (
        db.report_pending_payments,
        ["Payment ID", "Booking ID", "Guest", "Amount", "Date"],
        "Join across payments, bookings and guests, filtered to Pending."),
}


def page_reports():
    head("Reports", "Each report is one aggregate query")
    name = st.selectbox("Report", list(REPORTS))
    func, cols, explain = REPORTS[name]
    st.caption(explain)
    rows = func()
    if not rows:
        st.info("No data for this report yet.")
        return
    df = pd.DataFrame(rows, columns=cols)
    for c in df.columns:
        if c in ("Total collected", "Average", "Amount"):
            df[c] = df[c].apply(lambda v: f"Rs {float(v):,.2f}")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if name == "Occupancy by room type":
        st.bar_chart(pd.DataFrame(rows, columns=cols)
                     .set_index("Room type")[["Available", "Occupied"]],
                     height=280, color=["#8CBF9A", "#D99B86"])
    if name == "Revenue by payment method":
        d = pd.DataFrame(rows, columns=cols)
        d["Total collected"] = d["Total collected"].astype(float)
        st.bar_chart(d.set_index("Method")[["Total collected"]], height=280,
                     color="#8FA9B8")


# ======================================================================
#  MAIN
# ======================================================================
def main():
    st.set_page_config(page_title="Hotel Management System",
                       page_icon="H", layout="wide")

    # The radio widget's own key is the single source of truth, so the CSS
    # emitted at the top of this run already reflects the latest click.
    theme = st.session_state.get("theme_pick", "Eucalyptus & Oat")
    P = PALETTES[theme]
    st.markdown(css(P), unsafe_allow_html=True)

    if "user" not in st.session_state:
        with st.sidebar:
            st.markdown("### Appearance")
            st.radio("Palette", list(PALETTES),
                     index=list(PALETTES).index(theme), key="theme_pick")
        login_page(P)
        return

    u = st.session_state.user
    with st.sidebar:
        st.markdown(
            f"""<div style="padding:6px 0 14px 0">
              <div style="font-size:1.25rem;font-weight:700">Hotel Management</div>
              <div style="font-size:.72rem;letter-spacing:.18em;opacity:.75;
                   text-transform:uppercase">22AIE303 · DBMS</div>
            </div>""", unsafe_allow_html=True)

        page = st.radio("Go to", ["Dashboard", "Room types", "Rooms", "Guests",
                                  "Bookings", "Payments", "Reports"],
                        label_visibility="collapsed")
        st.divider()
        st.markdown(f"**{u['name']}** · {u['role']}")
        if st.button("Sign out"):
            st.session_state.pop("user")
            st.rerun()
        st.divider()
        st.caption("Palette")
        st.radio("Palette", list(PALETTES),
                 index=list(PALETTES).index(theme),
                 label_visibility="collapsed", key="theme_pick")

    try:
        {"Dashboard": page_dashboard, "Room types": page_room_types,
         "Rooms": page_rooms, "Guests": page_guests, "Bookings": page_bookings,
         "Payments": page_payments, "Reports": page_reports}[page]()
    except Exception as e:
        st.error(f"Database error: {e}")
        st.caption("Check that MySQL is running and db_config.py has the "
                   "right password.")


if __name__ == "__main__":
    main()
