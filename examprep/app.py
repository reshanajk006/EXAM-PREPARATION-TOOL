from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import json
import re
from io import BytesIO

app = Flask(__name__)
CORS(app)

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def generate_quiz_from_text(text):
    """Generate quiz questions from text (simplified version)"""
    # Split text into sentences
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 20]
    
    quiz = []
    # Take first 5 meaningful sentences and create questions
    for i, sentence in enumerate(sentences[:5]):
        if len(sentence) > 30:
            # Extract key terms (simplified)
            words = sentence.split()
            if len(words) > 5:
                # Create a fill-in-the-blank style question
                key_word = words[min(3, len(words)-1)]
                question = sentence.replace(key_word, "_____")
                
                quiz.append({
                    "question": question,
                    "options": [key_word, "Option B", "Option C", "Option D"],
                    "answer": key_word
                })
    
    return quiz

def generate_flashcards_from_text(text):
    """Generate flashcards from text"""
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 20]
    
    flashcards = []
    for i, sentence in enumerate(sentences[:10]):
        if len(sentence) > 30:
            words = sentence.split()
            # Create Q&A pairs
            mid = len(words) // 2
            question = " ".join(words[:mid]) + "...?"
            answer = " ".join(words[mid:])
            
            flashcards.append({
                "front": question,
                "back": answer
            })
    
    return flashcards

def generate_summary_from_text(text):
    """Generate summary from text"""
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
    
    # Take first few paragraphs as summary (simplified)
    summary = "<h3>Key Points:</h3><ul>"
    
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 30]
    for sentence in sentences[:5]:
        summary += f"<li>{sentence}</li>"
    
    summary += "</ul>"
    return summary

@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400
    
    pdf_file = request.files['pdf']
    text = extract_text_from_pdf(BytesIO(pdf_file.read()))
    quiz = generate_quiz_from_text(text)
    
    return jsonify({"quiz": quiz})

@app.route('/generate-flashcards', methods=['POST'])
def generate_flashcards():
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400
    
    pdf_file = request.files['pdf']
    text = extract_text_from_pdf(BytesIO(pdf_file.read()))
    flashcards = generate_flashcards_from_text(text)
    
    return jsonify({"flashcards": flashcards})

@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400
    
    pdf_file = request.files['pdf']
    text = extract_text_from_pdf(BytesIO(pdf_file.read()))
    summary = generate_summary_from_text(text)
    
    return jsonify({"summary": summary})

if __name__ == '__main__':
    app.run(debug=True, port=5000)