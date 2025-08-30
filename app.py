# -*- coding: utf-8 -*-
import os, random
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

# ---------------------------
# Config
# ---------------------------
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # Heroku/Render legacy style
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg2://', 1)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
AUTO_SEED = os.environ.get('AUTO_SEED', '0') == '1'

db = SQLAlchemy(app)

# ---------------------------
# Models
# ---------------------------
class Component(db.Model):
    __tablename__ = 'components'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

class User(db.Model):
    __tablename__ = 'users'
    username = db.Column(db.String(80), primary_key=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile = db.Column(db.String(10), nullable=False)  # CGPG, CGPAC, Docente
    tipo = db.Column(db.String(20))  # Regente/Auxiliar (docente opcional)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserComponent(db.Model):
    __tablename__ = 'user_components'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), db.ForeignKey('users.username'))
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    user = db.relationship('User', backref='area_components')
    component = db.relationship('Component')

class UserDiscipline(db.Model):
    __tablename__ = 'user_disciplines'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), db.ForeignKey('users.username'))
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    user = db.relationship('User', backref='disciplines')
    component = db.relationship('Component')

class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(80), db.ForeignKey('users.username'))
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'))
    serie = db.Column(db.String(10))
    turno = db.Column(db.String(20))
    modalidade = db.Column(db.String(30))
    itinerario = db.Column(db.String(60))
    segmento = db.Column(db.String(120))
    turma = db.Column(db.String(10))
    metodologia = db.Column(db.Text, nullable=False)
    avaliacao = db.Column(db.Text, nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    numero_aula = db.Column(db.String(10), nullable=False)
    periodo = db.Column(db.String(60), nullable=False)
    recursos = db.Column(db.Text, nullable=False)
    habilidades = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(15), default='Enviado')
    data_envio = db.Column(db.String(25))
    comp = db.relationship('Component')
    autor = db.relationship('User')

# ---------------------------
# Catálogos
# ---------------------------
SERIES = ["1", "2", "3"]
TURNOS = ["Integral", "Matutino", "Vespertino", "Noturno"]
MODALIDADES = ["Integral", "EJA", "Regular"]
ITINERARIOS = ["1ª Série", "CIÊNCIAS HUMANAS", "CIÊNCIAS EXATAS", "ENSINO TÉCNICO", "NSA"]
SEGMENTOS = [
    "Ensino Médio",
    "Ensino Profissional Técnico Administração",
    "Ensino Profissional Técnico Vendas",
    "Ensino Profissional Técnico Agronegocio",
    "Ensino Profissional Técnico Logística",
    "Ensino Profissional Técnico Desenvolvimento de Sistemas",
]
TURMAS = ["A", "B", "C", "D", "E", "F"]
TIPOS_DOCENTE = ["Regente", "Auxiliar"]

# ---------------------------
# Auth helpers
# ---------------------------

def require_login():
    if 'username' not in session:
        return redirect(url_for('login'))
    return None

def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if 'profile' not in session:
                return redirect(url_for('login'))
            if session['profile'] not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

from functools import wraps

# ---------------------------
# Auth
# ---------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('usuario','').strip()
        password = request.form.get('senha','')
        user = User.query.get(username)
        if user and user.check_password(password):
            session['username'] = user.username
            session['profile'] = user.profile
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------------
# Dashboards
# ---------------------------
@app.route('/dashboard')
def dashboard():
    r = require_login()
    if r: return r
    profile = session['profile']
    username = session['username']

    if profile == 'Docente':
        meus = Plan.query.filter_by(author=username).order_by(Plan.id.desc()).all()
        return render_template('dash_docente.html', planos=meus)
    elif profile == 'CGPAC':
        comps = [uc.component.name for uc in UserComponent.query.filter_by(username=username).all()]
        area_planos = (
            db.session.query(Plan)
            .join(Component, Plan.component_id == Component.id)
            .filter(Component.name.in_(comps))
            .order_by(Plan.id.desc())
            .all()
        )
        return render_template('dash_cgpac.html', planos=area_planos, comps=comps)
    elif profile == 'CGPG':
        enviados = Plan.query.filter_by(status='Enviado').count()
        aprovados = Plan.query.filter_by(status='Aprovado').count()
        reprovados = Plan.query.filter_by(status='Reprovado').count()
        planos = Plan.query.order_by(Plan.id.desc()).all()
        return render_template('dash_cgpg.html', planos=planos, enviados=enviados, aprovados=aprovados, reprovados=reprovados)
    else:
        abort(403)

# ---------------------------
# Docente: novo plano
# ---------------------------
@app.route('/plano/novo', methods=['GET','POST'])
@require_role('Docente')
def plano_novo():
    username = session['username']
    if request.method == 'POST':
        required = ['metodologia','avaliacao','conteudo','numero_aula','periodo','recursos','habilidades']
        for f in required:
            if not request.form.get(f):
                flash(f'Campo obrigatório não preenchido: {f}', 'warning')
                return render_template('plano_form.html', series=SERIES, turnos=TURNOS, modalidades=MODALIDADES, itinerarios=ITINERARIOS, segmentos=SEGMENTOS, turmas=TURMAS)
        ud = UserDiscipline.query.filter_by(username=username).first()
        if not ud:
            flash('Docente sem disciplina vinculada. Peça ao CGPG para cadastrar.', 'warning')
            return redirect(url_for('dashboard'))
        plano = Plan(
            author=username,
            component_id=ud.component_id,
            serie=request.form.get('serie') or '',
            turno=request.form.get('turno') or '',
            modalidade=request.form.get('modalidade') or '',
            itinerario=request.form.get('itinerario') or '',
            segmento=request.form.get('segmento') or '',
            turma=request.form.get('turma') or '',
            metodologia=request.form['metodologia'],
            avaliacao=request.form['avaliacao'],
            conteudo=request.form['conteudo'],
            numero_aula=request.form['numero_aula'],
            periodo=request.form['periodo'],
            recursos=request.form['recursos'],
            habilidades=request.form['habilidades'],
            status='Enviado',
            data_envio=datetime.now().strftime('%d/%m/%Y %H:%M')
        )
        db.session.add(plano)
        db.session.commit()
        flash('Plano enviado para validação do CGPAC.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('plano_form.html', series=SERIES, turnos=TURNOS, modalidades=MODALIDADES, itinerarios=ITINERARIOS, segmentos=SEGMENTOS, turmas=TURMAS)

# ---------------------------
# CGPAC: validação
# ---------------------------
@app.route('/plano/<int:pid>/aprovar', methods=['POST'])
@require_role('CGPAC')
def plano_aprovar(pid):
    username = session['username']
    comps = [uc.component_id for uc in UserComponent.query.filter_by(username=username).all()]
    p = Plan.query.get_or_404(pid)
    if p.component_id in comps:
        p.status = 'Aprovado'
        db.session.commit()
        flash('Plano aprovado.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/plano/<int:pid>/reprovar', methods=['POST'])
@require_role('CGPAC')
def plano_reprovar(pid):
    username = session['username']
    comps = [uc.component_id for uc in UserComponent.query.filter_by(username=username).all()]
    p = Plan.query.get_or_404(pid)
    if p.component_id in comps:
        p.status = 'Reprovado'
        db.session.commit()
        flash('Plano reprovado.', 'danger')
    return redirect(url_for('dashboard'))

# ---------------------------
# CGPG: Administração
# ---------------------------
@app.route('/admin')
@require_role('CGPG')
def admin_home():
    total_users = User.query.count()
    total_componentes = Component.query.count()
    total_planos = Plan.query.count()
    return render_template('admin_index.html', total_users=total_users, total_componentes=total_componentes, total_planos=total_planos)

@app.route('/admin/componentes', methods=['GET','POST'])
@require_role('CGPG')
def admin_componentes():
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        if not nome:
            flash('Informe o nome do componente.', 'warning')
        elif Component.query.filter_by(name=nome).first():
            flash('Componente já existe.', 'warning')
        else:
            db.session.add(Component(name=nome))
            db.session.commit()
            flash('Componente cadastrado.', 'success')
        return redirect(url_for('admin_componentes'))
    comps = Component.query.order_by(Component.name.asc()).all()
    return render_template('admin_componentes.html', componentes=comps)

@app.route('/admin/componentes/remover', methods=['POST'])
@require_role('CGPG')
def admin_componentes_remover():
    nome = request.form.get('nome')
    c = Component.query.filter_by(name=nome).first()
    if c:
        UserComponent.query.filter_by(component_id=c.id).delete()
        UserDiscipline.query.filter_by(component_id=c.id).delete()
        db.session.delete(c)
        db.session.commit()
        flash('Componente removido.', 'info')
    return redirect(url_for('admin_componentes'))

@app.route('/admin/usuarios')
@require_role('CGPG')
def admin_usuarios():
    lista = []
    for u in User.query.order_by(User.username.asc()).all():
        if u.profile == 'CGPG':
            lista.append({'usuario': u.username, 'perfil': 'CGPG', 'detalhe': '-'})
        elif u.profile == 'CGPAC':
            comps = ', '.join([uc.component.name for uc in UserComponent.query.filter_by(username=u.username).all()]) or '-'
            lista.append({'usuario': u.username, 'perfil': 'CGPAC', 'detalhe': comps})
        elif u.profile == 'Docente':
            discs = ', '.join([ud.component.name for ud in UserDiscipline.query.filter_by(username=u.username).all()]) or '-'
            tipo = u.tipo or '-'
            lista.append({'usuario': u.username, 'perfil': f'Docente ({tipo})', 'detalhe': discs})
    return render_template('admin_usuarios.html', usuarios_lista=lista)

@app.route('/admin/usuarios/novo', methods=['GET','POST'])
@require_role('CGPG')
def admin_usuarios_novo():
    comps = Component.query.order_by(Component.name.asc()).all()
    if request.method == 'POST':
        usuario = (request.form.get('usuario') or '').strip()
        senha = (request.form.get('senha') or '').strip()
        perfil = request.form.get('perfil')
        if not usuario or not senha or perfil not in ('CGPAC','Docente'):
            flash('Preencha usuário, senha e selecione um perfil válido.', 'warning')
            return redirect(url_for('admin_usuarios_novo'))
        if User.query.get(usuario):
            flash('Usuário já existe.', 'warning')
            return redirect(url_for('admin_usuarios_novo'))
        u = User(username=usuario, profile=perfil)
        u.set_password(senha)
        db.session.add(u)
        db.session.commit()
        if perfil == 'CGPAC':
            comps_sel = request.form.getlist('componentes')
            for nome in comps_sel:
                c = Component.query.filter_by(name=nome).first()
                if c:
                    db.session.add(UserComponent(username=usuario, component_id=c.id))
        else:
            discs_sel = request.form.getlist('disciplinas')
            tipo = request.form.get('tipo') or ''
            u.tipo = tipo
            for nome in discs_sel:
                c = Component.query.filter_by(name=nome).first()
                if c:
                    db.session.add(UserDiscipline(username=usuario, component_id=c.id))
        db.session.commit()
        flash('Usuário cadastrado com sucesso.', 'success')
        return redirect(url_for('admin_usuarios'))
    return render_template('admin_usuarios_form.html', componentes=comps, tipos=TIPOS_DOCENTE)

@app.route('/admin/usuarios/<usuario>/remover', methods=['POST'])
@require_role('CGPG')
def admin_usuarios_remover(usuario):
    if usuario == 'cgpg':
        flash('Não é permitido remover o usuário CGPG.', 'warning')
    else:
        UserComponent.query.filter_by(username=usuario).delete()
        UserDiscipline.query.filter_by(username=usuario).delete()
        User.query.filter_by(username=usuario).delete()
        db.session.commit()
        flash('Usuário removido.', 'info')
    return redirect(url_for('admin_usuarios'))

# ---------------------------
# Seeds
# ---------------------------
FIRST_NAMES = ["Ana","Bruno","Carla","Daniel","Eduarda","Felipe","Gabriela","Hugo","Isabela","João","Karen","Luiz","Marina","Nina","Otávio","Paula","Quésia","Rafael","Sofia","Tiago"]
LAST_NAMES = ["Silva","Santos","Oliveira","Pereira","Costa","Almeida","Ferraz","Freitas","Gomes","Rodrigues","Souza","Cardoso","Moreira","Mendes","Barbosa"]
COMPONENTES_PADRAO = ["Matemática","Física","Química","Português","Biologia","Geografia","História","Inglês","Artes","Sociologia"]


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def seed_base():
    # Componentes
    for nome in COMPONENTES_PADRAO:
        if not Component.query.filter_by(name=nome).first():
            db.session.add(Component(name=nome))
    db.session.commit()

    # CGPG fixo
    if not User.query.get('cgpg'):
        u = User(username='cgpg', profile='CGPG')
        u.set_password('master123')
        db.session.add(u)
        db.session.commit()

    # 2 CGPAC
    for idx, area in enumerate([["Matemática","Física","Química"],["Português","História","Geografia"]], start=1):
        uname = f"cgpac{idx}"
        if not User.query.get(uname):
            u = User(username=uname, profile='CGPAC')
            u.set_password('area123')
            db.session.add(u)
            db.session.commit()
        # vincular componentes
        for nome in area:
            c = Component.query.filter_by(name=nome).first()
            if c and not UserComponent.query.filter_by(username=uname, component_id=c.id).first():
                db.session.add(UserComponent(username=uname, component_id=c.id))
        db.session.commit()

    # 8 Docentes
    componentes = Component.query.order_by(Component.name.asc()).all()
    for i in range(1, 9):
        uname = f"docente{i:02d}"
        if not User.query.get(uname):
            u = User(username=uname, profile='Docente', tipo=random.choice(["Regente","Auxiliar"]))
            u.set_password('doc123')
            db.session.add(u)
            db.session.commit()
        # vincular 1-2 disciplinas
        discs = random.sample(componentes, k=random.choice([1,1,2]))
        for c in discs:
            if not UserDiscipline.query.filter_by(username=uname, component_id=c.id).first():
                db.session.add(UserDiscipline(username=uname, component_id=c.id))
        db.session.commit()


def seed_plans(qtd=40):
    usuarios_doc = User.query.filter_by(profile='Docente').all()
    if not usuarios_doc:
        return
    for _ in range(qtd):
        u = random.choice(usuarios_doc)
        ud = UserDiscipline.query.filter_by(username=u.username).first()
        if not ud:
            continue
        start = datetime.now() - timedelta(days=random.randint(0, 60))
        end = start + timedelta(days=14)
        periodo = f"{start.strftime('%d/%m')} a {end.strftime('%d/%m')}"
        p = Plan(
            author=u.username,
            component_id=ud.component_id,
            serie=random.choice(SERIES),
            turno=random.choice(TURNOS),
            modalidade=random.choice(MODALIDADES),
            itinerario=random.choice(ITINERARIOS),
            segmento=random.choice(SEGMENTOS),
            turma=random.choice(TURMAS),
            metodologia=random.choice(["Expositiva","Ativa","Sala invertida","Estudos dirigidos","Laboratorial"]),
            avaliacao=random.choice(["Prova","Projeto","Relatório","Rúbrica","Autoavaliação"]),
            conteudo=random.choice(["Funções do 1º grau","Cinemática","Interpretação textual","Tabela periódica","Revolução Francesa","Cartografia"]),
            numero_aula=str(random.randint(1, 30)),
            periodo=periodo,
            recursos=random.choice(["Quadro","Datashow","Laboratório","Chromebooks","Livros didáticos"]),
            habilidades=random.choice(["Resolver problemas","Interpretar gráficos","Analisar fontes","Aplicar fórmulas","Comunicar resultados"]),
            status=random.choice(["Enviado","Aprovado","Reprovado"]),
            data_envio=start.strftime('%d/%m/%Y %H:%M')
        )
        db.session.add(p)
    db.session.commit()

# endpoint para re-seed (somente CGPG)
@app.route('/admin/reset_demo', methods=['POST'])
@require_role('CGPG')
def reset_demo():
    # limpa e repovoa
    Plan.query.delete()
    UserComponent.query.delete()
    UserDiscipline.query.delete()
    User.query.filter(User.username != 'cgpg').delete()
    Component.query.delete()
    db.session.commit()
    seed_base()
    seed_plans(40)
    flash('Demo repovoada com dados aleatórios.', 'info')
    return redirect(url_for('dashboard'))

# ---------------------------
# CLI init
# ---------------------------
@app.cli.command('initdb')
def initdb_command():
    db.create_all()
    seed_base()
    if Plan.query.count() == 0:
        seed_plans(40)
    print('DB inicializado com dados de demo.')

# ---------------------------
# Startup hook
# ---------------------------
with app.app_context():
    db.create_all()
    if AUTO_SEED:
        # só semear se base vazia
        if Component.query.count() == 0 or User.query.count() <= 1:
            seed_base()
        if Plan.query.count() == 0:
            seed_plans(40)

# ---------------------------
# Run local
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
