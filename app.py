import os
import sqlite3
from flask import Flask, render_template, request, redirect, send_file
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
UPLOAD_FOLDER = '/mnt/data/uploads'
DB_PATH = '/mnt/data/dossiers.db'
ADMIN_PASSWORD = 'admin123'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Création de la base si elle n'existe pas
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
        mail_status TEXT DEFAULT 'Non envoyé'
    )''')
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
    heberge = request.form.get('heberge', 'non')

    fichiers = []
    for champ in ['piece_identite', 'justificatif_domicile', 'hebergement_pi', 'attestation_hebergement']:
        if champ in request.files:
            fichiers_champ = request.files.getlist(champ)
            for f in fichiers_champ:
                if f.filename:
                    filename = f"{datetime.now().timestamp()}_{f.filename}"
                    path = os.path.join(UPLOAD_FOLDER, filename)
                    f.save(path)
                    fichiers.append(filename)

    try:
        print("Tentative d'envoi à", email)
        msg = EmailMessage()
        msg['Subject'] = "Confirmation de dépôt de dossier"
        msg['From'] = "ecole@integraleacademy.com"
        msg['To'] = email
        msg.set_content("Bonjour,\n\nVotre dossier a bien été transmis. Nous reviendrons vers vous rapidement.\n\nL'équipe Intégrale Academy.")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login("ecole@integraleacademy.com", "Lv15052021@")
            smtp.send_message(msg)

        mail_status = "Envoyé"
    except Exception as e:
        print("Erreur mail :", e)
        mail_status = "Erreur"

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO dossiers (nom, prenom, email, heberge, fichiers, statut, commentaire, date, mail_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (nom, prenom, email, heberge, ','.join(fichiers), 'Incomplet', '', datetime.now().strftime('%Y-%m-%d'), mail_status))
        conn.commit()
    return redirect('/')

@app.route('/delete/<int:id>')
def delete(id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM dossiers WHERE id=?", (id,))
        conn.commit()
    return redirect('/?admin=' + ADMIN_PASSWORD)

@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    statut = request.form['statut']
    commentaire = request.form['commentaire']
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE dossiers SET statut=?, commentaire=? WHERE id=?", (statut, commentaire, id))
        conn.commit()
    return redirect('/?admin=' + ADMIN_PASSWORD)

@app.route('/generate_pdf/<int:id>')
def generate_pdf(id):
    from reportlab.pdfgen import canvas
    pdf_path = os.path.join(UPLOAD_FOLDER, f'dossier_{id}.pdf')
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM dossiers WHERE id=?', (id,))
        dossier = c.fetchone()
    if dossier:
        c = canvas.Canvas(pdf_path)
        c.drawString(100, 750, f"Nom : {dossier[1]}")
        c.drawString(100, 730, f"Prénom : {dossier[2]}")
        c.drawString(100, 710, f"Email : {dossier[3]}")
        c.drawString(100, 690, f"Statut : {dossier[6]}")
        c.save()
        return send_file(pdf_path, as_attachment=True)
    return 'Dossier introuvable', 404

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=10000)
