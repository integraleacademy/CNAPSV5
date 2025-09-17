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

# ... (toutes tes fonctions existantes convert_to_pdf, send_email_notification, etc.)

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
              <h2 style="color:#c0392b;">❌ Documents non conformes</h2>
              <p>Bonjour <strong>{user_name}</strong>,</p>
              <p>Après vérification, vos documents transmis <span style="color:red; font-weight:bold;">ne sont pas conformes</span>.</p>
              
              <p style="background:#fff3cd; padding:10px; border-radius:5px; border:1px solid #ffeeba;">
                ⚠️ <strong>Il est très important de fournir uniquement les documents demandés</strong> 
                (voir la liste précisée sur le formulaire).
              </p>
              
              <p><b>Commentaire de l’administration :</b><br/>
              <em>{comment}</em></p>

              <div style="text-align:center; margin:20px 0;">
                <a href="{url_for('index', _external=True)}" 
                   style="background:#27ae60; color:white; padding:12px 20px; text-decoration:none; font-size:16px; border-radius:5px;">
                   🔄 Refaire le dépôt de documents
                </a>
              </div>

              <p>Merci de bien vouloir recommencer la procédure dès que possible.</p>
              <p>L’équipe <strong>Intégrale Academy</strong></p>
            </div>
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

        if status == "non conforme":
            nom_prenom = f"{data[index]['prenom']} {data[index]['nom']}"
            commentaire = data[index].get("commentaire", "Aucun commentaire")
            send_non_conforme_email(data[index]["email"], nom_prenom, commentaire)
            data[index]["mail_non_conforme_date"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        save_data(data)
    return redirect(url_for('admin'))
