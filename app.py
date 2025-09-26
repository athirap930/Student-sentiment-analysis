# app.py: Final version with an advanced, LLM-simulated AI Recommendation Engine

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import mysql.connector
from textblob import TextBlob
from datetime import datetime
from collections import Counter
import pandas as pd
from fpdf import FPDF
import io
import zipfile

app = Flask(__name__)
CORS(app)

# --- Database Configuration ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2004', # IMPORTANT: Ensure this is your correct password
    'database': 'student_feedback'
}

# --- Core Functions (get_db_connection, process_and_analyze_feedback, save_feedback_to_db) ---
# These functions are unchanged
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def process_and_analyze_feedback(text):
    custom_corrections = {"roode": "rude", "amaezing": "amazing", "terible": "terrible", "horible": "horrible"}
    processed_text = str(text).lower()
    for wrong, right in custom_corrections.items():
        processed_text = processed_text.replace(wrong, right)
    original_blob = TextBlob(processed_text)
    try:
        if original_blob.detect_language() != 'en':
            processed_text = str(original_blob.translate(to='en'))
    except Exception as e:
        print(f"Translation failed: {e}")
    final_text = str(TextBlob(processed_text).correct())
    score = TextBlob(final_text).sentiment.polarity
    category = 'Positive' if score > 0 else 'Negative' if score < 0 else 'Neutral'
    return {'category': category, 'score': score, 'corrected_text': final_text, 'original_text': text}

def save_feedback_to_db(data):
    conn = get_db_connection()
    if not conn: return {"error": "Database connection failed"}, 500
    cursor = conn.cursor()
    analysis = data['analysis']
    sql = "INSERT INTO feedback (feedback_text, corrected_text, department, course, faculty, sentiment_category, sentiment_score, source) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    values = (analysis['original_text'], analysis['corrected_text'], data['department'], data['course'], data['faculty'], analysis['category'], analysis['score'], data['source'])
    try:
        cursor.execute(sql, values)
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        return {"error": f"Failed to insert feedback: {err}"}, 500
    finally:
        cursor.close()
        conn.close()
    return {"message": f"Feedback from {data['source']} added successfully"}, 201


# --- ADVANCED RECOMMENDATION ENGINE (IMPROVED) ---

def call_gemini_api_simulation(prompt):
    """
    This function simulates a real API call to a powerful LLM like Google's Gemini.
    For the demo, it uses keyword matching on the structured prompt to return
    high-quality, pre-written, and contextually relevant responses,
    mimicking what a real generative model would produce.
    """
    prompt_lower = prompt.lower()
    recommendations = []

    # Scenario 1: Clear top performer and a negative theme
    if "highest praise for" in prompt_lower and "common negative theme" in prompt_lower:
        faculty_name = prompt_lower.split("highest praise for:")[1].split("(")[0].strip().title()
        theme = prompt_lower.split("common negative theme:")[1].strip().replace("'", "")
        recommendations.append(f"💡 Leverage Excellence: {faculty_name} is receiving outstanding feedback. Consider a peer-mentoring program led by them to share best practices.")
        recommendations.append(f"❗ Action Required: The keyword '{theme}' is a recurring negative topic. Recommend a targeted survey to understand the root cause of this issue.")

    # Scenario 2: Clear faculty needing attention
    elif "needs attention" in prompt_lower:
        faculty_name = prompt_lower.split("needs attention:")[1].split("(")[0].strip().title()
        recommendations.append(f"🔍 Opportunity for Growth: Feedback for {faculty_name} shows a negative trend. Suggest a confidential peer review or offer additional teaching resources.")

    # Default fallback scenario
    else:
        recommendations.append("⭐ Overall sentiment is balanced. Continue monitoring key metrics for emerging trends.")
        recommendations.append("📊 Data-Driven Dialogue: Share department-level trend charts with faculty heads to foster proactive discussions on teaching quality.")

    return recommendations


def generate_recommendations(feedback_data):
    """Analyzes all feedback to find trends, synthesizes them into a prompt, and uses a simulated LLM to generate advice."""
    if len(feedback_data) < 5:
        return ["Not enough data to generate meaningful recommendations. More feedback is needed."]

    # 1. Analyze Entities (Faculty)
    faculty_scores = {}
    for item in feedback_data:
        faculty = item.get('faculty')
        score = item.get('sentiment_score')
        if faculty and faculty != 'N/A':
            faculty_scores.setdefault(faculty, []).append(score)
    
    faculty_analysis = {name: {'avg_score': sum(scores) / len(scores), 'reviews': len(scores)} for name, scores in faculty_scores.items() if len(scores) >= 2}

    # 2. Analyze Keywords (IMPROVED LOGIC)
    # FIX: Expanded stop words list to filter out meaningless common words like 'and', 'but', etc.
    stop_words = {
        'a', 'about', 'an', 'and', 'are', 'as', 'at', 'be', 'but', 'by', 'class', 'course', 
        'for', 'from', 'he', 'how', 'i', 'in', 'is', 'it', 'its', 'lecture', 'of', 'on', 
        'professor', 'she', 'student', 'teacher', 'that', 'the', 'they', 'this', 'to', 
        'was', 'were', 'what', 'when', 'where', 'who', 'with', 'you', 'very', 'really'
    }
    
    negative_words = []
    for item in feedback_data:
        if item.get('sentiment_category') == 'Negative':
            text_to_process = item.get('corrected_text') or item.get('feedback_text', '')
            words = text_to_process.lower().split()
            for word in words:
                clean_word = word.strip(".,!?")
                # FIX: Added a length check to ignore short, non-substantive words
                if len(clean_word) > 2 and clean_word not in stop_words:
                    negative_words.append(clean_word)
    
    neg_counts = Counter(negative_words)

    # 3. Synthesize Insights into a structured prompt
    insight_summary = "Analyze the following student feedback summary and generate actionable recommendations for a university administrator.\n\nData Summary:\n"
    
    top_faculty = sorted(faculty_analysis.items(), key=lambda x: x[1]['avg_score'], reverse=True)
    if top_faculty:
        insight_summary += f"- Highest praise for: {top_faculty[0][0]} (Avg Score: {top_faculty[0][1]['avg_score']:.2f}, {top_faculty[0][1]['reviews']} reviews)\n"
    
    bottom_faculty = sorted(faculty_analysis.items(), key=lambda x: x[1]['avg_score'])
    if bottom_faculty and bottom_faculty[0][1]['avg_score'] < 0:
        insight_summary += f"- Needs attention: {bottom_faculty[0][0]} (Avg Score: {bottom_faculty[0][1]['avg_score']:.2f}, {bottom_faculty[0][1]['reviews']} reviews)\n"

    if neg_counts:
        top_neg_word, _ = neg_counts.most_common(1)[0]
        insight_summary += f"- Common negative theme: '{top_neg_word}'\n"

    # 4. Call Simulated Gemini API with the synthesized prompt
    recommendations = call_gemini_api_simulation(insight_summary)
    
    return recommendations


# --- API Endpoints ---
# The endpoints for /feedback, /import/file, /export/* remain the same.
# The only change is the /recommendations endpoint now uses the new engine.

@app.route('/feedback', methods=['GET', 'POST'])
def feedback_handler():
    # ... This code is unchanged ...
    if request.method == 'GET':
        conn = get_db_connection()
        if not conn: return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC")
        feedback_data = cursor.fetchall()
        cursor.close()
        conn.close()
        for item in feedback_data:
            if isinstance(item.get('created_at'), datetime):
                item['created_at'] = item['created_at'].isoformat()
        return jsonify(feedback_data)
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'feedback_text' not in data: return jsonify({"error": "Missing feedback text"}), 400
        analysis_result = process_and_analyze_feedback(data['feedback_text'])
        payload = {"analysis": analysis_result, "department": data.get('department', 'N/A'), "course": data.get('course', 'N/A'), "faculty": data.get('faculty', 'N/A'), "source": "Manual Entry"}
        response, status_code = save_feedback_to_db(payload)
        return jsonify(response), status_code

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    # The recommendation engine needs more data than just text
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT faculty, sentiment_score, sentiment_category, corrected_text, feedback_text FROM feedback")
    feedback_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    recommendations = generate_recommendations(feedback_data)
    return jsonify(recommendations)
    
@app.route('/import/file', methods=['POST'])
def import_file():
    # ... This code is unchanged ...
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    try:
        if file.filename.endswith('.csv'): df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'): df = pd.read_excel(file)
        else: return jsonify({"error": "Invalid file type. Please upload a CSV or XLSX file."}), 400
        for _, row in df.iterrows():
            analysis_result = process_and_analyze_feedback(row['feedback_text'])
            payload = {"analysis": analysis_result, "department": row.get('department', 'N/A'), "course": row.get('course', 'N/A'), "faculty": row.get('faculty', 'N/A'), "source": "File Import"}
            save_feedback_to_db(payload)
        return jsonify({"message": f"Successfully imported {len(df)} records."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to process file: {e}"}), 500

# All /export endpoints are unchanged
@app.route('/export/csv', methods=['GET'])
def export_csv():
    # ... This code is unchanged ...
    conn = get_db_connection(); df = pd.read_sql("SELECT * FROM feedback", conn); conn.close()
    mem_file = io.BytesIO(); df.to_csv(mem_file, index=False); mem_file.seek(0)
    return send_file(mem_file, as_attachment=True, download_name='feedback_export.csv', mimetype='text/csv')

@app.route('/export/excel', methods=['GET'])
def export_excel():
    # ... This code is unchanged ...
    conn = get_db_connection(); df = pd.read_sql("SELECT * FROM feedback", conn); conn.close()
    mem_file = io.BytesIO(); df.to_excel(mem_file, index=False, sheet_name='Feedback'); mem_file.seek(0)
    return send_file(mem_file, as_attachment=True, download_name='feedback_export.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/export/pdf', methods=['GET'])
def export_pdf():
    # ... This code is unchanged ...
    conn = get_db_connection(); cursor = conn.cursor(dictionary=True); cursor.execute("SELECT * FROM feedback"); data = cursor.fetchall(); conn.close()
    total = len(data); positive_count = sum(1 for f in data if f['sentiment_category'] == 'Positive'); negative_count = sum(1 for f in data if f['sentiment_category'] == 'Negative'); avg_score = (sum(f['sentiment_score'] for f in data) / total) if total > 0 else 0; positive_rate = (positive_count / total * 100) if total > 0 else 0
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 18); pdf.cell(0, 10, "Student Feedback Aggregate Report", 0, 1, 'C'); pdf.ln(10)
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "Overall Statistics", 0, 1); pdf.set_font("Arial", '', 12); pdf.cell(95, 10, f"Total Feedback Entries: {total}", 1, 0); pdf.cell(95, 10, f"Average Sentiment Score: {avg_score:.2f}", 1, 1); pdf.cell(95, 10, f"Positive Rate: {positive_rate:.1f}%", 1, 0); pdf.cell(95, 10, f"Negative Feedback Count: {negative_count}", 1, 1); pdf.ln(10)
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "Recent Feedback Highlights", 0, 1); pdf.set_font("Arial", '', 10)
    for item in data[:5]: line = f"[{item['sentiment_category']}] {item['corrected_text' if item.get('corrected_text') else item['feedback_text']][:80]}..."; pdf.multi_cell(0, 5, line); pdf.ln(2)
    mem_file = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    return send_file(mem_file, as_attachment=True, download_name='feedback_report.pdf', mimetype='application/pdf')

@app.route('/export/zip', methods=['GET'])
def export_zip():
    # ... This code is unchanged ...
    conn = get_db_connection(); df = pd.read_sql("SELECT * FROM feedback", conn); conn.close()
    zip_buffer = io.BytesIO();
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        csv_buffer = io.StringIO(); df.to_csv(csv_buffer, index=False); zip_file.writestr('feedback_export.csv', csv_buffer.getvalue())
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 18); pdf.cell(0, 10, "Student Feedback Aggregate Report", 0, 1, 'C'); pdf.ln(10);
        total = len(df); positive_count = len(df[df['sentiment_category'] == 'Positive']); negative_count = len(df[df['sentiment_category'] == 'Negative']); avg_score = df['sentiment_score'].mean() if total > 0 else 0; positive_rate = (positive_count / total * 100) if total > 0 else 0;
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "Overall Statistics", 0, 1); pdf.set_font("Arial", '', 12); pdf.cell(95, 10, f"Total Feedback Entries: {total}", 1, 0); pdf.cell(95, 10, f"Average Sentiment Score: {avg_score:.2f}", 1, 1); pdf.cell(95, 10, f"Positive Rate: {positive_rate:.1f}%", 1, 0); pdf.cell(95, 10, f"Negative Feedback Count: {negative_count}", 1, 1); pdf.ln(10);
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "Recent Feedback Highlights", 0, 1); pdf.set_font("Arial", '', 10);
        for _, row in df.head(5).iterrows(): line = f"[{row['sentiment_category']}] {str(row.get('corrected_text') or row.get('feedback_text', ''))[:80]}..."; pdf.multi_cell(0, 5, line); pdf.ln(2);
        zip_file.writestr('feedback_report.pdf', pdf.output(dest='S').encode('latin-1'))
    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name='feedback_package.zip', mimetype='application/zip')


if __name__ == '__main__':
    app.run(debug=True)

