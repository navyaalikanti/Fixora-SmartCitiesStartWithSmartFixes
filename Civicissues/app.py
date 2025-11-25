import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "super_secret_key" 

USERS_FILE = "users.json"
OFFICIALS_FILE = "officials.json"
ISSUES_FILE = "all_issues.json"
AI_PREDICTIONS_FILE = "ai_predictions.json"

# ------------------- Helper Functions ------------------- #
# ------------------- Helper Functions ------------------- #
def load_data(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            try:
                # Use a specific check for AI predictions file
                if file == AI_PREDICTIONS_FILE:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
                # Original logic for other files
                data = json.load(f)
                if file == ISSUES_FILE:
                    return data if isinstance(data, dict) else {}
                else:
                    return data if data else []
            except json.JSONDecodeError:
                return [] if file == AI_PREDICTIONS_FILE else {} if file == ISSUES_FILE else []
    
    # Return appropriate empty data structure if file doesn't exist
    return [] if file == AI_PREDICTIONS_FILE else {} if file == ISSUES_FILE else []

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ------------------- Public Routes ------------------- #
@app.route("/")
def home():
    user_email = session.get("user_email")
    official_email = session.get("official_email")
    user = None
    if user_email:
        users = load_data(USERS_FILE)
        user = next((u for u in users if u["email"] == user_email), None)
    elif official_email:
        officials = load_data(OFFICIALS_FILE)
        user = next((o for o in officials if o["email"] == official_email), None)
    return render_template("index.html", user=user)

@app.route("/create-account")
def create_account():
    return render_template("create_account.html")

@app.route("/user-register", methods=["GET", "POST"])
def user_register():
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        pincode = request.form.get("pincode", "")
        users = load_data(USERS_FILE)
        if any(u["email"] == email for u in users):
            return redirect(url_for("user_register"))
        users.append({
            "email": email,
            "username": username,
            "password": password,
            "pincode": pincode,
            "upvoted_issues": [],
            "upvoted_ai_predictions": []
        })
        save_data(USERS_FILE, users)
        return redirect(url_for("user_login"))
    return render_template("user_register.html")

@app.route("/govt-register", methods=["GET", "POST"])
def govt_register():
    if request.method == "POST":
        dept = request.form["dept"]
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        officials = load_data(OFFICIALS_FILE)
        if any(o["email"] == email for o in officials):
            return redirect(url_for("govt_register"))
        officials.append({"dept": dept, "name": name, "email": email, "password": password})
        save_data(OFFICIALS_FILE, officials)
        return redirect(url_for("govt_login"))
    return render_template("govt_register.html")

@app.route("/user_login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        users = load_data(USERS_FILE)
        user = next((u for u in users if u["email"] == email and u["password"] == password), None)
        if user:
            session["user_email"] = user["email"]
            return redirect(url_for("citizen_home"))

        return redirect(url_for("user_login"))
    return render_template("user_login.html")

@app.route("/govt_login", methods=["GET", "POST"])
def govt_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        officials = load_data(OFFICIALS_FILE)
        official = next((o for o in officials if o["email"] == email and o["password"] == password), None)
        if official:
            session["official_email"] = official["email"]
            return redirect(url_for("official_home"))

        return redirect(url_for("govt_login"))
    return render_template("govt_login.html")

# ------------------- Citizen Dashboard ------------------- #
@app.route("/citizen_home", methods=["GET", "POST"])
def citizen_home():
    user_email = session.get("user_email")
    if not user_email:
        return redirect(url_for("user_login"))
    
    users = load_data("users.json")
    user = next((u for u in users if u["email"] == user_email), None)
    if not user:
        return redirect(url_for("user_login"))

    user_pincode = user.get("pincode")
    all_ai_predictions = load_data("ai_predictions.json")
    all_issues_data = load_data("all_issues.json")
    flattened_issues = []
    if isinstance(all_issues_data, dict):
        for user_issues_list in all_issues_data.values():
            if isinstance(user_issues_list, list):
                flattened_issues.extend(user_issues_list)

    # Load user's issues for the "My Issues" section
    user_issues = []
    username_key_lower = f"{user['username'].lower()}_issues"
    if isinstance(all_issues_data, dict):
        for key in all_issues_data:
            if key.lower() == username_key_lower:
                user_issues = all_issues_data[key]
                if not isinstance(user_issues, list):
                    user_issues = []
                break

    # Filter AI predictions for the user's pincode
    if user_pincode:
        ai_predictions_to_upvote = [
            pred for pred in all_ai_predictions 
            if pred.get("pincode") == user_pincode
        ]
    else:
        ai_predictions_to_upvote = []

    issues_to_display = []
    heading = ""
    upvoted_issue_ids = user.get("upvoted_issues", [])
    upvoted_ai_prediction_ids = user.get("upvoted_ai_predictions", [])

    if request.method == "POST":
        # User entered a pincode to filter issues
        pincode = request.form.get("pincode")
        issues_to_display = [i for i in flattened_issues if i.get('pincode') == pincode]
        heading = f"Issues in pincode: {pincode}"
    else:
        # Default: show issues in user's area (matching user's pincode)
        if user_pincode:
            issues_to_display = [i for i in flattened_issues if i.get('pincode') == user_pincode]
            heading = "Issues in your area"

    return render_template(
        "citizen_home.html",
        user=user,
        ai_predictions_to_upvote=ai_predictions_to_upvote,
        issues_to_display=issues_to_display,
        issues_heading=heading,
        upvoted_issue_ids=upvoted_issue_ids,
        upvoted_ai_prediction_ids=upvoted_ai_prediction_ids,
        user_issues=user_issues
    )

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    
    return redirect(url_for("login"))

@app.route("/report_issue", methods=["POST"])
def report_issue():
    if 'user_email' not in session:
        
        return redirect(url_for("user_login"))
    
    user_email = session['user_email']
    users = load_data(USERS_FILE)
    user = next((u for u in users if u['email'] == user_email), None)
    
    if not user:
       
        return redirect(url_for("user_login"))

    title = request.form['title']
    description = request.form['description']
    pincode = request.form.get('pincode')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    category = request.form['category']
    priority = request.form['priority']
    anonymous = request.form.get('anonymous', 'no') == 'yes'
    photo = request.files.get('photo')
    photo_path = None
    
    if photo and photo.filename != "":
        photo_path = f"static/uploads/{photo.filename}"
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
        photo.save(photo_path)
        
    now = datetime.now()
    issue_date = now.strftime("%Y-%m-%d")
    issue_time = now.strftime("%H:%M:%S")
    issue_month = now.strftime("%B")
    
    issue = {
        "title": title,
        "description": description,
        "pincode": pincode,
        "location": {"lat": latitude, "lng": longitude},
        "category": category,
        "priority": priority,
        "photo": photo_path,
        "anonymous": anonymous,
        "upvotes": 0,
        "date": issue_date,
        "time": issue_time,
        "month": issue_month
    }
    
    user_file = f"{user['username']}_issues.json"
    user_issues = load_data(user_file)
    if not isinstance(user_issues, list):
        user_issues = []
    
    user_issues.append(issue)
    save_data(user_file, user_issues)
    
    all_issues = load_data(ISSUES_FILE)
    username_key = f"{user['username']}_issues"
    if username_key not in all_issues:
        all_issues[username_key] = []
    
    global_issue = issue.copy()
    global_issue["username"] = user['username']
    global_issue["status"] = "Pending"
    all_issues[username_key].append(global_issue)
    save_data(ISSUES_FILE, all_issues)

    return redirect(url_for("citizen_home"))

# app.py

# ... (all existing imports and helper functions) ...

@app.route("/view_my_issues")
def view_my_issues():
    user_email = session.get("user_email")
    if not user_email:
        return redirect(url_for("user_login"))

    users = load_data(USERS_FILE)
    user = next((u for u in users if u["email"] == user_email), None)

    if not user:
        return redirect(url_for("user_login"))

    # Load all issues from the central file
    all_issues = load_data(ISSUES_FILE)
    user_issues = []

    # Check if the data is a dictionary and contains the user's issues (case-insensitive key lookup)
    username_key_lower = f"{user['username'].lower()}_issues"
    if isinstance(all_issues, dict):
        for key in all_issues:
            if key.lower() == username_key_lower:
                user_issues = all_issues[key]
                if not isinstance(user_issues, list):
                    user_issues = []
                break

    return render_template("view_my_issues.html", user=user, issues=user_issues)

# ... (rest of your existing code) ...

@app.route("/increment_upvote", methods=["POST"])
def increment_upvote():
    if 'user_email' not in session:
        return redirect(url_for("user_login"))
    
    user_email = session.get("user_email")
    users = load_data(USERS_FILE)
    user = next((u for u in users if u["email"] == user_email), None)
    if not user:
        return redirect(url_for("user_login"))

    issue_title = request.form.get('issue_title')
    issue_pincode = request.form.get('issue_pincode')
    issue_username = request.form.get('issue_username')

    # Compose a unique identifier for the issue to track upvotes
    issue_id = f"{issue_title}__{issue_pincode}__{issue_username}"

    # Check if user has already upvoted this issue
    if "upvoted_issues" not in user:
        user["upvoted_issues"] = []

    if issue_id in user["upvoted_issues"]:
        # User already upvoted this issue, redirect
        return redirect(url_for("citizen_home"))

    # Increment upvotes in all_issues.json
    all_issues = load_data(ISSUES_FILE)
    if isinstance(all_issues, dict) and issue_username:
        username_key = f"{issue_username}_issues"
        if username_key in all_issues and isinstance(all_issues[username_key], list):
            for issue in all_issues[username_key]:
                if issue.get('title') == issue_title and issue.get('pincode') == issue_pincode:
                    issue['upvotes'] = issue.get('upvotes', 0) + 1
                    break
            save_data(ISSUES_FILE, all_issues)

    # Increment upvotes in user's own issues file
    if issue_username:
        user_file = f"{issue_username}_issues.json"
        user_issues = load_data(user_file)
        if isinstance(user_issues, list):
            for issue in user_issues:
                if issue.get('title') == issue_title and issue.get('pincode') == issue_pincode:
                    issue['upvotes'] = issue.get('upvotes', 0) + 1
                    break
            save_data(user_file, user_issues)

    # Add issue_id to user's upvoted_issues and save users.json
    user["upvoted_issues"].append(issue_id)
    save_data(USERS_FILE, users)

    flash("Upvoted successfully!", "success")
    return redirect(url_for("citizen_home"))

@app.route("/official_home")
def official_home():
    user_email = session.get("official_email")
    officials = load_data(OFFICIALS_FILE)
    user = next((o for o in officials if o["email"] == user_email), None)

    # Get category filter from query parameters
    selected_category = request.args.get('category', '')

    # --- Simplified AI Predictions loading ---
    ai_predictions = load_data(AI_PREDICTIONS_FILE)

    # Load and process all issues for the main dashboard and tables
    all_issues_data = load_data(ISSUES_FILE)
    cleaned_issues = []
    issue_markers = []
    # ... (rest of your existing logic for all_issues and issue_markers) ...

    if isinstance(all_issues_data, dict):
        for issues_list in all_issues_data.values():
            if isinstance(issues_list, list):
                for issue in issues_list:
                    if isinstance(issue, dict):
                        if "status" not in issue:
                            issue["status"] = "Pending"
                        cleaned_issues.append(issue)

                        if issue.get("location") and issue["location"].get("lat") and issue["location"].get("lng"):
                            try:
                                lat = float(issue["location"]["lat"])
                                lng = float(issue["location"]["lng"])
                                issue_markers.append({
                                    "lat": lat,
                                    "lng": lng,
                                    "title": issue.get("title", "N/A"),
                                    "description": issue.get("description", "N/A"),
                                    "upvotes": issue.get("upvotes", 0),
                                    "photo": issue.get("photo"),
                                    "category": issue.get("category", "N/A"),
                                    "priority": issue.get("priority", "N/A"),
                                    "status": issue.get("status", "Pending"),
                                    "username": issue.get("username", "Anonymous"),
                                    "pincode": issue.get("pincode", "N/A"),
                                    "date": issue.get("date", "N/A"),
                                    "time": issue.get("time", "N/A")
                                })
                            except (ValueError, TypeError):
                                continue

    # Filter issues by category if selected
    if selected_category:
        cleaned_issues = [issue for issue in cleaned_issues if issue.get('category') == selected_category]

    # Calculate total and high-priority issues for the dashboard cards (based on filtered issues)
    total_issues = len(cleaned_issues)
    high_priority_issues = sum(1 for i in cleaned_issues if i.get('priority', '').lower() == 'high')
    high_risk_areas = [p for p in ai_predictions if p.get('priority', '').lower() == 'high']

    return render_template(
        "official_home.html",
        user=user,
        ai_predictions=ai_predictions, # This will now be a proper list
        all_issues=cleaned_issues,
        total_issues=total_issues,
        high_priority_issues=high_priority_issues,
        high_risk_areas=high_risk_areas,
        issue_markers=issue_markers,
        selected_category=selected_category
    )

@app.route("/update_issue_status", methods=["POST"])
def update_issue_status():
    if 'official_email' not in session:
        
        return redirect(url_for('govt_login'))
    
    issue_title = request.form.get('issue_title')
    issue_pincode = request.form.get('issue_pincode')
    issue_username = request.form.get('issue_username')
    new_status = request.form.get('status')
    
    all_raw = load_data(ISSUES_FILE)
    updated = False
    
    if isinstance(all_raw, dict) and issue_username:
        username_key = f"{issue_username}_issues"
        if username_key in all_raw and isinstance(all_raw[username_key], list):
            for issue in all_raw[username_key]:
                if issue.get('title') == issue_title and issue.get('pincode') == issue_pincode:
                    issue['status'] = new_status
                    updated = True
                    break
    
    if updated:
        save_data(ISSUES_FILE, all_raw)
        flash("Issue status updated successfully!", "success")

    return redirect(url_for('official_home'))

@app.route('/train_ai', methods=['POST'])
def train_ai_route():
    if 'official_email' not in session:
        
        return redirect(url_for('govt_login'))
    
    from train_ai import train_and_predict
    
    preds = train_and_predict()
    flash("AI training completed successfully!", "success")
    return redirect(url_for('official_home'))

@app.route("/upvote_ai_prediction", methods=["POST"])
def upvote_ai_prediction():
    if 'user_email' not in session:
        
        return redirect(url_for("user_login"))

    # Extract data from the form
    predicted_issue = request.form.get("predicted_issue")
    pincode = request.form.get("pincode")
    expected_date = request.form.get("expected_date")

    # Load the full list of all AI predictions
    full_preds = load_data("ai_predictions.json")

    user_email = session.get("user_email")
    users = load_data(USERS_FILE)
    user = next((u for u in users if u["email"] == user_email), None)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("citizen_home"))

    # Compose a unique identifier for the AI prediction to track upvotes
    prediction_id = f"{predicted_issue}__{pincode}__{expected_date}"

    # Check if user has already upvoted this AI prediction
    if "upvoted_ai_predictions" not in user:
        user["upvoted_ai_predictions"] = []

    if prediction_id in user["upvoted_ai_predictions"]:
        return redirect(url_for("citizen_home"))

    updated = False
    
    # Iterate through the full list to find and update the correct prediction
    if isinstance(full_preds, list):
        for fp in full_preds:
            if (fp.get("predicted_issue") == predicted_issue and
                fp.get("pincode") == pincode and
                fp.get("expected_date") == expected_date):

                # Ensure 'upvotes' key exists and is an integer
                fp['upvotes'] = int(fp.get('upvotes', 0)) + 1
                updated = True
                break

    if updated:
        save_data("ai_predictions.json", full_preds)
        # Add prediction_id to user's upvoted_ai_predictions and save users.json
        user["upvoted_ai_predictions"].append(prediction_id)
        save_data(USERS_FILE, users)
        flash("AI prediction upvoted successfully!", "success")

    return redirect(url_for("citizen_home"))

@app.route("/update_status/<issue_title>", methods=["POST"])
def update_issue_status_route(issue_title):
    all_issues = load_data(ISSUES_FILE)
    updated = False
    
    if isinstance(all_issues, dict):
        for username_key, issues_list in all_issues.items():
            if isinstance(issues_list, list):
                for issue in issues_list:
                    if issue["title"] == issue_title:
                        issue["status"] = "Resolved" if issue.get("status") == "Pending" else "Pending"
                        updated = True
                        break
            if updated:
                break
    else:
        if isinstance(all_issues, list):
            for issue in all_issues:
                if issue["title"] == issue_title:
                    issue["status"] = "Resolved" if issue.get("status") == "Pending" else "Pending"
                    updated = True
                    break
    
    if updated:
        save_data(ISSUES_FILE, all_issues)
    return redirect(url_for("official_home"))

@app.route("/search_issues", methods=["POST"])
def search_issues():
    pincode = request.form.get("pincode")
    all_issues_data = load_data(ISSUES_FILE)
    flattened_issues = []
    
    if isinstance(all_issues_data, dict):
        for user_issues_list in all_issues_data.values():
            if isinstance(user_issues_list, list):
                flattened_issues.extend(user_issues_list)
    elif isinstance(all_issues_data, list):
        flattened_issues = all_issues_data

    issues_to_display = [i for i in flattened_issues if i.get('pincode') == pincode]
    return jsonify({"issues": issues_to_display})

if __name__ == "__main__":
    app.run(debug=True)