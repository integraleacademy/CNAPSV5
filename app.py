from flask import Flask, render_template, request, redirect, send_file, url_for
import os
import json
import smtplib
import zipfile
from email.message import EmailMessage
from PIL import Image
import pypandoc
import shutil

# HEIC support (optionnel si pillow-heif installé)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_OK = True
except Exception as e:
    print(f"[WARNING] HEIC non activé: {e}")
    HEIC_OK = False

app = Flask(__name__)
UPLOAD_FOLDER = '/mnt/data/uploads'
DATA_FILE = '/mnt/data/data.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def clean_filename(text):
    return text.strip().replace(" ", "_").replace("'", "").replace('"', '')

def convert_to_pdf(filepath, output_filename):
    ext = os.path.splitext(filepath)[1].lower()
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{output_filename}.pdf")

    print(f"[INFO] Tentative de conversion : {filepath} → {pdf_path}")

    try:
        # PDF déjà prêt : on copie tel quel (sauf si même chemin)
        if ext == '.pdf':
            if os.path.abspath(filepath) == os.path.abspath(pdf_path):
                print(f"[INFO] PDF déjà au bon format (même chemin), pas de copie : {pdf_path}")
                return os.path.basename(pdf_path)
            shutil.copy(filepath, pdf_path)
            print(f"[SUCCESS] PDF déjà au bon format, copié : {pdf_path}")
            return os.path.basename(pdf_path)

        # --- Fallback 1 : tenter d'ouvrir comme image même si l'extension est vide/incorrecte ---
        try:
            img = Image.open(filepath)  # Pillow détecte par l'en-tête
            if getattr(img, "is_animated", False):
                img.seek(0)
            rgb_im = img.convert('RGB')
            rgb_im.save(pdf_path)
            print(f"[SUCCESS] PDF créé (sniff image) : {pdf_path}")
            return os.path.basename(pdf_path)
        except Exception:
            pass

        # --- Fallback 2 : détecter un PDF par signature magique ---
        try:
            with open(filepath, 'rb') as f:
                header = f.read(5)
            if header == b'%PDF-':
                if os.path.abspath(filepath) == os.path.abspath(pdf_path):
                    print(f"[INFO] PDF détecté par signature (même chemin), pas de copie : {pdf_path}")
                    return os.path.basename(pdf_path)
                shutil.copy(filepath, pdf_path)
                print(f"[SUCCESS] PDF détecté par signature, copié : {pdf_path}")
                return os.path.basename(pdf_path)
        except Exception:
            pass

        # Images avec extension connue (y compris HEIC si pillow-heif est activé)
        if ext in ['.jpg', '.jpeg', '.png', '.heic', '.webp', '.tif', '.tiff']:
            if ext == '.heic' and not HEIC_OK:
                print("[WARNING] Format HEIC reçu mais pillow-heif indisponible.")
                return None
            image = Image.open(filepath)
            if getattr(image, "is_animated", False):
                image.seek(0)
            rgb_im = image.convert('RGB')
            rgb_im.save(pdf_path)
            print(f"[SUCCESS] PDF créé : {pdf_path}")
            return os.path.basename(pdf_path)

        # Documents (nécessite pandoc + moteur PDF côté Render)
        elif ext in ['.doc', '.docx', '.odt', '.txt', '.rtf']:
            pypandoc.convert_file(filepath, 'pdf', outputfile=pdf_path)
            print(f"[SUCCESS] PDF créé : {pdf_path}")
            return os.path.basename(pdf_path)

        else:
            print(f"[WARNING] Format non pris en charge : {ext}")
            return None

    except Exception a
