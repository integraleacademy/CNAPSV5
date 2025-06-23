from flask import Flask, render_template, request, redirect, send_file, url_for, after_this_request
import os
import json
import smtplib
import zipfile
from email.message import EmailMessage

app = Flask(__name__)
UPLOAD_FOLDER = '/mnt/data/uploads'
DATA_FILE = '/mnt/data/data.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

    fichiers = []
    identite_files = request.files.getlist('identite')
    domicile_file = request.files.get('domicile')
    identite_hebergeant = request.files.get('identite_hebergeant')
    attestation_hebergement = request.files.get('attestation_hebergement')
# Sauvegarde des fichiers
if identite_files:
    fichiers += save_files(identite_files, "identite", nom, prenom)
if domicile_file and domicile_file.filename:
    fichiers += save_files([domicile_file], "domicile", nom, prenom)
heberge_list = []
if identite_hebergeant and identite_hebergeant.filename:
    heberge_list.append(identite_hebergeant)
if attestation_hebergement and attestation_hebergement.filename:
    heberge_list.append(attestation_hebergement)
if heberge_list:
    fichiers += save_files(heberge_list, "hebergeur", nom, prenom)


    def save_files(files, prefix, nom, prenom):
        paths = []
        for file in files:
            if file and file.filename:
                filename = f"{nom}_{prenom}_{prefix}_{file.filename}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                paths.append(path)
        return paths

            
    data = load_data()
    data.append({
        "nom": nom,
        "prenom": prenom,
        "email": email,
        "fichiers": fichiers
    })
    save_data(data)

    send_email(
        "Confirmation dépôt CNAPS",
        f"""Bonjour {prenom} {nom},

Votre dossier CNAPS a bien été reçu par notre équipe.

Nous reviendrons vers vous rapidement si des documents sont manquants.

Cordialement,  
L’équipe Intégrale Academy""",
        email
    )

    return redirect('/')

@app.route('/admin')
def admin():
    data = load_data()
    return render_template('admin.html', data=data)

@app.route('/delete', methods=['POST'])
def delete():
    nom = request.form['nom']
    prenom = request.form['prenom']
    data = load_data()
    new_data = [entry for entry in data if not (entry['nom'] == nom and entry['prenom'] == prenom)]

    for entry in data:
        if entry['nom'] == nom and entry['prenom'] == prenom:
            for path in entry['fichiers']:
                if os.path.exists(path):
                    os.remove(path)

    save_data(new_data)
    return redirect('/admin')


@app.route('/download', methods=['POST'])
def download():
    nom = request.form.get('nom')
    prenom = request.form.get('prenom')
    data = load_data()
    entry = next((e for e in data if e['nom'] == nom and e['prenom'] == prenom), None)
    if not entry or not entry.get('fichiers'):
        return "Aucun fichier trouvé pour ce dossier.", 404
    zip_path = f"/tmp/{nom}_{prenom}_documents.zip"
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for fpath in entry['fichiers']:
            if os.path.exists(fpath):
                zipf.write(fpath, os.path.basename(fpath))
    @after_this_request
    def cleanup(response):
        try:
            os.remove(zip_path)
        except Exception:
            pass
        return response
    return send_file(zip_path, as_attachment=True)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for f in fichiers:
            zipf.write(f, os.path.basename(f))

    return send_file(zip_path, as_attachment=True)

def send_email(subject, body, to_email):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = os.environ["SMTP_USER"]
    msg['To'] = to_email
    msg.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        smtp.send_message(msg)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))



@app.route('/download', methods=['POST'])
def download():
    nom = request.form.get('nom')
    prenom = request.form.get('prenom')
    data = load_data()
    entry = next((e for e in data if e['nom'] == nom and e['prenom'] == prenom), None)
    if not entry or not entry.get('fichiers'):
        return "Aucun fichier trouvé pour ce dossier.", 404
    zip_path = f"/tmp/{nom}_{prenom}_documents.zip"
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for fpath in entry['fichiers']:
            if os.path.exists(fpath):
                zipf.write(fpath, os.path.basename(fpath))
    @after_this_request
    def cleanup(response):
        try:
            os.remove(zip_path)
        except Exception:
            pass
        return response
    return send_file(zip_path, as_attachment=True)
 as zipf:
                for f in fichiers:
                    if os.path.exists(f):
                        zipf.write(f, os.path.basename(f))
            return send_file(zip_path, as_attachment=True)
    return "Entrée non trouvée.", 404
