
import sqlite3
import requests
from flask import Flask, render_template, request, redirect
from bs4 import BeautifulSoup

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_cnaps_status(link):
    try:
        if not link:
            return ""
        response = requests.get(link, timeout=10)
        if response.status_code == 200:
            content = response.text.lower()
            if "accepté" in content:
                return "accepté"
            elif "instruction" in content:
                return "instruction en cours"
            elif "décision" in content:
                return "décision en cours"
    except Exception as e:
        print("Erreur lors de la vérification CNAPS :", e)
    return ""

@app.route('/')
def index():
    conn = get_db_connection()
    dossiers = conn.execute('SELECT * FROM dossiers').fetchall()
    updated_dossiers = []
    for dossier in dossiers:
        dossier = dict(dossier)
        status = check_cnaps_status(dossier['lien'])
        dossier['check_auto'] = status
        updated_dossiers.append(dossier)
    conn.close()
    return render_template('index.html', dossiers=updated_dossiers)

@app.route('/add', methods=['POST'])
def add():
    nom = request.form['nom']
    prenom = request.form['prenom']
    formation = request.form.get('formation', '')
    session = request.form.get('session', '')
    lien = request.form.get('lien', '')
    statut = "INCOMPLET"
    statut_cnaps = ""
    commentaire = ""
    conn = get_db_connection()
    conn.execute("INSERT INTO dossiers (nom, prenom, formation, session, lien, statut, statut_cnaps, commentaire) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (nom, prenom, formation, session, lien, statut, statut_cnaps, commentaire))
    conn.commit()
    conn.close()
    return redirect('/')

# autres routes comme /edit, /delete, etc. seraient ici aussi

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=10000)
