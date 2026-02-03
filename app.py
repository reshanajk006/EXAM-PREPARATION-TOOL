from flask import Flask, render_template, request, jsonify
import PyPDF2
import os
import re
import random
from collections import Counter
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Allow large files (1GB)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

MAX_PAGES = 200          # hard cap for sanity
MAX_CHARS = 300_000      # process only first 300k chars

# ---------------- PDF UTIL ---------------- #

def extract_text_streaming(pdf_path):
    reader = PyPDF2.PdfReader(pdf_path)
    text_chunks = []

    char_count = 0
    for i, page in enumerate(reader.pages):
        if i >= MAX_PAGES:
            break

        page_text = page.extract_text() or ""
        if not page_text.strip():
            continue

        text_chunks.append(page_text)
        char_count += len(page_text)

        if char_count >= MAX_CHARS:
            break

    return " ".join(text_chunks)

# ---------------- NLP HELPERS ---------------- #

def extract_sentences(text):
    return [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 20]

def extract_key_terms(text):
    stopwords = set("""
    the be to of and a in that have i it for not on with he as you do at
    this but his by from they we say her she or an will my one all would
    there their what so up out if about who get which go me when make can
    like time no just him know take people into year your good some could
    them see other than then now look only come its over think also back
    after use two how our work first well way even new want because any
    these give day most us is was are been has had were said did
    """.split())

    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    words = [w for w in words if w not in stopwords]

    freq = Counter(words)
    return [w for w, c in freq.most_common(40) if c > 2]

def generate_summary(text, n=8):
    sentences = extract_sentences(text)
    if len(sentences) <= n:
        return " ".join(sentences)

    keywords = set(extract_key_terms(text))
    scored = []

    for i, s in enumerate(sentences):
        score = (len(sentences) - i) / len(sentences)
        score += len(set(s.lower().split()) & keywords) * 2
        scored.append((score, s))

    scored.sort(reverse=True)
    top = set(s for _, s in scored[:n])

    return " ".join(s for s in sentences if s in top)

def generate_quiz_questions(text, n=12):
    sentences = extract_sentences(text)
    keywords = extract_key_terms(text)
    quizzes = []

    for s in sentences:
        if len(quizzes) >= n:
            break

        hits = [k for k in keywords if k in s.lower()]
        if not hits:
            continue

        word = random.choice(hits)
        q = s.replace(word, "______", 1)

        options = random.sample(keywords, min(4, len(keywords)))
        if word not in options:
            options[0] = word

        random.shuffle(options)
        correct = chr(65 + options.index(word))

        quizzes.append({
            "question": q,
            "options": [f"{chr(65+i)}) {o.capitalize()}" for i, o in enumerate(options)],
            "correct": correct
        })

    return quizzes

def generate_flashcards(text, n=12):
    sentences = extract_sentences(text)
    keywords = extract_key_terms(text)

    def is_definition_sentence(sentence, keyword):
        s = sentence.lower()
        return (
            keyword in s and
            (
                f"{keyword} is" in s or
                f"{keyword} refers to" in s or
                f"{keyword} means" in s or
                f"{keyword} can be defined" in s
            )
        )

    cards = []
    used = set()

    for k in keywords:
        if len(cards) >= n:
            break

        if k in used:
            continue

        # Prefer definition-style sentences
        definition_sentences = [
            s for s in sentences if is_definition_sentence(s, k)
        ]

        # Fallback: explanatory sentences (short + clean)
        if not definition_sentences:
            definition_sentences = [
                s for s in sentences
                if k in s.lower() and 40 < len(s) < 200
            ]

        if not definition_sentences:
            continue

        back_text = definition_sentences[0]

        cards.append({
            "front": k.capitalize(),
            "back": back_text.strip()[:300]
        })

        used.add(k)

    return cards


# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF uploaded'}), 400

    file = request.files['pdf']
    filename = secure_filename(file.filename)

    if not filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Not a PDF'}), 400

    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)

    try:
        text = extract_text_streaming(path)

        if len(text) < 1000:
            return jsonify({'error': 'PDF has too little extractable text'}), 400

        data = {
            "summary": generate_summary(text),
            "quizzes": generate_quiz_questions(text),
            "flashcards": generate_flashcards(text)
        }

        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        os.remove(path)

if __name__ == '__main__':
    app.run(debug=True)
