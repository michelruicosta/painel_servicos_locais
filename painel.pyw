# -*- coding: utf-8 -*-
"""Painel local Finaud — liga/desliga API e tela de cada sistema neste PC.

Não vai para o site. Só Windows, só desenvolvimento.
"""
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
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, messagebox

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9
TITULO = "Finaud — Serviços locais"
MUTEX_NOME = "FinaudPainelServicosLocais"
PASTA_PAINEL = Path(__file__).resolve().parent
RAIZ_ATIVOS = Path(r"D:\02_Finaud\Projetos\ativos")
PASTA_LOGS = PASTA_PAINEL / "logs"

COR_FUNDO = "#1c1c1c"
COR_CARD = "#252525"
COR_BORDA = "#383838"
COR_TEXTO = "#e2e2e2"
COR_SUAVE = "#8a8a8a"
COR_NO_AR = "#4caf50"
COR_PARADO = "#ef5350"
COR_ESPERA = "#ff9800"
COR_LIGAR = "#2e7d32"
COR_DESLIGAR = "#c62828"


def python_do_projeto(raiz: Path) -> str:
    for relativo in (".venv/Scripts/python.exe", "venv/Scripts/python.exe"):
        candidato = raiz / relativo
        if candidato.is_file():
            return str(candidato)
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        python = exe.with_name("python.exe")
        if python.is_file():
            return str(python)
    return str(exe)


def npm_cmd() -> str:
    encontrado = shutil.which("npm.cmd") or shutil.which("npm")
    if not encontrado:
        raise FileNotFoundError("npm não encontrado. Instale o Node.js.")
    return encontrado


def ssh_cmd() -> str:
    encontrado = shutil.which("ssh")
    if not encontrado:
        raise FileNotFoundError("ssh não encontrado. Instale o OpenSSH (Windows → Configurações → Recursos opcionais).")
    return encontrado


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
    portal = RAIZ_ATIVOS / "portal_finaudapps"
    auditoria = RAIZ_ATIVOS / "Projeto_Auditoria_IA"
    normativos = RAIZ_ATIVOS / "normativos_ia"
    leiautes = RAIZ_ATIVOS / "leiautes"
    gestao = RAIZ_ATIVOS / "gestao_area_suporte"
    c214 = RAIZ_ATIVOS / "C214"
    prospeccao = RAIZ_ATIVOS / "prospeccao_finaud"
    site = RAIZ_ATIVOS / "migração site"
    conformidade = RAIZ_ATIVOS / "painel_conformidade"
    npm = npm_cmd()
    py_site = python_do_projeto(site)
    return [
        Servico(
            id="portal",
            nome="Portal / Admin",
            detalhe="Tela 8000 · API 8000",
            processos=[
                Processo(
                    chave="api",
                    cwd=portal / "portal-auth" / "backend",
                    argv=[python_do_projeto(portal), "-m", "app.main"],
                    porta=8000,
                    health="http://127.0.0.1:8000/health",
                ),
            ],
            abrir=[
                ("Portal", "http://127.0.0.1:8000/portal-preview/"),
                ("Admin", "http://127.0.0.1:8000/admin-preview/"),
            ],
        ),
        Servico(
            id="auditoria",
            nome="Auditoria IA",
            detalhe="Tela 5173 · API 8001",
            processos=[
                Processo(
                    chave="api",
                    cwd=auditoria / "backend",
                    argv=[python_do_projeto(auditoria), "-m", "app.main"],
                    porta=8001,
                    health="http://127.0.0.1:8001/health",
                ),
                Processo(
                    chave="tela",
                    cwd=auditoria / "frontend",
                    argv=[npm, "run", "dev"],
                    porta=5173,
                    health="http://127.0.0.1:5173/",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:5173/")],
        ),
        Servico(
            id="normativos",
            nome="Normativos IA",
            detalhe="Tela 5178 · API 8002",
            processos=[
                Processo(
                    chave="api",
                    cwd=normativos / "backend",
                    argv=[python_do_projeto(normativos), "-m", "app.main"],
                    porta=8002,
                    health="http://127.0.0.1:8002/health",
                ),
                Processo(
                    chave="tela",
                    cwd=normativos / "frontend",
                    argv=[npm, "run", "dev"],
                    porta=5178,
                    health="http://127.0.0.1:5178/",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:5178/")],
        ),
        Servico(
            id="leiautes",
            nome="Leiautes Bacen",
            detalhe="Tela 5177 · API 8003",
            processos=[
                Processo(
                    chave="api",
                    cwd=leiautes / "backend",
                    argv=[python_do_projeto(leiautes), "-m", "app.main"],
                    porta=8003,
                    health="http://127.0.0.1:8003/health",
                ),
                Processo(
                    chave="tela",
                    cwd=leiautes / "frontend",
                    argv=[npm, "run", "dev"],
                    porta=5177,
                    health="http://127.0.0.1:5177/",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:5177/")],
        ),
        Servico(
            id="gestao",
            nome="Gestão Área Suporte",
            detalhe="Tela 8004 · API 8004",
            processos=[
                Processo(
                    chave="flask",
                    cwd=gestao,
                    argv=[python_do_projeto(gestao), "scripts/servidor_telas.py"],
                    porta=8004,
                    health="http://127.0.0.1:8004/",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:8004/")],
        ),
        Servico(
            id="c214",
            nome="C214 Bacen",
            detalhe="Tela 5180 · API 8005",
            processos=[
                Processo(
                    chave="api",
                    cwd=c214 / "backend",
                    argv=[python_do_projeto(c214), "-m", "app.main"],
                    porta=8005,
                    health="http://127.0.0.1:8005/health",
                ),
                Processo(
                    chave="tela",
                    cwd=c214 / "frontend",
                    argv=[npm, "run", "dev"],
                    porta=5180,
                    health="http://127.0.0.1:5180/",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:5180/")],
        ),
        Servico(
            id="findabc",
            nome="findabc",
            detalhe="Tunnel+8010",
            processos=[
                Processo(
                    chave="tunnel",
                    cwd=PASTA_PAINEL,
                    argv=[
                        ssh_cmd(),
                        "-i", str(Path.home() / ".ssh" / "id_ed25519_cyberpanel"),
                        "-N",
                        "-L", "5432:127.0.0.1:5432",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ExitOnForwardFailure=yes",
                        "root@31.97.82.203",
                    ],
                    porta=5432,
                    health="tcp://127.0.0.1:5432",
                ),
                Processo(
                    chave="api",
                    cwd=RAIZ_ATIVOS / "findabc",
                    argv=[python_do_projeto(RAIZ_ATIVOS / "findabc"), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010"],
                    porta=8010,
                    health="http://127.0.0.1:8010/",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:8010/")],
        ),
        Servico(
            id="prospeccao",
            nome="Prospecção Finaud",
            detalhe="Tela 8006 · API 8006",
            processos=[
                Processo(
                    chave="flask",
                    cwd=prospeccao,
                    argv=[python_do_projeto(prospeccao), "scripts/servidor_prospeccao.py"],
                    porta=8006,
                    health="http://127.0.0.1:8006/",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:8006/")],
        ),
        Servico(
            id="s5",
            nome="S5 Enquadramento",
            detalhe="API 8007",
            processos=[
                Processo(
                    chave="api",
                    cwd=RAIZ_ATIVOS / "s5",
                    argv=[python_do_projeto(RAIZ_ATIVOS / "s5"), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8007"],
                    porta=8007,
                    health="http://127.0.0.1:8007/",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:8007/"), ("API", "http://127.0.0.1:8007/docs")],
        ),
        # HTML estático + API do assistente (MVP). Mesmo Ligar/Desligar dos demais.
        Servico(
            id="site",
            nome="Site institucional",
            detalhe="Tela 8090 · API 8091",
            processos=[
                Processo(
                    chave="tela",
                    cwd=site / "site",
                    argv=[py_site, "-m", "http.server", "8090", "--bind", "127.0.0.1"],
                    porta=8090,
                    health="http://127.0.0.1:8090/",
                ),
                Processo(
                    chave="api",
                    cwd=site / "atendimento",
                    argv=[python_do_projeto(site / "atendimento"), "-m", "app.main"],
                    porta=8091,
                    health="http://127.0.0.1:8091/health",
                ),
            ],
            abrir=[
                ("Abrir", "http://127.0.0.1:8090/"),
                ("Admin", "http://127.0.0.1:8091/admin/"),
            ],
        ),
        Servico(
            id="conformidade",
            nome="Painel Conformidade",
            detalhe="API 8009",
            processos=[
                Processo(
                    chave="api",
                    cwd=conformidade,
                    argv=[python_do_projeto(conformidade), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8009"],
                    porta=8009,
                    health="http://127.0.0.1:8009/health",
                ),
            ],
            abrir=[("Abrir", "http://127.0.0.1:8009/")],
        ),
        Servico(
            id="radar_bacen",
            nome="Radar Bacen",
            detalhe="Tela 8008 · API 8008",
            processos=[
                Processo(
                    chave="api",
                    cwd=RAIZ_ATIVOS / "radar_bacen",
                    argv=[python_do_projeto(RAIZ_ATIVOS / "radar_bacen"), "-m", "uvicorn", "app.web.app:app", "--host", "127.0.0.1", "--port", "8008"],
                    porta=8008,
                    health="http://127.0.0.1:8008/",
                ),
            ],
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
            creationflags=CREATE_NO_WINDOW,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    texto = bruto.decode("oem", errors="replace")
    achados: set[int] = set()
    padrao = re.compile(
        rf":{porta}(?!\d)\s+\S+\s+LISTENING\s+(\d+)",
        re.IGNORECASE,
    )
    for pid_txt in padrao.findall(texto):
        pid = int(pid_txt)
        if pid > 4:
            achados.add(pid)
    return achados


def matar_pid(pid: int) -> None:
    if pid <= 4:
        return
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
    )


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
    _CMDS_SEM_PATH = {"npm", "npm.cmd", "ssh"}
    if not Path(proc.argv[0]).exists() and proc.argv[0] not in _CMDS_SEM_PATH:
        raise FileNotFoundError(f"Programa não encontrado: {proc.argv[0]}")
    log_path = arquivo_log(servico_id, proc.chave)
    log = open(log_path, "a", encoding="utf-8", errors="replace")
    log.write(f"\n----- {datetime.now().isoformat(timespec='seconds')} -----\n")
    log.flush()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    subprocess.Popen(
        proc.argv,
        cwd=str(proc.cwd),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        env=env,
        creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
    )


def ligar_servico(servico: Servico) -> str | None:
    erros: list[str] = []
    for proc in servico.processos:
        try:
            iniciar_processo(servico.id, proc)
        except Exception as exc:
            erros.append(f"{proc.chave}: {exc}")
    if erros:
        return f"{servico.nome}: " + "; ".join(erros)
    return None


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


class LinhaServico(tk.Frame):
    def __init__(
        self, pai: tk.Widget, servico: Servico, ao_ligar, ao_desligar, estado_de
    ) -> None:
        borda = tk.Frame(pai, bg=COR_BORDA, bd=0)
        borda.pack(fill="x", pady=(0, 6))
        super().__init__(borda, bg=COR_CARD, bd=0, padx=10, pady=8)
        self.pack(fill="x")
        self.servico = servico
        self._ao_ligar = ao_ligar
        self._ao_desligar = ao_desligar
        self._estado_de = estado_de
        self.ocupado = False

        # Uma linha: status + nome | Ligar/Desligar + Abrir + Log
        linha = tk.Frame(self, bg=COR_CARD)
        linha.pack(fill="x")
        self.ponto = tk.Canvas(
            linha, width=14, height=14, highlightthickness=0, bg=COR_CARD, bd=0
        )
        self.ponto.pack(side="left", pady=(2, 0))
        self._oval = self.ponto.create_oval(2, 2, 12, 12, fill=COR_PARADO, outline="")

        textos = tk.Frame(linha, bg=COR_CARD)
        textos.pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Label(textos, text=servico.nome, style="Nome.TLabel").pack(anchor="w")
        self.lbl_detalhe = ttk.Label(
            textos, text=servico.detalhe, style="Detalhe.TLabel"
        )
        self.lbl_detalhe.pack(anchor="w")

        botoes = tk.Frame(linha, bg=COR_CARD)
        botoes.pack(side="right")
        self.btn_liga = tk.Button(
            botoes,
            text="Ligar",
            command=self._clique_liga,
            bd=0,
            padx=10,
            pady=3,
            font=("Segoe UI", 9),
            cursor="hand2",
            fg="white",
            activeforeground="white",
        )
        self.btn_liga.pack(side="left")
        for rotulo, url in servico.abrir:
            tk.Button(
                botoes,
                text=rotulo,
                command=lambda u=url: webbrowser.open(u),
                bd=1,
                relief="solid",
                padx=8,
                pady=2,
                font=("Segoe UI", 9),
                cursor="hand2",
                bg=COR_CARD,
                fg=COR_TEXTO,
                activebackground="#3a3a3a",
                highlightthickness=0,
            ).pack(side="left", padx=(6, 0))
        tk.Button(
            botoes,
            text="Log",
            command=self._abrir_log,
            bd=0,
            padx=6,
            pady=3,
            font=("Segoe UI", 9),
            cursor="hand2",
            bg=COR_CARD,
            fg=COR_SUAVE,
            activebackground=COR_CARD,
            activeforeground=COR_TEXTO,
        ).pack(side="left", padx=(4, 0))
        self._pintar_botao("parado")

    def _clique_liga(self) -> None:
        if self.ocupado:
            return
        if self._estado_de(self.servico) == "parado":
            self._ao_ligar(self.servico)
        else:
            self._ao_desligar(self.servico)

    def _abrir_log(self) -> None:
        PASTA_LOGS.mkdir(parents=True, exist_ok=True)
        os.startfile(PASTA_LOGS)

    def _pintar_botao(self, estado: str) -> None:
        if estado == "parado":
            self.btn_liga.configure(
                text="Ligar",
                bg=COR_LIGAR,
                activebackground="#1b5e20",
            )
        else:
            self.btn_liga.configure(
                text="Desligar",
                bg=COR_DESLIGAR,
                activebackground="#b71c1c",
            )

    def atualizar(self, estado: str, ocupado: bool) -> None:
        self.ocupado = ocupado
        cores = {
            "no_ar": COR_NO_AR,
            "parcial": COR_ESPERA,
            "ligando": COR_ESPERA,
            "desligando": COR_ESPERA,
            "parado": COR_PARADO,
        }
        textos = {
            "no_ar": "No ar",
            "parcial": "Parcial",
            "ligando": "Ligando…",
            "desligando": "Desligando…",
            "parado": "Parado",
        }
        self.ponto.itemconfigure(self._oval, fill=cores.get(estado, COR_PARADO))
        self.lbl_detalhe.configure(
            text=f"{self.servico.detalhe} · {textos.get(estado, estado)}"
        )
        self.btn_liga.configure(state="disabled" if ocupado else "normal")
        if not ocupado:
            self._pintar_botao("parado" if estado == "parado" else "no_ar")


class Painel(tk.Tk):
    def __init__(self, servicos: list[Servico]) -> None:
        super().__init__()
        self.servicos = servicos
        self.linhas: dict[str, LinhaServico] = {}
        self.ocupados: set[str] = set()
        self.acoes: dict[str, str] = {}
        self.estados: dict[str, str] = {s.id: "parado" for s in servicos}
        self.inicio_acao: dict[str, float] = {}
        self._fila: queue.Queue = queue.Queue()
        self.title(TITULO)
        self.configure(bg=COR_FUNDO)
        self.minsize(460, 520)
        self._estilos()
        self._montar()
        self._posicionar()
        threading.Thread(target=self._trabalhador, daemon=True).start()
        threading.Thread(target=self._observar, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _estilos(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Fundo.TFrame", background=COR_FUNDO)
        style.configure("Card.TFrame", background=COR_CARD)
        style.configure(
            "Titulo.TLabel",
            background=COR_FUNDO,
            foreground=COR_TEXTO,
            font=("Segoe UI Semibold", 14),
        )
        style.configure(
            "Sub.TLabel",
            background=COR_FUNDO,
            foreground=COR_SUAVE,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Nome.TLabel",
            background=COR_CARD,
            foreground=COR_TEXTO,
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "Detalhe.TLabel",
            background=COR_CARD,
            foreground=COR_SUAVE,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Rodape.TLabel",
            background=COR_FUNDO,
            foreground=COR_SUAVE,
            font=("Segoe UI", 8),
        )

    def _montar(self) -> None:
        capa = ttk.Frame(self, style="Fundo.TFrame", padding=(16, 14, 16, 8))
        capa.pack(fill="x")
        ttk.Label(capa, text="Serviços locais", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(
            capa,
            text="Liga a tela e a API de cada sistema neste PC.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        acoes = ttk.Frame(capa, style="Fundo.TFrame")
        acoes.pack(fill="x")
        tk.Button(
            acoes,
            text="Ligar todos",
            command=self._ligar_todos,
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 9),
            cursor="hand2",
            bg=COR_LIGAR,
            fg="white",
            activebackground="#1b5e20",
            activeforeground="white",
        ).pack(side="left")
        tk.Button(
            acoes,
            text="Desligar todos",
            command=self._desligar_todos,
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 9),
            cursor="hand2",
            bg=COR_DESLIGAR,
            fg="white",
            activebackground="#b71c1c",
            activeforeground="white",
        ).pack(side="left", padx=(8, 0))

        lista = ttk.Frame(self, style="Fundo.TFrame", padding=(16, 4, 16, 8))
        lista.pack(fill="both", expand=True)
        for servico in self.servicos:
            linha = LinhaServico(
                lista,
                servico,
                self._enfileirar_ligar,
                self._enfileirar_desligar,
                self._estado_cache,
            )
            self.linhas[servico.id] = linha

        ttk.Label(
            self,
            text="Só neste computador. Não mexe no site no ar.",
            style="Rodape.TLabel",
            padding=(16, 0, 16, 12),
        ).pack(anchor="w")

    def _posicionar(self) -> None:
        self.update_idletasks()
        largura, altura = 520, 560
        x = self.winfo_screenwidth() - largura - 28
        y = max(24, self.winfo_screenheight() - altura - 72)
        self.geometry(f"{largura}x{altura}+{x}+{y}")
        self.attributes("-topmost", True)
        self.after(800, lambda: self.attributes("-topmost", False))

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
        for servico in self.servicos:
            if self._estado_cache(servico) != "no_ar":
                self._enfileirar_ligar(servico)

    def _desligar_todos(self) -> None:
        for servico in reversed(self.servicos):
            if self._estado_cache(servico) != "parado":
                self._enfileirar_desligar(servico)

    def _trabalhador(self) -> None:
        while True:
            acao, servico = self._fila.get()
            threading.Thread(
                target=self._executar, args=(acao, servico), daemon=True
            ).start()

    def _executar(self, acao: str, servico: Servico) -> None:
        erro = None
        try:
            if acao == "ligar":
                erro = ligar_servico(servico)
            else:
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
        self.estados = novos
        agora = time.time()
        for servico in self.servicos:
            sid = servico.id
            if sid not in self.ocupados:
                continue
            acao = self.acoes.get(sid)
            atual = novos.get(sid)
            estourou = agora - self.inicio_acao.get(sid, agora) > 50
            if acao == "ligar" and (atual == "no_ar" or estourou):
                self.ocupados.discard(sid)
                self.acoes.pop(sid, None)
                self.inicio_acao.pop(sid, None)
            elif acao == "desligar" and (atual == "parado" or estourou):
                self.ocupados.discard(sid)
                self.acoes.pop(sid, None)
                self.inicio_acao.pop(sid, None)
        self._pintar_linhas()

    def _pintar_linhas(self) -> None:
        for servico in self.servicos:
            estado = self.estados.get(servico.id, "parado")
            ocupado = servico.id in self.ocupados
            visivel = estado
            if ocupado:
                visivel = (
                    "ligando" if self.acoes.get(servico.id) == "ligar" else "desligando"
                )
            self.linhas[servico.id].atualizar(visivel, ocupado)


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
