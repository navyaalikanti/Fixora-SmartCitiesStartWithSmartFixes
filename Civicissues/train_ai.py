import pandas as pd
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from collections import Counter
from datetime import datetime, timedelta

# File paths
ISSUES_FILE = "issues.json"  # Ensure this matches your data file
AI_PREDICTIONS_FILE = "ai_predictions.json"
MIN_ISSUES_FOR_PREDICTION = 10  # Minimum issues per pincode to make a prediction

# Map categories to human-friendly messages
CATEGORY_MESSAGES = {
    "Road / Potholes": "Potholes may increase due to rainy season.",
    "Garbage / Waste": "Garbage is likely to accumulate; timely disposal recommended.",
    "Streetlight / Broken": "Streetlights may fail; maintenance might be needed.",
    "Water / Leakage": "Water supply may face leakages or interruptions due to aging pipelines or seasonal effects.",
    "Electricity / Power Cut": "Electricity may be disrupted in this area, especially during rainy/maintenance periods.",
    "Traffic / Transport": "Traffic congestion may increase during peak hours.",
    "Pollution": "Pollution levels might rise; caution advised.",
    "Public Facility / Park": "Public facility issues or park wear-and-tear may be reported."
}

# ------------------- Helper Functions ------------------- #
def load_data(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                return {}
    return {}

def save_data(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

def flatten_issues(all_issues_data):
    """Flattens the dictionary of issues into a single list."""
    flattened = []
    if isinstance(all_issues_data, dict):
        for issues_list in all_issues_data.values():
            if isinstance(issues_list, list):
                flattened.extend(issues_list)
    return flattened

def preprocess_data(issues):
    """Prepares the data for the AI model."""
    data = []
    for issue in issues:
        if issue.get("pincode") and issue.get("category") and issue.get("date") and issue.get("priority"):
            try:
                date_obj = datetime.strptime(issue["date"], "%Y-%m-%d")
                data.append({
                    'pincode': issue['pincode'],
                    'day_of_week': date_obj.weekday(),
                    'month': date_obj.month,
                    'category': issue['category'],
                    'priority': issue['priority']
                })
            except ValueError:
                continue
    return pd.DataFrame(data)

# ------------------- Main Training and Prediction Function ------------------- #
def train_and_predict():
    """Trains the model and generates future predictions."""
    print("Starting AI model training and prediction...")
    all_issues_data = load_data(ISSUES_FILE)
    issues = flatten_issues(all_issues_data)

    if not issues:
        print("No issues found to train the model.")
        save_data(AI_PREDICTIONS_FILE, [])
        return []

    df = preprocess_data(issues)

    if df.empty:
        print("No valid data for training after preprocessing.")
        save_data(AI_PREDICTIONS_FILE, [])
        return []

    # Get a list of pincodes with enough issues to be relevant
    pincode_counts = df['pincode'].value_counts()
    relevant_pincodes = pincode_counts[pincode_counts >= MIN_ISSUES_FOR_PREDICTION].index.tolist()
    df = df[df['pincode'].isin(relevant_pincodes)]
    
    if df.empty:
        print(f"Not enough issues found (min={MIN_ISSUES_FOR_PREDICTION}) to train the model.")
        save_data(AI_PREDICTIONS_FILE, [])
        return []

    # Prepare data for the model
    X = df[['pincode', 'day_of_week', 'month']].copy()
    y = df['category']
    
    # Convert categorical pincode to numerical representation
    X['pincode_code'] = X['pincode'].astype('category').cat.codes
    pincode_mapping = dict(enumerate(X['pincode'].astype('category').cat.categories))
    
    X = X[['pincode_code', 'day_of_week', 'month']]
    
    # Train the RandomForestClassifier model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    # Generate predictions for the next 3 days
    upcoming_predictions = []
    today = datetime.now()
    
    for pincode_code, pincode_str in pincode_mapping.items():
        pincode_issues = df[df['pincode'] == pincode_str]

        # Generate predictions for the next 3 days for this pincode
        for i in range(1, 4):  # Predict for the next 3 days
            future_date = today + timedelta(days=i)
            future_data = pd.DataFrame([{
                'pincode_code': pincode_code,
                'day_of_week': future_date.weekday(),
                'month': future_date.month
            }])
            
            # Predict the category
            predicted_category = model.predict(future_data)[0]
            
            # Determine priority based on past data
            priority_counts = pincode_issues[pincode_issues['category'] == predicted_category]['priority'].value_counts()
            predicted_priority = priority_counts.idxmax() if not priority_counts.empty else "Low"

            # Get human-friendly description
            description = CATEGORY_MESSAGES.get(predicted_category, f"{predicted_category} may occur due to past trends.")

            # Append the prediction to the list
            upcoming_predictions.append({
                "pincode": pincode_str,
                "predicted_issue": predicted_category,
                "expected_date": future_date.strftime("%Y-%m-%d"),
                "description": description,
                "priority": predicted_priority,
                "upvotes": 0
            })
    
    # Save the new predictions
    save_data(AI_PREDICTIONS_FILE, upcoming_predictions)
    print(f"✅ AI predictions updated! {len(upcoming_predictions)} predictions generated.")
    return upcoming_predictions

if __name__ == "__main__":
    train_and_predict()