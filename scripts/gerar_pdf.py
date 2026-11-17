"""Abre o relatório no LibreOffice (sem janela), atualiza o sumário e exporta em PDF.

Executar com o Python do LibreOffice:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" scripts/gerar_pdf.py
"""
import subprocess
import time
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue

RAIZ = Path(__file__).resolve().parent.parent
DOCX = RAIZ / "docs" / "relatorio" / "Relatorio_Projeto_Integrado_BarberAgenda.docx"
PDF = DOCX.with_suffix(".pdf")
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"


def prop(nome, valor):
    p = PropertyValue()
    p.Name, p.Value = nome, valor
    return p


proc = subprocess.Popen([SOFFICE, "--headless", "--invisible", "--norestore", "--nologo",
                         "--accept=socket,host=127.0.0.1,port=2002;urp;"])
ctx_local = uno.getComponentContext()
resolver = ctx_local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", ctx_local)
for _ in range(60):
    try:
        ctx = resolver.resolve("uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext")
        break
    except Exception:
        time.sleep(1)
desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
doc = desktop.loadComponentFromURL(DOCX.as_uri(), "_blank", 0, (prop("Hidden", True),))
try:
    indices = doc.getDocumentIndexes()
    for i in range(indices.getCount()):
        indices.getByIndex(i).update()          # gera o sumário com os números de página
    doc.refresh()
    for i in range(indices.getCount()):         # 2ª passada: páginas podem mudar após a 1ª
        indices.getByIndex(i).update()
    print("sumários atualizados:", indices.getCount())
    doc.storeToURL(PDF.as_uri(), (prop("FilterName", "writer_pdf_Export"),))
    print("PDF:", PDF, round(PDF.stat().st_size / 1024 / 1024, 2), "MB")
finally:
    doc.close(True)
    try:
        desktop.terminate()
    except Exception:
        pass
    proc.wait(timeout=30)
