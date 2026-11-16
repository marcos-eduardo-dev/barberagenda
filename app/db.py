"""Conexão com o banco SQLite e carga inicial de dados."""
import os
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db():
    """Abre (uma vez por requisição) a conexão com o banco."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Cria as tabelas e insere os dados iniciais (usuários, profissionais e serviços)."""
    db = get_db()
    with open(SCHEMA, encoding="utf-8") as f:
        db.executescript(f.read())

    db.executemany(
        "INSERT INTO usuario (nome, login, senha_hash, perfil) VALUES (?, ?, ?, ?)",
        [
            ("Ana Atendente", "ana", generate_password_hash("barber123"), "ATENDENTE"),
            ("Carlos Gerente", "carlos", generate_password_hash("gerente123"), "GERENTE"),
        ],
    )
    db.executemany(
        "INSERT INTO profissional (nome, especialidade) VALUES (?, ?)",
        [("João Silva", "Corte e barba"), ("Pedro Santos", "Corte degradê"), ("Lucas Oliveira", "Barba")],
    )
    db.executemany(
        "INSERT INTO servico (nome, duracao_min, preco) VALUES (?, ?, ?)",
        [("Corte", 30, 40.00), ("Barba", 30, 30.00), ("Corte + Barba", 60, 65.00), ("Sobrancelha", 15, 15.00)],
    )
    db.commit()
