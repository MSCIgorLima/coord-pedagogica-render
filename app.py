# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(32)

# ---------------------------
# DADOS EM MEMÓRIA (MVP)
# ---------------------------
# Componentes curriculares cadastrados
componentes = ["Matemática", "Física"]

# Usuários (login simples para MVP)
#  - CGPG: Coordenador Geral
#  - CGPAC: Coord. de Área (possui lista de componentes sob responsabilidade)
#  - Docente: possui lista de disciplinas (componentes) e função (Regente/Auxiliar - opcional)
usuarios = {
    "cgpg": {"senha": "master123", "perfil": "CGPG"},
    "coord_area1": {"senha": "area123", "perfil": "CGPAC", "componentes": ["Matemática", "Física"]},
    "docente1": {"senha": "doc123", "perfil": "Docente", "disciplinas": ["Matemática"], "tipo": "Regente"},
}

# Catálogos (para filtros/formulários)
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

# Planos de aula (lista simples com id incremental)
planos = []
_next_id = 1

def next_id():
    global _next_id
    nid = _next_id
    _next_id += 1
    return nid

# ---------------------------
# AUTH / AUTORIZAÇÃO
# ---------------------------

def require_login():
    if "usuario" not in session:
        return redirect(url_for('login'))
    return None

def require_role(*roles):
    def wrapper(fn):
        def inner(*args, **kwargs):
            if "perfil" not in session:
                return redirect(url_for('login'))
            if session["perfil"] not in roles:
                abort(403)
            return fn(*args, **kwargs)
        inner.__name__ = fn.__name__
        return inner
    return wrapper

# ---------------------------
# LOGIN / LOGOUT
# ---------------------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        u = usuarios.get(usuario)
        if u and u.get('senha') == senha:
            session['usuario'] = usuario
            session['perfil'] = u['perfil']
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------------------
# DASHBOARDS
# ---------------------------
@app.route('/dashboard')
def dashboard():
    r = require_login()
    if r: return r
    perfil = session['perfil']
    usuario = session['usuario']

    if perfil == 'Docente':
        meus = [p for p in planos if p['autor'] == usuario]
        return render_template('dash_docente.html', planos=meus)
    elif perfil == 'CGPAC':
        comps = usuarios.get(usuario, {}).get('componentes', [])
        area_planos = [p for p in planos if p['disciplina'] in comps]
        return render_template('dash_cgpac.html', planos=area_planos, comps=comps)
    elif perfil == 'CGPG':
        enviados = sum(1 for p in planos if p['status'] == 'Enviado')
        aprovados = sum(1 for p in planos if p['status'] == 'Aprovado')
        reprovados = sum(1 for p in planos if p['status'] == 'Reprovado')
        return render_template('dash_cgpg.html', planos=planos, enviados=enviados, aprovados=aprovados, reprovados=reprovados)
    else:
        abort(403)

# ---------------------------
# DOCENTE: CRIAR PLANO
# ---------------------------
@app.route('/plano/novo', methods=['GET', 'POST'])
@require_role('Docente')
def plano_novo():
    if request.method == 'POST':
        required = ['metodologia','avaliacao','conteudo','numero_aula','periodo','recursos','habilidades']
        for f in required:
            if not request.form.get(f):
                flash(f'Campo obrigatório não preenchido: {f}', 'warning')
                return render_template('plano_form.html', series=SERIES, turnos=TURNOS, modalidades=MODALIDADES, itinerarios=ITINERARIOS, segmentos=SEGMENTOS, turmas=TURMAS)
        autor = session['usuario']
        # Docente só enxerga suas disciplinas; pegue a primeira como padrão neste MVP
        disciplinas_docente = usuarios[autor].get('disciplinas', [])
        disciplina = disciplinas_docente[0] if disciplinas_docente else 'Disciplina'
        plano = {
            'id': next_id(),
            'autor': autor,
            'disciplina': disciplina,
            'serie': request.form.get('serie') or '',
            'turno': request.form.get('turno') or '',
            'modalidade': request.form.get('modalidade') or '',
            'itinerario': request.form.get('itinerario') or '',
            'segmento': request.form.get('segmento') or '',
            'turma': request.form.get('turma') or '',
            'metodologia': request.form['metodologia'],
            'avaliacao': request.form['avaliacao'],
            'conteudo': request.form['conteudo'],
            'numero_aula': request.form['numero_aula'],
            'periodo': request.form['periodo'],
            'recursos': request.form['recursos'],
            'habilidades': request.form['habilidades'],
            'status': 'Enviado',
            'data_envio': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        planos.append(plano)
        flash('Plano enviado para validação do CGPAC.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('plano_form.html', series=SERIES, turnos=TURNOS, modalidades=MODALIDADES, itinerarios=ITINERARIOS, segmentos=SEGMENTOS, turmas=TURMAS)

# ---------------------------
# CGPAC: APROVAR / REPROVAR
# ---------------------------
@app.route('/plano/<int:pid>/aprovar', methods=['POST'])
@require_role('CGPAC')
def plano_aprovar(pid):
    usuario = session['usuario']
    comps = usuarios.get(usuario, {}).get('componentes', [])
    for p in planos:
        if p['id'] == pid and p['disciplina'] in comps:
            p['status'] = 'Aprovado'
            flash('Plano aprovado.', 'success')
            break
    return redirect(url_for('dashboard'))

@app.route('/plano/<int:pid>/reprovar', methods=['POST'])
@require_role('CGPAC')
def plano_reprovar(pid):
    usuario = session['usuario']
    comps = usuarios.get(usuario, {}).get('componentes', [])
    for p in planos:
        if p['id'] == pid and p['disciplina'] in comps:
            p['status'] = 'Reprovado'
            flash('Plano reprovado.', 'danger')
            break
    return redirect(url_for('dashboard'))

# ---------------------------
# CGPG: ADMINISTRAÇÃO
# - Cadastrar componentes curriculares
# - Cadastrar CGPAC e Docentes
# ---------------------------
@app.route('/admin')
@require_role('CGPG')
def admin_home():
    total_users = len(usuarios)
    total_componentes = len(componentes)
    total_planos = len(planos)
    return render_template('admin_index.html', total_users=total_users, total_componentes=total_componentes, total_planos=total_planos)

# Componentes
@app.route('/admin/componentes', methods=['GET', 'POST'])
@require_role('CGPG')
def admin_componentes():
    if request.method == 'POST':
        novo = (request.form.get('nome') or '').strip()
        if not novo:
            flash('Informe o nome do componente.', 'warning')
        elif novo in componentes:
            flash('Componente já existe.', 'warning')
        else:
            componentes.append(novo)
            flash('Componente cadastrado.', 'success')
        return redirect(url_for('admin_componentes'))
    return render_template('admin_componentes.html', componentes=componentes)

@app.route('/admin/componentes/remover', methods=['POST'])
@require_role('CGPG')
def admin_componentes_remover():
    nome = request.form.get('nome')
    if nome in componentes:
        componentes.remove(nome)
        # também remover dos usuários (disciplinas/componentes)
        for u, data in usuarios.items():
            if data.get('perfil') == 'CGPAC':
                data['componentes'] = [c for c in data.get('componentes', []) if c != nome]
            if data.get('perfil') == 'Docente':
                data['disciplinas'] = [d for d in data.get('disciplinas', []) if d != nome]
        flash('Componente removido.', 'info')
    return redirect(url_for('admin_componentes'))

# Usuários (CGPAC / Docente)
@app.route('/admin/usuarios')
@require_role('CGPG')
def admin_usuarios():
    # montar visão para listagem
    lista = []
    for u, data in usuarios.items():
        if u == 'cgpg':
            lista.append({'usuario': u, 'perfil': 'CGPG', 'detalhe': '-'})
        elif data.get('perfil') == 'CGPAC':
            detalhe = ', '.join(data.get('componentes', [])) or '-'
            lista.append({'usuario': u, 'perfil': 'CGPAC', 'detalhe': detalhe})
        elif data.get('perfil') == 'Docente':
            det = ', '.join(data.get('disciplinas', [])) or '-'
            tipo = data.get('tipo') or '-'
            lista.append({'usuario': u, 'perfil': f'Docente ({tipo})', 'detalhe': det})
    return render_template('admin_usuarios.html', usuarios_lista=lista)

@app.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@require_role('CGPG')
def admin_usuarios_novo():
    if request.method == 'POST':
        usuario = (request.form.get('usuario') or '').strip()
        senha = (request.form.get('senha') or '').strip()
        perfil = request.form.get('perfil')
        if not usuario or not senha or perfil not in ('CGPAC','Docente'):
            flash('Preencha usuário, senha e selecione um perfil válido.', 'warning')
            return redirect(url_for('admin_usuarios_novo'))
        if usuario in usuarios:
            flash('Usuário já existe.', 'warning')
            return redirect(url_for('admin_usuarios_novo'))
        if perfil == 'CGPAC':
            comps_sel = request.form.getlist('componentes')
            usuarios[usuario] = {"senha": senha, "perfil": "CGPAC", "componentes": comps_sel}
        else:
            discs_sel = request.form.getlist('disciplinas')
            tipo = request.form.get('tipo') or ''
            usuarios[usuario] = {"senha": senha, "perfil": "Docente", "disciplinas": discs_sel, "tipo": tipo}
        flash('Usuário cadastrado com sucesso.', 'success')
        return redirect(url_for('admin_usuarios'))
    return render_template('admin_usuarios_form.html', componentes=componentes, tipos=TIPOS_DOCENTE)

@app.route('/admin/usuarios/<usuario>/remover', methods=['POST'])
@require_role('CGPG')
def admin_usuarios_remover(usuario):
    if usuario == 'cgpg':
        flash('Não é permitido remover o usuário CGPG.', 'warning')
    elif usuario in usuarios:
        usuarios.pop(usuario, None)
        flash('Usuário removido.', 'info')
    return redirect(url_for('admin_usuarios'))

# ---------------------------
# SEED PARA DEMONSTRAÇÃO (CGPG)
# ---------------------------
@app.route('/seed_demo')
@require_role('CGPG')
def seed_demo():
    # cria alguns planos fictícios
    if not planos:
        planos.extend([
            {
                'id': next_id(), 'autor': 'docente1', 'disciplina': 'Matemática',
                'serie': '1', 'turno': 'Matutino', 'modalidade': 'Regular', 'itinerario': '1ª Série',
                'segmento': 'Ensino Médio', 'turma': 'A', 'metodologia': 'Expositiva', 'avaliacao': 'Prova',
                'conteudo': 'Funções do 1º grau', 'numero_aula': '1', 'periodo': '01/09 a 15/09', 'recursos': 'Quadro', 'habilidades': 'Resolver funções',
                'status': 'Enviado', 'data_envio': datetime.now().strftime('%d/%m/%Y %H:%M')
            },
            {
                'id': next_id(), 'autor': 'docente1', 'disciplina': 'Matemática',
                'serie': '1', 'turno': 'Matutino', 'modalidade': 'Regular', 'itinerario': '1ª Série',
                'segmento': 'Ensino Médio', 'turma': 'B', 'metodologia': 'Ativa', 'avaliacao': 'Projeto',
                'conteudo': 'Equações', 'numero_aula': '2', 'periodo': '01/09 a 15/09', 'recursos': 'Datashow', 'habilidades': 'Modelar equações',
                'status': 'Aprovado', 'data_envio': datetime.now().strftime('%d/%m/%Y %H:%M')
            },
            {
                'id': next_id(), 'autor': 'docente1', 'disciplina': 'Física',
                'serie': '2', 'turno': 'Vespertino', 'modalidade': 'Regular', 'itinerario': 'CIÊNCIAS EXATAS',
                'segmento': 'Ensino Médio', 'turma': 'C', 'metodologia': 'Laboratorial', 'avaliacao': 'Relatório',
                'conteudo': 'Cinemática', 'numero_aula': '3', 'periodo': '16/09 a 30/09', 'recursos': 'Laboratório', 'habilidades': 'Medir velocidade',
                'status': 'Reprovado', 'data_envio': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
        ])
        flash('Dados de exemplo criados.', 'info')
    else:
        flash('Já existem dados na base (memória).', 'info')
    return redirect(url_for('dashboard'))

# ---------------------------
# MAIN (local)
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
