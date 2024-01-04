from flask import redirect, session, flash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

db = sqlite3.connect("tasksly.db", check_same_thread=False)
db.row_factory = sqlite3.Row

def suggest_alternate_usernames(username):
    suggestions = []
    current = username

    # Suggesting alternate usernames by adding numbers behind current username 
    for i in range(1, 10):
        suggestion = f"{current}{i}"
        cursor = db.execute("SELECT * FROM users WHERE username = ?", (suggestion,))
        suggested_match = cursor.fetchone()
        if not suggested_match:
            suggestions.append(suggestion)

    # If there are not 3 available alternate usernames already, suggest more by changing capitalisation
    while len(suggestions) < 3:
        for i in range(len(current)):
            char = current[i]
            # Check if chosen is a character
            if char.isalpha():
                # Check if current character is uppercased or lowercased and change 
                if char.isupper():
                    modified = current[:i] + char.lower() + current[i + 1:]
                elif char.islower():
                    modified = current[:i] + char.upper() + current[i + 1:]

                if modified not in suggestions:
                    cursor = db.execute("SELECT * FROM users WHERE username = ?", (modified,))
                    suggested_match = cursor.fetchone()
                    if not suggested_match:
                        suggestions.append(modified)
    
    return suggestions

def password_has_uppercase(password):
    for i in range(len(password)):
        if password[i].isupper():
            return True
    return False


def password_has_number(password):
    for i in range(len(password)):
        if password[i].isdigit():
            return True
    return False


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def update_streaks(user_id, task_id):

    # Check if task has already been added into streaks by using task_id

    today_date = datetime.now().date()
    cursor = db.execute("SELECT * FROM streaks WHERE user_id = ? AND task_id = ? AND DATE(date) = ?", (user_id, task_id, today_date,))
    row = cursor.fetchone()
    if not row:
        try:
            db.execute("INSERT INTO streaks (user_id, task_id, date, completed) VALUES (?, ?, ?, ?)", (user_id, task_id, today_date, 0,))
            db.commit()
        except Exception as e:
            flash(f"Error inserting into streaks table: {e}", "error")
    
    # Check if task has been completed after changes and update streaks table accordingly

    cursor = db.execute("SELECT * FROM history WHERE user_id = ? AND task_id = ? AND DATE(time) = ?",(user_id, task_id, today_date))
    history_of_task_today = cursor.fetchall()
    total_in_seconds_of_task_today = 0 

    for row in history_of_task_today:
        total_in_seconds_of_task_today += row["duration_hours"] * 3600 + row["duration_minutes"] * 60 + row["duration_seconds"]  
    
    cursor = db.execute("SELECT * FROM tasks WHERE user_id = ? AND id = ?",(user_id, task_id,))
    goal_of_task_now = cursor.fetchone()
    goal_in_seconds_of_task_now = goal_of_task_now["goal_hours"] * 3600 + goal_of_task_now["goal_minutes"] * 60

    if total_in_seconds_of_task_today >= goal_in_seconds_of_task_now:
        try:
            db.execute("UPDATE streaks SET completed = ? WHERE user_id = ? AND task_id = ? AND DATE(date) = ?",(1, user_id, task_id, today_date,))
            db.commit()
        except Exception as e:
            flash(f"Error updating streaks table: {e}", "error")
    elif total_in_seconds_of_task_today < goal_in_seconds_of_task_now:
        try:
            db.execute("UPDATE streaks SET completed = ? WHERE user_id = ? AND task_id = ? AND DATE(date) = ?",(0, user_id, task_id, today_date,))
            db.commit()
        except Exception as e:
            flash(f"Error updating streaks table: {e}", "error")

    update_day_streaks(user_id)


def update_day_streaks(user_id):
    
    # Add today into table if there is yet to be one
    
    today_date = datetime.now().date()
    cursor = db.execute("SELECT * FROM day_streaks WHERE user_id = ? AND date = ?", (user_id, today_date,))
    row = cursor.fetchone()

    if not row:
        # Calculate how many tasks there are
        cursor = db.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,))
        no_of_tasks = len(cursor.fetchall())
        try:
            db.execute("INSERT INTO day_streaks (user_id, date, no_of_tasks, completed) VALUES (?, ?, ?, ?)", (user_id, today_date, no_of_tasks, 0))
            db.commit()
        except Exception as e:
            flash(f"Error inserting into day_streaks table: {e}", "error")
        
    # Check if number of tasks has changed
    cursor = db.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,))
    no_of_tasks = len(cursor.fetchall())

    cursor = db.execute("SELECT * FROM day_streaks WHERE user_id = ? AND DATE(date) = ?", (user_id, today_date,))
    stored_no_of_tasks = cursor.fetchone()["no_of_tasks"]

    if stored_no_of_tasks != no_of_tasks:

        # Update day_streaks table

        try:
            db.execute("UPDATE day_streaks SET no_of_tasks = ? WHERE user_id = ? AND date = ?",(no_of_tasks, user_id, today_date,))
            db.commit()
        except Exception as e:
            flash(f"Error updating day_streaks table: {e}", "error")

    # Check if all the tasks today have been completed 
    cursor = db.execute("SELECT * FROM streaks WHERE user_id = ? AND date = ? AND completed = ?", (user_id, today_date, 1,))
    no_of_tasks_completed = len(cursor.fetchall())

    if no_of_tasks_completed == no_of_tasks:
        try:
            db.execute("UPDATE day_streaks SET completed = ? WHERE user_id = ? AND date = ?",(1, user_id, today_date,))
            db.commit()
        except Exception as e:
            flash(f"Error updating day_streaks table: {e}", "error")
    else:
        try:
            db.execute("UPDATE day_streaks SET completed = ? WHERE user_id = ? AND date = ?",(0, user_id, today_date,))
            db.commit()
        except Exception as e:
            flash(f"Error updating day_streaks table: {e}", "error")

    
