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
            img = Image.open(filepath)
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

    except Exception as e:
        print(f"[ERROR] Conversion échouée pour {filepath} : {e}")
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
    nom = clean_filename(request.form['nom'])
    prenom = clean_filename(request.form['prenom'])
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
                orig_ext = os.path.splitext(file.filename)[1].lower()

                # Si pas d'extension, on essaie de déduire via mimetype
                if not orig_ext:
                    mt = (getattr(file, "mimetype", "") or "").lower()
                    ext_map = {
                        'image/heic': '.heic',
                        'image/heif': '.heic',
                        'image/jpeg': '.jpg',
                        'image/png': '.png',
                        'image/webp': '.webp',
                        'image/tiff': '.tif',
                        'application/pdf': '.pdf',
                    }
                    orig_ext = ext_map.get(mt, '.bin')

                temp_path = os.path.join(UPLOAD_FOLDER, f"{base_filename}{orig_ext}")
                file.save(temp_path)

                converted = convert_to_pdf(temp_path, base_filename)
                if converted:
                    final_path = os.path.join(UPLOAD_FOLDER, converted)
                    if os.path.abspath(final_path) != os.path.abspath(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception as e:
                            print(f"[WARNING] Impossible de supprimer {temp_path} : {e}")
                    paths.append(converted)
                else:
                    print(f"[WARNING] Aucun PDF généré pour {temp_path}")
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

    print(f"[INFO] Dossier reçu pour {prenom} {nom} – {len(fichiers)} fichier(s) PDF enregistrés.")
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
            else:
                print(f"[ERROR] Fichier manquant : {file_path}")
    return send_file(zip_path, as_attachment=True)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        print(f"[ERROR] Tentative d’accès à un fichier inexistant : {path}")
        return "Fichier introuvable", 404
    return send_file(path)

def send_non_conforme_email(user_email, user_name, comment):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_password = os.environ.get("EMAIL_PASSWORD")

    if not smtp_user or not smtp_password:
        print("Email environment variables not set.")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = "Documents non conformes - Intégrale Academy"
        msg["From"] = smtp_user
        msg["To"] = user_email

        contenu_txt = f"""Bonjour {user_name},

Après vérification, vos documents transmis ne sont pas conformes.
Merci de refaire la procédure.

Commentaire : {comment}

Cordialement,
L’équipe Intégrale Academy
"""
        contenu_html = f"""
        <html>
          <body style='font-family: Arial, sans-serif; color: #333;'>
            <p>Bonjour <strong>{user_name}</strong>,</p>
            <p>Après vérification, vos documents transmis <span style="color:red;"><b>ne sont pas conformes</b></span>.</p>
            <p><b>Commentaire :</b> {comment}</p>
            <p>Merci de refaire la procédure.</p>
            <p>L’équipe <strong>Intégrale Academy</strong></p>
          </body>
        </html>
        """
        msg.set_content(contenu_txt)
        msg.add_alternative(contenu_html, subtype="html")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            print(f"[MAIL] Non conforme envoyé à {user_email}")

    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email NON CONFORME : {e}")


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
        save_data(data)

        # si NON CONFORME => envoyer mail
        if status == "non conforme":
            nom_prenom = f"{data[index]['prenom']} {data[index]['nom']}"
            commentaire = data[index].get("commentaire", "Aucun commentaire")
            send_non_conforme_email(data[index]["email"], nom_prenom, commentaire)

    return redirect(url_for('admin'))

