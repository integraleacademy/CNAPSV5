
from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DB_PATH = '/mnt/data/cnaps.db'
ADMIN_PASSWORD = 'admin123'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST' and 'admin_password' in request.form:
        if request.form['admin_password'] == ADMIN_PASSWORD:
            session['admin'] = True
        else:
            session['admin'] = False
        return redirect('/')

    is_admin = session.get('admin', False)

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT nom, prenom, email, heberge, fichiers, statut, commentaire, date, mail_status, id FROM dossiers")
        data = c.fetchall()

    return render_template('index.html', data=data, admin=is_admin)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

@app.route('/delete/<int:id>')
def delete(id):
    if not session.get('admin'):
        return redirect('/')
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM dossiers WHERE id=?", (id,))
        conn.commit()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)