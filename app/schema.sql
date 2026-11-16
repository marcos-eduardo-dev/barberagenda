-- BarberAgenda - script de criação do banco (SQLite)
-- As tabelas seguem exatamente o MER e o dicionário de dados do relatório.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS agendamento;
DROP TABLE IF EXISTS servico;
DROP TABLE IF EXISTS profissional;
DROP TABLE IF EXISTS cliente;
DROP TABLE IF EXISTS usuario;

CREATE TABLE usuario (
    id_usuario   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         VARCHAR(100) NOT NULL,
    login        VARCHAR(30)  NOT NULL UNIQUE,
    senha_hash   VARCHAR(255) NOT NULL,
    perfil       VARCHAR(10)  NOT NULL DEFAULT 'ATENDENTE'
                 CHECK (perfil IN ('ATENDENTE', 'GERENTE'))
);

CREATE TABLE cliente (
    id_cliente    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          VARCHAR(100) NOT NULL,
    telefone      VARCHAR(15)  NOT NULL UNIQUE,
    email         VARCHAR(100),
    data_cadastro DATE NOT NULL DEFAULT (DATE('now', 'localtime'))
);

CREATE TABLE profissional (
    id_profissional INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            VARCHAR(100) NOT NULL,
    especialidade   VARCHAR(50),
    ativo           BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE servico (
    id_servico  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        VARCHAR(60)   NOT NULL,
    duracao_min INTEGER       NOT NULL CHECK (duracao_min > 0),
    preco       DECIMAL(8, 2) NOT NULL CHECK (preco >= 0)
);

CREATE TABLE agendamento (
    id_agendamento  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente      INTEGER NOT NULL REFERENCES cliente(id_cliente),
    id_profissional INTEGER NOT NULL REFERENCES profissional(id_profissional),
    id_servico      INTEGER NOT NULL REFERENCES servico(id_servico),
    id_usuario      INTEGER NOT NULL REFERENCES usuario(id_usuario),
    data            DATE    NOT NULL,
    hora            TIME    NOT NULL,
    status          VARCHAR(10) NOT NULL DEFAULT 'AGENDADO'
                    CHECK (status IN ('AGENDADO', 'CANCELADO', 'CONCLUIDO')),
    observacao      VARCHAR(200),
    criado_em       DATETIME NOT NULL DEFAULT (DATETIME('now', 'localtime'))
);

CREATE INDEX idx_agendamento_data ON agendamento (data, id_profissional);
