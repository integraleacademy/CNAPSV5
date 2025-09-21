from flask import Flask, render_template, request, redirect, send_file, url_for, flash
import os, json, smtplib, zipfile, shutil
from email.message import EmailMessage
from PIL import Image
import pypandoc
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = '/mnt/data/uploads'
DATA_FILE = '/mnt/data/data.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def convert_to_pdf(filepath, output_filename):
    ext = os.path.splitext(filepath)[1].lower()
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{output_filename}.pdf")
    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if ext == ".pdf":
            shutil.copy(filepath, pdf_path)
            return os.path.basename(pdf_path)
        if ext in [".jpg", ".jpeg", ".png"]:
            image = Image.open(filepath)
            rgb_im = image.convert("RGB")
            rgb_im.save(pdf_path)
            return os.path.basename(pdf_path)
        if ext in [".doc", ".docx", ".odt", ".txt", ".rtf"]:
            pypandoc.convert_file(filepath, "pdf", outputfile=pdf_path)
            return os.path.basename(pdf_path)
        return None
    except Exception as e:
        print(f"[ERROR] Conversion échouée : {e}")
        return None

def send_email(user_email, subject, contenu_txt, contenu_html):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_password = os.environ.get("EMAIL_PASSWORD")
    if not smtp_user or not smtp_password:
        print("⚠️ EMAIL_USER ou EMAIL_PASSWORD manquant")
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = user_email
        msg.set_content(contenu_txt)
        msg.add_alternative(contenu_html, subtype="html")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"⚠️ Erreur mail : {e}")
        return False

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/submit', methods=["POST"])
def submit():
    nom = request.form["nom"]
    prenom = request.form["prenom"]
    email = request.form["email"]
    fichiers = []

    def save_files(files, prefix):
        paths = []
        for i, file in enumerate(files):
            if file and file.filename:
                base_filename = f"{nom}_{prenom}_{prefix}_{i}"
                temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(temp_path)
                converted = convert_to_pdf(temp_path, base_filename)
                if converted:
                    paths.append(converted)
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        return paths

    fichiers += save_files(request.files.getlist("id_files"), "id")
    fichiers += save_files([request.files.get("domicile_file")], "domicile")
    fichiers += save_files(request.files.getlist("identite_hebergeant"), "id_hebergeant")
    fichiers += save_files(request.files.getlist("attestation_hebergement"), "attestation")

    data = load_data()
    dossier = {
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "fichiers": fichiers,
        "commentaire": "",
        "statut": "",
        "mail_non_conforme_date": "",
        "mail_conforme_date": "",
        "dernier_mail_non_conforme": "",
        "dernier_mail_conforme": ""
    }
    data.append(dossier)
    save_data(data)

    return redirect(url_for("confirmation"))

@app.route("/confirmation")
def confirmation():
    return render_template("confirmation.html")

@app.route("/admin")
def admin():
    data = load_data()
    for dossier in data:
        fichiers_existants = []
        for fichier in dossier.get("fichiers", []):
            if os.path.exists(os.path.join(UPLOAD_FOLDER, fichier)):
                fichiers_existants.append(fichier)
        dossier["fichiers"] = fichiers_existants
    return render_template("admin.html", data=data, file_count=len(os.listdir(UPLOAD_FOLDER)), dossier_count=len(data))

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        return "Fichier introuvable", 404
    return send_file(path)
