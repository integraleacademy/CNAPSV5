from flask import Flask, render_template, request, redirect, send_file, url_for
import os
import json
import smtplib
import zipfile
from email.message import EmailMessage
from PIL import Image
import pypandoc

app = Flask(__name__)
UPLOAD_FOLDER = '/mnt/data/uploads'
DATA_FILE = '/mnt/data/data.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def convert_to_pdf(filepath, output_filename):
    ext = os.path.splitext(filepath)[1].lower()
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{output_filename}.pdf")

    try:
        if ext in ['.jpg', '.jpeg', '.png']:
            image = Image.open(filepath)
            rgb_im = image.convert('RGB')
            rgb_im.save(pdf_path)
        elif ext in ['.doc', '.docx', '.odt', '.txt', '.rtf']:
            pypandoc.convert_file(filepath, 'pdf', outputfile=pdf_path)
        else:
            print(f"Format non pris en charge pour la conversion : {ext}")
            return None
        return os.path.basename(pdf_path)
    except Exception as e:
        print(f"Erreur lors de la conversion de {filepath} : {e}")
        return None

def send_email_notification(user_email, user_name):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_password = os.environ.get("EMAIL_PASSWORD")

    if not smtp_user or not smtp_password:
        print("Email environment variables not set.")
        return

    try:
        msg_to_user = EmailMessage()
        msg_to_user["Subject"] = "Confirmation de dépôt de dossier CNAPS - Intégrale Academy"
        msg_to_user["From"] = smtp_user
        msg_to_user["To"] = user_email
        msg_to_user.set_content(f"""Bonjour {user_name},\n\nNous avons bien reçu votre dossier CNAPS. Il est en cours de traitement.\n\nMerci pour votre confiance,\nL’équipe Intégrale Academy.""")
        msg_to_user.add_alternative(f"""
        <html>
          <body style='font-family: Arial, sans-serif; color: #333;'>
            <div style='max-width: 600px; margin: auto; border: 1px solid #ccc; padding: 20px; border-radius: 10px;'>
              <p>Bonjour <strong>{user_name}</strong>,</p>
              <p>Nous avons bien reçu votre dossier CNAPS. Il est en cours de traitement.</p>
              <p>Merci pour votre confiance,</p>
              <p>L’équipe <strong>Intégrale Academy</strong></p>
            </div>
          </body>
        </html>
        """, subtype='html')

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg_to_user)

    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    nom = request.form['nom']
    prenom = request.form['prenom']
    email = request.form['email']
    send_email_notification(email, f"{prenom} {nom}")

    fichiers = []
    id_files = request.files.getlist('id_files')
    domicile_file = request.files.get('domicile_file')
    identite_hebergeant = request.files.get('identite_hebergeant')
    attestation_hebergement = request.files.get('attestation_hebergement')
    hebergeur_files = request.files.getlist('hebergeur_files')

    def save_files(files, prefix, nom, prenom):
        paths = []
        for i, file in enumerate(files):
            if file and file.filename:
                base_filename = f"{nom}_{prenom}_{prefix}_{i}"
                temp_path = os.path.join(UPLOAD_FOLDER, f"{base_filename}{os.path.splitext(file.filename)[1]}")
                file.save(temp_path)
                converted = convert_to_pdf(temp_path, base_filename)
                if converted:
                    os.remove(temp_path)
                    paths.append(converted)
        return paths

    fichiers += save_files(id_files, "id", nom, prenom)
    fichiers += save_files([domicile_file], "domicile", nom, prenom)
    fichiers += save_files(hebergeur_files, "hebergeur", nom, prenom)
    fichiers += save_files([identite_hebergeant], "id_hebergeant", nom, prenom)
    fichiers += save_files([attestation_hebergement], "attestation", nom, prenom)

    data = load_data()
    data.append({
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "fichiers": fichiers
    })
    save_data(data)

    print(f"Dossier reçu pour {prenom} {nom} – {len(fichiers)} fichier(s) PDF enregistrés.")
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    data = load_data()
    return render_template('admin.html', data=data)

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
    return send_file(os.path.join(UPLOAD_FOLDER, filename))
