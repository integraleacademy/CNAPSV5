import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, send_file
from datetime import datetime
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = '/mnt/data/uploads'
DB_PATH = '/mnt/data/dossiers.db'
ADMIN_PASSWORD = "admin123"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS dossiers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nom TEXT,
                        prenom TEXT,
                        email TEXT,
                        heberge TEXT,
                        fichiers TEXT,
                        statut TEXT,
                        commentaire TEXT,
                        date TEXT,
                        mail_status TEXT)''')
        conn.commit()

@app.route('/')
def index():
    password = request.args.get("admin")
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM dossiers")
        data = c.fetchall()
    return render_template('index.html', data=data, admin=password == ADMIN_PASSWORD)

@app.route('/submit', methods=['POST'])
def submit():
    nom = request.form['nom']
    prenom = request.form['prenom']
    email = request.form['email']
    heberge = request.form['heberge']
    fichiers = []

    files = request.files.getlist('piece_identite')
    for f in files:
        filename = secure_filename(f.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(path)
        fichiers.append(path)

    for key in ['justificatif_domicile', 'hebergement_pi', 'attestation_hebergement']:
        f = request.files.get(key)
        if f and f.filename:
            filename = secure_filename(f.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            f.save(path)
            fichiers.append(path)

    mail_status = "Non envoyé"
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO dossiers (nom, prenom, email, heberge, fichiers, statut, commentaire, date, mail_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (nom, prenom, email, heberge, ','.join(fichiers), 'Incomplet', '', datetime.now().strftime('%Y-%m-%d'), mail_status))
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

@app.route('/delete/<int:id>')
def delete(id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM dossiers WHERE id = ?", (id,))
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
    c.save()

    return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)