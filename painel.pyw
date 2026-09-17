# -*- coding: utf-8 -*-
"""Painel local Finaud — liga/desliga API e tela de cada sistema neste PC."""
from __future__ import annotations

import ctypes
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import socket
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system DPI aware — coordenadas lógicas consistentes
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_DISPONIVEL = True
except ImportError:
    TRAY_DISPONIVEL = False

CREATE_NO_WINDOW         = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
ERROR_ALREADY_EXISTS     = 183
SW_RESTORE               = 9
TITULO                   = "Finaud — Serviços locais"
MUTEX_NOME               = "FinaudPainelServicosLocais"
PASTA_PAINEL             = Path(__file__).resolve().parent
RAIZ_ATIVOS              = Path(r"D:\02_Finaud\Projetos\ativos")
PASTA_LOGS               = PASTA_PAINEL / "logs"
ARQUIVO_TEMA             = PASTA_PAINEL / "tema.txt"

# Lê preferência salva (padrão: light)
try:
    _tema_salvo = ARQUIVO_TEMA.read_text().strip()
    if _tema_salvo not in ("light", "dark"):
        _tema_salvo = "light"
except Exception:
    _tema_salvo = "light"

ctk.set_appearance_mode(_tema_salvo)


def _cor_tk(cores: tuple[str, str]) -> str:
    """Retorna a cor correta (claro/escuro) para widgets tk nativos."""
    return cores[1] if ctk.get_appearance_mode().lower() == "dark" else cores[0]

# ── Paleta  (claro, escuro) ───────────────────────────────────────────────────
BG_APP      = ("#f5f7fc", "#090c18")
BG_HEADER   = ("#ebeef8", "#07091a")
BG_LISTA    = ("#ffffff", "#0d1122")
BORDA_LISTA = ("#d0d4e8", "#1a1e3a")
BORDA_ROW   = ("#e8eaf2", "#111828")   # tk.Frame — usar _cor_tk()
COR_TEXTO   = ("#1a2040", "#ccd4ee")
COR_SUAVE   = ("#7080a0", "#252a40")
COR_LABEL   = "#3a5aff"

_COR_DOT = {
    "no_ar":      ("#2e7d32", "#2d9a50"),
    "parcial":    ("#e65100", "#9a7020"),
    "ligando":    ("#e65100", "#9a7020"),
    "desligando": ("#e65100", "#9a7020"),
    "parado":     ("#b71c1c", "#7a2020"),
}
_COR_NOME = {
    "no_ar":      COR_TEXTO,
    "parcial":    ("#7a4a10", "#a08050"),
    "ligando":    ("#7a4a10", "#a08050"),
    "desligando": ("#7a4a10", "#a08050"),
    "parado":     ("#7a3030", "#7a5050"),
}


def _uptime_label(estado: str, uptime_str: str) -> tuple[str, tuple]:
    if estado == "no_ar":
        return uptime_str, ("#2e7d32", "#4aaa70")
    if estado in ("ligando", "parcial"):
        return "Ligando…", ("#e65100", "#b09040")
    if estado == "desligando":
        return "Saindo…", ("#e65100", "#b09040")
    return "Parado", ("#c62828", "#a05050")


# ── Backend ───────────────────────────────────────────────────────────────────

def python_do_projeto(raiz: Path) -> str:
    for rel in (".venv/Scripts/python.exe", "venv/Scripts/python.exe"):
        c = raiz / rel
        if c.is_file():
            return str(c)
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        p = exe.with_name("python.exe")
        if p.is_file():
            return str(p)
    return str(exe)


def npm_cmd() -> str:
    found = shutil.which("npm.cmd") or shutil.which("npm")
    if not found:
        raise FileNotFoundError("npm não encontrado. Instale o Node.js.")
    return found


def ssh_cmd() -> str:
    found = shutil.which("ssh")
    if not found:
        raise FileNotFoundError(
            "ssh não encontrado. Instale o OpenSSH "
            "(Windows → Configurações → Recursos opcionais)."
        )
    return found


@dataclass
class Processo:
    chave: str
    cwd: Path
    argv: list[str]
    porta: int
    health: str


@dataclass
class Servico:
    id: str
    nome: str
    detalhe: str
    processos: list[Processo]
    abrir: list[tuple[str, str]]


def catalogo() -> list[Servico]:
    portal      = RAIZ_ATIVOS / "portal_finaudapps"
    auditoria   = RAIZ_ATIVOS / "Projeto_Auditoria_IA"
    normativos  = RAIZ_ATIVOS / "normativos_ia"
    leiautes    = RAIZ_ATIVOS / "leiautes"
    gestao      = RAIZ_ATIVOS / "gestao_area_suporte"
    c214        = RAIZ_ATIVOS / "C214"
    prospeccao  = RAIZ_ATIVOS / "prospeccao_finaud"
    site        = RAIZ_ATIVOS / "migração site"
    conformidade= RAIZ_ATIVOS / "painel_conformidade"
    npm         = npm_cmd()
    py_site     = python_do_projeto(site)
    return [
        Servico(
            id="portal", nome="Portal / Admin", detalhe="Tela 8000 · API 8000",
            processos=[Processo("api", portal / "portal-auth" / "backend",
                                [python_do_projeto(portal), "-m", "app.main"],
                                8000, "http://127.0.0.1:8000/health")],
            abrir=[("Portal", "http://127.0.0.1:8000/portal-preview/"),
                   ("Admin",  "http://127.0.0.1:8000/admin-preview/")],
        ),
        Servico(
            id="auditoria", nome="Auditoria IA", detalhe="Tela 5173 · API 8001",
            processos=[
                Processo("api",  auditoria / "backend",  [python_do_projeto(auditoria), "-m", "app.main"], 8001, "http://127.0.0.1:8001/health"),
                Processo("tela", auditoria / "frontend", [npm, "run", "dev"], 5173, "http://127.0.0.1:5173/"),
            ],
            abrir=[("Abrir", "http://127.0.0.1:5173/")],
        ),
        Servico(
            id="normativos", nome="Normativos IA", detalhe="Tela 5178 · API 8002",
            processos=[
                Processo("api",  normativos / "backend",  [python_do_projeto(normativos), "-m", "app.main"], 8002, "http://127.0.0.1:8002/health"),
                Processo("tela", normativos / "frontend", [npm, "run", "dev"], 5178, "http://127.0.0.1:5178/"),
            ],
            abrir=[("Abrir", "http://127.0.0.1:5178/")],
        ),
        Servico(
            id="leiautes", nome="Leiautes Bacen", detalhe="Tela 5177 · API 8003",
            processos=[
                Processo("api",  leiautes / "backend",  [python_do_projeto(leiautes), "-m", "app.main"], 8003, "http://127.0.0.1:8003/health"),
                Processo("tela", leiautes / "frontend", [npm, "run", "dev"], 5177, "http://127.0.0.1:5177/"),
            ],
            abrir=[("Abrir", "http://127.0.0.1:5177/")],
        ),
        Servico(
            id="gestao", nome="Gestão Área Suporte", detalhe="Tela 8004 · API 8004",
            processos=[Processo("flask", gestao, [python_do_projeto(gestao), "scripts/servidor_telas.py"], 8004, "http://127.0.0.1:8004/")],
            abrir=[("Abrir", "http://127.0.0.1:8004/")],
        ),
        Servico(
            id="c214", nome="C214 Bacen", detalhe="Tela 5180 · API 8005",
            processos=[
                Processo("api",  c214 / "backend",  [python_do_projeto(c214), "-m", "app.main"], 8005, "http://127.0.0.1:8005/health"),
                Processo("tela", c214 / "frontend", [npm, "run", "dev"], 5180, "http://127.0.0.1:5180/"),
            ],
            abrir=[("Abrir", "http://127.0.0.1:5180/")],
        ),
        Servico(
            id="findabc", nome="findabc", detalhe="Tunnel · API 8010",
            processos=[
                Processo("tunnel", PASTA_PAINEL, [
                    ssh_cmd(), "-i", str(Path.home() / ".ssh" / "id_ed25519_cyberpanel"),
                    "-N", "-L", "5432:127.0.0.1:5432",
                    "-o", "StrictHostKeyChecking=no", "-o", "ExitOnForwardFailure=yes",
                    "root@31.97.82.203",
                ], 5432, "tcp://127.0.0.1:5432"),
                Processo("api", RAIZ_ATIVOS / "findabc", [
                    python_do_projeto(RAIZ_ATIVOS / "findabc"),
                    "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010",
                ], 8010, "http://127.0.0.1:8010/"),
            ],
            abrir=[("Abrir", "http://127.0.0.1:8010/")],
        ),
        Servico(
            id="prospeccao", nome="Prospecção Finaud", detalhe="Tela 8006 · API 8006",
            processos=[Processo("flask", prospeccao, [python_do_projeto(prospeccao), "scripts/servidor_prospeccao.py"], 8006, "http://127.0.0.1:8006/")],
            abrir=[("Abrir", "http://127.0.0.1:8006/")],
        ),
        Servico(
            id="s5", nome="S5 Enquadramento", detalhe="API 8007",
            processos=[Processo("api", RAIZ_ATIVOS / "s5", [
                python_do_projeto(RAIZ_ATIVOS / "s5"),
                "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8007",
            ], 8007, "http://127.0.0.1:8007/")],
            abrir=[("Abrir", "http://127.0.0.1:8007/"), ("API", "http://127.0.0.1:8007/docs")],
        ),
        Servico(
            id="site", nome="Site institucional", detalhe="Tela 8090 · API 8091",
            processos=[
                Processo("tela", site / "site", [py_site, "-m", "http.server", "8090", "--bind", "127.0.0.1"], 8090, "http://127.0.0.1:8090/"),
                Processo("api",  site / "atendimento", [python_do_projeto(site / "atendimento"), "-m", "app.main"], 8091, "http://127.0.0.1:8091/health"),
            ],
            abrir=[("Abrir", "http://127.0.0.1:8090/"), ("Admin", "http://127.0.0.1:8091/admin/")],
        ),
        Servico(
            id="conformidade", nome="Painel Conformidade", detalhe="API 8009",
            processos=[Processo("api", conformidade, [
                python_do_projeto(conformidade),
                "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8009",
            ], 8009, "http://127.0.0.1:8009/health")],
            abrir=[("Abrir", "http://127.0.0.1:8009/")],
        ),
        Servico(
            id="radar_bacen", nome="Radar Bacen", detalhe="Tela 8008 · API 8008",
            processos=[Processo("api", RAIZ_ATIVOS / "radar_bacen", [
                python_do_projeto(RAIZ_ATIVOS / "radar_bacen"),
                "-m", "uvicorn", "app.web.app:app", "--host", "127.0.0.1", "--port", "8008",
            ], 8008, "http://127.0.0.1:8008/")],
            abrir=[("Abrir", "http://127.0.0.1:8008/")],
        ),
    ]


def porta_aberta(porta: int, timeout: float = 0.15) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=timeout):
            return True
    except OSError:
        return False


def estado_das_portas(servico: Servico) -> str:
    resultados = [porta_aberta(p.porta) for p in servico.processos]
    if all(resultados):
        return "no_ar"
    if any(resultados):
        return "parcial"
    return "parado"


def pids_na_porta(porta: int) -> set[int]:
    try:
        bruto = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            creationflags=CREATE_NO_WINDOW, stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    texto = bruto.decode("oem", errors="replace")
    achados: set[int] = set()
    padrao = re.compile(rf":{porta}(?!\d)\s+\S+\s+LISTENING\s+(\d+)", re.IGNORECASE)
    for pid_txt in padrao.findall(texto):
        pid = int(pid_txt)
        if pid > 4:
            achados.add(pid)
    return achados


def matar_pid(pid: int) -> None:
    if pid <= 4:
        return
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                   capture_output=True, creationflags=CREATE_NO_WINDOW)


def matar_porta(porta: int) -> None:
    for pid in pids_na_porta(porta):
        matar_pid(pid)


def arquivo_log(servico_id: str, chave: str) -> Path:
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)
    return PASTA_LOGS / f"{servico_id}-{chave}.log"


def iniciar_processo(servico_id: str, proc: Processo) -> None:
    if porta_aberta(proc.porta):
        return
    if not proc.cwd.is_dir():
        raise FileNotFoundError(f"Pasta não encontrada: {proc.cwd}")
    _SEM_PATH = {"npm", "npm.cmd", "ssh"}
    if not Path(proc.argv[0]).exists() and proc.argv[0] not in _SEM_PATH:
        raise FileNotFoundError(f"Programa não encontrado: {proc.argv[0]}")
    log_path = arquivo_log(servico_id, proc.chave)
    log = open(log_path, "a", encoding="utf-8", errors="replace")
    log.write(f"\n----- {datetime.now().isoformat(timespec='seconds')} -----\n")
    log.flush()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    subprocess.Popen(
        proc.argv, cwd=str(proc.cwd),
        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        env=env, creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
    )


def ligar_servico(servico: Servico) -> str | None:
    erros: list[str] = []
    for proc in servico.processos:
        try:
            iniciar_processo(servico.id, proc)
        except Exception as exc:
            erros.append(f"{proc.chave}: {exc}")
    return (f"{servico.nome}: " + "; ".join(erros)) if erros else None


def desligar_servico(servico: Servico) -> None:
    for proc in reversed(servico.processos):
        matar_porta(proc.porta)


def ja_existe_outra_janela() -> bool:
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NOME)
    if not handle:
        return False
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        hwnd = ctypes.windll.user32.FindWindowW(None, TITULO)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        return True
    return False


def _formatar_uptime(segundos: int) -> str:
    h, r = divmod(segundos, 3600)
    m, _ = divmod(r, 60)
    return f"↑ {h}h {m}m" if h else f"↑ {m}m"


# ── UI ────────────────────────────────────────────────────────────────────────

def _lnk(parent: ctk.CTkFrame, texto: str, url: str,
         cor: tuple = ("#1565c0", "#5a80c0")) -> None:
    lbl = ctk.CTkLabel(parent, text=texto, text_color=cor,
                        font=ctk.CTkFont("Segoe UI", 9), cursor="hand2")
    lbl.pack(side="left", padx=(0, 6))
    lbl.bind("<Button-1>", lambda _e: webbrowser.open(url))
    lbl.bind("<Enter>", lambda _e: lbl.configure(text_color=("#1976d2", "#8ab0f0")))
    lbl.bind("<Leave>", lambda _e: lbl.configure(text_color=cor))


class LinhaServico(ctk.CTkFrame):
    def __init__(self, pai, servico: Servico, ao_ligar, ao_desligar, estado_de) -> None:
        super().__init__(pai, fg_color=BG_LISTA, corner_radius=0, border_width=0)
        self.pack(fill="x")
        self.servico = servico
        self._ao_ligar = ao_ligar
        self._ao_desligar = ao_desligar
        self._estado_de = estado_de
        self.ocupado = False

        # Linha separadora no fundo
        self._sep_row = tk.Frame(self, bg=_cor_tk(BORDA_ROW), height=1)
        self._sep_row.pack(side="bottom", fill="x")

        # Conteúdo interno
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=9)

        # ── Zona A: ponto de status + nome + detalhe ──
        za = ctk.CTkFrame(inner, fg_color="transparent")
        za.pack(side="left", fill="x", expand=True)

        self._dot = ctk.CTkLabel(za, text="●", text_color=("#b71c1c", "#7a2020"),
                                  font=ctk.CTkFont("Segoe UI", 8))
        self._dot.pack(side="left", padx=(0, 8))

        self._lbl_nome = ctk.CTkLabel(za, text=servico.nome,
                                       text_color=COR_TEXTO,
                                       font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
                                       anchor="w")
        self._lbl_nome.pack(side="left")

        ctk.CTkLabel(za, text=" · ", text_color=("#b0b8d0", "#3a4060"),
                     font=ctk.CTkFont("Segoe UI", 10)).pack(side="left")

        ctk.CTkLabel(za, text=servico.detalhe, text_color=("#5060a0", "#5a6490"),
                     font=ctk.CTkFont("Consolas", 9), anchor="w").pack(side="left")

        # ── Zona B: uptime ──
        self._lbl_uptime = ctk.CTkLabel(inner, text="", text_color=("#2e7d32", "#4aaa70"),
                                         font=ctk.CTkFont("Segoe UI", 10),
                                         width=80, anchor="e")
        self._lbl_uptime.pack(side="left", padx=(6, 0))

        # ── Zona C: botão + separador + links ──
        zc = ctk.CTkFrame(inner, fg_color="transparent")
        zc.pack(side="right")

        self._btn = ctk.CTkButton(
            zc, text="Ligar", width=80, height=26, corner_radius=4,
            fg_color=("#e8f5e9", "#081808"), text_color=("#2e7d32", "#409060"),
            hover_color=("#c8e6c9", "#0a2010"),
            border_width=0, font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
            command=self._clique,
        )
        self._btn.pack(side="left")

        self._sep_ver = tk.Frame(zc, bg=_cor_tk(("#c8cce0", "#151a30")), width=1, height=14)
        self._sep_ver.pack(side="left", padx=8)

        for rotulo, url in servico.abrir:
            cor_lnk = ("#1a7040", "#4a9060") if rotulo == "API" else ("#1565c0", "#5a80c0")
            _lnk(zc, rotulo if rotulo == "API" else f"↗ {rotulo}", url, cor_lnk)

        lbl_log = ctk.CTkLabel(zc, text="log", text_color=("#9090b0", "#3a4468"),
                                 font=ctk.CTkFont("Segoe UI", 9), cursor="hand2")
        lbl_log.pack(side="left")
        lbl_log.bind("<Button-1>", lambda _e: self._abrir_log())
        lbl_log.bind("<Enter>", lambda _e: lbl_log.configure(text_color=("#3050c0", "#7a88c0")))
        lbl_log.bind("<Leave>", lambda _e: lbl_log.configure(text_color=("#9090b0", "#3a4468")))

    def atualizar_tema(self) -> None:
        self._sep_row.configure(bg=_cor_tk(BORDA_ROW))
        self._sep_ver.configure(bg=_cor_tk(("#c8cce0", "#151a30")))

    def _clique(self) -> None:
        if self.ocupado:
            return
        if self._estado_de(self.servico) == "parado":
            self._ao_ligar(self.servico)
        else:
            self._ao_desligar(self.servico)

    def _abrir_log(self) -> None:
        PASTA_LOGS.mkdir(parents=True, exist_ok=True)
        os.startfile(PASTA_LOGS)

    def atualizar(self, estado: str, ocupado: bool, uptime: str = "") -> None:
        self.ocupado = ocupado
        self._dot.configure(text_color=_COR_DOT.get(estado, "#7a2020"))
        self._lbl_nome.configure(text_color=_COR_NOME.get(estado, "#7a5050"))
        txt_up, cor_up = _uptime_label(estado, uptime)
        self._lbl_uptime.configure(text=txt_up, text_color=cor_up)
        if ocupado:
            self._btn.configure(state="disabled", text="Aguardar…",
                                 fg_color=("#f5f5e8", "#181400"),
                                 text_color=("#909060", "#504020"),
                                 hover_color=("#f5f5e8", "#181400"))
        elif estado == "parado":
            self._btn.configure(state="normal", text="Ligar",
                                 fg_color=("#e8f5e9", "#081808"),
                                 text_color=("#2e7d32", "#409060"),
                                 hover_color=("#c8e6c9", "#0a2010"))
        else:
            self._btn.configure(state="normal", text="Desligar",
                                 fg_color=("#ffebee", "#200808"),
                                 text_color=("#c62828", "#c05050"),
                                 hover_color=("#ffcdd2", "#280a0a"))


class Painel(ctk.CTk):
    def __init__(self, servicos: list[Servico]) -> None:
        super().__init__()
        self.servicos      = servicos
        self.linhas:        dict[str, LinhaServico] = {}
        self.ocupados:      set[str]                = set()
        self.acoes:         dict[str, str]          = {}
        self.estados:       dict[str, str]          = {s.id: "parado" for s in servicos}
        self.inicio_acao:   dict[str, float]        = {}
        self.inicio_no_ar:  dict[str, float]        = {}
        self._fila:         queue.Queue             = queue.Queue()
        self._icone_tray                            = None

        self.title(TITULO)
        self.configure(fg_color=BG_APP)
        self.minsize(520, 540)
        self._montar()
        self._posicionar()
        self.after(300, self._esconder_monitor_window)
        threading.Thread(target=self._trabalhador, daemon=True).start()
        threading.Thread(target=self._observar,    daemon=True).start()
        if TRAY_DISPONIVEL:
            self.protocol("WM_DELETE_WINDOW", self._minimizar_para_tray)
            self._criar_tray()
        else:
            self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ── Layout ───────────────────────────────────────────────────────────────

    def _montar(self) -> None:
        # Header
        hd = ctk.CTkFrame(self, fg_color=BG_HEADER, corner_radius=0, height=56)
        hd.pack(fill="x")
        hd.pack_propagate(False)

        hd_inner = ctk.CTkFrame(hd, fg_color="transparent")
        hd_inner.pack(fill="both", expand=True, padx=20)

        # Título (esquerda)
        left = ctk.CTkFrame(hd_inner, fg_color="transparent")
        left.pack(side="left", fill="y")
        ctk.CTkLabel(left, text="Finaud", text_color=("#8090b0", "#505880"),
                     font=ctk.CTkFont("Segoe UI", 9), anchor="w").pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(left, text="Serviços locais", text_color=COR_TEXTO,
                     font=ctk.CTkFont("Segoe UI", 14, weight="bold"), anchor="w").pack(anchor="w")

        # Botões globais (direita)
        right = ctk.CTkFrame(hd_inner, fg_color="transparent")
        right.pack(side="right", fill="y")

        ctk.CTkButton(
            right, text="Ligar todos", command=self._ligar_todos,
            width=95, height=28, corner_radius=5, border_width=1,
            fg_color=("#e8f5e9", "#0d2218"), text_color=("#2e7d32", "#4caf50"),
            hover_color=("#c8e6c9", "#102a1e"), border_color=("#a5d6a7", "#1a4a28"),
            font=ctk.CTkFont("Segoe UI", 9),
        ).pack(side="left", padx=(0, 6), pady=14)

        ctk.CTkButton(
            right, text="Desligar todos", command=self._desligar_todos,
            width=105, height=28, corner_radius=5, border_width=1,
            fg_color=("#ffebee", "#1e0a0a"), text_color=("#c62828", "#ef5350"),
            hover_color=("#ffcdd2", "#260c0c"), border_color=("#ef9a9a", "#4a1010"),
            font=ctk.CTkFont("Segoe UI", 9),
        ).pack(side="left", padx=(0, 6))

        if TRAY_DISPONIVEL:
            ctk.CTkButton(
                right, text="↙ Bandeja", command=self._minimizar_para_tray,
                width=80, height=28, corner_radius=5, border_width=1,
                fg_color="transparent", text_color=("#5060a0", "#3a4070"),
                border_color=("#c0c8e0", "#1a1e3a"), hover_color=("#e8eaf2", "#0d1020"),
                font=ctk.CTkFont("Segoe UI", 9),
            ).pack(side="left", padx=(0, 6))

        icone_tema = "🌙" if ctk.get_appearance_mode().lower() == "light" else "☀"
        self._btn_tema = ctk.CTkButton(
            right, text=icone_tema, command=self._alternar_tema,
            width=34, height=28, corner_radius=5, border_width=1,
            fg_color="transparent", text_color=("#5060a0", "#3a4070"),
            border_color=("#c0c8e0", "#1a1e3a"), hover_color=("#e8eaf2", "#0d1020"),
            font=ctk.CTkFont("Segoe UI", 13),
        )
        self._btn_tema.pack(side="left")

        # Título da página
        ph = ctk.CTkFrame(self, fg_color="transparent")
        ph.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(ph, text="este PC", text_color=COR_LABEL,
                     font=ctk.CTkFont("Segoe UI", 10, weight="bold"), anchor="w").pack(anchor="w")
        ctk.CTkLabel(ph, text="Serviços da operação", text_color=COR_TEXTO,
                     font=ctk.CTkFont("Segoe UI", 20, weight="bold"), anchor="w").pack(anchor="w")
        self.lbl_resumo = ctk.CTkLabel(ph, text="verificando…", text_color=COR_SUAVE,
                                        font=ctk.CTkFont("Segoe UI", 10), anchor="w")
        self.lbl_resumo.pack(anchor="w", pady=(2, 0))

        # Lista de serviços
        lista = ctk.CTkScrollableFrame(
            self, fg_color=BG_LISTA, corner_radius=8,
            border_width=1, border_color=BORDA_LISTA,
            scrollbar_button_color=("#c0c8e0", "#1a1e3a"),
            scrollbar_button_hover_color=("#9095b5", "#252a4a"),
        )
        lista.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        for servico in self.servicos:
            linha = LinhaServico(
                lista, servico,
                self._enfileirar_ligar, self._enfileirar_desligar,
                self._estado_cache,
            )
            self.linhas[servico.id] = linha

    def _alternar_tema(self) -> None:
        atual = ctk.get_appearance_mode().lower()
        novo = "dark" if atual == "light" else "light"
        ctk.set_appearance_mode(novo)
        for linha in self.linhas.values():
            linha.atualizar_tema()
        self._btn_tema.configure(text="☀" if novo == "dark" else "🌙")
        try:
            ARQUIVO_TEMA.write_text(novo)
        except Exception:
            pass

    def _posicionar(self) -> None:
        # Passo 1: aplicar tamanho e colocar fora da tela temporariamente.
        # Passo 2 (after 200ms): medir o tamanho físico real e mover para o canto.
        largura_logica, altura_logica = 580, 640
        self.deiconify()
        self.geometry(f"{largura_logica}x{altura_logica}+0+0")
        self.update_idletasks()
        self.after(200, lambda: self._posicionar_final(largura_logica, altura_logica))

    def _posicionar_final(self, largura_logica: int, altura_logica: int) -> None:
        # Posição em pixels físicos via MoveWindow — geometry(+X+Y) não funciona com CTk/DPI.
        scale = self.winfo_fpixels('1i') / 96.0
        phys_w = int(largura_logica * scale) + 4
        phys_h = int(altura_logica * scale) + 36
        hwnd = 0
        try:
            import ctypes as _ct
            class _RECT(_ct.Structure):
                _fields_ = [("left", _ct.c_long), ("top", _ct.c_long),
                            ("right", _ct.c_long), ("bottom", _ct.c_long)]
            wa = _RECT()
            _ct.windll.user32.SystemParametersInfoW(0x30, 0, _ct.byref(wa), 0)
            hwnd = _ct.windll.user32.GetAncestor(self.winfo_id(), 2) or \
                   _ct.windll.user32.FindWindowW(None, TITULO)
            rect = _RECT()
            if hwnd and _ct.windll.user32.GetWindowRect(hwnd, _ct.byref(rect)):
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w >= 100 and h >= 100:
                    phys_w, phys_h = w, h
            margem = 24
            x = max(0, wa.right - phys_w - margem)
            y = max(24, wa.bottom - phys_h - margem)
        except Exception:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, sw - phys_w - 24)
            y = max(24, sh - phys_h - 24)
        if hwnd:
            ctypes.windll.user32.MoveWindow(hwnd, x, y, phys_w, phys_h, True)
        else:
            self.geometry(f"{largura_logica}x{altura_logica}+{x}+{y}")
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(1000, lambda: self.attributes("-topmost", False))

    def _esconder_monitor_window(self) -> None:
        import ctypes as _ct
        _u32 = _ct.windll.user32
        _cur_pid = _ct.windll.kernel32.GetCurrentProcessId()

        _EnumCb = _ct.WINFUNCTYPE(_ct.c_bool, _ct.c_void_p, _ct.c_void_p)
        _titles_to_hide = ("TtkMonitorWindow",)

        def _cb(hwnd, _lp):
            buf = _ct.create_unicode_buffer(256)
            _u32.GetWindowTextW(hwnd, buf, 256)
            title = buf.value
            pid = _ct.c_ulong(0)
            _u32.GetWindowThreadProcessId(hwnd, _ct.byref(pid))
            if pid.value == _cur_pid and title in _titles_to_hide:
                _u32.ShowWindow(hwnd, 0)   # SW_HIDE
            return True

        _u32.EnumWindows(_EnumCb(_cb), 0)

    # ── Ações ─────────────────────────────────────────────────────────────────

    def _enfileirar_ligar(self, servico: Servico) -> None:
        if servico.id in self.ocupados:
            return
        self.ocupados.add(servico.id)
        self.acoes[servico.id] = "ligar"
        self.inicio_acao[servico.id] = time.time()
        self._fila.put(("ligar", servico))
        self._pintar_linhas()

    def _enfileirar_desligar(self, servico: Servico) -> None:
        if servico.id in self.ocupados:
            return
        self.ocupados.add(servico.id)
        self.acoes[servico.id] = "desligar"
        self.inicio_acao[servico.id] = time.time()
        self._fila.put(("desligar", servico))
        self._pintar_linhas()

    def _estado_cache(self, servico: Servico) -> str:
        return self.estados.get(servico.id, "parado")

    def _ligar_todos(self) -> None:
        for s in self.servicos:
            if self._estado_cache(s) != "no_ar":
                self._enfileirar_ligar(s)

    def _desligar_todos(self) -> None:
        for s in reversed(self.servicos):
            if self._estado_cache(s) != "parado":
                self._enfileirar_desligar(s)

    def _trabalhador(self) -> None:
        while True:
            acao, servico = self._fila.get()
            threading.Thread(target=self._executar, args=(acao, servico), daemon=True).start()

    def _executar(self, acao: str, servico: Servico) -> None:
        erro = None
        try:
            erro = ligar_servico(servico) if acao == "ligar" else None
            if acao == "desligar":
                desligar_servico(servico)
        except Exception as exc:
            erro = str(exc)
        try:
            self.after(0, lambda s=servico, e=erro: self._terminou(s, e))
        except tk.TclError:
            return

    def _terminou(self, servico: Servico, erro: str | None) -> None:
        if erro:
            self.acoes.pop(servico.id, None)
            self.ocupados.discard(servico.id)
            self.inicio_acao.pop(servico.id, None)
            self._pintar_linhas()
            messagebox.showerror(TITULO, erro, parent=self)

    def _observar(self) -> None:
        while True:
            novos = {s.id: estado_das_portas(s) for s in self.servicos}
            try:
                self.after(0, lambda n=novos: self._aplicar_estados(n))
            except tk.TclError:
                return
            time.sleep(0.6)

    def _aplicar_estados(self, novos: dict[str, str]) -> None:
        agora = time.time()
        for sid, novo in novos.items():
            prev = self.estados.get(sid, "parado")
            if novo == "no_ar" and prev != "no_ar":
                self.inicio_no_ar[sid] = agora
            elif novo != "no_ar" and prev == "no_ar":
                self.inicio_no_ar.pop(sid, None)
        self.estados = novos

        no_ar = sum(1 for s in self.servicos if novos.get(s.id) == "no_ar")
        total = len(self.servicos)
        self.lbl_resumo.configure(text=f"{no_ar} de {total} serviços ativos · este PC")

        agora2 = time.time()
        for servico in self.servicos:
            sid = servico.id
            if sid not in self.ocupados:
                continue
            acao  = self.acoes.get(sid)
            atual = novos.get(sid)
            estourou = agora2 - self.inicio_acao.get(sid, agora2) > 50
            if acao == "ligar"    and (atual == "no_ar"  or estourou):
                self.ocupados.discard(sid); self.acoes.pop(sid, None); self.inicio_acao.pop(sid, None)
            elif acao == "desligar" and (atual == "parado" or estourou):
                self.ocupados.discard(sid); self.acoes.pop(sid, None); self.inicio_acao.pop(sid, None)

        self._pintar_linhas()

    def _pintar_linhas(self) -> None:
        agora = time.time()
        for servico in self.servicos:
            estado  = self.estados.get(servico.id, "parado")
            ocupado = servico.id in self.ocupados
            visivel = estado
            if ocupado:
                visivel = "ligando" if self.acoes.get(servico.id) == "ligar" else "desligando"
            uptime = ""
            if estado == "no_ar" and servico.id in self.inicio_no_ar:
                uptime = _formatar_uptime(int(agora - self.inicio_no_ar[servico.id]))
            self.linhas[servico.id].atualizar(visivel, ocupado, uptime)

    # ── System tray ───────────────────────────────────────────────────────────

    def _icone_imagem(self) -> "Image.Image":
        no_ar = sum(1 for s in self.servicos if self.estados.get(s.id) == "no_ar")
        total = len(self.servicos)
        cor = "#4caf50" if no_ar == total else "#ff9800" if no_ar > 0 else "#ef5350"
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse([8, 8, 56, 56], fill=cor)
        return img

    def _criar_tray(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Abrir painel", self._mostrar_janela, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Ligar todos",    lambda icon, item: self.after(0, self._ligar_todos)),
            pystray.MenuItem("Desligar todos", lambda icon, item: self.after(0, self._desligar_todos)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", self._sair_do_tray),
        )
        self._icone_tray = pystray.Icon("finaud", self._icone_imagem(), TITULO, menu)
        threading.Thread(target=self._icone_tray.run, daemon=True).start()

    def _minimizar_para_tray(self) -> None:
        self.withdraw()
        if self._icone_tray:
            self._icone_tray.icon = self._icone_imagem()

    def _mostrar_janela(self, icon=None, item=None) -> None:
        self.after(0, self._restaurar)

    def _restaurar(self) -> None:
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(500, lambda: self.attributes("-topmost", False))

    def _sair_do_tray(self, icon=None, item=None) -> None:
        if self._icone_tray:
            self._icone_tray.stop()
        self.after(0, self.destroy)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if ja_existe_outra_janela():
        return
    try:
        servicos = catalogo()
    except FileNotFoundError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(TITULO, str(exc))
        return
    app = Painel(servicos)
    app.mainloop()


if __name__ == "__main__":
    main()
