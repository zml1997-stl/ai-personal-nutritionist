import streamlit as st
import json
import os
import uuid
from datetime import datetime
import google.generativeai as genai

# Configure app
st.set_page_config(page_title="AI Nutritionist", layout="wide")

# Initialize session state variables if they don't exist
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'history' not in st.session_state:
    st.session_state.history = {}
if 'current_view' not in st.session_state:
    st.session_state.current_view = "login"
if 'current_plan' not in st.session_state:
    st.session_state.current_plan = None

# File path for saving meal plans
HISTORY_FILE = "meal_plan_history.json"

# User credentials (in a real app, this should be securely stored)
USERS = {
    "Zach": "ZML",
    "Mal": "MMM"
}

# Configure Gemini API
API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else None

# Function to configure Gemini
def configure_gemini():
    if not API_KEY:
        st.error("Please set your Gemini API key in Streamlit secrets.")
        return False
    
    try:
        genai.configure(api_key=API_KEY)
        return True
    except Exception as e:
        st.error(f"Error configuring Gemini API: {str(e)}")
        return False

# Load existing history
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                return history
        except Exception as e:
            st.error(f"Error loading history: {str(e)}")
    return {}

# Save history
def save_history(history):
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        st.error(f"Error saving history: {str(e)}")

# Function to generate meal plan
def generate_meal_plan(gluten_free, dairy_free, additional_info):
    if not configure_gemini():
        return "Error: Unable to configure Gemini API"

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        dietary_constraints = []
        if gluten_free:
            dietary_constraints.append("gluten-free")
        if dairy_free:
            dietary_constraints.append("dairy-free")
        
        constraints_text = ", ".join(dietary_constraints) if dietary_constraints else "No specific dietary restrictions"
        
        prompt = f"""
        Act as a professional nutritionist. Create a personalized meal plan with the following considerations:
        
        Dietary Restrictions: {constraints_text}
        Additional Information: {additional_info}
        
        Please provide a structured meal plan that includes:
        1. Breakfast options (3 suggestions)
        2. Lunch options (3 suggestions)
        3. Dinner options (3 suggestions)
        4. Snack options (3 suggestions)
        5. Nutritional insights about this plan
        6. Customized recommendations based on the provided information
        
        Format the response in markdown.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating meal plan: {str(e)}"

# Login function
def login(username, password):
    if username in USERS and USERS[username] == password:
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.current_view = "meal_planner"
        st.session_state.history = load_history()
        return True
    return False

# Logout function
def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.current_view = "login"

# Save meal plan
def save_meal_plan(meal_plan, preferences):
    if st.session_state.username not in st.session_state.history:
        st.session_state.history[st.session_state.username] = {}
    
    plan_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    st.session_state.history[st.session_state.username][plan_id] = {
        "timestamp": timestamp,
        "preferences": preferences,
        "meal_plan": meal_plan
    }
    
    save_history(st.session_state.history)
    return plan_id

# App layout and routing
def main():
    st.title("AI Nutritionist")
    
    # Navigation sidebar
    if st.session_state.authenticated:
        with st.sidebar:
            st.write(f"Logged in as: {st.session_state.username}")
            
            if st.button("Meal Planner"):
                st.session_state.current_view = "meal_planner"
                
            if st.button("History"):
                st.session_state.current_view = "history"
                
            if st.button("Logout"):
                logout()
    
    # Routing based on current view
    if not st.session_state.authenticated:
        render_login_page()
    elif st.session_state.current_view == "meal_planner":
        render_meal_planner()
    elif st.session_state.current_view == "history":
        render_history_page()
    elif st.session_state.current_view == "view_plan":
        render_view_plan()

# Login page
def render_login_page():
    st.header("Login")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")
        
        if login_button:
            if login(username, password):
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with col2:
        st.info("Welcome to the AI Nutritionist App")
        st.write("This application provides personalized meal planning based on your dietary preferences and needs.")

# Meal planner page
def render_meal_planner():
    st.header("Personalized Meal Planner")
    
    with st.form(key="meal_plan_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            gluten_free = st.checkbox("Gluten Free")
            dairy_free = st.checkbox("Dairy Free")
        
        additional_info = st.text_area(
            "Additional Information",
            placeholder="Example: high-protein, low sodium, lots of chicken, fruit, etc..."
        )
        
        submit_button = st.form_submit_button("Generate Meal Plan")
    
    if submit_button:
        with st.spinner("Generating your personalized meal plan..."):
            preferences = {
                "gluten_free": gluten_free,
                "dairy_free": dairy_free,
                "additional_info": additional_info
            }
            
            meal_plan = generate_meal_plan(gluten_free, dairy_free, additional_info)
            st.session_state.current_plan = {
                "meal_plan": meal_plan,
                "preferences": preferences
            }
    
    # Display current meal plan if it exists
    if st.session_state.current_plan:
        st.markdown(st.session_state.current_plan["meal_plan"])
        
        if st.button("Save This Meal Plan"):
            plan_id = save_meal_plan(
                st.session_state.current_plan["meal_plan"],
                st.session_state.current_plan["preferences"]
            )
            st.success(f"Meal plan saved successfully! ID: {plan_id}")

# History page
def render_history_page():
    st.header("Your Meal Plan History")
    
    if st.session_state.username not in st.session_state.history or not st.session_state.history[st.session_state.username]:
        st.info("You haven't saved any meal plans yet.")
        return
    
    user_history = st.session_state.history[st.session_state.username]
    
    # Show history as a table
    history_data = []
    for plan_id, plan_info in user_history.items():
        timestamp = plan_info.get("timestamp", "Unknown")
        preferences = plan_info.get("preferences", {})
        
        dietary_restrictions = []
        if preferences.get("gluten_free"):
            dietary_restrictions.append("Gluten-Free")
        if preferences.get("dairy_free"):
            dietary_restrictions.append("Dairy-Free")
        
        restrictions_text = ", ".join(dietary_restrictions) if dietary_restrictions else "None"
        additional_info = preferences.get("additional_info", "")
        
        history_data.append({
            "ID": plan_id,
            "Date": timestamp,
            "Dietary Restrictions": restrictions_text,
            "Additional Info": additional_info[:30] + "..." if len(additional_info) > 30 else additional_info
        })
    
    # Custom history item display using columns
    for item in history_data:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            st.write(f"**Date:** {item['Date']}")
        
        with col2:
            st.write(f"**Restrictions:** {item['Dietary Restrictions']}")
            st.write(f"**Notes:** {item['Additional Info']}")
            
        with col3:
            if st.button("View", key=f"view_{item['ID']}"):
                st.session_state.current_plan = user_history[item['ID']]
                st.session_state.current_view = "view_plan"
                st.rerun()
        
        st.divider()

# View plan page
def render_view_plan():
    st.header("Saved Meal Plan")
    
    if st.session_state.current_plan:
        st.markdown(st.session_state.current_plan["meal_plan"])
        
        if st.button("Back to History"):
            st.session_state.current_view = "history"
            st.rerun()
    else:
        st.error("No meal plan to display")
        if st.button("Back"):
            st.session_state.current_view = "history"
            st.rerun()

# Run the app
if __name__ == "__main__":
    main()