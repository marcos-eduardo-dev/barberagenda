"""Monta o relatório técnico (docs/relatorio/*.docx) a partir dos diagramas, prints e código.

Trechos entre [[ ]] saem destacados em amarelo: são dados que só o aluno pode
preencher ou confirmar (nome, instituição, link do GitHub etc.).
"""
import ast
import io
import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
IMG = RAIZ / "docs" / "img"
SAIDA = RAIZ / "docs" / "relatorio" / "Relatorio_Projeto_Integrado_BarberAgenda.docx"
SAIDA.parent.mkdir(parents=True, exist_ok=True)
GITHUB = "https://github.com/marcos-eduardo-dev/barberagenda"
ANO = date.today().year
FONTE_AUTOR = f"Fonte: elaborado pelo autor ({ANO})."

doc = Document()

# ------------------------------------------------------------------ estilos ABNT
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21)
sec.top_margin, sec.left_margin = Cm(3), Cm(3)
sec.bottom_margin, sec.right_margin = Cm(2), Cm(2)

normal = doc.styles["Normal"]
normal.font.name = "Arial"
normal.font.size = Pt(12)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
normal.paragraph_format.line_spacing = 1.5
normal.paragraph_format.space_after = Pt(6)

for nome, tam in (("Heading 1", 12), ("Heading 2", 12), ("Heading 3", 12)):
    st = doc.styles[nome]
    st.font.name = "Arial"
    rf = st.element.rPr.find(qn("w:rFonts"))
    for k in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf is not None and rf.get(qn(k)):
            del rf.attrib[qn(k)]
    st.font.size = Pt(tam)
    st.font.bold = nome != "Heading 3"
    st.font.italic = False
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.paragraph_format.space_before = Pt(12)
    st.paragraph_format.space_after = Pt(12)
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.keep_with_next = True

FIG = [0]
TAB = [0]


def runs(par, texto, bold=False, italic=False, size=None, font=None):
    """Adiciona texto ao parágrafo; **negrito** e [[destaque amarelo]]."""
    for parte in re.split(r"(\*\*.+?\*\*|\[\[.+?\]\])", texto):
        if not parte:
            continue
        r_bold, hl = bold, False
        if parte.startswith("**"):
            parte, r_bold = parte[2:-2], True
        elif parte.startswith("[["):
            parte, hl = parte[2:-2], True
        r = par.add_run(parte)
        r.bold, r.italic = r_bold, italic
        if size:
            r.font.size = Pt(size)
        if font:
            r.font.name = font
        if hl:
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return par


def P(texto, align="justify", indent=True, **kw):
    p = doc.add_paragraph()
    p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "left": WD_ALIGN_PARAGRAPH.LEFT, "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    if indent and align == "justify":
        p.paragraph_format.first_line_indent = Cm(1.25)
    return runs(p, texto, **kw)


def B(texto, nivel=0):
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Cm(1.25 + nivel * 0.8)
    return runs(p, texto)


def N(texto):
    p = doc.add_paragraph(style="List Number")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return runs(p, texto)


def H1(texto, quebra=True):
    if quebra:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    return doc.add_heading(texto.upper(), level=1)


def H2(texto):
    return doc.add_heading(texto, level=2)


def H3(texto):
    return doc.add_heading(texto, level=3)


def legenda(texto, fonte=FONTE_AUTOR):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(0)
    runs(p, texto, size=10, bold=True)
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.paragraph_format.line_spacing = 1.0
    f.paragraph_format.space_after = Pt(12)
    runs(f, fonte, size=10)


def figura(arquivo, titulo, largura=15.5, fonte=FONTE_AUTOR):
    """Insere a imagem (convertida para JPEG para o arquivo ficar leve) e a legenda embaixo."""
    FIG[0] += 1
    im = Image.open(IMG / arquivo).convert("RGB")
    larg_px = int(largura / 2.54 * 170)          # ~170 dpi é suficiente para impressão
    if im.width > larg_px:
        im = im.resize((larg_px, int(im.height * larg_px / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85, optimize=True)
    buf.seek(0)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(4)
    altura_max = 20.0
    alt = largura * im.height / im.width
    if alt > altura_max:
        p.add_run().add_picture(buf, height=Cm(altura_max))
    else:
        p.add_run().add_picture(buf, width=Cm(largura))
    legenda(f"Figura {FIG[0]} – {titulo}", fonte)
    return FIG[0]


def bordas(tabela):
    tbl = tabela._tbl
    pr = tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "000000")
        b.append(e)
    pr.append(b)


def sombrear(cel, cor="D9D9D9"):
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), cor)
    cel._tc.get_or_add_tcPr().append(sh)


def tabela(titulo, cab, linhas, larguras=None, fonte=FONTE_AUTOR, tam=10):
    """Tabela ABNT/IBGE: título acima, fonte abaixo."""
    TAB[0] += 1
    t_p = doc.add_paragraph()
    t_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_p.paragraph_format.keep_with_next = True
    t_p.paragraph_format.line_spacing = 1.0
    runs(t_p, f"Quadro {TAB[0]} – {titulo}", size=10, bold=True)
    t = doc.add_table(rows=1, cols=len(cab))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    bordas(t)
    for i, c in enumerate(cab):
        cel = t.rows[0].cells[i]
        cel.text = ""
        runs(cel.paragraphs[0], c, bold=True, size=tam)
        sombrear(cel)
    for linha in linhas:
        cells = t.add_row().cells
        for i, v in enumerate(linha):
            cells[i].text = ""
            partes = str(v).split("\n")
            runs(cells[i].paragraphs[0], partes[0], size=tam)
            for extra in partes[1:]:
                runs(cells[i].add_paragraph(), extra, size=tam)
    for row in t.rows:
        for i, cel in enumerate(row.cells):
            for par in cel.paragraphs:
                par.paragraph_format.line_spacing = 1.0
                par.paragraph_format.space_after = Pt(2)
                par.paragraph_format.first_line_indent = None
            if larguras:
                cel.width = Cm(larguras[i])
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.LEFT
    f.paragraph_format.line_spacing = 1.0
    f.paragraph_format.space_after = Pt(12)
    runs(f, fonte, size=10)
    return t


def codigo(texto, titulo, arquivo):
    """Trecho de código como TEXTO (não imagem), em fonte monoespaçada."""
    TAB[0] += 1
    t_p = doc.add_paragraph()
    t_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    t_p.paragraph_format.keep_with_next = True
    t_p.paragraph_format.line_spacing = 1.0
    runs(t_p, f"Quadro {TAB[0]} – {titulo} (arquivo {arquivo})", size=10, bold=True)
    t = doc.add_table(rows=1, cols=1)
    bordas(t)
    cel = t.rows[0].cells[0]
    sombrear(cel, "F5F5F5")
    cel.text = ""
    linhas = texto.rstrip().split("\n")
    for i, l in enumerate(linhas):
        par = cel.paragraphs[0] if i == 0 else cel.add_paragraph()
        par.paragraph_format.line_spacing = 1.0
        par.paragraph_format.space_after = Pt(0)
        r = par.add_run(l if l else " ")
        r.font.name = "Consolas"
        r.font.size = Pt(8.5)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    f = doc.add_paragraph()
    f.paragraph_format.line_spacing = 1.0
    f.paragraph_format.space_after = Pt(12)
    runs(f, FONTE_AUTOR, size=10)


def fonte_de(arquivo, *nomes, classe=None):
    """Extrai do arquivo-fonte o código exato das funções/métodos pedidos."""
    src = (RAIZ / arquivo).read_text(encoding="utf-8")
    tree = ast.parse(src)
    blocos = []
    for no in ast.walk(tree):
        if isinstance(no, ast.ClassDef) and classe and no.name == classe:
            for m in no.body:
                if isinstance(m, ast.FunctionDef) and m.name in nomes:
                    blocos.append((m.lineno, m))
        elif isinstance(no, ast.FunctionDef) and not classe and no.name in nomes:
            blocos.append((no.lineno, no))
    linhas = src.split("\n")
    out = []
    for _, no in sorted(blocos, key=lambda x: x[0]):
        ini = (no.decorator_list[0].lineno if no.decorator_list else no.lineno) - 1
        trecho = linhas[ini:no.end_lineno]
        recuo = min(len(l) - len(l.lstrip()) for l in trecho if l.strip())
        out.append("\n".join(l[recuo:] for l in trecho))
    return "\n\n".join(out)


def sumario():
    p = doc.add_paragraph()
    r = p.add_run()
    for tipo, txt in (("begin", None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None)):
        if tipo:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tipo); r._r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = txt; r._r.append(e)
    r2 = p.add_run("Clique com o botão direito aqui e escolha \"Atualizar campo\" para gerar o sumário.")
    r2.italic = True
    r3 = p.add_run()
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); r3._r.append(e)
    # pede ao Word para atualizar os campos (sumário) ao abrir
    upd = OxmlElement("w:updateFields"); upd.set(qn("w:val"), "true")
    st_el = doc.settings.element
    depois = [st_el.find(qn(t)) for t in ("w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr", "w:compat", "w:docVars", "w:rsids")]
    depois = [d for d in depois if d is not None]
    (depois[0].addprevious(upd) if depois else st_el.append(upd))


# ================================================================== CAPA
for t in ("[[NOME DA INSTITUIÇÃO]]", "[[NOME DO CURSO]]"):
    P(t, "center", bold=True)
for _ in range(5):
    doc.add_paragraph()
P("[[NOME COMPLETO DO ALUNO]]", "center", bold=True)
P("RA: [[000000]]", "center")
for _ in range(5):
    doc.add_paragraph()
P("BARBERAGENDA: SISTEMA DE AGENDAMENTO PARA BARBEARIA", "center", bold=True, size=14)
P("Projeto Integrado – Relatório Técnico", "center")
for _ in range(9):
    doc.add_paragraph()
P("[[CIDADE]]", "center", bold=True)
P(str(ANO), "center", bold=True)

# ================================================================== SUMÁRIO
doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
P("SUMÁRIO", "center", bold=True)
sumario()

# ================================================================== 1 APRESENTAÇÃO
H1("1 Apresentação do tema")
P("Este relatório apresenta o desenvolvimento do **BarberAgenda**, um sistema web para controlar "
  "os agendamentos de uma barbearia de pequeno porte. O sistema permite cadastrar clientes, marcar "
  "horários com um profissional para um serviço (corte, barba etc.), consultar a agenda do dia, "
  "cancelar agendamentos e gerar um relatório de atendimentos por período. O trabalho percorre o ciclo "
  "completo de desenvolvimento – requisitos, modelagem, prototipação, codificação com banco de dados e "
  "testes –, que corresponde às atividades fundamentais do processo de software descritas por "
  "Sommerville (2018): especificação, projeto e implementação, validação e evolução.")

H2("1.1 Por que este tema")
P("Muitas barbearias de bairro ainda controlam os horários em caderno ou pelo WhatsApp. Esse controle "
  "manual causa problemas comuns: dois clientes marcados no mesmo horário com o mesmo barbeiro, "
  "dificuldade para saber quem vem no dia e nenhuma visão de quantos atendimentos cada profissional fez "
  "no mês. Um sistema simples de agendamento resolve esses pontos sem exigir recursos complexos, o que o "
  "torna adequado ao prazo de um semestre.")

H2("1.2 Validação do tema")
P("O tema atende aos três critérios exigidos para o Projeto Integrado, como mostra o Quadro 1.")
tabela("Validação do tema", ["Critério", "Como o BarberAgenda atende"], [
    ["Pelo menos 3 funcionalidades diferentes", "Cadastrar cliente (RF02), agendar horário (RF03), consultar "
     "agenda do dia (RF04), cancelar agendamento (RF05) e gerar relatório (RF06)."],
    ["Pelo menos 1 consulta ao banco", "Consulta da agenda do dia (SELECT com JOIN entre agendamento, "
     "cliente, profissional e servico) e verificação de horário ocupado."],
    ["Viável no semestre", "Sistema web simples (Python/Flask + SQLite), sem pagamento online nem aplicativo "
     "nativo. Duas funcionalidades principais foram implementadas e testadas."],
], [5, 11])

H2("1.3 Levantamento de informações")
P("Para levantar os requisitos foram usadas duas das técnicas sugeridas. Pressman e Maxim (2016) destacam "
  "que a concepção e o levantamento de requisitos dependem de entender o problema do ponto de vista de "
  "quem vai usar o sistema, e que combinar fontes reduz a chance de omitir necessidades importantes.")
tabela("Fontes das informações levantadas", ["Técnica", "O que foi feito", "Informações obtidas"], [
    ["Pesquisa de sistemas parecidos", "Análise das funções públicas de sistemas de agendamento para "
     "barbearias e salões disponíveis no mercado (como Trinks, AppBarber e Booksy), pelos sites e "
     "demonstrações.",
     "Agenda separada por profissional; cadastro de cliente com telefone como contato principal; "
     "cada serviço tem duração e preço; bloqueio de horários já ocupados; relatórios de atendimentos."],
    ["Experiência própria como cliente", "[[Relato da sua experiência como cliente de barbearia – ajuste "
     "este texto à sua realidade.]]",
     "[[Ex.: o atendente marca pelo WhatsApp e anota num caderno; já houve encaixe de dois clientes no "
     "mesmo horário; o cliente é identificado pelo nome e telefone; o horário de funcionamento é das 9h "
     "às 19h.]]"],
], [3.6, 6.2, 6.2])
P("Com base nessas fontes foram definidas as regras de negócio do sistema: (RN01) um profissional não pode "
  "ter dois agendamentos ativos com horários sobrepostos, considerando a duração do serviço; (RN02) não é "
  "permitido agendar em data ou hora que já passou; (RN03) o atendimento ocorre das 09:00 às 19:00; e "
  "(RN04) não podem existir dois clientes com o mesmo telefone.")

# ================================================================== 2 FASE 1
H1("2 Fase 1 – Análise de requisitos")
P("Requisitos funcionais descrevem o que o sistema deve fazer, enquanto requisitos não funcionais são "
  "restrições sobre os serviços oferecidos, como desempenho, segurança e usabilidade (SOMMERVILLE, 2018). "
  "Os requisitos do BarberAgenda estão nos Quadros 3 e 4.")

H2("2.1 Requisitos funcionais")
tabela("Requisitos funcionais", ["ID", "Requisito", "Descrição", "Caso de uso"], [
    ["RF01", "Autenticar usuário", "O sistema deve permitir que o atendente ou o gerente entre informando "
     "login e senha.", "UC01"],
    ["RF02", "Cadastrar cliente", "O sistema deve cadastrar clientes com nome (obrigatório), telefone com DDD "
     "(obrigatório e único) e e-mail (opcional), e listar os clientes cadastrados.", "UC02"],
    ["RF03", "Agendar horário", "O sistema deve registrar um agendamento informando cliente, serviço, "
     "profissional, data e hora, impedindo horários ocupados, no passado ou fora do funcionamento.", "UC03"],
    ["RF04", "Consultar agenda do dia", "O sistema deve listar os agendamentos de uma data, em ordem de hora, "
     "com filtro opcional por profissional.", "UC04"],
    ["RF05", "Cancelar agendamento", "O sistema deve permitir cancelar um agendamento ativo, liberando o "
     "horário para outro cliente.", "UC05"],
    ["RF06", "Gerar relatório de atendimentos", "O sistema deve mostrar, para um período, a quantidade de "
     "atendimentos e o faturamento previsto por profissional, sem contar os cancelados.", "UC06"],
], [1.3, 3.4, 9.3, 2])

H2("2.2 Requisitos não funcionais")
tabela("Requisitos não funcionais", ["ID", "Categoria", "Descrição"], [
    ["RNF01", "Desempenho", "As telas de cadastro, agendamento e consulta devem responder em até 3 segundos."],
    ["RNF02", "Segurança", "Todas as telas, exceto o login, devem exigir usuário autenticado; as senhas devem "
     "ser gravadas no banco apenas como hash, nunca em texto puro."],
    ["RNF03", "Usabilidade", "O sistema deve funcionar no navegador do celular (telas a partir de 360 px de "
     "largura) e mostrar mensagens de erro claras, em português."],
    ["RNF04", "Persistência", "Os dados devem ser gravados em banco de dados relacional (SQLite), com chaves "
     "estrangeiras para garantir a integridade entre as tabelas."],
], [1.6, 2.8, 11.6])

H2("2.3 Diagrama de casos de uso")
P("O diagrama de casos de uso mostra quem usa o sistema (atores) e o que cada um pode fazer (BOOCH; "
  "RUMBAUGH; JACOBSON, 2012). No BarberAgenda há dois atores: o **Atendente**, que faz o dia a dia da "
  "recepção, e o **Gerente**, que herda tudo o que o atendente faz e também gera o relatório. O caso de "
  "uso Agendar horário inclui (<<include>>) a verificação de conflito, que é executada sempre; o "
  "cancelamento estende (<<extend>>) a consulta da agenda, pois é feito a partir dela.")
figura("01_casos_de_uso.png", "Diagrama de casos de uso do BarberAgenda", 15)

H2("2.4 Descrição dos casos de uso")
P("Cada caso de uso foi descrito de forma simplificada, com ator, objetivo e passos principais, seguindo "
  "a estrutura sugerida por Guedes (2018).")
ucs = [
    ("UC01 – Fazer login", "Atendente ou Gerente", "Entrar no sistema para usar as funções restritas (RF01).",
     "Usuário cadastrado no banco.",
     ["Usuário abre o sistema e vê a tela de login.", "Informa login e senha e clica em Entrar.",
      "Sistema confere a senha com o hash gravado.", "Sistema abre a Agenda do dia."],
     "Login ou senha errados: sistema mostra \"Login ou senha inválidos\" e continua na tela de login."),
    ("UC02 – Cadastrar cliente", "Atendente", "Registrar um novo cliente da barbearia (RF02).",
     "Atendente autenticado.",
     ["Atendente abre a tela Clientes.", "Preenche nome, telefone e, se quiser, e-mail.",
      "Clica em Salvar cliente.", "Sistema valida os dados e grava o cliente.",
      "Sistema mostra a mensagem de sucesso e o cliente na lista."],
     "Nome vazio, telefone inválido ou telefone já cadastrado: sistema mostra o erro e não grava."),
    ("UC03 – Agendar horário", "Atendente", "Marcar um horário para um cliente com um profissional (RF03).",
     "Atendente autenticado e cliente já cadastrado.",
     ["Atendente abre Novo agendamento.", "Seleciona cliente, serviço e profissional (lidos do banco).",
      "Informa data e hora e clica em Confirmar agendamento.",
      "Sistema verifica data futura, horário de funcionamento e conflito de horário (include).",
      "Sistema grava o agendamento com status AGENDADO e abre a agenda do dia."],
     "Horário ocupado, data passada ou fora do expediente: sistema mostra o erro e mantém o formulário "
     "preenchido."),
    ("UC04 – Consultar agenda do dia", "Atendente", "Ver os horários marcados em uma data (RF04).",
     "Atendente autenticado.",
     ["Atendente abre Agenda do dia (data de hoje vem preenchida).",
      "Opcionalmente escolhe outra data ou um profissional e clica em Consultar.",
      "Sistema consulta o banco e lista os agendamentos em ordem de hora."],
     "Sem agendamentos na data: sistema mostra \"Nenhum agendamento para esta data\"."),
    ("UC05 – Cancelar agendamento", "Atendente", "Desmarcar um horário e liberá-lo (RF05).",
     "Agendamento com status AGENDADO exibido na agenda.",
     ["Na agenda do dia, atendente clica em Cancelar na linha desejada.", "Sistema pede confirmação.",
      "Atendente confirma.", "Sistema altera o status para CANCELADO e mostra a agenda atualizada."],
     "Atendente desiste na confirmação: nada é alterado."),
    ("UC06 – Gerar relatório de atendimentos", "Gerente", "Acompanhar a produção de cada profissional (RF06).",
     "Gerente autenticado.",
     ["Gerente abre Relatório.", "Informa a data inicial e a final e clica em Gerar.",
      "Sistema soma, por profissional, os atendimentos não cancelados e o valor dos serviços.",
      "Sistema mostra a tabela com os totais."],
     "Período sem atendimentos: os profissionais aparecem com quantidade 0 e valor R$ 0,00."),
]
for nome, ator, obj, pre, passos, alt in ucs:
    H3(nome)
    tabela(f"Descrição do caso de uso {nome.split(' – ')[0]}", ["Item", "Descrição"], [
        ["Ator", ator], ["Objetivo", obj], ["Pré-condição", pre],
        ["Passos principais", "\n".join(f"{i}. {p}" for i, p in enumerate(passos, 1))],
        ["Fluxo alternativo", alt],
    ], [3.5, 12.5])

# ================================================================== 3 FASE 2
H1("3 Fase 2 – Modelagem do sistema")
P("A modelagem foi feita para que os mesmos nomes aparecessem em todos os artefatos: as classes do "
  "diagrama de classes (Cliente, Profissional, Servico, Agendamento e Usuario) viram as tabelas do MER "
  "(cliente, profissional, servico, agendamento e usuario), os atributos têm os mesmos nomes das colunas "
  "do banco e os métodos são exatamente os implementados no código (arquivo app/models.py). O último "
  "quadro desta seção mostra essa rastreabilidade de cada requisito até o código.")

H2("3.1 Diagrama de classes")
P("O diagrama de classes representa a estrutura estática do sistema: classes, atributos, operações e "
  "relacionamentos (BOOCH; RUMBAUGH; JACOBSON, 2012). A classe central é **Agendamento**, que liga um "
  "Cliente, um Profissional, um Servico e o Usuario que registrou a marcação. Cada um desses pode estar "
  "em zero ou muitos agendamentos (multiplicidade 1 para 0..*). As regras de negócio ficam nos métodos "
  "validar() e verificar_conflito().")
figura("02_classes.png", "Diagrama de classes do BarberAgenda", 16)

H2("3.2 Modelo Entidade-Relacionamento (MER)")
P("O MER descreve os dados do sistema em termos de entidades, atributos e relacionamentos (ELMASRI; "
  "NAVATHE, 2018). Foi usada a notação pé-de-galinha. Todos os relacionamentos são do tipo 1:N: um "
  "cliente possui vários agendamentos, um profissional atende vários agendamentos, um serviço é usado em "
  "vários agendamentos e um usuário registra vários agendamentos. Por isso, conforme Heuser (2009), a "
  "chave do lado 1 é levada como chave estrangeira para a tabela agendamento.")
figura("03_mer.png", "Modelo Entidade-Relacionamento do BarberAgenda", 16)

H2("3.3 Dicionário de dados")
P("O dicionário de dados detalha cada campo das tabelas criadas no banco (arquivo app/schema.sql). "
  "PK = chave primária; FK = chave estrangeira; UQ = valor único.")
dic = {
    "cliente": [
        ["id_cliente", "INTEGER", "Identificador do cliente (autoincremento)", "Sim", "PK"],
        ["nome", "VARCHAR(100)", "Nome completo do cliente (mínimo 3 letras)", "Sim", ""],
        ["telefone", "VARCHAR(15)", "Telefone com DDD, só dígitos (10 ou 11)", "Sim", "UQ"],
        ["email", "VARCHAR(100)", "E-mail do cliente", "Não", ""],
        ["data_cadastro", "DATE", "Data em que o cliente foi cadastrado (automática)", "Sim", ""],
    ],
    "profissional": [
        ["id_profissional", "INTEGER", "Identificador do profissional", "Sim", "PK"],
        ["nome", "VARCHAR(100)", "Nome do barbeiro", "Sim", ""],
        ["especialidade", "VARCHAR(50)", "Especialidade principal (ex.: corte degradê)", "Não", ""],
        ["ativo", "BOOLEAN", "1 = atende atualmente; 0 = desligado (padrão 1)", "Sim", ""],
    ],
    "servico": [
        ["id_servico", "INTEGER", "Identificador do serviço", "Sim", "PK"],
        ["nome", "VARCHAR(60)", "Nome do serviço (ex.: Corte, Barba)", "Sim", ""],
        ["duracao_min", "INTEGER", "Duração do serviço em minutos (> 0)", "Sim", ""],
        ["preco", "DECIMAL(8,2)", "Preço do serviço em reais (>= 0)", "Sim", ""],
    ],
    "usuario": [
        ["id_usuario", "INTEGER", "Identificador do usuário do sistema", "Sim", "PK"],
        ["nome", "VARCHAR(100)", "Nome do funcionário", "Sim", ""],
        ["login", "VARCHAR(30)", "Nome de acesso ao sistema", "Sim", "UQ"],
        ["senha_hash", "VARCHAR(255)", "Hash da senha (a senha nunca é gravada em texto)", "Sim", ""],
        ["perfil", "VARCHAR(10)", "ATENDENTE ou GERENTE", "Sim", ""],
    ],
    "agendamento": [
        ["id_agendamento", "INTEGER", "Identificador do agendamento", "Sim", "PK"],
        ["id_cliente", "INTEGER", "Cliente atendido", "Sim", "FK → cliente"],
        ["id_profissional", "INTEGER", "Profissional que vai atender", "Sim", "FK → profissional"],
        ["id_servico", "INTEGER", "Serviço marcado", "Sim", "FK → servico"],
        ["id_usuario", "INTEGER", "Usuário que registrou o agendamento", "Sim", "FK → usuario"],
        ["data", "DATE", "Data do atendimento (AAAA-MM-DD)", "Sim", ""],
        ["hora", "TIME", "Hora de início (HH:MM)", "Sim", ""],
        ["status", "VARCHAR(10)", "AGENDADO, CANCELADO ou CONCLUIDO (padrão AGENDADO)", "Sim", ""],
        ["observacao", "VARCHAR(200)", "Observação livre do atendente", "Não", ""],
        ["criado_em", "DATETIME", "Data e hora do registro (automática)", "Sim", ""],
    ],
}
for ent, linhas in dic.items():
    tabela(f"Dicionário de dados da entidade {ent}", ["Campo", "Tipo", "Descrição", "Obrigatório", "Chave"],
           linhas, [3.2, 2.8, 6.4, 1.9, 2.4], tam=9)

H2("3.4 Diagrama de sequência")
P("O diagrama de sequência mostra a troca de mensagens entre os objetos ao longo do tempo para realizar "
  "um caso de uso (GUEDES, 2018). Foi modelado o caso de uso principal, **UC03 – Agendar horário**. "
  "Note que as mensagens usam os mesmos métodos do diagrama de classes (validar, buscar_por_id, "
  "verificar_conflito e salvar) e as mesmas tabelas do MER. O fragmento alt mostra os dois caminhos: "
  "horário livre (grava) e horário ocupado ou dado inválido (mostra erro).")
figura("04_sequencia_agendar.png", "Diagrama de sequência do caso de uso UC03 – Agendar horário", 15)

H2("3.5 Rastreabilidade entre os modelos")
P("Para garantir a coerência entre requisitos, diagramas e código, o quadro a seguir relaciona cada requisito "
  "funcional com o caso de uso, a classe e o método, as tabelas e a tela correspondente.")
tabela("Rastreabilidade: requisito → caso de uso → classe/método → tabela → tela",
       ["RF", "UC", "Classe.método", "Tabelas", "Tela"], [
    ["RF01", "UC01", "Usuario.autenticar()", "usuario", "Tela 1 – Login"],
    ["RF02", "UC02", "Cliente.validar(), Cliente.salvar(), Cliente.listar()", "cliente", "Tela 2 – Cadastro de cliente"],
    ["RF03", "UC03", "Agendamento.validar(), verificar_conflito(), salvar(); Servico.buscar_por_id()",
     "agendamento, servico, cliente, profissional", "Tela 3 – Novo agendamento"],
    ["RF04", "UC04", "Agendamento.listar_por_data()", "agendamento, cliente, profissional, servico", "Tela 4 – Agenda do dia"],
    ["RF05", "UC05", "Agendamento.cancelar()", "agendamento", "Tela 4 – Agenda do dia"],
    ["RF06", "UC06", "Agendamento.relatorio_periodo()", "agendamento, profissional, servico", "Tela 5 – Relatório"],
], [1.3, 1.3, 6, 4, 3.4], tam=9)

# ================================================================== 4 FASE 3
H1("4 Fase 3 – Prototipagem de telas")
P("Os protótipos foram feitos como wireframes de baixa fidelidade, que mostram apenas a disposição dos "
  "campos e botões, sem preocupação com cores. Segundo Pressman e Maxim (2016), a prototipação ajuda o "
  "usuário a validar os requisitos antes da codificação. Também foram seguidas heurísticas de usabilidade "
  "de Nielsen (1993), como mensagens de erro em linguagem simples e prevenção de erros (por exemplo, "
  "listas de seleção em vez de digitação livre para cliente, serviço e profissional). As notas amarelas "
  "nos wireframes indicam as regras de cada tela.")
telas = [
    ("wireframe_1.png", "Protótipo da Tela 1 – Login",
     "Serve para o funcionário entrar no sistema (RF01). O usuário digita login e senha e clica em Entrar; "
     "se estiverem errados, aparece uma mensagem e o acesso é negado."),
    ("wireframe_2.png", "Protótipo da Tela 2 – Cadastro de cliente",
     "Serve para cadastrar e ver os clientes (RF02). O atendente preenche nome, telefone e e-mail e clica em "
     "Salvar cliente; à direita, a lista mostra todos os clientes já cadastrados."),
    ("wireframe_3.png", "Protótipo da Tela 3 – Novo agendamento",
     "Serve para marcar um horário (RF03). O atendente escolhe cliente, serviço e profissional nas listas, "
     "informa data e hora e clica em Confirmar; se o horário estiver ocupado, o sistema avisa."),
    ("wireframe_4.png", "Protótipo da Tela 4 – Agenda do dia",
     "Serve para ver quem será atendido em uma data (RF04) e cancelar marcações (RF05). O atendente escolhe "
     "a data e, se quiser, o profissional, e clica em Consultar; o botão Cancelar fica em cada linha."),
    ("wireframe_5.png", "Protótipo da Tela 5 – Relatório de atendimentos",
     "Serve para o gerente acompanhar a produção (RF06). Ele informa o período e clica em Gerar para ver a "
     "quantidade de atendimentos e o faturamento previsto por profissional."),
]
for arq, tit, desc in telas:
    H3(tit.replace("Protótipo da ", ""))
    P(desc)
    figura(arq, tit, 15)

# ================================================================== 5 FASE 4
H1("5 Fase 4 – Desenvolvimento")
P("O sistema foi desenvolvido em **Python 3.12** com o microframework **Flask 3.1** (PALLETS, 2025) e "
  "banco de dados **SQLite** (SQLITE, 2025). As tabelas foram criadas exatamente como no MER e no "
  "dicionário de dados (arquivo app/schema.sql). O código segue a separação vista no diagrama de "
  "sequência: as telas (templates HTML), o controlador (rotas em app/__init__.py) e as classes de "
  "domínio que acessam o banco (app/models.py). Todas as consultas usam parâmetros (?), o que evita "
  "injeção de SQL.")
P(f"Código-fonte no GitHub: {GITHUB}", indent=False, align="left")
P("Para executar: instalar as dependências com \"pip install -r requirements.txt\" e rodar \"python "
  "run.py\"; o banco é criado automaticamente na primeira execução. Usuários de teste: ana / barber123 "
  "(atendente) e carlos / gerente123 (gerente).", indent=False, align="left")
P("Foram implementadas todas as funcionalidades RF01 a RF06. As duas funcionalidades principais, "
  "descritas a seguir com o código, são o **cadastro de cliente (RF02)**, que grava no banco, e o "
  "**agendamento de horário (RF03)**, que lê clientes, serviços e profissionais do banco e grava o "
  "agendamento. Também é mostrada a consulta da agenda do dia (RF04).")

H2("5.1 Funcionalidade 1 – Cadastrar cliente (RF02)")
P("A tela de clientes envia os dados para a rota /clientes. O controlador cria um objeto Cliente, chama "
  "validar() – que confere nome, formato do telefone, telefone repetido no banco e e-mail – e, se não "
  "houver erros, chama salvar(), que executa o INSERT na tabela cliente.")
codigo(fonte_de("app/models.py", "validar", "salvar", "listar", classe="Cliente"),
       "Classe Cliente: validação e gravação no banco", "app/models.py")
codigo(fonte_de("app/__init__.py", "clientes"), "Rota que recebe o formulário de cadastro de cliente",
       "app/__init__.py")
figura("f4_cadastro_preenchido.png", "Tela de cadastro de cliente preenchida", 15)
figura("ct01_cadastro_valido.png", "Cliente gravado no banco e exibido na lista", 15)

H2("5.2 Funcionalidade 2 – Agendar horário (RF03)")
P("A tela Novo agendamento carrega cliente, serviço e profissional a partir do banco. Ao confirmar, o "
  "método validar() da classe Agendamento busca a duração do serviço, confere se a data não passou e se o "
  "horário está dentro do expediente e chama verificar_conflito(), que consulta os agendamentos ativos "
  "do mesmo profissional na data e verifica se algum se sobrepõe ao novo intervalo. Só então salvar() "
  "grava o registro na tabela agendamento.")
codigo(fonte_de("app/models.py", "validar", "verificar_conflito", "salvar", classe="Agendamento"),
       "Classe Agendamento: regras de negócio e gravação", "app/models.py")
codigo(fonte_de("app/__init__.py", "novo_agendamento"), "Rota de novo agendamento", "app/__init__.py")
figura("f4_agendamento_preenchido.png", "Tela de novo agendamento com dados lidos do banco", 15)

H2("5.3 Consulta ao banco – Agenda do dia (RF04)")
P("A agenda do dia é a consulta principal do sistema. Ela junta as quatro tabelas para mostrar, em ordem "
  "de hora, cliente, telefone, serviço, profissional e situação de cada agendamento.")
codigo(fonte_de("app/models.py", "listar_por_data", classe="Agendamento"),
       "Consulta SQL da agenda do dia", "app/models.py")
figura("f4_agenda_do_dia.png", "Agenda do dia exibindo os agendamentos gravados", 15)

H2("5.4 Outras telas do sistema")
figura("tela_login.png", "Tela de login do sistema em funcionamento", 14)
figura("f4_relatorio.png", "Relatório de atendimentos por profissional (perfil Gerente)", 14)
P("O quadro a seguir mostra o script de criação da tabela agendamento, com as chaves estrangeiras que "
  "implementam os relacionamentos do MER.")
schema = (RAIZ / "app" / "schema.sql").read_text(encoding="utf-8")
codigo(schema[schema.index("CREATE TABLE agendamento"):schema.index("CREATE INDEX")].strip(),
       "Criação da tabela agendamento", "app/schema.sql")
P("Para atender ao RNF03, a interface se adapta à largura do celular (Figura a seguir).")
figura("f4_celular_agenda.png", "Agenda do dia na largura de um celular (RNF03)", 6.5)

# ================================================================== 6 FASE 5
H1("6 Fase 5 – Testes")
P("Testar é executar um programa com a intenção de encontrar erros (MYERS; SANDLER; BADGETT, 2011). "
  "Foram usados testes funcionais de caixa-preta: para cada caso, o resultado esperado foi anotado antes "
  "da execução, o teste foi executado no navegador e o resultado obtido foi registrado com print. Os "
  "mesmos oito casos também foram automatizados com a biblioteca pytest (arquivo tests/test_app.py), "
  "permitindo repetir todos os testes a cada alteração do código.")

H2("6.1 Plano de testes")
cts = [
    ["CT01", "Cadastro de cliente com dados válidos (RF02)", "Nome: Rafael Costa; telefone: (11) 98888-7777; "
     "e-mail válido", "Cliente salvo e exibido na lista com mensagem de sucesso", "Conforme esperado", "Aprovado"],
    ["CT02", "Cadastro sem nome (RF02)", "Nome vazio; telefone válido", "Mensagem \"Informe o nome do "
     "cliente\" e nada é gravado", "Conforme esperado", "Aprovado"],
    ["CT03", "Cadastro com telefone já existente (RF02 / RN04)", "Outro nome com o telefone (11) 98888-7777",
     "Mensagem de telefone já cadastrado e nada é gravado", "Conforme esperado", "Aprovado"],
    ["CT04", "Agendamento válido (RF03 / RF04)", "Rafael Costa, Corte + Barba, João Silva, amanhã às 10:00",
     "Agendamento confirmado e exibido na agenda do dia como AGENDADO", "Conforme esperado", "Aprovado"],
    ["CT05", "Agendar em horário ocupado (RN01)", "Bruno Lima com João Silva às 10:30 (João ocupado das "
     "10:00 às 11:00)", "Sistema impede e avisa que o profissional já tem agendamento", "Conforme esperado",
     "Aprovado"],
    ["CT06", "Login com senha errada (RF01 / RNF02)", "Login ana; senha incorreta",
     "Mensagem \"Login ou senha inválidos\" e acesso negado", "Conforme esperado", "Aprovado"],
    ["CT07", "Cancelar agendamento (RF05)", "Cancelar o agendamento de Felipe Rocha às 11:00",
     "Status muda para CANCELADO e o horário fica livre", "Conforme esperado", "Aprovado"],
    ["CT08", "Agendar em data passada (RN02)", "Data de ontem às 15:00",
     "Sistema impede e avisa que a data/hora já passou", "Conforme esperado", "Aprovado"],
]
tabela("Plano de testes e resultados", ["ID", "O que foi testado", "Entrada", "Resultado esperado",
                                         "Resultado obtido", "Situação"], cts,
       [1.2, 3.2, 3.8, 3.8, 2.2, 1.8], tam=8.5)

H2("6.2 Evidências da execução")
evid = [
    ("ct01_cadastro_valido.png", "CT01 – Cliente cadastrado com sucesso e listado"),
    ("ct02_cadastro_sem_nome.png", "CT02 – Cadastro sem nome bloqueado com mensagem de erro"),
    ("ct03_telefone_duplicado.png", "CT03 – Telefone repetido bloqueado"),
    ("ct04_agendamento_valido.png", "CT04 – Agendamento confirmado e exibido na agenda"),
    ("ct05_horario_ocupado.png", "CT05 – Sistema impede agendamento em horário ocupado"),
    ("ct06_login_invalido.png", "CT06 – Login com senha errada recusado"),
    ("ct07_cancelamento.png", "CT07 – Agendamento cancelado e horário liberado"),
    ("ct08_data_passada.png", "CT08 – Sistema impede agendamento em data passada"),
]
for arq, tit in evid:
    figura(arq, tit, 14)
P("Além da execução manual, os testes automatizados foram executados com o comando \"python -m pytest "
  "-v\", e os oito passaram, como mostra a figura a seguir.")
figura("testes_pytest.png", "Execução dos testes automatizados (pytest)", 15)

# ================================================================== 7 CONSIDERAÇÕES
H1("7 Considerações finais")
P("O projeto permitiu aplicar, em um sistema real e de escopo controlado, todas as etapas do "
  "desenvolvimento de software. O maior aprendizado foi perceber como as fases dependem umas das outras: "
  "ao definir bem os requisitos e as regras de negócio no início, a modelagem das classes e do banco "
  "ficou direta, e o código pôde seguir os mesmos nomes, o que facilitou manter a coerência entre "
  "diagramas, dicionário de dados e implementação.")
P("A principal dificuldade foi a regra de conflito de horário. A primeira ideia era comparar apenas a hora "
  "de início, mas isso deixaria passar casos em que um serviço de 60 minutos invade o horário seguinte. "
  "A solução foi calcular o intervalo de cada agendamento a partir da duração do serviço e verificar a "
  "sobreposição de intervalos, o que foi confirmado pelo caso de teste CT05. Outro ponto de atenção foi a "
  "segurança: as senhas são guardadas como hash e todas as consultas usam parâmetros.")
P("[[Complete com a sua experiência pessoal: o que foi mais difícil para você, o que aprendeu sobre UML, "
  "banco de dados ou Python e o que faria diferente.]]")
P("Como trabalhos futuros, o sistema pode receber o cadastro de profissionais e serviços pela interface, a "
  "marcação de atendimento como concluído, o envio de lembrete ao cliente e uma tela para o próprio "
  "cliente consultar horários livres.")

# ================================================================== REFERÊNCIAS
H1("Referências", quebra=True)
refs = [
    "BOOCH, Grady; RUMBAUGH, James; JACOBSON, Ivar. **UML**: guia do usuário. 2. ed. Rio de Janeiro: Elsevier, 2012.",
    "ELMASRI, Ramez; NAVATHE, Shamkant B. **Sistemas de banco de dados**. 7. ed. São Paulo: Pearson, 2018.",
    "GUEDES, Gilleanes T. A. **UML 2**: uma abordagem prática. 3. ed. São Paulo: Novatec, 2018.",
    "HEUSER, Carlos Alberto. **Projeto de banco de dados**. 6. ed. Porto Alegre: Bookman, 2009.",
    "MYERS, Glenford J.; SANDLER, Corey; BADGETT, Tom. **The art of software testing**. 3. ed. Hoboken: John Wiley & Sons, 2011.",
    "NIELSEN, Jakob. **Usability engineering**. San Diego: Academic Press, 1993.",
    f"PALLETS. **Flask documentation**. Versão 3.1. [S. l.], 2025. Disponível em: https://flask.palletsprojects.com/. Acesso em: {date.today().day} nov. {ANO}.",
    "PRESSMAN, Roger S.; MAXIM, Bruce R. **Engenharia de software**: uma abordagem profissional. 8. ed. Porto Alegre: AMGH, 2016.",
    "SOMMERVILLE, Ian. **Engenharia de software**. 10. ed. São Paulo: Pearson Education do Brasil, 2018.",
    f"SQLITE. **SQLite documentation**. [S. l.], 2025. Disponível em: https://www.sqlite.org/docs.html. Acesso em: {date.today().day} nov. {ANO}.",
    "[[SOBRENOME, Nome do professor. **Título do material de aula**. Cidade: Instituição, ano. Material didático da disciplina X.]]",
]
for r in refs:
    p = P(r, "left", indent=False)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(12)

# numeração de página no rodapé (à direita)
for s in doc.sections:
    fp = s.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = fp.add_run()
    for tipo, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if tipo:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tipo); r._r.append(e)
        else:
            e = OxmlElement("w:instrText"); e.text = txt; r._r.append(e)
    r.font.size = Pt(10)

doc.save(SAIDA)
print(SAIDA, round(SAIDA.stat().st_size / 1024 / 1024, 2), "MB;", FIG[0], "figuras;", TAB[0], "quadros")
