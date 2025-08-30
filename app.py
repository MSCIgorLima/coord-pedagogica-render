from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)

# Simulação de banco de dados em memória
usuarios = {
    "cgpg": {"senha": "master123", "perfil": "CGPG"},
    "coord_area1": {"senha": "area123", "perfil": "CGPAC", "componentes": ["Matemática", "Física"]},
    "docente1": {"senha": "doc123", "perfil": "Docente", "disciplinas": ["Matemática"]},
}

planos = []

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]
        if usuario in usuarios and usuarios[usuario]["senha"] == senha:
            session["usuario"] = usuario
            session["perfil"] = usuarios[usuario]["perfil"]
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    perfil = session["perfil"]
    usuario = session["usuario"]
    if perfil == "Docente":
        planos_usuario = [p for p in planos if p["autor"] == usuario]
        return render_template("dashboard_docente.html", planos=planos_usuario)
    elif perfil == "CGPAC":
        componentes = usuarios[usuario]["componentes"]
        planos_area = [p for p in planos if p["disciplina"] in componentes]
        return render_template("dashboard_cgpac.html", planos=planos_area)
    elif perfil == "CGPG":
        return render_template("dashboard_cgpg.html", planos=planos)
    return "Perfil não reconhecido"

@app.route("/novo_plano", methods=["GET", "POST"])
def novo_plano():
    if "usuario" not in session or session["perfil"] != "Docente":
        return redirect(url_for("login"))
    if request.method == "POST":
        plano = {
            "autor": session["usuario"],
            "metodologia": request.form["metodologia"],
            "avaliacao": request.form["avaliacao"],
            "conteudo": request.form["conteudo"],
            "numero_aula": request.form["numero_aula"],
            "periodo": request.form["periodo"],
            "recursos": request.form["recursos"],
            "habilidades": request.form["habilidades"],
            "disciplina": usuarios[session["usuario"]]["disciplinas"][0],
            "status": "Enviado",
            "data_envio": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        planos.append(plano)
        return redirect(url_for("dashboard"))
    return render_template("novo_plano.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
