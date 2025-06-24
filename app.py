from flask import Flask, render_template, request, redirect, send_file, url_for
import os
import json
import smtplib
import zipfile
from email.message import EmailMessage

app = Flask(__name__)
UPLOAD_FOLDER = '/mnt/data/uploads'
DATA_FILE = '/mnt/data/data.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
              <div style='text-align: center;'>
                <img src='https://cnapsv5-1.onrender.com/static/logo_integrale_academy_mail.png' alt='Logo Intégrale Academy' style='max-width: 180px; margin-bottom: 20px;' />
              </div>
              <h2 style='color: #2e7d32;'>✅ Dossier CNAPS bien reçu</h2>
              <p>Bonjour <strong>{user_name}</strong>,</p>
              <p>Nous vous confirmons la bonne réception de votre dossier pour la demande d’autorisation CNAPS.</p>
              <p>Notre équipe va désormais procéder à l’étude de votre dossier et le transmettre au CNAPS pour instruction si tout est conforme.
              Si des documents sont manquants ou non conformes, nous reviendrons vers vous pour compléter votre dossier.</p>
              <p>Pour toute question, n’hésitez pas à nous contacter par mail sur l'adresse <a href='mailto:ecole@integraleacademy.com'>ecole@integraleacademy.com</a> ou par téléphone au 04 22 47 07 68.</p>
              <p style='margin-top: 30px;'>Merci pour votre confiance,</p>
              <p>L’équipe <strong>Intégrale Academy</strong></p>
              <hr>
              <p style='font-size: 12px; color: #888;'>Ce message est généré automatiquement. Merci de ne pas y répondre.</p>
            </div>
          </body>
        </html>
        """, subtype='html')

        msg_to_admin = EmailMessage()
        msg_to_admin["Subject"] = f"Nouveau dossier CNAPS reçu - {user_name}"
        msg_to_admin["From"] = smtp_user
        msg_to_admin["To"] = "isf.demande@gmail.com"
        msg_to_admin.set_content(f"""Un nouveau dossier a été déposé par {user_name} ({user_email}).\nConsultez l’espace admin pour plus d’infos.""")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg_to_user)
            server.send_message(msg_to_admin)
            print("Emails sent successfully.")

    except Exception as e:
        print(f"Erreur lors de l'envoi des emails : {e}")


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
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
        for file in files:
            if file and file.filename:
                filename = f"{nom}_{prenom}_{prefix}_{file.filename}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                paths.append(filename)
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

    print(f"Email non envoyé à {email} – fonction désactivée")

    return redirect('/?submitted=true')

@app.route('/admin')
def admin():
    data = load_data()
    return render_template('admin.html', data=data)

@app.route('/delete', methods=['POST'])
def delete():
    nom = request.form.get('nom')
    prenom = request.form.get('prenom')

    data = load_data()
    new_data = []

    for entry in data:
        if entry['nom'] == nom and entry['prenom'] == prenom:
            # Supprimer les fichiers associés
            fichiers = entry.get('fichiers', [])
            for file in fichiers:
                path = os.path.join(UPLOAD_FOLDER, file)
                if os.path.exists(path):
                    os.remove(path)
        else:
            new_data.append(entry)

    save_data(new_data)
    return redirect('/admin')


@app.route('/download', methods=['POST'])
def download():
    nom = request.form.get('nom')
    prenom = request.form.get('prenom')

    entry = next((e for e in load_data() if e["nom"] == nom and e["prenom"] == prenom), None)
    if not entry or not entry["fichiers"]:
        return "Aucun fichier trouvé.", 404

    zip_path = os.path.join(UPLOAD_FOLDER, f"{nom}_{prenom}.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in entry["fichiers"]:
            full_path = os.path.join(UPLOAD_FOLDER, file)
            if os.path.exists(full_path):
                zipf.write(full_path, file)

    return send_file(zip_path, as_attachment=True)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
