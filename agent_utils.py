import base64
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

def get_client(api_key):
    if not api_key or not OpenAI:
        return None
    return OpenAI(api_key=api_key)

def analyze_xray_image(image_bytes, api_key=None):
    """
    Vision-Language Agent: Analyzes the X-Ray image directly using GPT-4o.
    """
    client = get_client(api_key)
    if not client:
        # Mock VLM Response
        return "Mock VLM Analysis: The provided X-Ray exhibits structural characteristics suggestive of a fracture in the highlighted region. Bone density appears normal otherwise, but strict correlation with clinical symptoms is advised."
    
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "You are an expert AI radiologist. Analyze this X-ray image and provide a concise 3-sentence visual breakdown of any potential fractures or anomalies."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error connecting to Vision API: {e}"

def triage_scan(prediction, confidence, api_key=None):
    """
    Triaging Agent: Evaluates the severity and assigns a priority level.
    """
    client = get_client(api_key)
    if not client:
        # Mock Triaging
        if "Fractured" in prediction and confidence > 80:
            return "Urgent"
        elif "Fractured" in prediction:
            return "Elevated"
        return "Routine"

    prompt = f"""
    You are an AI Triaging Agent for an emergency room.
    An X-Ray was just scanned. 
    Prediction: {prediction}
    Model Confidence: {confidence}%
    
    Categorize the priority of this scan into exactly one of three categories: "Routine", "Elevated", or "Urgent".
    Reply with ONLY the category word.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0,
            max_tokens=10
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Routine"

def generate_medical_report(patient_name, prediction, confidence, notes, vlm_analysis, api_key=None):
    """
    Medical Report Agent: Generates a professional medical report based on all inputs.
    """
    client = get_client(api_key)
    if not client:
        # Mock Report
        report = f"""
### ScanTec Automated Radiology Report
**Patient Name:** {patient_name}  
**Primary Finding:** {prediction} (Confidence: {confidence:.1f}%)

**Detailed AI Visual Analysis:**
{vlm_analysis}

**Doctor's Clinical Notes:**
{notes}

**Conclusion:** 
Findings suggest {prediction.lower()} pathology. Proceed with required immobilization and follow-up protocols as suggested in the clinical notes.
"""
        return report.strip()

    prompt = f"""
    You are an expert radiologist writing a comprehensive medical report.
    Format the report in clean Markdown.
    
    Patient Name: {patient_name}
    Base AI Prediction: {prediction} ({confidence}% confidence)
    VLM Detailed Analysis: {vlm_analysis}
    Doctor's Notes: {notes}
    
    Write a structured, professional radiologic report containing:
    1. Header (ScanTec Automated Radiology Report)
    2. Patient Information
    3. Clinical Indication (Based on notes)
    4. Findings (Based on VLM and Base AI)
    5. Impression/Conclusion
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating report: {e}"

def chat_with_assistant(messages, role, api_key=None):
    """
    Interactive Assistant Agent: Allows users or doctors to chat with the AI about the results.
    """
    client = get_client(api_key)
    if not client:
        import random
        last_msg = messages[-1]['content'].lower() if messages else ""
        if role == "doctor":
            if any(word in last_msg for word in ["fracture", "scan", "patient"]):
                return "Mock Assistant (Doctor): Based on typical X-Ray patterns, I recommend strict immobilization and orthopedic consultation."
            elif any(word in last_msg for word in ["hello", "hi"]):
                return "Mock Assistant (Doctor): Hello Doctor. I have reviewed the recent scan queue. How can I assist you today?"
            responses = [
                "Mock Assistant (Doctor): That requires a closer look at the initial scan slices. (Live API key needed for deeper insights)",
                "Mock Assistant (Doctor): I agree with that assessment. Let's monitor the patient's recovery trajectory.",
                "Mock Assistant (Doctor): Interesting query. In offline mode, my clinical insight is limited. Please provide an API key for live analysis."
            ]
            return random.choice(responses)
        else:
            if any(word in last_msg for word in ["pain", "hurt"]):
                return "Mock Assistant (Patient): I understand it can be painful! Please make sure to follow your doctor's icing instructions."
            elif any(word in last_msg for word in ["what", "how", "why"]):
                return "Mock Assistant (Patient): That's a great question about your recovery. Usually, it takes 4-6 weeks to heal, but please consult your doctor for specifics!"
            elif any(word in last_msg for word in ["hello", "hi"]):
                return "Mock Assistant (Patient): Hello! I am your ScanTec AI. How are you feeling today?"
            responses = [
                "Mock Assistant (Patient): I hear you. Make sure to get plenty of rest! (Add an API key to enable my live intelligence).",
                "Mock Assistant (Patient): That's good to know. Keep tracking your symptoms and notes.",
                "Mock Assistant (Patient): Since I'm currently in offline Mock Mode, I can only provide general support. Please ask your actual doctor for medical advice!"
            ]
            return random.choice(responses)

    system_prompt = (
        "You are a helpful, professional medical AI assistant called ScanTec AI. "
        "If you are talking to a 'user', explain things simply without medical jargon. "
        "If you are talking to an 'admin' (doctor), provide concise, technical, and professional second opinions."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": f"{system_prompt} You are speaking to a {role}."}] + messages,
            temperature=0.7,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error with chat assistant: {e}"
