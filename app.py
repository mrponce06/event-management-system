import sqlite3
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__, template_folder="pages", static_folder="resources")
app.secret_key = "event_system_secret_key"


def get_db_connection():
  conn = sqlite3.connect("database.db")
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            venue TEXT NOT NULL,
            capacity INTEGER NOT NULL
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            participant_id INTEGER NOT NULL,
            attendance_status TEXT DEFAULT 'Registered',
            FOREIGN KEY (event_id) REFERENCES events (event_id),
            FOREIGN KEY (participant_id) REFERENCES participants (participant_id),
            UNIQUE(event_id, participant_id)
        )
    """)
  conn.commit()
  conn.close()


init_db()


@app.route("/")
def index():
  conn = get_db_connection()
  total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
  total_participants = conn.execute(
      "SELECT COUNT(*) FROM participants"
  ).fetchone()[0]
  total_registrations = conn.execute(
      "SELECT COUNT(*) FROM registrations"
  ).fetchone()[0]
  conn.close()
  return render_template(
      "index.html",
      total_events=total_events,
      total_participants=total_participants,
      total_registrations=total_registrations,
  )


# --- EVENTS CRUD (May Validation para sa 3 Conditions) ---
@app.route("/events", methods=["GET", "POST"])
def manage_events():
  conn = get_db_connection()
  if request.method == "POST":
    title = request.form["title"].strip()
    event_date = request.form["event_date"]
    venue = request.form["venue"].strip()
    capacity = request.form["capacity"]

    try:
      # Condition 1: Same title, same date, same venue (Dapat bawal)
      exact_match = conn.execute(
          "SELECT * FROM events WHERE title = ? AND event_date = ? AND venue"
          " = ?",
          (title, event_date, venue),
      ).fetchone()

      # Condition 3: Different title, pero same date at same venue (Dapat bawal - Venue conflict)
      venue_date_conflict = conn.execute(
          "SELECT * FROM events WHERE event_date = ? AND venue = ? AND title !="
          " ?",
          (event_date, venue, title),
      ).fetchone()

      if exact_match:
        flash(
            "Error: An event with the exact same title, date, and venue"
            " already exists!",
            "danger",
        )
      elif venue_date_conflict:
        flash(
            "Error: The venue is already booked for another event on this"
            " date!",
            "danger",
        )
      else:
        # Condition 2: Same title, same date pero different venue, OR different date pero same venue (Tatanggapin)
        conn.execute(
            "INSERT INTO events (title, event_date, venue, capacity) VALUES"
            " (?, ?, ?, ?)",
            (title, event_date, venue, capacity),
        )
        conn.commit()
        flash("Event created successfully!", "success")
    except Exception as e:
      flash(f"Error creating event: {e}", "danger")
    finally:
      conn.close()
    return redirect(url_for("manage_events"))

  events = conn.execute("SELECT * FROM events").fetchall()
  conn.close()
  return render_template("events.html", events=events)


@app.route("/events/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
  conn = get_db_connection()
  if request.method == "POST":
    title = request.form["title"].strip()
    event_date = request.form["event_date"]
    venue = request.form["venue"].strip()
    capacity = request.form["capacity"]

    try:
      # Validation din para sa Edit
      exact_match = conn.execute(
          "SELECT * FROM events WHERE title = ? AND event_date = ? AND venue"
          " = ? AND event_id != ?",
          (title, event_date, venue, event_id),
      ).fetchone()

      venue_date_conflict = conn.execute(
          "SELECT * FROM events WHERE event_date = ? AND venue = ? AND title !="
          " ? AND event_id != ?",
          (event_date, venue, title, event_id),
      ).fetchone()

      if exact_match:
        flash(
            "Error: Another event with this exact title, date, and venue"
            " already exists!",
            "danger",
        )
      elif venue_date_conflict:
        flash(
            "Error: The venue is already booked for another event on this"
            " date!",
            "danger",
        )
      else:
        conn.execute(
            "UPDATE events SET title = ?, event_date = ?, venue = ?, capacity = ?"
            " WHERE event_id = ?",
            (title, event_date, venue, capacity, event_id),
        )
        conn.commit()
        flash("Event updated successfully!", "success")
    except Exception as e:
      flash(f"Error updating event: {e}", "danger")
    finally:
      conn.close()
    return redirect(url_for("manage_events"))

  event = conn.execute(
      "SELECT * FROM events WHERE event_id = ?", (event_id,)
  ).fetchone()
  conn.close()
  return render_template("edit_event.html", event=event)


@app.route("/events/delete/<int:event_id>", methods=["POST"])
def delete_event(event_id):
  conn = get_db_connection()
  try:
    conn.execute("DELETE FROM registrations WHERE event_id = ?", (event_id,))
    conn.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
    conn.commit()
    flash("Event deleted successfully.", "success")
  except Exception as e:
    flash(f"Error deleting event: {e}", "danger")
  finally:
    conn.close()
  return redirect(url_for("manage_events"))


# --- PARTICIPANTS CRUD ---
@app.route("/participants", methods=["GET", "POST"])
def manage_participants():
  conn = get_db_connection()
  if request.method == "POST":
    name = request.form["name"]
    contact = request.form["contact"]

    try:
      existing_name = conn.execute(
          "SELECT * FROM participants WHERE name = ?", (name,)
      ).fetchone()

      if existing_name:
        flash(
            "Error: A participant with this name already exists!", "danger"
        )
      else:
        conn.execute(
            "INSERT INTO participants (name, contact) VALUES (?, ?)",
            (name, contact),
        )
        conn.commit()
        flash("Participant registered successfully!", "success")
    except Exception as e:
      flash(f"Error registering participant: {e}", "danger")
    finally:
      conn.close()
    return redirect(url_for("manage_participants"))

  participants = conn.execute("SELECT * FROM participants").fetchall()
  conn.close()
  return render_template("participants.html", participants=participants)


@app.route("/participants/edit/<int:participant_id>", methods=["GET", "POST"])
def edit_participant(participant_id):
  conn = get_db_connection()
  if request.method == "POST":
    name = request.form["name"]
    contact = request.form["contact"]

    try:
      existing_name = conn.execute(
          "SELECT * FROM participants WHERE name = ? AND participant_id != ?",
          (name, participant_id),
      ).fetchone()

      if existing_name:
        flash("Error: Another participant already has this name!", "danger")
      else:
        conn.execute(
            "UPDATE participants SET name = ?, contact = ? WHERE participant_id"
            " = ?",
            (name, contact, participant_id),
        )
        conn.commit()
        flash("Participant updated successfully!", "success")
    except Exception as e:
      flash(f"Error updating participant: {e}", "danger")
    finally:
      conn.close()
    return redirect(url_for("manage_participants"))

  participant = conn.execute(
      "SELECT * FROM participants WHERE participant_id = ?", (participant_id,)
  ).fetchone()
  conn.close()
  return render_template("edit_participant.html", participant=participant)


@app.route("/participants/delete/<int:participant_id>", methods=["POST"])
def delete_participant(participant_id):
  conn = get_db_connection()
  try:
    conn.execute(
        "DELETE FROM registrations WHERE participant_id = ?", (participant_id,)
    )
    conn.execute("DELETE FROM participants WHERE participant_id = ?", (participant_id,))
    conn.commit()
    flash("Participant completely deleted from system.", "success")
  except Exception as e:
    flash(f"Error deleting participant: {e}", "danger")
  finally:
    conn.close()
  return redirect(url_for("manage_participants"))


# --- REGISTRATIONS & ATTENDANCE MANAGEMENT ---
@app.route("/registrations", methods=["GET", "POST"])
def manage_registrations():
  conn = get_db_connection()
  if request.method == "POST":
    event_id = request.form["event_id"]
    participant_id = request.form["participant_id"]
    selected_event = request.form.get("event_filter_state", "")
    selected_status = request.form.get("status_filter_state", "")

    try:
      event = conn.execute(
          "SELECT capacity FROM events WHERE event_id = ?", (event_id,)
      ).fetchone()
      current_regs = conn.execute(
          "SELECT COUNT(*) FROM registrations WHERE event_id = ?", (event_id,)
      ).fetchone()[0]

      if current_regs >= event["capacity"]:
        flash(
            "Registration failed: Event has already reached maximum capacity!",
            "danger",
        )
      else:
        try:
          conn.execute(
              "INSERT INTO registrations (event_id, participant_id,"
              " attendance_status) VALUES (?, ?, 'Registered')",
              (event_id, participant_id),
          )
          conn.commit()
          flash(
              "Participant successfully registered and added to slot!",
              "success",
          )
        except sqlite3.IntegrityError:
          flash(
              "Error: This participant is already registered for this event!",
              "warning",
          )
    except Exception as e:
      flash(f"Error during registration: {e}", "danger")
    finally:
      conn.close()

    return redirect(
        url_for(
            "manage_registrations",
            event_filter=selected_event,
            status_filter=selected_status,
        )
    )

  events = conn.execute("SELECT * FROM events").fetchall()
  participants = conn.execute("SELECT * FROM participants").fetchall()

  selected_event = request.args.get("event_filter", "")
  selected_status = request.args.get("status_filter", "")

  query = """
        SELECT R.registration_id, E.title AS event_title, E.event_date, E.venue, 
               P.name AS participant_name, R.attendance_status, E.event_id, P.participant_id
        FROM registrations R
        JOIN events E ON R.event_id = E.event_id
        JOIN participants P ON R.participant_id = P.participant_id
        WHERE 1=1
    """
  params = []

  if selected_event and selected_event != "":
    query += " AND E.event_id = ?"
    params.append(selected_event)

  if selected_status and selected_status != "":
    query += " AND R.attendance_status = ?"
    params.append(selected_status)

  registrations = conn.execute(query, params).fetchall()

  event_stats = None
  if selected_event and selected_event != "":
    event_info = conn.execute(
        "SELECT * FROM events WHERE event_id = ?", (selected_event,)
    ).fetchone()
    if event_info:
      total_capacity = event_info["capacity"]
      occupied = conn.execute(
          "SELECT COUNT(*) FROM registrations WHERE event_id = ?",
          (selected_event,),
      ).fetchone()[0]
      remaining = max(0, total_capacity - occupied)
      event_stats = {
          "title": event_info["title"],
          "capacity": total_capacity,
          "occupied": occupied,
          "remaining": remaining,
      }

  conn.close()
  return render_template(
      "registrations.html",
      events=events,
      participants=participants,
      registrations=registrations,
      selected_event=selected_event,
      selected_status=selected_status,
      event_stats=event_stats,
  )


@app.route(
    "/registrations/remove/<int:registration_id>", methods=["POST"]
)
def remove_registration(registration_id):
  selected_event = request.form.get("event_filter_state", "")
  selected_status = request.form.get("status_filter_state", "")

  conn = get_db_connection()
  try:
    conn.execute(
        "DELETE FROM registrations WHERE registration_id = ?", (registration_id,)
    )
    conn.commit()
    flash(
        "Participant successfully removed from this event slot (Record still"
        " exists in main participants list).",
        "success",
    )
  except Exception as e:
    flash(f"Error removing participant from event: {e}", "danger")
  finally:
    conn.close()

  return redirect(
      url_for(
          "manage_registrations",
          event_filter=selected_event,
          status_filter=selected_status,
      )
  )


@app.route(
    "/attendance/update/<int:registration_id>/<status>", methods=["POST"]
)
def update_attendance(registration_id, status):
  if status not in ["Present", "Absent", "Registered"]:
    flash("Invalid attendance status.", "danger")
    return redirect(url_for("manage_registrations"))

  selected_event = request.form.get("event_filter_state", "")
  selected_status = request.form.get("status_filter_state", "")

  conn = get_db_connection()
  try:
    conn.execute(
        "UPDATE registrations SET attendance_status = ? WHERE registration_id ="
        " ?",
        (status, registration_id),
    )
    conn.commit()
    flash(f"Attendance marked as {status}.", "success")
  except Exception as e:
    flash(f"Error updating attendance: {e}", "danger")
  finally:
    conn.close()

  return redirect(
      url_for(
          "manage_registrations",
          event_filter=selected_event,
          status_filter=selected_status,
      )
  )


# --- SEARCH & FILTER VIEW ---
@app.route("/search")
def search_system():
  query = request.args.get("q", "")
  conn = get_db_connection()
  try:
    events = conn.execute(
        "SELECT * FROM events WHERE title LIKE ? OR venue LIKE ?",
        (f"%{query}%", f"%{query}%"),
    ).fetchall()
    participants = conn.execute(
        "SELECT * FROM participants WHERE name LIKE ? OR contact LIKE ?",
        (f"%{query}%", f"%{query}%"),
    ).fetchall()
  finally:
    conn.close()
  return render_template(
      "search.html", query=query, events=events, participants=participants
  )


if __name__ == "__main__":
  app.run(debug=True)