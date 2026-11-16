"""BarberAgenda - sistema de agendamento para barbearia (Flask + SQLite)."""
import os
from functools import wraps

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

from . import db as database
from .models import Agendamento, Cliente, Profissional, Servico, Usuario, hoje


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao"),
        DATABASE=os.path.join(app.instance_path, "barberagenda.db"),
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    app.teardown_appcontext(database.close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Cria o banco: flask --app app init-db"""
        database.init_db()
        print("Banco criado em", app.config["DATABASE"])

    with app.app_context():
        if not os.path.exists(app.config["DATABASE"]):
            database.init_db()

    # ------------------------------------------------------------ autenticação
    def login_obrigatorio(view):
        """RNF02 - toda tela, exceto o login, exige usuário autenticado."""
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    @app.before_request
    def carregar_usuario():
        g.usuario = session.get("usuario")

    @app.route("/login", methods=["GET", "POST"])
    def login():  # RF01
        if request.method == "POST":
            usuario = Usuario.autenticar(request.form["login"], request.form["senha"])
            if usuario:
                session.clear()
                session["usuario"] = {"id": usuario.id_usuario, "nome": usuario.nome,
                                      "perfil": usuario.perfil}
                return redirect(url_for("agenda"))
            flash("Login ou senha inválidos.", "erro")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------------ RF02 clientes
    @app.route("/clientes", methods=["GET", "POST"])
    @login_obrigatorio
    def clientes():
        form = {}
        if request.method == "POST":
            form = request.form
            cliente = Cliente(nome=form.get("nome"), telefone=form.get("telefone"),
                              email=form.get("email"))
            erros = cliente.validar()
            if erros:
                for e in erros:
                    flash(e, "erro")
            else:
                cliente.salvar()
                flash(f"Cliente {cliente.nome} cadastrado com sucesso.", "sucesso")
                return redirect(url_for("clientes"))
        return render_template("clientes.html", clientes=Cliente.listar(), form=form)

    # ------------------------------------------------------- RF03 agendamento
    @app.route("/agendamentos/novo", methods=["GET", "POST"])
    @login_obrigatorio
    def novo_agendamento():
        form = {"data": request.args.get("data", hoje())}
        if request.method == "POST":
            form = request.form
            ag = Agendamento(
                id_cliente=form.get("id_cliente", type=int),
                id_profissional=form.get("id_profissional", type=int),
                id_servico=form.get("id_servico", type=int),
                id_usuario=g.usuario["id"],
                data=form.get("data", ""),
                hora=form.get("hora", ""),
                observacao=form.get("observacao", "").strip(),
            )
            erros = ag.validar()
            if erros:
                for e in erros:
                    flash(e, "erro")
            else:
                ag.salvar()
                flash("Agendamento confirmado.", "sucesso")
                return redirect(url_for("agenda", data=ag.data))
        return render_template(
            "agendamento_novo.html", form=form, clientes=Cliente.listar(),
            profissionais=Profissional.listar_ativos(), servicos=Servico.listar(),
        )

    # ------------------------------------------------------- RF04 agenda do dia
    @app.route("/")
    @app.route("/agenda")
    @login_obrigatorio
    def agenda():
        data = request.args.get("data") or hoje()
        id_prof = request.args.get("id_profissional", type=int)
        return render_template(
            "agenda.html", data=data, id_profissional=id_prof,
            agendamentos=Agendamento.listar_por_data(data, id_prof),
            profissionais=Profissional.listar_ativos(),
        )

    # ----------------------------------------------------------- RF05 cancelar
    @app.route("/agendamentos/<int:id_agendamento>/cancelar", methods=["POST"])
    @login_obrigatorio
    def cancelar_agendamento(id_agendamento):
        if Agendamento.cancelar(id_agendamento):
            flash("Agendamento cancelado. O horário ficou livre.", "sucesso")
        else:
            flash("Agendamento não encontrado ou já cancelado.", "erro")
        return redirect(url_for("agenda", data=request.form.get("data") or hoje()))

    # ---------------------------------------------------------- RF06 relatório
    @app.route("/relatorio")
    @login_obrigatorio
    def relatorio():
        inicio = request.args.get("inicio") or hoje()[:8] + "01"
        fim = request.args.get("fim") or hoje()
        linhas = Agendamento.relatorio_periodo(inicio, fim)
        return render_template("relatorio.html", inicio=inicio, fim=fim, linhas=linhas,
                               total_qtd=sum(l["quantidade"] for l in linhas),
                               total_valor=sum(l["total"] for l in linhas))

    @app.template_filter("br")
    def data_br(valor):
        """AAAA-MM-DD -> DD/MM/AAAA"""
        return "/".join(reversed(valor.split("-"))) if valor else ""

    @app.template_filter("fone")
    def fone(v):
        v = v or ""
        return f"({v[:2]}) {v[2:-4]}-{v[-4:]}" if len(v) in (10, 11) else v

    @app.template_filter("reais")
    def reais(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return app
