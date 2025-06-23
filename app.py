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
    id_files = request.files.getlist('id_files')
    domicile_file = request.files.get('domicile_file')
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
