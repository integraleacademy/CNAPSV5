from flask import Flask, render_template, request, redirect, send_file, url_for, flash
import os
import json
import smtplib
import zipfile
from email.message import EmailMessage
from PIL import Image, ImageFile
import pypandoc
import shutil
from datetime import datetime

# Activer la tolérance Pillow pour les JPEG tronqués
ImageFile.LOAD_TRUNCATED_IMAGES = True

# HEIC support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_OK = True
except Exception as e:
    print(f"[WARNING] HEIC non activé: {e}")
    HEIC_OK = False

app = Flask(__name__)
app.secret_key = "supersecretkey"
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
            return os.path.basename(filepath)

        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
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
        return os.path.basename(filepath)

# -----------------------
# Gestion des emails (style harmonisé)
# -----------------------

def template_email(titre, color, contenu_html, bouton=None):
    logo_url = "https://cnapsv5-1.onrender.com/static/logo_integrale_academy.png"
    bouton_html = ""
    if bouton:
        bouton_html = f"""
        <div style="text-align:center; margin:30px 0;">
          <a href="{bouton['url']}"
             style="display:inline-block; background:{bouton['couleur']}; color:white; padding:14px 22px; 
                    text-decoration:none; font-size:16px; font-weight:bold; border-radius:6px;">
            {bouton['texte']}
          </a>
        </div>
        """
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color:#f5f5f5; padding:20px; color:#333;">
        <div style="max-width:600px; margin:auto; background:white; padding:25px; border-radius:10px; border:1px solid #ddd;">
          
          <!-- Logo + Nom -->
          <div style="text-align:center; margin-bottom:20px;">
            <img src="{logo_url}" alt="Intégrale Academy" style="max-height:80px; width:auto; display:block; margin:auto;">
            <div style="font-size:18px; font-weight:bold; margin-top:8px;">Intégrale Academy</div>
          </div>

          <!-- Titre -->
          <h2 style="color:{color}; text-align:center; margin-top:0;">{titre}</h2>

          <!-- Contenu -->
          {contenu_html}

          <!-- Bouton -->
          {bouton_html}

          <!-- Signature -->
          <p style="margin-top:30px; text-align:center; font-size:14px; color:#555;">
            Cordialement,<br>L’équipe <strong>Intégrale Academy</strong>
          </p>
        </div>
      </body>
    </html>
    """

def send_email(user_email, subject, contenu_txt, contenu_html):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_password = os.environ.get("EMAIL_PASSWORD")

    if not smtp_user or not smtp_password:
        print("⚠️ EMAIL_USER ou EMAIL_PASSWORD non définis dans Render")
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
        print(f"⚠️ Erreur lors de l'envoi du mail ({subject}) à {user_email} : {e}")
        return False

# --- Confirmation de dépôt ---
def send_accuse_reception(user_email, user_name):
    contenu_txt = f"Bonjour {user_name},\n\nVotre dossier a bien été transmis ✅"
    contenu_html = template_email(
        "✅ Confirmation de dépôt CNAPS",
        "#27ae60",
        f"""
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>📩 Votre dossier CNAPS a bien été <span style="color:green; font-weight:bold;">transmis</span> ✅</p>
        <p>Nous allons à présent procéder à une 🔍 vérification de vos documents et nous reviendrons vers vous dans les meilleurs délais.</p>
        """
    )
    return send_email(user_email, "Confirmation de dépôt - Intégrale Academy", contenu_txt, contenu_html)

# --- Documents non conformes ---
def send_non_conforme_email(user_email, user_name, comment, dossier, data):
    contenu_txt = f"Bonjour {user_name},\n\nVos documents ne sont pas conformes ❌\nCommentaire : {comment}"
    contenu_html = template_email(
        "❌ Documents CNAPS non conformes",
        "#c0392b",
        f"""
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>❌ Après vérification par nos services, nous vous informons que les documents transmis 
        <span style="color:red; font-weight:bold;">ne sont pas conformes</span>.</p>
        
        <div style="background:#fff3cd; padding:15px; border-radius:8px; border:1px solid #ffeeba; margin:20px 0;">
          ⚠️ <strong>Détail des non conformités :</strong><br><br>
          <em>{comment}</em>
        </div>

        <p>Nous vous remercions de bien vouloir fournir des documents conformes à la réglementation en vigueur.</p>
        """,
        bouton={
            "url": url_for('index', _external=True),
            "texte": "🔄 Déposer une nouvelle demande",
            "couleur": "#27ae60"
        }
    )
    dossier["dernier_mail_non_conforme"] = contenu_html
    save_data(data)
    send_email(user_email, "Documents non conformes - Intégrale Academy", contenu_txt, contenu_html)

# --- Documents conformes ---
def send_conforme_email(user_email, user_name, dossier, data):
    contenu_txt = f"Bonjour {user_name},\n\nVos documents sont conformes ✅"
    contenu_html = template_email(
        "✅ Documents CNAPS conformes",
        "#27ae60",
        f"""
        <p>Bonjour <strong>{user_name}</strong>,</p>
        <p>✅ Après vérification par nos services, nous vous informons que les documents transmis sont 
        <span style="color:green; font-weight:bold;">conformes</span>.</p>
        <p>📤 Nous avons transmis la demande d'autorisation auprès du CNAPS – Ministère de l'intérieur.</p>
        <p>👮 Les services de l’État vont procéder à une enquête administrative (vérification des antécédents judiciaires).</p>
        <p>📮 Après enquête, vous recevrez votre autorisation par courrier postal à votre domicile.</p>
        """
    )
    dossier["dernier_mail_conforme"] = contenu_html
    save_data(data)
    send_email(user_email, "Documents conformes - Intégrale Academy", contenu_txt, contenu_html)

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

    fichiers = []
    id_files = request.files.getlist('id_files')
    domicile_files = request.files.getlist('domicile_file')
    identite_hebergeant_files = request.files.getlist('identite_hebergeant')
    attestation_hebergement_files = request.files.getlist('attestation_hebergement')

    def save_files(files, prefix, nom, prenom):
        paths = []
        for i, file in enumerate(files):
            if file and file.filename:
                base_filename = f"{nom}_{prenom}_{prefix}_{i}"
                orig_ext = os.path.splitext(file.filename)[1].lower()
                temp_path = os.path.join(UPLOAD_FOLDER, f"{base_filename}{orig_ext}")
                try:
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
                    else:
                        paths.append(os.path.basename(temp_path))
                except Exception as e:
                    print(f"[ERROR] Sauvegarde échouée : {e}")
        return paths

    fichiers += save_files(id_files, "id", nom, prenom)
    fichiers += save_files(domicile_files, "domicile", nom, prenom)
    fichiers += save_files(identite_hebergeant_files, "id_hebergeant", nom, prenom)
    fichiers += save_files(attestation_hebergement_files, "attestation", nom, prenom)

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

    send_accuse_reception(email, f"{prenom} {nom}")
    return redirect(url_for('confirmation'))

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/admin')
def admin():
    data = load_data()
    for dossier in data:
        fichiers_existants = []
        for fichier in dossier.get("fichiers", []):
            if os.path.exists(os.path.join(UPLOAD_FOLDER, fichier)):
                fichiers_existants.append(fichier)
        dossier["fichiers"] = fichiers_existants

    file_count = len(os.listdir(UPLOAD_FOLDER))
    dossier_count = len(data)

    return render_template('admin.html', data=data, file_count=file_count, dossier_count=dossier_count)

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
            send_non_conforme_email(data[index]["email"], nom_prenom, commentaire, data[index], data)
            data[index]["mail_non_conforme_date"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        elif status == "conforme":
            nom_prenom = f"{data[index]['prenom']} {data[index]['nom']}"
            send_conforme_email(data[index]["email"], nom_prenom, data[index], data)
            data[index]["mail_conforme_date"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        save_data(data)
    return redirect(url_for('admin'))

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
        prefix = f"{dossier['nom']}_{dossier['prenom']}_"
        for f in os.listdir(UPLOAD_FOLDER):
            if f.startswith(prefix):
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, f))
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
    save_data([])  # vider data.json
    for f in os.listdir(UPLOAD_FOLDER):
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, f))
        except Exception:
            pass
    flash("✅ Base et fichiers vidés avec succès.")
    return redirect(url_for('admin'))
