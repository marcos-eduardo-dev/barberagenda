"""Testes automatizados dos casos de teste CT01 a CT08 do plano de testes."""
from datetime import date, timedelta

import pytest

from app import create_app

AMANHA = (date.today() + timedelta(days=1)).isoformat()
ONTEM = (date.today() - timedelta(days=1)).isoformat()


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "teste.db")})
    with app.test_client() as c:
        yield c


def entrar(c, login="ana", senha="barber123"):
    return c.post("/login", data={"login": login, "senha": senha}, follow_redirects=True)


def cadastrar(c, nome="Rafael Costa", telefone="(11) 98888-7777", email=""):
    return c.post("/clientes", data={"nome": nome, "telefone": telefone, "email": email},
                  follow_redirects=True)


def agendar(c, hora="10:00", data=AMANHA, servico=1, prof=1, cliente=1):
    return c.post("/agendamentos/novo", data={
        "id_cliente": cliente, "id_profissional": prof, "id_servico": servico,
        "data": data, "hora": hora}, follow_redirects=True)


def texto(resp):
    return resp.get_data(as_text=True)


def test_ct01_cadastro_cliente_valido(client):
    entrar(client)
    r = cadastrar(client)
    assert "cadastrado com sucesso" in texto(r)
    assert "Rafael Costa" in texto(r) and "(11) 98888-7777" in texto(r)


def test_ct02_cadastro_sem_nome(client):
    entrar(client)
    r = cadastrar(client, nome="")
    assert "Informe o nome do cliente" in texto(r)
    assert "Nenhum cliente cadastrado" in texto(r)


def test_ct03_telefone_duplicado(client):
    entrar(client)
    cadastrar(client)
    r = cadastrar(client, nome="Outro Nome")
    assert "Já existe um cliente cadastrado com este telefone" in texto(r)
    assert "Clientes cadastrados (1)" in texto(r)


def test_ct04_agendamento_valido_aparece_na_agenda(client):
    entrar(client)
    cadastrar(client)
    r = agendar(client)
    assert "Agendamento confirmado" in texto(r)
    assert "10:00" in texto(r) and "Rafael Costa" in texto(r) and "AGENDADO" in texto(r)


def test_ct05_horario_ocupado(client):
    entrar(client)
    cadastrar(client)
    cadastrar(client, nome="Bruno Lima", telefone="11977776666")
    agendar(client, hora="10:00", servico=3)          # Corte + Barba: 10:00-11:00
    r = agendar(client, hora="10:30", cliente=2)        # sobrepõe
    assert "já tem um agendamento neste horário" in texto(r)


def test_ct06_login_invalido(client):
    r = entrar(client, senha="errada")
    assert "Login ou senha inválidos" in texto(r)
    assert client.get("/agenda").status_code == 302    # continua bloqueado


def test_ct07_cancelar_libera_horario(client):
    entrar(client)
    cadastrar(client)
    agendar(client)
    r = client.post("/agendamentos/1/cancelar", data={"data": AMANHA}, follow_redirects=True)
    assert "Agendamento cancelado" in texto(r) and "CANCELADO" in texto(r)
    assert "Agendamento confirmado" in texto(agendar(client))   # mesmo horário de novo


def test_ct08_data_no_passado(client):
    entrar(client)
    cadastrar(client)
    r = agendar(client, data=ONTEM)
    assert "já passou" in texto(r)
