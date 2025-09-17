from flask import Flask, render_template, request, redirect, send_file, url_for
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
except Exception as e:
    print(f"[WARNING] HEIC non activé: {e}")
    HEIC_OK = False

app = Flask(__name__)
UPLOAD_FOLDER = '/mnt/data/uploads'
DATA_FILE = '/mnt/data/data.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -----------------------
# Fonctions utilitaires
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
    return text.strip().replace(" ", "_").replace("'", "").replace('"', '')

def convert_to_pdf(filepath, output_filename):
    ext = os.path.splitext(filepath)[1].lower()
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{output_filename}.pdf")

    try:
        if ext == '.pdf':
            shutil.copy(filepath, pdf_path)
            return os.path.basename(pdf_path)

        try:
            img = Image.open(filepath)
            if getattr(img, "is_animated", False):
                img.seek(0)
            rgb_im = img.convert('RGB')
            rgb_im.save(pdf_path)
            return os.path.basename(pdf_path)
        except Exception:
            pass

        if ext in ['.jpg', '.jpeg', '.png', '.heic', '.webp', '.tif', '.tiff']:
            if ext == '.heic' and not HEIC_OK:
                return None
            image = Image.open(filepath)
            if getattr(image, "is_animated", False):
                image.seek(0)
            rgb_im = image.convert('RGB')
            rgb_im.save(pdf_path)
            return os.path.basename(pdf_path)

        elif ext in ['.doc', '.docx', '.odt', '.txt', '.rtf']:
            pypandoc.convert_file(filepath, 'pdf', outputfile=pdf_path)
            return os.path.basename(pdf_path)

        return None

    except Exception as e:
        print(f"[ERROR] Conversion échouée : {e}")
        return None


# -----------------------
# Gestion des emails
# -----------------------

def send_email_notification(user_email, user_name):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_password = os.environ.get("EMAIL_PASSWORD")

    if not smtp_user or not smtp_password:
        print("Email environment variables not set.")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = "Confirmation de dépôt de dossier CNAPS - Intégrale Academy"
        msg["From"] = smtp_user
        msg["To"] = user_email
        msg.set_content(f"""Bonjour {user_name},

Nous avons bien reçu votre dossier CNAPS. Il est en cours de traitement.

Merci pour votre confiance,
L’équipe Intégrale Academy.""")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")


def send_non_conforme_email(user_email, user_name, comment, dossier):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_password = os.environ.get("EMAIL_PASSWORD")

    contenu_txt = f"""Bonjour {user_name},

Après vérification, vos documents transmis ne sont pas conformes.
Merci de refaire la procédure en suivant le lien ci-dessous :
{url_for('index', _external=True)}

⚠️ Il est très important de fournir uniquement les documents demandés (voir la liste précisée sur le formulaire).

Commentaire : {comment}

Cordialement,
L’équipe Intégrale Academy
"""

    contenu_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color:#f5f5f5; padding:20px; color:#333;">
        <div style="max-width:600px; margin:auto; background:white; padding:20px; border-radius:10px; border:1px solid #ddd;">
          <h2 style="color:#c0392b;">❌ Documents non conformes CNAPS</h2>
          <p>Bonjour <strong>{user_name}</strong>,</p>
          <p>Après vérification, vos documents transmis <span style="color:red; font-weight:bold;">ne sont pas conformes</span>.</p>
          <p style="background:#fff3cd; padding:10px; border-radius:5px; border:1px solid #ffeeba;">
            ⚠️ <strong>Merci de fournir uniquement les documents demandés</strong>.
          </p>
          <p><b>Détail :</b><br/><em>{comment}</em></p>
          <div style="text-align:center; margin:20px 0;">
            <a href="{url_for('index', _external=True)}" 
               style="background:#27ae60; color:white; padding:12px 20px; text-decoration:none; font-size:16px; border-radius:5px;">
               🔄 Déposer une nouvelle demande
            </a>
          </div>
          <p>Merci de refaire la procédure dès que possible.</p>
          <p>L’équipe <strong>Intégrale Academy</strong></p>
        </div>
      </body>
    </html>
    """

    # On sauvegarde le mail dans le dossier
    dossier["dernier_mail_non_conforme"] = contenu_html

    if not smtp_user or not smtp_password:
        print("Email environment variables not set.")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = "Documents non conformes - Intégrale Academy"
        msg["From"] = smtp_user
        msg["To"] = user_email
        msg.set_content(contenu_txt)
        msg.add_alternative(contenu_html, subtype="html")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            print(f"[MAIL] Non conforme envoyé à {user_email}")

    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email NON CONFORME : {e}")


# -----------------------
# Routes Flask
# -----------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    nom = clean_filename(request.form['nom'])
    prenom = clean_filename(request.form['prenom'])
    email = request.form['email']
    send_email_notification(email, f"{prenom} {nom}")

    fichiers = []
    id_files = request.files.getlist('id_files')
    domicile_file = request.files.get('domicile_file')
    identite_hebergeant = request.files.get('identite_hebergeant')
    attestation_hebergement = request.files.get('attestation_hebergement')

    def save_files(files, prefix, nom, prenom):
        paths = []
        for i, file in enumerate(files):
            if file and file.filename:
                base_filename = f"{nom}_{prenom}_{prefix}_{i}"
                orig_ext = os.path.splitext(file.filename)[1].lower()
                temp_path = os.path.join(UPLOAD_FOLDER, f"{base_filename}{orig_ext}")
                file.save(temp_path)
                converted = convert_to_pdf(temp_path, base_filename)
                if converted:
                    final_path = os.path.join(UPLOAD_FOLDER, converted)
                    if os.path.abspath(final_path) != os.path.abspath(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
                    paths.append(converted)
        return paths

    fichiers += save_files(id_files, "id", nom, prenom)
    fichiers += save_files([domicile_file], "domicile", nom, prenom)
    fichiers += save_files([identite_hebergeant], "id_hebergeant", nom, prenom)
    fichiers += save_files([attestation_hebergement], "attestation", nom, prenom)

    data = load_data()
    data.append({
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "fichiers": fichiers,
        "commentaire": "",
        "statut": "",
        "mail_non_conforme_date": "",
        "mail_conforme_date": "",
        "dernier_mail_non_conforme": ""
    })
    save_data(data)

    return redirect(url_for('index', submitted="true"))

@app.route('/admin')
def admin():
    data = load_data()
    return render_template('admin.html', data=data)

@app.route('/save_comment', methods=['POST'])
def save_comment():
    index = int(request.form['index'])
    comment = request.form['commentaire']
    data = load_data()
    if 0 <= index < len(data):
        data[index]["commentaire"] = comment
        save_data(data)
    return redirect(url_for('admin'))

@app.route('/set_status', methods=['POST'])
def set_status():
    index = int(request.form['index'])
    status = request.form['status']
    data = load_data()
    if 0 <= index < len(data):
        data[index]["statut"] = status
        if status == "non conforme":
            nom_prenom = f"{data[index]['prenom']} {data[index]['nom']}"
            commentaire = data[index].get("commentaire", "Aucun commentaire")
            send_non_conforme_email(data[index]["email"], nom_prenom, commentaire, data[index])
            data[index]["mail_non_conforme_date"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        elif status == "conforme":
            data[index]["mail_conforme_date"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        save_data(data)
    return redirect(url_for('admin'))

@app.route('/delete', methods=['POST'])
def delete():
    index = int(request.form['index'])
    data = load_data()
    if 0 <= index < len(data):
        for fichier in data[index]["fichiers"]:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, fichier))
            except:
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
