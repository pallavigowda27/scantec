import streamlit as st
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import pandas as pd
import altair as alt
import io
import os

# Dev branch update: add a simple comment so this branch differs from main for the PR comparison.
from model_utils import get_model, predict_fracture, preprocess_image, enhance_image
from gradcam import generate_mock_gradcam
from pdf_utils import generate_pdf_report
from db_utils import init_db, insert_scan, update_feedback, update_notes, update_report_path, get_recent_scans, authenticate_user, create_user, get_scans_for_user, get_all_scans, get_username, update_password, get_user_email, update_user_email, insert_comment, get_comments_for_scan, log_audit, get_audit_logs, export_scans_to_csv, import_scans_from_csv, send_email
from agent_utils import analyze_xray_image, triage_scan, generate_medical_report, chat_with_assistant

# Initialize Database
init_db()

# Setup the page aesthetics
st.set_page_config(page_title="ScanTec - Fracture Detection", page_icon="🦴", layout="wide")

# Custom CSS for Premium Design
st.markdown("""
    <style>
    .main {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .stButton>button {
        background-color: #238636;
        color: white;
        border-radius: 6px;
        border: 1px solid rgba(240, 246, 252, 0.1);
        padding: 5px 16px;
        font-weight: 600;
        transition: 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #2ea043;
        border-color: rgba(240, 246, 252, 0.1);
    }
    h1, h2, h3 {
        color: #58a6ff !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .css-1d391kg {
        background-color: #161b22;
    }
    .st-emotion-cache-16txtl3 {
        padding: 3rem 1.5rem;
    }
    div.stSpinner > div {
        border-color: #58a6ff transparent transparent transparent;
    }
    </style>
""", unsafe_allow_html=True)

# Login/Signup function
def login_signup():
    st.markdown("<h1>🦴 ScanTec Login/Signup</h1>", unsafe_allow_html=True)
    st.markdown("### AI-Powered Medical Diagnostic System for X-Ray Fracture Detection")
    st.markdown("---")
    
    mode = st.radio("Choose Action", ["Login", "Sign Up"])
    
    if mode == "Sign Up":
        st.subheader("Sign Up")
        username = st.text_input("Username", key="signup_username")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        role = st.selectbox("Role", ["user", "admin"], key="signup_role")
        email = st.text_input("Email (optional)", key="signup_email")
        
        if st.button("Sign Up"):
            if password != confirm_password:
                st.error("Passwords do not match.")
            elif not username or not password:
                st.error("Please fill all fields.")
            else:
                user_id = create_user(username, password, role, email)
                if user_id:
                    st.success(f"Account created successfully! User ID: {user_id}. You can now log in.")
                    log_audit(user_id, "signup", f"User {username} signed up")
                else:
                    st.error("Username already exists.")
    
    elif mode == "Login":
        st.subheader("Login")
        role = st.selectbox("Select Role", ["user", "admin"], key="login_role")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            user_id, user_role = authenticate_user(username, password)
            if user_id and user_role == role:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user_id
                st.session_state['role'] = role
                st.session_state['username'] = username
                log_audit(user_id, "login", f"User {username} logged in")
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials or role mismatch.")
    
    # For demo, create default users if not exist
    if st.button("Create Demo Users"):
        create_user("doctor", "pass", "admin")
        create_user("patient", "pass", "user")
        st.success("Demo users created: doctor/pass (admin), patient/pass (user)")

# Main app
def main_app():
    # Application Header
    st.markdown("<h1>🦴 ScanTec</h1>", unsafe_allow_html=True)
    st.markdown("### AI-Powered Medical Diagnostic System for X-Ray Fracture Detection")
    st.markdown("---")
    
    role = st.session_state['role']
    user_id = st.session_state['user_id']
    
    # Sidebar navigation
    with st.sidebar:
        username = st.session_state.get('username') or get_username(user_id)
        st.markdown(f"### Welcome, {username}")
        if role == "admin":
            page = st.radio("Go to", ["Dashboard", "Analytics", "Audit Logs", "EHR Export"])
        else:
            page = st.radio("Go to", ["Dashboard", "Profile"])
        
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()
            
        st.markdown("---")
        st.markdown("### AI Agent Settings")
        api_key = st.text_input("OpenAI API Key (Optional)", type="password", help="Leave blank to use Mock Agents.", key="sidebar_api_key")
        st.session_state['api_key'] = api_key
    
    if role == "admin":
        if page == "Dashboard":
            doctor_dashboard(user_id)
        elif page == "Analytics":
            analytics_dashboard()
        elif page == "Audit Logs":
            audit_logs_page()
        elif page == "EHR Export":
            ehr_page()
    elif role == "user":
        if page == "Dashboard":
            user_dashboard(user_id)
        elif page == "Profile":
            user_profile(user_id)

def doctor_dashboard(user_id):
    st.header("Doctor Dashboard")
    
    # Search functionality
    st.subheader("Search Scans")
    search_query = st.text_input("Search by Patient Name or Prediction", "")
    filter_status = st.selectbox("Filter by Report Status", ["All", "Reported", "Pending"])
    
    scans = get_all_scans()
    
    # Filter scans
    if search_query:
        scans = [s for s in scans if search_query.lower() in s['patient_name'].lower() or search_query.lower() in s['prediction'].lower()]
    if filter_status == "Reported":
        scans = [s for s in scans if s['report_path']]
    elif filter_status == "Pending":
        scans = [s for s in scans if not s['report_path']]
    
    st.write(f"Showing {len(scans)} scans")
    
    for scan in scans:
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.subheader(f"Patient: {scan['patient_name']} ({scan['patient_age']})")
                st.write(f"Scan ID: {scan['id']}")
                st.write(f"Timestamp: {scan['timestamp']}")
            with col2:
                priority = scan.get('priority_level', 'Routine')
                st.write(f"**Priority:** {priority}")
                st.write(f"Prediction: {scan['prediction']}")
                st.write(f"Confidence: {scan['confidence']:.2f}%")
                
                with st.expander("VLM Detailed Analysis"):
                    st.write(scan.get('vlm_analysis', 'No VLM analysis available.'))
                
                # Editable notes
                notes = st.text_area(f"Doctor Notes for Scan {scan['id']}", value=scan['doctor_notes'] or "", key=f"notes_{scan['id']}")
                if st.button(f"Update Notes for Scan {scan['id']}", key=f"update_{scan['id']}"):
                    update_notes(scan['id'], notes)
                    log_audit(user_id, "update_notes", f"Updated notes for scan {scan['id']}")
                    st.success("Notes updated!")
                
                # Comments
                st.subheader("Comments")
                comments = get_comments_for_scan(scan['id'])
                for comment in comments:
                    st.write(f"{comment['username']} ({comment['timestamp']}): {comment['comment']}")
                new_comment = st.text_input(f"Add Comment for Scan {scan['id']}", key=f"comment_{scan['id']}")
                if st.button(f"Add Comment for Scan {scan['id']}", key=f"add_comment_{scan['id']}"):
                    insert_comment(scan['id'], user_id, new_comment)
                    log_audit(user_id, "add_comment", f"Added comment to scan {scan['id']}")
                    st.success("Comment added!")
                    st.rerun()
            with col3:
                if not scan['report_path'] or not os.path.exists(scan['report_path']):
                    if st.button(f"Generate Report for Scan {scan['id']}", key=f"gen_{scan['id']}"):
                        # Agentic Medical Report Generation
                        ai_report_content = generate_medical_report(scan['patient_name'], scan['prediction'], scan['confidence'], notes, scan.get('vlm_analysis', ''), st.session_state.get('api_key'))
                        
                        from pdf_utils import generate_simple_pdf_report
                        pdf_path = generate_simple_pdf_report(scan['prediction'], scan['confidence'], ai_report_content, scan['patient_name'], scan['patient_age'])
                        update_report_path(scan['id'], pdf_path)
                        log_audit(user_id, "generate_report", f"Generated agentic report for scan {scan['id']}")
                        
                        # Send email to patient
                        user_email = get_user_email(scan['user_id'])
                        if user_email:
                            send_email(user_email, "Your Scan Report is Ready", f"Your scan report for {scan['patient_name']} is now available.")
                        st.success("Report generated!")
                        st.rerun()
                else:
                    st.write("Report generated")
                    # Provide download
                    if scan['report_path'] and os.path.exists(scan['report_path']):
                        with open(scan['report_path'], "rb") as f:
                            st.download_button(f"Download Report for Scan {scan['id']}", f, file_name=f"report_{scan['id']}.pdf", key=f"download_{scan['id']}")
                    else:
                        st.error("Report file no longer exists.")
            st.markdown("---")
            
    # Doctor Chat Assistant
    st.markdown("---")
    st.subheader("👨‍⚕️ ScanTec Doctor AI Assistant")
    if 'doc_chat' not in st.session_state:
        st.session_state['doc_chat'] = [{"role": "assistant", "content": "Hello Doctor! How can I assist you with these scans today?"}]
        
    for msg in st.session_state['doc_chat']:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    if prompt := st.chat_input("Ask ScanTec AI...", key="doc_chat_input"):
        st.session_state['doc_chat'].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state['doc_chat']]
        with st.spinner("AI is thinking..."):
            response = chat_with_assistant(api_messages, role="doctor", api_key=st.session_state.get('api_key'))
        st.session_state['doc_chat'].append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)

def user_dashboard(user_id):
    st.header("Patient Dashboard")
    
    # Upload section
    st.subheader("Upload X-Ray")
    patient_name = st.text_input("Your Name")
    patient_age = st.text_input("Your Age")
    uploaded_files = st.file_uploader("Choose X-Ray(s)...", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    # Preprocessing options
    st.subheader("Preprocessing Options")
    brightness = st.slider("Brightness", 0.5, 2.0, 1.0, 0.1)
    contrast = st.slider("Contrast", 0.5, 2.0, 1.0, 0.1)
    apply_clahe = st.checkbox("Apply CLAHE")
    apply_blur = st.checkbox("Apply Blur")
    apply_sharpen = st.checkbox("Apply Sharpen")
    
    if uploaded_files and patient_name and patient_age:
        for uploaded_file in uploaded_files:
            if st.button(f"Analyze {uploaded_file.name}"):
                # Process
                original_pil_image = Image.open(uploaded_file).convert('RGB')
                enhanced_image = enhance_image(original_pil_image, brightness, contrast, apply_clahe, apply_blur, apply_sharpen)
                preprocessed = preprocess_image(enhanced_image)
                prediction, confidence = predict_fracture(preprocessed)
                
                # AI Agents: Vision & Triage
                buf = io.BytesIO()
                original_pil_image.save(buf, format='JPEG')
                image_bytes = buf.getvalue()
                
                with st.spinner("AI Agents Analyzing Image..."):
                    vlm_analysis = analyze_xray_image(image_bytes, st.session_state.get('api_key'))
                    priority = triage_scan(prediction, confidence, st.session_state.get('api_key'))
                
                # Store
                scan_id = insert_scan(prediction, confidence, patient_name, patient_age, user_id, priority, vlm_analysis)
                st.success(f"Analysis complete for {uploaded_file.name}: {prediction} with {confidence:.2f}% confidence")
                
                # Display images
                col1, col2 = st.columns(2)
                with col1:
                    st.image(original_pil_image, caption="Original Image", width=350)
                with col2:
                    st.image(enhanced_image, caption="Enhanced Image", width=350)
                
                # Auto generate notes
                if "Fractured" in prediction:
                    notes = f"Patient {patient_name} ({patient_age} yrs old) presented for X-Ray. AI indicates {confidence:.2f}% confidence of fracture.\n\nClinical Suggestions:\n- Recommend strict immobilization.\n- Schedule orthopedic consultation.\n- Prescribe pain management as necessary."
                else:
                    notes = f"Patient {patient_name} ({patient_age} yrs old) presented for X-Ray. AI indicates no visible fracture.\n\nClinical Suggestions:\n- Rest and ice affected area.\n- Follow up if pain persists after 1 week."
                
                update_notes(scan_id, notes)
                log_audit(user_id, "upload_scan", f"Uploaded scan {scan_id}")
                
                # Send email to doctors
                admins = [get_user_email(uid) for uid in [1,2] if get_user_email(uid)]  # Assuming default users
                for email in admins:
                    send_email(email, "New Scan Uploaded", f"New scan uploaded by {patient_name}.")
                
                st.info("Your scan has been submitted for doctor review. Check back later for the report.")
    
    # View reports
    st.subheader("Your Reports")
    scans = get_scans_for_user(user_id)
    for scan in scans:
        with st.expander(f"Scan {scan['id']} - {scan['timestamp']}"):
            st.write(f"Prediction: {scan['prediction']}")
            st.write(f"Confidence: {scan['confidence']:.2f}%")
            st.write(f"Notes: {scan['doctor_notes']}")
            if scan['report_path'] and os.path.exists(scan['report_path']):
                with open(scan['report_path'], "rb") as f:
                    st.download_button(f"Download Report for Scan {scan['id']}", f, file_name=f"report_{scan['id']}.pdf", key=f"user_download_{scan['id']}")
            else:
                st.write("Report not yet available or the file was removed. Doctor review pending.")
    
    # Trends
    st.subheader("Scan Trends")
    if scans:
        df = pd.DataFrame(scans)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X('timestamp:T', title='Scan Timestamp'),
            y=alt.Y('confidence:Q', title='AI Confidence (%)'),
            tooltip=[alt.Tooltip('timestamp:T', title='Timestamp'), alt.Tooltip('confidence:Q', title='Confidence')]
        ).properties(width=700, height=350)
        st.altair_chart(chart, use_container_width=True)
        st.write("Each dot is one saved scan; the line shows confidence over time.")

    # Patient Chat Assistant
    st.markdown("---")
    st.subheader("🤖 ScanTec Patient Assistant")
    if 'patient_chat' not in st.session_state:
        st.session_state['patient_chat'] = [{"role": "assistant", "content": "Hi there! I am the ScanTec AI. I can explain your X-Ray results or give you general recovery information. What would you like to know?"}]
        
    for msg in st.session_state['patient_chat']:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    if prompt := st.chat_input("Ask about your scan or recovery...", key="patient_chat_input"):
        st.session_state['patient_chat'].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state['patient_chat']]
        with st.spinner("AI is thinking..."):
            response = chat_with_assistant(api_messages, role="patient", api_key=st.session_state.get('api_key'))
        st.session_state['patient_chat'].append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)

def user_profile(user_id):
    st.header("User Profile")
    
    st.subheader("Update Email")
    current_email = get_user_email(user_id)
    new_email = st.text_input("Email", value=current_email)
    if st.button("Update Email"):
        update_user_email(user_id, new_email)
        log_audit(user_id, "update_email", f"Updated email to {new_email}")
        st.success("Email updated!")
    
    st.subheader("Change Password")
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_new_password = st.text_input("Confirm New Password", type="password")
    
    if st.button("Change Password"):
        if not current_password or not new_password:
            st.error("Please fill all fields.")
        elif new_password != confirm_new_password:
            st.error("New passwords do not match.")
        else:
            # For simplicity, update password without verifying current
            update_password(user_id, new_password)
            log_audit(user_id, "change_password", "Password changed")
            st.success("Password changed successfully!")
    


def analytics_dashboard():
    st.header("Analytics Dashboard")
    
    scans = get_all_scans()
    
    total_scans = len(scans)
    fractured = len([s for s in scans if "Fractured" in s['prediction']])
    non_fractured = total_scans - fractured
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Scans", total_scans)
    with col2:
        st.metric("Fractured", fractured)
    with col3:
        st.metric("Non-Fractured", non_fractured)
    
    # Simple chart
    import pandas as pd
    df = pd.DataFrame({"Type": ["Fractured", "Non-Fractured"], "Count": [fractured, non_fractured]})
    st.bar_chart(df.set_index("Type"))

def audit_logs_page():
    st.header("Audit Logs")
    logs = get_audit_logs()
    st.dataframe(logs)

def ehr_page():
    st.header("EHR Integration")
    if st.button("Export Scans to CSV"):
        csv_path = export_scans_to_csv()
        with open(csv_path, "rb") as f:
            st.download_button("Download CSV", f, file_name="scans_export.csv")
    
    uploaded_csv = st.file_uploader("Import Scans from CSV", type="csv")
    if uploaded_csv and st.button("Import"):
        # Save and import
        with open("temp.csv", "wb") as f:
            f.write(uploaded_csv.getbuffer())
        import_scans_from_csv("temp.csv")
        st.success("Imported successfully!")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_signup()
else:
    main_app()
