"""Gera os diagramas UML/MER do relatório como SVG (docs/diagramas/*.svg).

Os nomes de classes, entidades e atributos são os mesmos do código (app/models.py)
e do banco (app/schema.sql), para manter a coerência entre os modelos.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "docs" / "diagramas"
OUT.mkdir(parents=True, exist_ok=True)

FONT = "Arial, Helvetica, sans-serif"
INK = "#1f1b18"
ACC = "#8a4b14"
FILL = "#fff8ee"
HEAD = "#e9b872"


def tw(text, size):
    """Largura aproximada do texto em Arial."""
    return len(text) * size * 0.56


def txt(x, y, s, size=14, anchor="start", weight="normal", style="normal", fill=INK):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" font-style="{style}" fill="{fill}">'
            f'{escape(s)}</text>')


def line(x1, y1, x2, y2, dash=False, w=1.6, color=INK, marker=None):
    d = ' stroke-dasharray="7 5"' if dash else ""
    m = f' marker-end="url(#{marker})"' if marker else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{w}"{d}{m}/>'


DEFS = f"""<defs>
<marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
  <path d="M0,0 L10,5 L0,10" fill="none" stroke="{INK}" stroke-width="1.6"/></marker>
<marker id="cheia" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto">
  <path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>
<marker id="heranca" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="14" markerHeight="14" orient="auto">
  <path d="M0,0 L12,6 L0,12 z" fill="#fff" stroke="{INK}" stroke-width="1.3"/></marker>
</defs>"""


def svg(name, w, h, body, title):
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
         f'{DEFS}<rect width="100%" height="100%" fill="#fff"/>'
         f'{txt(20, 30, title, 16, weight="bold", fill="#555")}'
         + "".join(body) + "</svg>")
    (OUT / f"{name}.svg").write_text(s, encoding="utf-8")


# ------------------------------------------------------------------ casos de uso
def actor(cx, top, nome):
    p = [f'<circle cx="{cx}" cy="{top + 14}" r="13" fill="#fff" stroke="{INK}" stroke-width="1.8"/>',
         line(cx, top + 27, cx, top + 70, w=1.8), line(cx - 24, top + 42, cx + 24, top + 42, w=1.8),
         line(cx, top + 70, cx - 20, top + 100, w=1.8), line(cx, top + 70, cx + 20, top + 100, w=1.8),
         txt(cx, top + 122, nome, 15, "middle", "bold")]
    return p


def ellipse(cx, cy, rx, ry, linhas, fill=FILL):
    p = [f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{ACC}" stroke-width="1.8"/>']
    y0 = cy - (len(linhas) - 1) * 9 + 5
    for i, l in enumerate(linhas):
        p.append(txt(cx, y0 + i * 18, l, 14, "middle"))
    return p


def edge_ellipse(cx, cy, rx, ry, px, py):
    """Ponto na borda da elipse na direção de (px, py)."""
    import math
    a = math.atan2(py - cy, px - cx)
    return cx + rx * math.cos(a), cy + ry * math.sin(a)


def casos_de_uso():
    b = []
    b.append(f'<rect x="270" y="55" width="820" height="650" rx="6" fill="none" stroke="{INK}" stroke-width="1.6"/>')
    b.append(txt(680, 80, "Sistema BarberAgenda", 15, "middle", "bold"))
    at = (110, 190)   # (cx, top)
    ge = (110, 480)
    b += actor(*at, "Atendente")
    b += actor(*ge, "Gerente")
    # generalização Gerente -> Atendente
    b.append(line(110, 478, 110, 336, marker="heranca"))
    ucs = [("UC01", ["UC01", "Fazer login"], 125), ("UC02", ["UC02", "Cadastrar cliente"], 225),
           ("UC03", ["UC03", "Agendar horário"], 325), ("UC04", ["UC04", "Consultar agenda do dia"], 445),
           ("UC05", ["UC05", "Cancelar agendamento"], 545), ("UC06", ["UC06", "Gerar relatório", "de atendimentos"], 645)]
    cx, rx, ry = 560, 125, 36
    pos = {}
    for code, label, cy in ucs:
        pos[code] = (cx, cy)
    for code, label, cy in ucs:
        ax, ay = (134, 232) if code != "UC06" else (134, 522)
        ex, ey = edge_ellipse(cx, cy, rx, ry, ax, ay)
        b.append(line(ax, ay, ex, ey))
    for code, label, cy in ucs:
        b += ellipse(cx, cy, rx, ry, label)
    # include
    b += ellipse(930, 325, 115, 36, ["Verificar conflito", "de horário"], fill="#f4efe8")
    b.append(line(cx + rx, 325, 815, 325, dash=True, marker="seta"))
    b.append(txt(750, 315, "«include»", 13, "middle", style="italic"))
    # extend UC05 -> UC04
    b.append(line(cx, 545 - ry, cx, 445 + ry + 2, dash=True, marker="seta"))
    b.append(txt(cx + 8, 500, "«extend»", 13, style="italic"))
    svg("01_casos_de_uso", 1110, 725, b, "Diagrama de Casos de Uso")


# ------------------------------------------------------------- caixas de classe
def caixa(x, y, nome, attrs, metodos=None, w=None, head=HEAD, size=13.5, stereo=None):
    lh = size + 7
    linhas = [nome] + attrs + (metodos or [])
    w = w or max(tw(l, size) for l in linhas) + 30
    hh = 34 if not stereo else 48
    ha = len(attrs) * lh + 12
    hm = (len(metodos) * lh + 12) if metodos is not None else 0
    h = hh + ha + hm
    p = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{FILL}" stroke="{ACC}" stroke-width="1.8"/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="{hh}" fill="{head}" stroke="{ACC}" stroke-width="1.8"/>']
    if stereo:
        p.append(txt(x + w / 2, y + 18, stereo, 12, "middle", style="italic"))
        p.append(txt(x + w / 2, y + 38, nome, 15, "middle", "bold"))
    else:
        p.append(txt(x + w / 2, y + 23, nome, 15, "middle", "bold"))
    yy = y + hh + 6 + size
    for a in attrs:
        under = a.startswith("PK ") or a.startswith("PK,")
        p.append(txt(x + 10, yy, a, size, weight="bold" if under else "normal"))
        yy += lh
    if metodos is not None:
        p.append(line(x, y + hh + ha, x + w, y + hh + ha, color=ACC, w=1.4))
        yy = y + hh + ha + 6 + size
        for m in metodos:
            p.append(txt(x + 10, yy, m, size))
            yy += lh
    return p, (x, y, w, h)


def classes():
    b = []
    ag, rag = caixa(450, 250, "Agendamento",
                    ["- id_agendamento : int", "- id_cliente : int", "- id_profissional : int",
                     "- id_servico : int", "- id_usuario : int", "- data : date", "- hora : time",
                     "- status : str", "- observacao : str"],
                    ["+ validar() : list", "+ verificar_conflito(inicio, fim) : bool", "+ salvar() : int",
                     "+ cancelar(id_agendamento) : bool", "+ listar_por_data(data, id_profissional) : list",
                     "+ relatorio_periodo(data_inicio, data_fim) : list"])
    cl, rcl = caixa(40, 60, "Cliente",
                    ["- id_cliente : int", "- nome : str", "- telefone : str", "- email : str", "- data_cadastro : date"],
                    ["+ validar() : list", "+ salvar() : int", "+ listar() : list"])
    us, rus = caixa(40, 560, "Usuario",
                    ["- id_usuario : int", "- nome : str", "- login : str", "- senha_hash : str", "- perfil : str"],
                    ["+ autenticar(login, senha) : Usuario"])
    pr, rpr = caixa(1000, 60, "Profissional",
                    ["- id_profissional : int", "- nome : str", "- especialidade : str", "- ativo : bool"],
                    ["+ listar_ativos() : list"])
    sv, rsv = caixa(1000, 560, "Servico",
                    ["- id_servico : int", "- nome : str", "- duracao_min : int", "- preco : float"],
                    ["+ listar() : list", "+ buscar_por_id(id_servico) : Servico"])
    ax, ay, aw, ah = rag
    rel = [  # (caixa, ponto na caixa, ponto no Agendamento, rótulo, mult_lado, mult_ag)
        (rcl, "dir", (ax, ay + 40), "possui", "1", "0..*"),
        (rus, "dir", (ax, ay + ah - 40), "registra", "1", "0..*"),
        (rpr, "esq", (ax + aw, ay + 40), "atende", "1", "0..*"),
        (rsv, "esq", (ax + aw, ay + ah - 40), "refere-se a", "1", "0..*"),
    ]
    for (x, y, w, h), lado, (tx, ty), rot, m1, m2 in rel:
        sx = x + w if lado == "dir" else x
        sy = y + h / 2
        b.append(line(sx, sy, tx, ty))
        mx, my = (sx + tx) / 2, (sy + ty) / 2
        b.append(f'<rect x="{mx - tw(rot, 13) / 2 - 4}" y="{my - 15}" width="{tw(rot, 13) + 8}" height="20" fill="#fff"/>')
        b.append(txt(mx, my, rot, 13, "middle", style="italic"))
        d1 = 14 if lado == "dir" else -14
        desce = ty > sy
        b.append(txt(sx + d1, sy - 10 if desce else sy + 24, m1, 14, "middle", "bold"))
        b.append(txt(tx - d1 * 2.2, ty + 24 if desce else ty - 10, m2, 14, "middle", "bold"))
    b += ag + cl + us + pr + sv
    svg("02_classes", 1330, 830, b, "Diagrama de Classes")


# --------------------------------------------------------------------------- MER
def crow(x, y, direcao, muitos):
    """Desenha a terminação pé-de-galinha. direcao: 'L' (entidade à esquerda do ponto) ou 'R'."""
    s = 1 if direcao == "R" else -1   # sentido para dentro da entidade
    p = []
    if muitos:   # zero-ou-muitos: círculo + pé de galinha
        p.append(line(x - s * 2, y, x - s * 16, y - 9))
        p.append(line(x - s * 2, y, x - s * 16, y + 9))
        p.append(f'<circle cx="{x - s * 24}" cy="{y}" r="6" fill="#fff" stroke="{INK}" stroke-width="1.5"/>')
    else:        # exatamente um: duas barras
        p.append(line(x - s * 10, y - 9, x - s * 10, y + 9))
        p.append(line(x - s * 17, y - 9, x - s * 17, y + 9))
    return p


def mer():
    b = []
    ent = {}
    ag, ent["agendamento"] = caixa(500, 250, "agendamento",
        ["PK id_agendamento : INTEGER", "FK id_cliente : INTEGER", "FK id_profissional : INTEGER",
         "FK id_servico : INTEGER", "FK id_usuario : INTEGER", "data : DATE", "hora : TIME",
         "status : VARCHAR(10)", "observacao : VARCHAR(200)", "criado_em : DATETIME"], w=300, stereo="«tabela»")
    cl, ent["cliente"] = caixa(50, 70, "cliente",
        ["PK id_cliente : INTEGER", "nome : VARCHAR(100)", "telefone : VARCHAR(15) UQ",
         "email : VARCHAR(100)", "data_cadastro : DATE"], w=280, stereo="«tabela»")
    us, ent["usuario"] = caixa(50, 520, "usuario",
        ["PK id_usuario : INTEGER", "nome : VARCHAR(100)", "login : VARCHAR(30) UQ",
         "senha_hash : VARCHAR(255)", "perfil : VARCHAR(10)"], w=280, stereo="«tabela»")
    pr, ent["profissional"] = caixa(970, 70, "profissional",
        ["PK id_profissional : INTEGER", "nome : VARCHAR(100)", "especialidade : VARCHAR(50)",
         "ativo : BOOLEAN"], w=280, stereo="«tabela»")
    sv, ent["servico"] = caixa(970, 520, "servico",
        ["PK id_servico : INTEGER", "nome : VARCHAR(60)", "duracao_min : INTEGER",
         "preco : DECIMAL(8,2)"], w=280, stereo="«tabela»")
    ax, ay, aw, ah = ent["agendamento"]
    for nome, lado, ty, rot in [("cliente", "esq", ay + 95, "possui"), ("usuario", "esq", ay + 170, "registra"),
                                ("profissional", "dir", ay + 100, "atende"), ("servico", "dir", ay + 200, "é usado em")]:
        x, y, w, h = ent[nome]
        if lado == "esq":
            sx, sy = x + w, y + h / 2
            ex = ax
            mid = (sx + ex) / 2
            pts = f"{sx},{sy} {mid},{sy} {mid},{ty} {ex},{ty}"
            b.append(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
            b += crow(sx, sy, "L", False)      # lado 1 (cliente)
            b += crow(ex, ty, "R", True)       # lado N (agendamento)
            b.append(txt(mid + 8, (sy + ty) / 2, rot, 13, style="italic"))
            b.append(txt(sx + 12, sy - 14, "1", 13, weight="bold"))
            b.append(txt(ex - 34, ty - 14, "N", 13, weight="bold"))
        else:
            sx, sy = x, y + h / 2
            ex = ax + aw
            mid = (sx + ex) / 2
            pts = f"{sx},{sy} {mid},{sy} {mid},{ty} {ex},{ty}"
            b.append(f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
            b += crow(sx, sy, "R", False)
            b += crow(ex, ty, "L", True)
            b.append(txt(mid - 8, (sy + ty) / 2, rot, 13, "end", style="italic"))
            b.append(txt(sx - 18, sy - 14, "1", 13, weight="bold"))
            b.append(txt(ex + 26, ty - 14, "N", 13, weight="bold"))
    b += ag + cl + us + pr + sv
    b.append(txt(50, 790, "Notação pé-de-galinha (Crow's Foot): ‖ = exatamente um;  ○< = zero ou muitos.  "
                          "PK = chave primária, FK = chave estrangeira, UQ = valor único.", 13, fill="#555"))
    svg("03_mer", 1300, 810, b, "Modelo Entidade-Relacionamento (MER)")


# ------------------------------------------------------------------- sequência
def sequencia():
    parts = [("Atendente", "ator"), ("Tela Novo\nAgendamento", "boundary"), ("Controlador\nnovo_agendamento", "control"),
             ("Agendamento", "entity"), ("Servico", "entity"), ("Banco SQLite", "db")]
    xs = [90, 290, 500, 720, 920, 1110]
    msgs = [  # (de, para, texto, tipo) tipo: c=chamada, r=retorno, s=self
        (0, 1, "preenche os dados", "c"),
        (0, 1, "clica em \"Confirmar\"", "c"),
        (1, 2, "POST /agendamentos/novo", "c"),
        (2, 3, "Agendamento(dados)", "c"),
        (2, 3, "validar()", "c"),
        (3, 4, "buscar_por_id(id_servico)", "c"),
        (4, 5, "SELECT * FROM servico WHERE id_servico = ?", "c"),
        (5, 4, "duracao_min, preco", "r"),
        (4, 3, "servico", "r"),
        (3, 3, "confere data futura e horário 09:00–19:00", "s"),
        (3, 3, "verificar_conflito(inicio, fim)", "s"),
        (3, 5, "SELECT agendamentos ativos do profissional na data", "c"),
        (5, 3, "horários ocupados", "r"),
        ("alt", "[horário livre e dados válidos]"),
        (3, 2, "lista de erros vazia", "r"),
        (2, 3, "salvar()", "c"),
        (3, 5, "INSERT INTO agendamento (...)", "c"),
        (5, 3, "id_agendamento", "r"),
        (2, 1, "redirect para a agenda do dia", "r"),
        (1, 0, "\"Agendamento confirmado.\"", "r"),
        ("else", "[horário ocupado ou dados inválidos]"),
        (3, 2, "lista de erros", "r"),
        (2, 1, "formulário preenchido + mensagens", "r"),
        (1, 0, "mensagem de erro", "r"),
        ("end",),
    ]
    b = []
    top = 100
    head_h = 56
    y = top + head_h + 40
    rows = []
    n = 0
    alt_top = None
    for m in msgs:
        if m[0] == "alt":
            alt_top = y - 8
            rows.append(("altlabel", y, m[1])); y += 34
        elif m[0] == "else":
            rows.append(("else", y, m[1])); y += 34
        elif m[0] == "end":
            rows.append(("end", y)); y += 20
        else:
            n += 1
            rows.append(("msg", y, m, n)); y += 44 if m[3] != "s" else 52
    bottom = y + 10
    # lifelines
    for (nome, tipo), x in zip(parts, xs):
        b.append(line(x, top + head_h, x, bottom, dash=True, w=1.2, color="#888"))
    for (nome, tipo), x in zip(parts, xs):
        ls = nome.split("\n")
        if tipo == "ator":
            b += actor(x, top - 40, "")
            b.append(txt(x, top + head_h + 8, nome, 14, "middle", "bold"))
            continue
        w = max(tw(l, 14) for l in ls) + 30
        rx = 22 if tipo == "db" else 4
        b.append(f'<rect x="{x - w / 2}" y="{top}" width="{w}" height="{head_h}" rx="{rx}" fill="{FILL}" stroke="{ACC}" stroke-width="1.8"/>')
        ster = {"boundary": "«boundary»", "control": "«control»", "entity": "«entity»", "db": "«database»"}[tipo]
        b.append(txt(x, top + 16, ster, 11, "middle", style="italic", fill="#666"))
        for i, l in enumerate(ls):
            b.append(txt(x, top + 33 + i * 16, l, 14, "middle", "bold"))
    # mensagens
    for r in rows:
        if r[0] == "msg":
            _, yy, (de, para, texto, tipo), num = r
            label = f"{num}. {texto}"
            if tipo == "s":
                x = xs[de]
                b.append(f'<polyline points="{x},{yy} {x + 40},{yy} {x + 40},{yy + 20} {x + 6},{yy + 20}" fill="none" stroke="{INK}" stroke-width="1.6" marker-end="url(#cheia)"/>')
                b.append(f'<rect x="{x + 45}" y="{yy}" width="{tw(label, 13) + 6}" height="18" fill="#fff"/>')
                b.append(txt(x + 48, yy + 14, label, 13))
            else:
                x1, x2 = xs[de], xs[para]
                b.append(line(x1, yy, x2 + (-4 if x2 > x1 else 4), yy, dash=(tipo == "r"),
                              marker="cheia" if tipo == "c" else "seta"))
                cx = (x1 + x2) / 2
                b.append(f'<rect x="{cx - tw(label, 13) / 2 - 3}" y="{yy - 21}" width="{tw(label, 13) + 6}" height="17" fill="#fff"/>')
                b.append(txt(cx, yy - 7, label, 13, "middle"))
        elif r[0] == "altlabel":
            yy = r[1]
            b.append(f'<path d="M30,{yy - 8} h52 v14 l-8,8 h-44 z" fill="#f4efe8" stroke="{INK}" stroke-width="1.3"/>')
            b.append(txt(40, yy + 9, "alt", 13, weight="bold"))
            b.append(txt(96, yy + 9, r[2], 13, style="italic"))
        elif r[0] == "else":
            yy = r[1]
            b.append(line(30, yy - 8, 1200, yy - 8, dash=True, w=1.2))
            b.append(txt(40, yy + 10, r[2], 13, style="italic"))
        elif r[0] == "end":
            yy = r[1]
            b.append(f'<rect x="30" y="{alt_top}" width="1170" height="{yy - alt_top}" fill="none" stroke="{INK}" stroke-width="1.3"/>')
    svg("04_sequencia_agendar", 1230, bottom + 20, b, "Diagrama de Sequência – UC03 Agendar horário")


if __name__ == "__main__":
    casos_de_uso()
    classes()
    mer()
    sequencia()
    print("SVGs gerados em", OUT)
