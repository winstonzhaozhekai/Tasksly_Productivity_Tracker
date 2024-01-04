import os
import re
import json
from datetime import datetime, timedelta
from flask import Flask, flash, redirect, render_template, request, session, jsonify
import sqlite3
import bcrypt
from helpers import suggest_alternate_usernames, password_has_number, password_has_uppercase, login_required, update_streaks

# Generate salt 
salt = bcrypt.gensalt()

# Generate a secret key
secret_key = os.urandom(24)

# Create the Flask app
app = Flask(__name__)

# Set the secret key
app.config['SECRET_KEY'] = secret_key

# Configure database
db = sqlite3.connect("tasksly.db", check_same_thread=False)
db.row_factory = sqlite3.Row

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route('/login', methods=["GET", "POST"])
def login():
    # Forget current session user id
    session.clear()

    if request.method == "POST":
        # Check all fields are filled in 
        if not request.form.get("username"):
            flash("Username required", "error")
            return render_template("login.html")
        elif not request.form.get("password"):
            flash("Password required", "error")
            return render_template("login.html")
        
        # Search database if there is username
        username = request.form.get("username")
        cursor = db.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchall()

        # Check if there is only one of that username and password is correct 
        password = request.form.get("password").encode('utf-8')
        hashed_password = bcrypt.hashpw(password, row[0]["salt"])
        stored_hashed = bcrypt.hashpw(row[0]["hash"], row[0]["salt"])
        if len(row) != 1 or not bcrypt.checkpw(hashed_password, stored_hashed):
            flash("Invalid username and/or password", "error")
            return render_template("login.html")
        
        # Remember which user has logged in
        if len(row) == 1:
            session["user_id"] = row[0]["id"]
            # Redirect user to homepage
            return redirect("/")
        else:
            flash("Error loggin in. Please try again", "error")
            return render_template("login.html")
    else:
        return render_template("login.html")


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Check all fields are filled in 
        if not request.form.get("username"):
            flash("Username required", "error")
            return render_template("register.html")
        elif not request.form.get("password"):
            flash("Password required", "error")
            return render_template("register.html")
        elif not request.form.get("confirmation"):
            flash("Please confirm your Password", "error")
            return render_template("register.html")
        
        # Check username is at least 5 characters long 
        username = request.form.get("username")
        if len(username) < 5: 
            flash("Please choose an username with at least 5 characters", "error")
            return render_template("register.html")
        
        # Check that password and confirmation matches 
        password = request.form.get("password")
        if password != request.form.get("confirmation"):
            flash("Passwords do not match", "error")
            return render_template("register.html", last_username=username)

        # Check that password meets requirements (At least 8 characters long, One caps, One number)
        if len(password) < 8:
            flash("Please choose a password with at least 8 characters, one uppercased letter and a number", "error")
            return render_template("register.html", last_username=username)
        elif password_has_uppercase(password) == False:
            flash("Please choose a password with at least 8 characters, one uppercased letter and a number", "error")
            return render_template("register.html", last_username=username)
        elif password_has_number(password) == False:
            flash("Please choose a password with at least 8 characters, one uppercased letter and a number", "error")
            return render_template("register.html", username=username)
        
        # Check that username is not taken 
        cursor = db.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            # If username is taken, suggest 3 alternate usernames for the user
            username = row["username"]
            alternate_usernames = suggest_alternate_usernames(username)
            flash("That username has already been taken, here are some alternatives: ", "error")
            for i in range(3):
                if i < 2:
                    flash(f"{alternate_usernames[i]},")
                if i == 2:
                    flash(alternate_usernames[i])
            
            return render_template("register.html")
        
        # Generate hashed password to store in database
        password = request.form.get("password").encode('utf-8')
        hashed = bcrypt.hashpw(password, salt)

        # Insert user into database
        try:
            db.execute("INSERT INTO users (username, hash, salt) VALUES (?, ?, ?)", (username, hashed, salt,))
            db.commit()  
        except Exception as e:
            flash(f"Database insertion error: {e}", "error")
            return render_template("register.html")

        # Log in user and remember the user's session
        cursor = db.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row is not None:
            session["user_id"] = int(row["id"])
            return redirect("/")
        else:
            flash("Trouble uploading data. Please try again", "error")
            return render_template("register.html", last_username=username)

    else:
        return render_template("register.html")
    
@app.route('/')
@login_required
def index():
    cursor = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    row = cursor.fetchone()
    cursor = db.execute("SELECT * FROM tasks WHERE user_id = ?", (session["user_id"],))
    tasks = cursor.fetchall()
    if row: 
        user = row["username"]

        # Display latest 3 focus sessions
        query = """
        SELECT history.id, tasks.task, history.duration_hours, history.duration_minutes, history.duration_seconds, history.time
        FROM history
        JOIN tasks ON history.task_id = tasks.id
        WHERE history.user_id = ? 
        ORDER BY time DESC LIMIT 3
        """
        cursor = db.execute(query, (session["user_id"],))
        history = cursor.fetchall()

        # Calculate the duration left of each task for the day
        duration_left = []
        cursor = db.execute("SELECT * FROM tasks WHERE user_id = ?", (session["user_id"],))
        task_duration = cursor.fetchall()

        for task in task_duration:
            hours = task["goal_hours"]
            minutes = task["goal_minutes"]
            seconds = hours * 3600 + minutes * 60
            duration_left.append({"id": task["id"], "duration": seconds})

        today_date = datetime.now()
        start_of_day = today_date.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
        end_of_day = start_of_day + timedelta(days=1) - timedelta(microseconds=1)

        query = """
        SELECT tasks.id, tasks.task, history.duration_hours, history.duration_minutes, history.duration_seconds, history.time
        FROM history
        JOIN tasks ON history.task_id = tasks.id
        WHERE history.user_id = ? AND history.time >= ? AND history.time <= ?
        """
        cursor = db.execute(query, (session["user_id"], start_of_day, end_of_day,))
        today_records = cursor.fetchall()

        for record in today_records:
            for task_dict in duration_left:
                if record["id"] == task_dict["id"]:
                    task_dict["duration"] -= (record["duration_hours"] * 3600 + record["duration_minutes"] * 60 + record["duration_seconds"])
                    if task_dict["duration"] < 0:
                        task_dict["duration"] = 0

        # Calculate how many tasks remaining for the day and total duration remaining
        counter_tasks = 0
        total_duration_left = 0
        for task_dict in duration_left:
            if task_dict["duration"] > 0:
                total_duration_left += task_dict["duration"]
                counter_tasks += 1

        return render_template("index.html", user=user, tasks=tasks, history=history, duration_left=duration_left, counter_tasks=counter_tasks, total_duration_left=total_duration_left)
    else:
        flash("Error loading page", "error")
        return render_template("index.html", tasks=tasks)
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/focus', methods=["POST", "GET"])
@login_required
def focus():
    if request.method == "POST":
        # Check if field is filled up
        if not request.form.get("task"):
            flash("Please choose a task", "error")
            return redirect("/focus")

        # Check if user has the task
        task = request.form.get("task")
        cursor = db.execute("SELECT * FROM tasks WHERE user_id = ? AND task = ?", (session["user_id"], task,))
        match = cursor.fetchone()
        if not match:
            flash("You do not have this task", "error")
            return redirect("/focus")
        
        # If user has the task, select it and redirect to focusing page
        elif match:
            task = match["task"]
            return render_template("focusing.html", task=task)
        
    else:
        cursor = db.execute("SELECT * FROM tasks WHERE user_id = ?", (session["user_id"],))
        tasks = cursor.fetchall()
        return render_template("focus.html", tasks=tasks)

@app.route('/history')
@login_required
def history():
    query = """
    SELECT history.id, tasks.task, history.duration_hours, history.duration_minutes, history.duration_seconds, history.time
    FROM history
    JOIN tasks ON history.task_id = tasks.id
    WHERE history.user_id = ?
    ORDER BY history.time DESC
    """
    history = db.execute(query, (session["user_id"],))

    today_date = datetime.now().date()
    query = """
    SELECT history.id
    FROM history
    JOIN tasks ON history.task_id = tasks.id
    WHERE history.user_id = ? AND DATE(history.time) = ?
    """
    cursor = db.execute(query, (session["user_id"], today_date,))
    today_history = [row["id"] for row in cursor.fetchall()]
    return render_template("history.html", history=history, today_history=today_history)

@app.route('/tasks', methods=["POST", "GET"])
@login_required
def tasks():
    if request.method == "POST":
        # Check if field is filled up
        if not request.form.get("task"):
            flash("Please enter a task", "error")
            return redirect("/tasks")
        elif not request.form.get("goal"):
            flash("Please set a goal", "error")
            return redirect("/tasks")
        
        # Check if user already has the task
        task = request.form.get("task").title()
        cursor = db.execute("SELECT * FROM tasks WHERE user_id = ? AND task = ?", (session["user_id"], task,))
        match = cursor.fetchone()
        if match:
            flash("You already have added this task", "error")
            return redirect("/tasks")
        
        # Check if user entered goal in the correct format (hh:mm)
        goal = request.form.get("goal")
        pattern = r'^(0[0-9]|1[0-9]|2[0-3]|24):[0-5][0-9]$'
        if not re.match(pattern, goal):
            flash("Please input your goal in the format of hh:mm", "error")
            return redirect("/tasks")

        # Add task into database 
        hours, minutes = goal.split(":")
        hours = int(hours)
        minutes = int(minutes)
        try:
            db.execute("INSERT INTO tasks (user_id, task, goal_hours, goal_minutes) VALUES (?, ?, ?, ?)", (session["user_id"], task, hours, minutes,))
            db.commit()
            flash("Task successfully added!", "success")
            return redirect("/tasks")
        except Exception as e:
            flash(f"Database insertion error: {e}", "error")
            redirect("/tasks")
        
    else:
        cursor = db.execute("SELECT * FROM tasks WHERE user_id = ?", (session["user_id"],))
        tasks = cursor.fetchall()
        return render_template("tasks.html", tasks=tasks)

@app.route('/streaks')
@login_required
def streaks():
    cursor = db.execute("SELECT * FROM tasks WHERE user_id = ?", (session["user_id"],))
    tasks = cursor.fetchall()

    # Calculate the longest streak from today for each task

    cursor = db.execute("SELECT * FROM tasks WHERE user_id = ?", (session["user_id"],))
    task_ids = [row["id"] for row in cursor.fetchall()]
    dict = []
    today_date = datetime.now().date()

    for task_id in task_ids:
        cursor = db.execute("SELECT date FROM streaks WHERE user_id = ? AND task_id = ? AND completed = ? ORDER BY date DESC LIMIT 1",(session["user_id"],task_id, 1,))
        latest_streak_date_row = cursor.fetchone()
        streak_length = 0

        if latest_streak_date_row:
            latest_streak_date_str = latest_streak_date_row["date"]
            latest_streak_date = datetime.strptime(latest_streak_date_str, "%Y-%m-%d")
            latest_streak_date_str = latest_streak_date.strftime("%Y-%m-%d")
            today_date_str = today_date.strftime("%Y-%m-%d")

            if latest_streak_date_str == today_date_str:
                streak_length = 1

                while True:
                    previous_date = latest_streak_date - timedelta(days = 1)
                    previous_date_str = previous_date.strftime("%Y-%m-%d")
                    cursor = db.execute("SELECT completed FROM streaks WHERE user_id = ? AND task_id = ? AND date = ?",(session["user_id"],task_id, previous_date_str,))
                    previous_streak = cursor.fetchone()

                    if previous_streak and previous_streak["completed"] == 1:
                        streak_length += 1
                        latest_streak_date = previous_date
                    else:
                        break

        streak_dict = {"id": task_id, "streak_length": streak_length}
        dict.append(streak_dict)

    # Calculate the longest streak in number of days with every task completed

    cursor = db.execute("SELECT date FROM day_streaks WHERE user_id = ? AND completed = ? ORDER BY date DESC LIMIT 1",(session["user_id"], 1,))
    latest_day_streaks_row = cursor.fetchone()
    day_streaks_length = 0

    if latest_day_streaks_row:
        latest_streak_date_str = latest_day_streaks_row["date"]
        latest_streak_date = datetime.strptime(latest_streak_date_str, "%Y-%m-%d")
        latest_streak_date_str = latest_streak_date.strftime("%Y-%m-%d")
        today_date_str = today_date.strftime("%Y-%m-%d")

        if latest_streak_date_str == today_date_str:
                day_streaks_length = 1

                while True:
                    previous_date = latest_streak_date - timedelta(days = 1)
                    previous_date_str = previous_date.strftime("%Y-%m-%d")
                    cursor = db.execute("SELECT completed FROM day_streaks WHERE user_id = ? AND date = ?",(session["user_id"], previous_date_str,))
                    previous_streak = cursor.fetchone()

                    if previous_streak and previous_streak["completed"] == 1:
                        day_streaks_length += 1
                        latest_streak_date = previous_date
                    else:
                        break
        
    return render_template("streaks.html", tasks=tasks, dict=dict, day_streaks_length=day_streaks_length)


@app.route('/delete_task', methods=["POST"])
@login_required
def delete_task():
    id = request.form.get("id")
    cursor = db.execute("SELECT * FROM tasks WHERE user_id = ? AND id = ?", (session["user_id"], id,))
    row = cursor.fetchall()

    if len(row) == 1:
        try:
            db.execute("DELETE FROM tasks WHERE user_id = ? AND id = ?", (session["user_id"], id,))
            db.commit()
            flash("Task deleted successfully", "success")
            return redirect("/tasks")
        except Exception as e:
            flash("Error deleting task: " + str(e), "error")
            return redirect("/tasks")
    else: 
        flash("Error deleting task, please try again", "error")
        return redirect("/tasks")
    

@app.route('/delete_history', methods=["POST"])
@login_required
def delete_history():
    id = request.form.get("id")
    cursor = db.execute("SELECT * FROM history WHERE user_id = ? AND id = ?", (session["user_id"], id,))
    row = cursor.fetchall()

    if len(row) == 1:
        task_id = row[0]["task_id"]
        try:
            db.execute("DELETE FROM history WHERE user_id = ? AND id = ?", (session["user_id"], id,))
            db.commit()

            update_streaks(session["user_id"], task_id)

            flash("Session deleted successfully", "success")
            return redirect("/history")
        except Exception as e:
            flash("Error deleting session: " + str(e), "error")
            return redirect("/history")
    else: 
        flash("Error deleting session, please try again", "error")
        return redirect("/history")


@app.route('/focusing')
@login_required
def focusing():
    if request.referrer and "/focus" in request.referrer:
        return render_template("focusing.html")
    else:
        return redirect("/focus")

@app.route('/save_timer', methods=["POST"])
@login_required
def save_timer():
    data = request.json
    if data:
        timer_state = data.get("timerState")
        task = data.get("task").strip()
        time = datetime.now()
        formatted_time = time.strftime("%Y-%m-%d %H:%M")

        if timer_state is not None:
            hours = timer_state.get("hours")
            minutes = timer_state.get("minutes")
            seconds = timer_state.get("seconds")
        else:
            hours = 0
            minutes = 0
            seconds = 0
        
        cursor = db.execute("SELECT * FROM tasks WHERE user_id = ? and task = ?", (session["user_id"], task,))
        task_id = int(cursor.fetchone()["id"])

        try:
            db.execute("INSERT INTO history (user_id, task_id, duration_hours, duration_minutes, duration_seconds, time) VALUES (?, ?, ?, ?, ?, ?)", (session["user_id"], task_id, hours, minutes, seconds, formatted_time))
            db.commit()
            flash("Focus session successfully logged!", "success")
        except Exception as e:
            flash("Error logging session: " + str(e), "error")

        update_streaks(session["user_id"], task_id)

        response_data = {"message": "Focus session successfully logged!", "task": task, "duration_hours": hours, "duration_minutes": minutes, "duration_seconds": seconds}
        return jsonify(response_data), 200
    else:
        return jsonify({"error": "Invalid data"}), 400
    
@app.route('/edit_task', methods=["POST"])
@login_required
def edit():
    data = request.json
    if data:
        task_id = int(data.get("taskId"))
        new_goal = data.get("editedGoal")
        
        hours_part = new_goal.split("H")
        minutes_part = hours_part[1].split("M")

        new_goal_hours = int(hours_part[0])
        new_goal_minutes = int(minutes_part[0])
        
        try:
            db.execute("UPDATE tasks SET goal_hours = ?, goal_minutes = ? WHERE user_id = ? AND id = ?", (new_goal_hours, new_goal_minutes, session["user_id"], task_id,))
            db.commit()

            update_streaks(session["user_id"], task_id)

            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": "Error editing goal: " + str(e)}), 500
        
    else:
        return jsonify({"error": "Invalid data"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=8000)