# BarberAgenda

Sistema web de agendamento para barbearia, feito para o **Projeto Integrado**.
Python 3.12 + Flask 3.1 + SQLite.

## Funcionalidades

| Requisito | Funcionalidade | Tela |
|---|---|---|
| RF01 | Login de atendente/gerente (senha com hash) | `/login` |
| RF02 | Cadastrar e listar clientes | `/clientes` |
| RF03 | Agendar horário (impede horário ocupado, data passada e fora do expediente) | `/agendamentos/novo` |
| RF04 | Consultar a agenda do dia, com filtro por profissional | `/agenda` |
| RF05 | Cancelar agendamento | botão na agenda |
| RF06 | Relatório de atendimentos e faturamento por profissional | `/relatorio` |

## Como executar

```bash
pip install -r requirements.txt
python run.py
```

Acesse http://127.0.0.1:5000. O banco (`instance/barberagenda.db`) é criado na primeira execução
com profissionais, serviços e dois usuários de teste:

| Login | Senha | Perfil |
|---|---|---|
| ana | barber123 | Atendente |
| carlos | gerente123 | Gerente |

Para recriar o banco do zero: `flask --app app init-db`.

## Testes

```bash
python -m pytest -v
```

Os testes CT01 a CT08 do plano de testes estão em [tests/test_app.py](tests/test_app.py).

## Estrutura

```
app/
  schema.sql       criação das tabelas (igual ao MER e ao dicionário de dados)
  db.py            conexão com o SQLite e dados iniciais
  models.py        classes Usuario, Cliente, Profissional, Servico e Agendamento
  __init__.py      rotas (controlador)
  templates/       telas HTML
tests/             testes automatizados (pytest)
docs/
  diagramas/       diagramas em SVG (casos de uso, classes, MER, sequência)
  wireframes/      protótipos das telas
  img/             diagramas e prints em PNG
scripts/           geração dos diagramas, prints e do relatório
```
