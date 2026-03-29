from flask import Flask, request, jsonify, render_template
import os
import PyPDF2
import re
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract

app = Flask(__name__)

# ---------------- Configuration ----------------
UPLOAD_FOLDER = "uploads"
TEXT_FOLDER = "text_files"

ALLOWED_PDF_EXTENSIONS = {'pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}

EXTRACTED_TEXTS = {}
LATEST_FILE = ""

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEXT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- Tesseract (Windows path) ----------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\sreeramkrishna\Downloads\tesseract-5.4.0.20240606\tesseract.exe"

# ---------------- Utility ----------------
def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_PDF_EXTENSIONS.union(ALLOWED_IMAGE_EXTENSIONS)

def clean_text(text):
    # Keep only letters and spaces → required for ESP32
    text = re.sub(r'[^a-zA-Z ]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + " "
    except Exception as e:
        print(f"[ERROR] PDF read failed: {e}")

    return clean_text(text)

def extract_text_from_image(image_path):
    text = ""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        print(f"[ERROR] Image OCR failed: {e}")

    return clean_text(text)

# ---------------- Routes ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    global LATEST_FILE

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
    ext = filename.rsplit('.', 1)[1].lower()

    # Decide processing type
    if ext in ALLOWED_PDF_EXTENSIONS:
        text = extract_text_from_pdf(save_path)
    else:
        text = extract_text_from_image(save_path)

    print("Uploaded:", filename)
    print("Extracted text:", text[:200])  # preview only

    EXTRACTED_TEXTS[name_without_ext] = text
    LATEST_FILE = name_without_ext

    # Save text file
    with open(os.path.join(TEXT_FOLDER, f"{name_without_ext}.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    return "File uploaded and processed successfully"

@app.route("/get_text", methods=["GET"])
def get_text():
    if not LATEST_FILE:
        return jsonify({"text": ""})

    return jsonify({
        "filename": LATEST_FILE,
        "text": EXTRACTED_TEXTS.get(LATEST_FILE, "")
    })

# 🔴 VIEW TEXT IN BROWSER (DEBUG)
@app.route("/view_text")
def view_text():
    if not LATEST_FILE:
        return "No file uploaded yet"

    text = EXTRACTED_TEXTS.get(LATEST_FILE, "")

    return f"""
    <html>
    <head>
        <title>Extracted Text</title>
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                background: #f4f4f4;
                padding: 15px;
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <h2>Latest File: {LATEST_FILE}</h2>
        <pre>{text}</pre>
    </body>
    </html>
    """

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)