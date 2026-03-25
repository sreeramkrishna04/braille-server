from flask import Flask, request, jsonify, render_template
import os
import PyPDF2
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---------------- Configuration ----------------
UPLOAD_FOLDER = "uploads"
TEXT_FOLDER = "text_files"
ALLOWED_EXTENSIONS = {'pdf'}

EXTRACTED_TEXTS = {}   # stores extracted text
LATEST_PDF = ""        # stores latest uploaded PDF name

# Create required folders
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEXT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- Utility Functions ----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + " "
        text = re.sub(r'\s+', ' ', text).strip()
    except Exception as e:
        print(f"[ERROR] PDF read failed: {e}")
    return text

# ---------------- Routes ----------------
@app.route("/")
def index():
    return "Braille server running"

@app.route("/upload", methods=["POST"])
def upload_file():
    global LATEST_PDF

    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']

    if file.filename == "":
        return "No selected file", 400

    if not allowed_file(file.filename):
        return "Invalid file type", 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    name_without_ext = filename.rsplit('.', 1)[0]

    text = extract_text_from_pdf(save_path)

    EXTRACTED_TEXTS[name_without_ext] = text
    LATEST_PDF = name_without_ext

    # Save backup text
    with open(os.path.join(TEXT_FOLDER, f"{name_without_ext}.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    return "PDF uploaded and processed successfully", 200

@app.route("/get_text", methods=["GET"])
def get_text():
    if not LATEST_PDF:
        return jsonify({"text": ""}), 200

    return jsonify({
        "filename": LATEST_PDF,
        "text": EXTRACTED_TEXTS.get(LATEST_PDF, "")
    })

# ---------------- Render Entry Point ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # REQUIRED for Render
    app.run(host="0.0.0.0", port=port)