from flask import Flask, render_template, request, redirect, send_file, send_from_directory
import os, json, zipfile, smtplib
from email.message import EmailMessage

app = Flask(__name__)

# ──────────────────────────────
#  CHEMINS ET DOSSIERS
# ──────────────────────────────
BASE_DIR      = app.root_path                    # dossier du projet
STATIC_DIR    = os.path.join(BASE_DIR, 'static') # /static
UPLOAD_FOLDER = os.path.join(STATIC_DIR, 'uploads')
DATA_FILE     = os.path.join(BASE_DIR, 'data.json')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ──────────────────────────────
#  OUTILS INTERNES
# ──────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_files(files, prefix, nom, prenom):
    """
    Enregistre les fichiers reçus dans /static/uploads et renvoie
    la liste des NOMS DE FICHIER (pas le chemin complet).
    """
    saved = []
    for f in files:
        if f and f.filename:
            safe_name = f.filename.replace(' ', '_')
            fname = f"{nom}_{prenom}_{prefix}_{safe_name}"
            f.save(os.path.join(UPLOAD_FOLDER, fname))
            saved.append(fname)
    return saved

def send_email(subject, body, to_addr):
    """Envoi basique via Gmail – configure SMTP_USER / SMTP_PASS en variables d’env."""
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    if not smtp_user or not smtp_pass:
        return
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_addr
    msg.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(smtp_user, smtp_pass)
        s.send_message(msg)

# ──────────────────────────────
#  ROUTES
# ──────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    nom    = request.form['nom']
    prenom = request.form['prenom']
    email  = request.form['email']

    fichiers  = save_files(request.files.getlist('id_files'), 'id', nom, prenom)
    domicile  = request.files.get('domicile_file')
    if domicile:
        fichiers += save_files([domicile], 'domicile', nom, prenom)
    fichiers += save_files(request.files.getlist('hebergeur_files'), 'hebergeur', nom, prenom)

    data = load_data()
    data.append({'nom': nom, 'prenom': prenom, 'email': email, 'fichiers': fichiers})
    save_data(data)

    send_email(
        'Confirmation dépôt CNAPS',
        f'Bonjour {prenom} {nom},\n\nVotre dossier a bien été reçu.\n',
        email
    )
    return redirect('/')

@app.route('/admin')
def admin():
    return render_template('admin.html', data=load_data())

@app.route('/delete', methods=['POST'])
def delete():
    nom    = request.form['nom']
    prenom = request.form['prenom']

    data, new_data = load_data(), []
    for entry in data:
        if entry['nom'] == nom and entry['prenom'] == prenom:
            for fname in entry['fichiers']:
                path = os.path.join(UPLOAD_FOLDER, fname)
                if os.path.exists(path):
                    os.remove(path)
        else:
            new_data.append(entry)

    save_data(new_data)
    return redirect('/admin')

@app.route('/download', methods=['POST'])
def download():
    nom, prenom = request.form['nom'], request.form['prenom']
    entry = next((e for e in load_data()
                  if e['nom'] == nom and e['prenom'] == prenom), None)
    if not entry:
        return 'Aucun dossier', 404

    zip_name = f"{nom}_{prenom}.zip"
    zip_path = os.path.join(UPLOAD_FOLDER, zip_name)

    with zipfile.ZipFile(zip_path, 'w') as z:
        for fname in entry['fichiers']:
            z.write(os.path.join(UPLOAD_FOLDER, fname), fname)

    return send_file(zip_path, as_attachment=True)

# Sert les fichiers uploadés : /uploads/<nom_du_fichier>
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ──────────────────────────────
#  LANCEMENT (compat. Render)
# ──────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
