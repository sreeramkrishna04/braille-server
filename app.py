from flask import Flask, request, jsonify
import os, re, uuid

import pytesseract
from PIL import Image
import cv2
import numpy as np

from pdf2image import convert_from_path
import pdfplumber

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

LATEST_TEXT = ""
VERSION = 0

# -------- CLEAN TEXT --------
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9.,;:?!\'"()\-\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# -------- IMAGE OCR --------
def extract_text_from_image(path):
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    text = pytesseract.image_to_string(thresh)
    return text

# -------- PDF --------
def extract_text_from_pdf(path):
    text = ""

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + " "
    except:
        pass

    # fallback OCR
    if len(text.strip()) < 50:
        images = convert_from_path(path)
        for img in images:
            temp_path = "temp.jpg"
            img.save(temp_path)
            text += extract_text_from_image(temp_path)

    return text

# -------- HOME --------
@app.route("/")
def home():
    return "Server Running"

# -------- UPLOAD --------
@app.route("/upload", methods=["POST"])
def upload():
    global LATEST_TEXT, VERSION

    if 'file' not in request.files:
        return "No file", 400

    file = request.files['file']

    if file.filename == "":
        return "No file selected", 400

    ext = file.filename.split('.')[-1].lower()
    filename = str(uuid.uuid4()) + "." + ext

    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    text = ""

    if ext in ['jpg','jpeg','png']:
        text = extract_text_from_image(path)

    elif ext == 'pdf':
        text = extract_text_from_pdf(path)

    text = clean_text(text)
    text = text[:500]   # limit for ESP32

    LATEST_TEXT = text
    VERSION += 1

    return jsonify({"message":"ok","version":VERSION})

# -------- GET TEXT --------
@app.route("/get_text", methods=["GET"])
def get_text():
    return jsonify({
        "version": VERSION,
        "text": LATEST_TEXT
    })

# -------- RUN --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)