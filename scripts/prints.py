"""Tira os prints do relatório: wireframes (Fase 3), telas reais (Fase 4) e
evidências dos casos de teste CT01-CT08 (Fase 5).

Sobe o sistema num banco temporário, executa cada caso de teste pelo navegador
(Chrome via Playwright) e salva os PNG em docs/img.
"""
import html
import subprocess
import sys
import tempfile
import threading
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from app import create_app  # noqa: E402

IMG = RAIZ / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:5055"
AMANHA = (date.today() + timedelta(days=1)).isoformat()
ONTEM = (date.today() - timedelta(days=1)).isoformat()

tmp = tempfile.mkdtemp()
app = create_app({"DATABASE": str(Path(tmp) / "prints.db")})
server = make_server("127.0.0.1", 5055, app)
threading.Thread(target=server.serve_forever, daemon=True).start()


def shot(page, nome, full=False):
    page.screenshot(path=str(IMG / f"{nome}.png"), full_page=full)
    print("ok", nome)


def destacar(page, texto):
    """Contorna em vermelho a mensagem/linha que comprova o resultado do teste."""
    page.evaluate("""t => { for (const el of document.querySelectorAll('.msg, td, tr')) {
        if (el.innerText.includes(t)) { el.style.outline = '3px solid #e00'; el.style.outlineOffset = '2px'; return; } } }""",
                  texto)


def login(page, usuario="ana", senha="barber123"):
    page.goto(URL + "/login")
    page.fill("#login", usuario)
    page.fill("#senha", senha)
    page.click("button[type=submit]")


def cliente(page, nome, tel, email=""):
    page.goto(URL + "/clientes")
    page.fill("#nome", nome)
    page.fill("#telefone", tel)
    page.fill("#email", email)
    page.click("button[type=submit]")


def agendar(page, cliente_txt, servico_txt, prof_txt, data, hora, obs=""):
    page.goto(URL + "/agendamentos/novo")
    page.select_option("#id_cliente", label=cliente_txt)
    page.select_option("#id_servico", label=servico_txt)
    page.select_option("#id_profissional", label=prof_txt)
    page.fill("#data", data)
    page.fill("#hora", hora)
    page.fill("#observacao", obs)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")

    # ---------------------------------------------------------------- Fase 3
    pg = browser.new_page(viewport={"width": 960, "height": 600})
    pg.goto((RAIZ / "docs" / "wireframes" / "wireframes.html").as_uri())
    for i in range(1, 6):
        pg.locator(f"#wf{i}").screenshot(path=str(IMG / f"wireframe_{i}.png"))
        print("ok wireframe", i)
    pg.close()

    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())

    # ---------------------------------------------- CT06 login inválido + tela de login
    page.goto(URL + "/login")
    shot(page, "tela_login")
    page.fill("#login", "ana")
    page.fill("#senha", "senhaerrada")
    page.click("button[type=submit]")
    destacar(page, "inválidos")
    shot(page, "ct06_login_invalido")

    login(page)

    # ---------------------------------------------------- CT02 cadastro sem nome
    page.goto(URL + "/clientes")
    page.fill("#telefone", "11988887777")
    page.click("button[type=submit]")
    destacar(page, "Informe o nome")
    shot(page, "ct02_cadastro_sem_nome")

    # -------------------------------------------------- CT01 cadastro válido
    page.goto(URL + "/clientes")
    page.fill("#nome", "Rafael Costa")
    page.fill("#telefone", "(11) 98888-7777")
    page.fill("#email", "rafael.costa@email.com")
    shot(page, "f4_cadastro_preenchido")
    page.click("button[type=submit]")
    destacar(page, "cadastrado com sucesso")
    shot(page, "ct01_cadastro_valido")

    for n, t, e in [("Bruno Lima", "11977776666", ""), ("Diego Martins", "11966665555", "diego@email.com"),
                    ("Felipe Rocha", "11955554444", ""), ("Gustavo Alves", "11944443333", "gustavo@email.com")]:
        cliente(page, n, t, e)

    # -------------------------------------------------- CT03 telefone duplicado
    page.goto(URL + "/clientes")
    page.fill("#nome", "Rafael C. Souza")
    page.fill("#telefone", "11988887777")
    page.click("button[type=submit]")
    destacar(page, "Já existe")
    shot(page, "ct03_telefone_duplicado")

    # -------------------------------------------------- CT04 agendamento válido
    agendar(page, "Rafael Costa · (11) 98888-7777", "Corte + Barba · 60 min · R$ 65,00",
            "João Silva · Corte e barba", AMANHA, "10:00", "Prefere máquina 2 nas laterais")
    shot(page, "f4_agendamento_preenchido")
    page.click("button[type=submit]")
    destacar(page, "Rafael Costa")
    shot(page, "ct04_agendamento_valido")

    # mais agendamentos para a agenda ficar realista
    for c, s, pr, h in [
        ("Bruno Lima · (11) 97777-6666", "Corte · 30 min · R$ 40,00", "Pedro Santos · Corte degradê", "09:00"),
        ("Diego Martins · (11) 96666-5555", "Barba · 30 min · R$ 30,00", "Lucas Oliveira · Barba", "09:30"),
        ("Felipe Rocha · (11) 95555-4444", "Corte · 30 min · R$ 40,00", "João Silva · Corte e barba", "11:00"),
        ("Gustavo Alves · (11) 94444-3333", "Sobrancelha · 15 min · R$ 15,00", "Pedro Santos · Corte degradê", "14:00"),
    ]:
        agendar(page, c, s, pr, AMANHA, h)
        page.click("button[type=submit]")

    # -------------------------------------------------- CT05 horário ocupado
    agendar(page, "Bruno Lima · (11) 97777-6666", "Corte · 30 min · R$ 40,00",
            "João Silva · Corte e barba", AMANHA, "10:30")
    page.click("button[type=submit]")
    destacar(page, "já tem um agendamento")
    shot(page, "ct05_horario_ocupado")

    # -------------------------------------------------- CT08 data no passado
    agendar(page, "Bruno Lima · (11) 97777-6666", "Corte · 30 min · R$ 40,00",
            "Pedro Santos · Corte degradê", ONTEM, "15:00")
    page.click("button[type=submit]")
    destacar(page, "já passou")
    shot(page, "ct08_data_passada")

    # --------------------------------------------- RF04 agenda do dia (consulta)
    page.goto(f"{URL}/agenda?data={AMANHA}")
    shot(page, "f4_agenda_do_dia")

    # -------------------------------------------------- CT07 cancelar
    page.locator("tr", has_text="Felipe Rocha").locator("button").click()
    page.wait_for_load_state()
    destacar(page, "Agendamento cancelado")
    page.evaluate("""() => { for (const tr of document.querySelectorAll('tbody tr'))
        if (tr.innerText.includes('Felipe Rocha')) tr.style.outline = '3px solid #e00'; }""")
    shot(page, "ct07_cancelamento")

    # -------------------------------------------------- RF06 relatório (gerente)
    page.goto(URL + "/logout")
    login(page, "carlos", "gerente123")
    page.goto(f"{URL}/relatorio?inicio={date.today().isoformat()[:8]}01&fim={AMANHA}")
    shot(page, "f4_relatorio")

    # -------------------------------------------------- RNF03 celular
    mob = browser.new_context(viewport={"width": 390, "height": 760}, device_scale_factor=1.5)
    mp = mob.new_page()
    mp.goto(URL + "/login")
    mp.fill("#login", "ana"); mp.fill("#senha", "barber123"); mp.click("button[type=submit]")
    mp.goto(f"{URL}/agenda?data={AMANHA}")
    shot(mp, "f4_celular_agenda")
    mob.close()

    # -------------------------------------------------- pytest (evidência extra)
    r = subprocess.run([sys.executable, "-m", "pytest", "-v", "--no-header", "-p", "no:cacheprovider"],
                       cwd=RAIZ, capture_output=True, text=True)
    saida = html.escape(r.stdout.replace(str(RAIZ), "projeto-integrado-barbearia"))
    tp = browser.new_page(viewport={"width": 1000, "height": 400})
    tp.set_content(f"""<body style="margin:0;background:#1e1e1e"><pre style="color:#d4d4d4;font:14px Consolas,monospace;
        padding:16px;margin:0;white-space:pre-wrap">$ python -m pytest -v\n{saida}</pre></body>""")
    tp.screenshot(path=str(IMG / "testes_pytest.png"), full_page=True)
    print("ok pytest", r.returncode)
    browser.close()

server.shutdown()
