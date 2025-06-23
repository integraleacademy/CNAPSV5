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
        # Email admin
            subject="Nouveau dossier CNAPS",
            recipient="ecole@integraleacademy.com",
            body=f"Nouvelle soumission :\nNom : {nom}\nPrénom : {prenom}\nEmail : {email}"
        )

        # Email stagiaire
            subject="Confirmation de dépôt",
            recipient=email,
            body=f"Bonjour {prenom},\n\nVotre demande a bien été reçue par Intégrale Academy.\nNous la traiterons dans les plus brefs délais."
        )
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

        # Email admin
            subject="Nouveau dossier CNAPS",
            recipient="ecole@integraleacademy.com",
            body=f"Nouvelle soumission :\nNom : {nom}\nPrénom : {prenom}\nEmail : {email}"
        )

        # Email stagiaire
            subject="Confirmation de dépôt",
            recipient=email,
            body=f"Bonjour {prenom},\n\nVotre demande a bien été reçue par Intégrale Academy.\nNous la traiterons dans les plus brefs délais."
        )

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


@app.route('/update_status', methods=['POST'])
def update_status():
    nom = request.form.get('nom')
    prenom = request.form.get('prenom')
    new_status = request.form.get('statut')

    data = load_data()
    for entry in data:
        if entry['nom'] == nom and entry['prenom'] == prenom:
            entry['statut'] = new_status
    save_data(data)

        # Email admin
            subject="Nouveau dossier CNAPS",
            recipient="ecole@integraleacademy.com",
            body=f"Nouvelle soumission :\nNom : {nom}\nPrénom : {prenom}\nEmail : {email}"
        )

        # Email stagiaire
            subject="Confirmation de dépôt",
            recipient=email,
            body=f"Bonjour {prenom},\n\nVotre demande a bien été reçue par Intégrale Academy.\nNous la traiterons dans les plus brefs délais."
        )
    return redirect('/admin')

