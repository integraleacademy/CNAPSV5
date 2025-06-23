
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
import os
import smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename
import sqlite3
from datetime import datetime
from reportlab.pdfgen import canvas
import zipfile

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = '/mnt/data/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB_PATH = '/mnt/data/cnaps.db'

ADMIN_PASSWORD = 'admin123'
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS dossiers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nom TEXT,
                        prenom TEXT,
                        email TEXT,
                        heberge INTEGER,
                        fichiers TEXT,
                        statut TEXT,
                        commentaire TEXT,
                        date TEXT
                    )''')
        conn.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    admin_html = ""
    if request.method == 'POST' and 'admin_pass' in request.form:
        if request.form['admin_pass'] == ADMIN_PASSWORD:
            session['admin'] = True
        else:
            flash("Mot de passe incorrect")

    if session.get('admin'):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            dossiers = c.execute("SELECT * FROM dossiers").fetchall()
        admin_html = "<table><tr><th>Nom</th><th>Prénom</th><th>Email</th><th>Statut</th><th>Commentaire</th><th>Actions</th></tr>"
        for d in dossiers:
            admin_html += f'''
                <tr>
                    <td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td>
                    <td>
                        <form action="/update/{d[0]}" method="post">
                            <select name="statut">
                                <option {'selected' if d[6]=='Complet' else ''}>Complet</option>
                                <option {'selected' if d[6]=='Incomplet' else ''}>Incomplet</option>
                            </select>
                    </td>
                    <td><input type="text" name="commentaire" value="{d[7]}"></td>
                    <td>
                        <button type="submit">Mettre à jour</button>
                        </form>
                        <a href="/generate_pdf/{d[0]}">PDF</a> | <a href="/download_all/{d[0]}">.zip</a>
                    </td>
                </tr>'''
        admin_html += "</table>"
    else:
        admin_html = '''
        <form method="post">
            <input type="password" name="admin_pass" placeholder="Mot de passe admin" required>
            <button type="submit">Connexion</button>
        </form>'''

    return render_template('index.html', admin_html=admin_html)

@app.route('/submit', methods=['POST'])
def submit():
    nom = request.form['nom']
    prenom = request.form['prenom']
    email = request.form['email']
    heberge = 1 if 'heberge' in request.form else 0
    fichiers = []

    for field in ['identite', 'domicile']:
        file = request.files.get(field)
        if file:
            filename = f"{nom}_{prenom}_{secure_filename(file.filename)}"
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
            fichiers.append(filename)

    if heberge:
        for field in ['identite_hebergeant', 'attestation_hebergement']:
            file = request.files.get(field)
            if file:
                filename = f"{nom}_{prenom}_{secure_filename(file.filename)}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                fichiers.append(filename)

    msg = EmailMessage()
    msg['Subject'] = "Confirmation de dépôt de dossier CNAPS"
    msg['From'] = SMTP_USER
    msg['To'] = email
    msg.set_content(f"Bonjour {prenom},\n\nVotre dossier a bien été reçu.\n\nDocuments reçus : {', '.join(fichiers)}")

    try:
        try:
    print("Tentative d'envoi à", email)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)
except Exception as e:
    print("Erreur envoi mail:", e)
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
    except Exception as e:
        print("Erreur envoi mail:", e)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO dossiers (nom, prenom, email, heberge, fichiers, statut, commentaire, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (nom, prenom, email, heberge, ','.join(fichiers), 'Incomplet', '', datetime.now().strftime('%Y-%m-%d')))
        conn.commit()

    return redirect(url_for('index'))

@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    statut = request.form['statut']
    commentaire = request.form['commentaire']
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE dossiers SET statut = ?, commentaire = ? WHERE id = ?", (statut, commentaire, id))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/generate_pdf/<int:id>')
def generate_pdf(id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        dossier = c.execute("SELECT nom, prenom FROM dossiers WHERE id = ?", (id,)).fetchone()

    pdf_path = f"/mnt/data/{dossier[0]}_{dossier[1]}_attestation.pdf"
    c = canvas.Canvas(pdf_path)
    c.drawString(100, 750, "Attestation de dépôt de dossier CNAPS")
    c.drawString(100, 700, f"Nom : {dossier[0]}")
    c.drawString(100, 680, f"Prénom : {dossier[1]}")
    c.drawString(100, 660, "Votre dossier a bien été déposé.")
    c.save()

    return send_from_directory('/mnt/data', os.path.basename(pdf_path), as_attachment=True)

@app.route('/download_all/<int:id>')
def download_all(id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        dossier = c.execute("SELECT nom, prenom, fichiers FROM dossiers WHERE id = ?", (id,)).fetchone()
    nom, prenom, fichiers = dossier
    filenames = fichiers.split(',')

    zip_name = f"{nom}_{prenom}_documents.zip"
    zip_path = f"/mnt/data/{zip_name}"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for filename in filenames:
            full_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(full_path):
                zipf.write(full_path, arcname=filename)

    return send_from_directory('/mnt/data', zip_name, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
