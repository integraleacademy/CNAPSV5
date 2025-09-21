from flask import Flask, render_template, request, redirect, send_file, url_for, flash
import os
import json
import smtplib
import zipfile
from email.message import EmailMessage
from PIL import Image
import pypandoc
import shutil
from datetime import datetime

# HEIC support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_OK = True
    print("[INFO] pillow-heif chargé -> HEIC support activé")
except Exception as e:
    print(f"[WARNING] HEIC non activé: {e}")
    HEIC_OK = False

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = '/mnt/data/uploads'
DATA_FILE = '/mnt/data/data.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------
# Utilitaires JSON
# -----------------------

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def clean_filename(text):
    # ✅ normalisation en minuscules pour éviter les problèmes de casse
    return text.strip().replace(" ", "_").replace("'", "").replace('"', '').lower()

# -----------------------
# Conversion fichiers
# -----------------------

def convert_to_pdf(filepath, output_filename):
    ext = os.path.splitext(filepath)[1].lower()
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{output_filename}.pdf")

    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        if ext == '.pdf':
            if os.path.abspath(filepath) != os.path.abspath(pdf_path):
                shutil.move(filepath, pdf_path)
            return os.path.basename(pdf_path)

        if ext in ['.jpg', '.jpeg', '.png', '.heic', '.webp', '.tif', '.tiff']:
            if ext == '.heic' and not HEIC_OK:
                print(f"[ERROR] HEIC reçu mais pillow-heif non dispo: {filepath}")
                os.remove(filepath)
                return None
            image = Image.open(filepath)
            if getattr(image, "is_animated", False):
                image.seek(0)
            rgb_im = image.convert('RGB')
            rgb_im.save(pdf_path)
            os.remove(filepath)
            return os.path.basename(pdf_path)

        elif ext in ['.doc', '.docx', '.odt', '.txt', '.rtf']:
            try:
                pypandoc.convert_file(filepath, 'pdf', outputfile=pdf_path)
                os.remove(filepath)
                return os.path.basename(pdf_path)
            except Exception as e:
                print(f"[ERROR] pypandoc échoué: {filepath} -> {e}")
                os.remove(filepath)
                return None

        else:
            print(f"[ERROR] Extension non supportée: {filepath}")
            os.remove(filepath)
            return None

    except Exception as e:
        print(f"[ERROR] Conversion échouée pour {filepath} : {e}")
        try:
            os.remove(filepath)
        except Exception:
            pass
        return None

# -----------------------
# Envoi mails
# -----------------------

def send_email(user_email, subject, contenu_txt, contenu_html):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_password = os.environ.get("EMAIL_PASSWORD")

    if not smtp_user or not smtp_password:
        print("⚠️ EMAIL_USER ou EMAIL_PASSWORD non définis")
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

        print(f"📧 Mail '{subject}' envoyé à {user_email}")
        return True
    except Exception as e:
        print(f"⚠️ Erreur mail {subject} -> {e}")
        return False

def send_accuse_reception(user_email, user_name):
    contenu_txt = f"Bonjour {user_name},\n\nVotre dossier a bien été transmis ✅"
    contenu_html = f"<p>Bonjour <b>{user_name}</b>,<br/>Votre dossier a bien été transmis ✅</p>"
    return send_email(user_email, "Confirmation de dépôt - Intégrale Academy", contenu_txt, contenu_html)

# -----------------------
# Sauvegarde fichiers
# -----------------------

def save_files(files, prefix, nom, prenom):
    paths = []
    for i, file in enumerate(files):
        if not file or not getattr(file, "filename", None) or file.filename.strip() == "":
            print(f"[DEBUG] Aucun fichier sélectionné pour {prefix} ({nom} {prenom}) index {i}")
            continue

        orig_ext = os.path.splitext(file.filename)[1].lower()
        base_filename = f"{nom}_{prenom}_{prefix}_{i}"
        temp_path = os.path.join(UPLOAD_FOLDER, f"{base_filename}{orig_ext}")

        try:
            file.save(temp_path)
            print(f"[DEBUG] Sauvegarde fichier brut: {temp_path}")
        except Exception as e:
            print(f"[ERROR] Impossible d'écrire {temp_path}: {e}")
            continue

        converted = convert_to_pdf(temp_path, base_filename)
        if converted:
            print(f"[INFO] Fichier sauvegardé: {converted}")
            paths.append(converted)
        else:
            print(f"[ERROR] Conversion échouée pour {temp_path}")

    return paths

# -----------------------
# Routes Flask
# -----------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    nom = clean_filename(request.form.get('nom', ''))
    prenom = clean_filename(request.form.get('prenom', ''))
    email = request.form.get('email', '')

    id_files = request.files.getlist('id_files') or []
    domicile_file = request.files.get('domicile_file')
    identite_hebergeant_files = request.files.getlist('identite_hebergeant') or []
    attestation_hebergement_files = request.files.getlist('attestation_hebergement') or []

    fichiers = []
    fichiers += save_files(id_files, "id", nom, prenom)
    fichiers += save_files([domicile_file] if domicile_file else [], "domicile", nom, prenom)
    fichiers += save_files(identite_hebergeant_files, "id_hebergeant", nom, prenom)
    fichiers += save_files(attestation_hebergement_files, "attestation", nom, prenom)

    print(f"[DEBUG] fichiers collectés pour {prenom} {nom}: {fichiers}")

    if not fichiers:
        flash("⚠️ Aucun fichier valide reçu, merci de recommencer.")
        print(f"[WARN] Aucun fichier valide pour {prenom} {nom}")
        return redirect(url_for("index"))

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

    print(f"[DEBUG] Dossier prêt à sauvegarde: {dossier}")

    data.append(dossier)
    save_data(data)

    reloaded = load_data()
    print(f"[DEBUG] Dernier dossier après sauvegarde: {reloaded[-1]}")

    send_accuse_reception(email, f"{prenom} {nom}")
    print(f"[INFO] Dossier enregistré pour {prenom} {nom} ({len(fichiers)} fichiers)")

    return redirect(url_for('confirmation'))

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/admin')
def admin():
    data = load_data()
    # ✅ plus de problème de casse, les noms de fichiers sont normalisés en minuscules
    for dossier in data:
        fichiers_existants = []
        for fichier in dossier.get("fichiers", []):
            if os.path.exists(os.path.join(UPLOAD_FOLDER, fichier)):
                fichiers_existants.append(fichier)
        dossier["fichiers"] = fichiers_existants

    file_count = len(os.listdir(UPLOAD_FOLDER))
    dossier_count = len(data)
    return render_template('admin.html', data=data, file_count=file_count, dossier_count=dossier_count)

@app.route('/mail_preview/<int:index>/<status>')
def mail_preview(index, status):
    data = load_data()
    if 0 <= index < len(data):
        if status == "conforme":
            return data[index].get("dernier_mail_conforme", "Pas de mail conforme enregistré")
        elif status == "non_conforme":
            return data[index].get("dernier_mail_non_conforme", "Pas de mail non conforme enregistré")
    return "Mail introuvable"

@app.route('/delete', methods=['POST'])
def delete():
    index = int(request.form['index'])
    data = load_data()
    if 0 <= index < len(data):
        dossier = data[index]
        for fichier in dossier["fichiers"]:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, fichier))
            except Exception:
                pass
        data.pop(index)
        save_data(data)
    return redirect(url_for('admin'))

@app.route('/download', methods=['POST'])
def download():
    index = int(request.form['index'])
    data = load_data()
    dossier = data[index]
    zip_path = os.path.join(UPLOAD_FOLDER, f"{dossier['nom']}_{dossier['prenom']}.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for fichier in dossier["fichiers"]:
            file_path = os.path.join(UPLOAD_FOLDER, fichier)
            if os.path.exists(file_path):
                zipf.write(file_path, fichier)
    return send_file(zip_path, as_attachment=True)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        return "Fichier introuvable", 404
    return send_file(path)

@app.route('/reset', methods=['POST'])
def reset():
    save_data([])
    for f in os.listdir(UPLOAD_FOLDER):
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, f))
        except Exception:
            pass
    flash("✅ Base et fichiers vidés avec succès.")
    return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
