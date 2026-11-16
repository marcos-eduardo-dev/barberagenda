"""Classes de domínio do BarberAgenda.

Cada classe corresponde a uma classe do Diagrama de Classes e a uma tabela do MER
(mesmos nomes de atributos e de colunas).
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from werkzeug.security import check_password_hash

from .db import get_db

HORA_ABERTURA = time(9, 0)
HORA_FECHAMENTO = time(19, 0)


# --------------------------------------------------------------------------- Usuario
@dataclass
class Usuario:
    id_usuario: int
    nome: str
    login: str
    perfil: str

    @staticmethod
    def autenticar(login, senha):
        """RF01 - devolve o Usuario se login e senha conferem, senão None."""
        row = get_db().execute(
            "SELECT * FROM usuario WHERE login = ?", (login.strip(),)
        ).fetchone()
        if row and check_password_hash(row["senha_hash"], senha):
            return Usuario(row["id_usuario"], row["nome"], row["login"], row["perfil"])
        return None


# --------------------------------------------------------------------------- Cliente
@dataclass
class Cliente:
    nome: str
    telefone: str
    email: str = ""
    id_cliente: int = None
    data_cadastro: str = None

    def validar(self):
        """Regras do RF02. Devolve a lista de erros (vazia = válido)."""
        erros = []
        self.nome = (self.nome or "").strip()
        self.telefone = re.sub(r"\D", "", self.telefone or "")
        self.email = (self.email or "").strip()

        if len(self.nome) < 3:
            erros.append("Informe o nome do cliente (mínimo 3 letras).")
        if len(self.telefone) not in (10, 11):
            erros.append("Informe um telefone válido com DDD (10 ou 11 dígitos).")
        elif get_db().execute(
            "SELECT 1 FROM cliente WHERE telefone = ?", (self.telefone,)
        ).fetchone():
            erros.append("Já existe um cliente cadastrado com este telefone.")
        if self.email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email):
            erros.append("E-mail inválido.")
        return erros

    def salvar(self):
        """RF02 - grava o cliente no banco (INSERT)."""
        db = get_db()
        cur = db.execute(
            "INSERT INTO cliente (nome, telefone, email) VALUES (?, ?, ?)",
            (self.nome, self.telefone, self.email or None),
        )
        db.commit()
        self.id_cliente = cur.lastrowid
        return self.id_cliente

    @staticmethod
    def listar():
        return get_db().execute(
            "SELECT * FROM cliente ORDER BY nome"
        ).fetchall()


# ---------------------------------------------------------------------- Profissional
@dataclass
class Profissional:
    id_profissional: int
    nome: str
    especialidade: str
    ativo: bool = True

    @staticmethod
    def listar_ativos():
        return get_db().execute(
            "SELECT * FROM profissional WHERE ativo = 1 ORDER BY nome"
        ).fetchall()


# --------------------------------------------------------------------------- Servico
@dataclass
class Servico:
    id_servico: int
    nome: str
    duracao_min: int
    preco: float

    @staticmethod
    def listar():
        return get_db().execute("SELECT * FROM servico ORDER BY nome").fetchall()

    @staticmethod
    def buscar_por_id(id_servico):
        return get_db().execute(
            "SELECT * FROM servico WHERE id_servico = ?", (id_servico,)
        ).fetchone()


# ----------------------------------------------------------------------- Agendamento
@dataclass
class Agendamento:
    id_cliente: int
    id_profissional: int
    id_servico: int
    id_usuario: int
    data: str          # AAAA-MM-DD
    hora: str          # HH:MM
    observacao: str = ""
    status: str = "AGENDADO"
    id_agendamento: int = None

    def validar(self, agora=None):
        """Regras do RF03. Devolve a lista de erros (vazia = válido)."""
        agora = agora or datetime.now()
        erros = []
        if not (self.id_cliente and self.id_profissional and self.id_servico):
            erros.append("Selecione cliente, profissional e serviço.")
        try:
            inicio = datetime.strptime(f"{self.data} {self.hora}", "%Y-%m-%d %H:%M")
        except ValueError:
            erros.append("Informe data e hora válidas.")
            return erros
        servico = Servico.buscar_por_id(self.id_servico)
        if servico is None:
            erros.append("Serviço inexistente.")
            return erros

        fim = inicio + timedelta(minutes=servico["duracao_min"])
        if inicio < agora:
            erros.append("Não é possível agendar em data ou hora que já passou.")
        if inicio.time() < HORA_ABERTURA or fim.time() > HORA_FECHAMENTO or fim.date() != inicio.date():
            erros.append("Horário fora do funcionamento da barbearia (09:00 às 19:00).")
        if not erros and self.verificar_conflito(inicio, fim):
            erros.append("O profissional já tem um agendamento neste horário. Escolha outro horário.")
        return erros

    def verificar_conflito(self, inicio, fim):
        """RN01 - há outro agendamento ATIVO do mesmo profissional que se sobrepõe?"""
        rows = get_db().execute(
            """SELECT a.hora, s.duracao_min
                 FROM agendamento a
                 JOIN servico s ON s.id_servico = a.id_servico
                WHERE a.id_profissional = ? AND a.data = ? AND a.status = 'AGENDADO'""",
            (self.id_profissional, self.data),
        ).fetchall()
        for r in rows:
            outro_inicio = datetime.strptime(f"{self.data} {r['hora']}", "%Y-%m-%d %H:%M")
            outro_fim = outro_inicio + timedelta(minutes=r["duracao_min"])
            if inicio < outro_fim and outro_inicio < fim:
                return True
        return False

    def salvar(self):
        """RF03 - grava o agendamento no banco (INSERT)."""
        db = get_db()
        cur = db.execute(
            """INSERT INTO agendamento
                   (id_cliente, id_profissional, id_servico, id_usuario, data, hora, observacao)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (self.id_cliente, self.id_profissional, self.id_servico, self.id_usuario,
             self.data, self.hora, self.observacao or None),
        )
        db.commit()
        self.id_agendamento = cur.lastrowid
        return self.id_agendamento

    @staticmethod
    def cancelar(id_agendamento):
        """RF05 - muda o status para CANCELADO (libera o horário)."""
        db = get_db()
        cur = db.execute(
            "UPDATE agendamento SET status = 'CANCELADO' "
            "WHERE id_agendamento = ? AND status = 'AGENDADO'",
            (id_agendamento,),
        )
        db.commit()
        return cur.rowcount == 1

    @staticmethod
    def listar_por_data(data, id_profissional=None):
        """RF04 - consulta da agenda de um dia (JOIN entre as 4 tabelas)."""
        sql = """SELECT a.id_agendamento, a.data, a.hora, a.status, a.observacao,
                        c.nome AS cliente, c.telefone,
                        p.nome AS profissional, s.nome AS servico, s.duracao_min, s.preco
                   FROM agendamento a
                   JOIN cliente      c ON c.id_cliente      = a.id_cliente
                   JOIN profissional p ON p.id_profissional = a.id_profissional
                   JOIN servico      s ON s.id_servico      = a.id_servico
                  WHERE a.data = ?"""
        params = [data]
        if id_profissional:
            sql += " AND a.id_profissional = ?"
            params.append(id_profissional)
        sql += " ORDER BY a.hora, p.nome"
        return get_db().execute(sql, params).fetchall()

    @staticmethod
    def relatorio_periodo(data_inicio, data_fim):
        """RF06 - total de atendimentos e faturamento previsto por profissional."""
        return get_db().execute(
            """SELECT p.nome AS profissional,
                      COUNT(a.id_agendamento) AS quantidade,
                      COALESCE(SUM(s.preco), 0) AS total
                 FROM profissional p
                 LEFT JOIN agendamento a ON a.id_profissional = p.id_profissional
                                        AND a.status <> 'CANCELADO'
                                        AND a.data BETWEEN ? AND ?
                 LEFT JOIN servico s ON s.id_servico = a.id_servico
                GROUP BY p.id_profissional
                ORDER BY total DESC""",
            (data_inicio, data_fim),
        ).fetchall()


def hoje():
    return date.today().isoformat()
