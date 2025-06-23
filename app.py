
from flask import Flask, render_template, request, redirect, url_for
import os, json

app = Flask(__name__)
DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.route("/admin")
def admin():
    data = load_data()
    return render_template("admin.html", data=data)

@app.route("/delete", methods=["POST"])
def delete():
    row_id = int(request.form["row_id"])
    data = load_data()
    if 0 <= row_id < len(data):
        data.pop(row_id)
        save_data(data)
    return redirect("/admin")
