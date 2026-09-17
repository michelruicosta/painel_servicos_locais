# Registro de Correções — Painel Serviços Locais

_Entradas em ordem decrescente. Formato: `YYYY-MM-DD HH:MM`_

---

## 2026-09-17

### 10:07 — Conflito de portas ao reiniciar serviços pelo painel

🔎 **Em miúdos:** quando o painel desligava um serviço e tentava ligá-lo de novo rápido demais, às vezes o processo antigo ainda segurava a porta — e o novo falhava silenciosamente. Agora o painel aguarda a porta ser liberada antes de subir o novo processo, e mata qualquer processo externo que esteja na porta antes de iniciar.

- **Problema:** serviço findabc ficou preso em "Ligando..." após ciclo desligar/ligar. Dois processos uvicorn tentando usar a porta 8010 ao mesmo tempo.
- **Causa raiz:** `desligar_servico` chamava `taskkill` e retornava imediatamente, sem aguardar o OS liberar o socket TCP. `iniciar_processo` subia o novo processo antes da porta estar livre. Agravado por processo uvicorn iniciado manualmente durante debug (não rastreado pelo painel).
- **Correção:** em `desligar_servico` — loop de até 5 s aguardando todas as portas do serviço serem liberadas. Em `iniciar_processo` — mata qualquer processo externo na porta antes de iniciar, aguarda até 3 s pela liberação; se não liberar, assume que já está rodando e retorna sem subir duplicata.
- **Arquivo:** `painel.pyw` — funções `desligar_servico` e `iniciar_processo`
- **Validação:** ✅ Serviço findabc foi desligado e ligado via painel sem conflito após a correção. Aplicado a todos os 12 serviços do catálogo.

---

### 10:07 — `abrir.vbs` usando Python do sistema em vez do venv

🔎 **Em miúdos:** o script que abre o painel pelo duplo-clique estava usando o Python instalado no sistema, não o Python do ambiente virtual do projeto. Se o Python do sistema for diferente, o painel pode não abrir ou abrir com dependências erradas.

- **Problema:** `abrir.vbs` chamava `pythonw.exe` sem caminho completo, dependendo do PATH do sistema.
- **Causa raiz:** script escrito antes de o projeto ter venv dedicado.
- **Correção:** script agora usa `\.venv\Scripts\pythonw.exe` com caminho absoluto relativo à pasta do projeto.
- **Arquivo:** `abrir.vbs`
- **Validação:** ✅ Arquivo modificado e verificado no diff (`git diff abrir.vbs`).

---

### 09:11 — Internal Server Error em `/login` do findabc (Starlette 1.6 API change)

🔎 **Em miúdos:** o findabc foi atualizado para uma versão nova do Starlette sem atualizar o código que renderiza as páginas HTML. A nova versão exige que a ordem dos argumentos seja diferente. Resultado: todas as páginas quebravam com erro 500 ao tentar abrir.

- **Problema:** `http://127.0.0.1:8010/login` retornava Internal Server Error (500) ao ser acessado pelo painel.
- **Causa raiz:** Starlette 1.6.0 mudou a assinatura de `TemplateResponse` — primeiro argumento passa a ser `request: Request`, não mais o nome do template. Com a assinatura antiga, o dict de contexto era recebido como `name` e causava `TypeError: unhashable type: 'dict'` no cache LRU do Jinja2.
- **Correção:** 54 chamadas corrigidas em 6 arquivos do findabc via script regex em lote:
  - `app/main.py` — 22 chamadas
  - `app/routers/auth.py` — 16 chamadas
  - `app/routers/finaud.py` — 10 chamadas
  - `app/routers/mfa.py` — 4 chamadas
  - `app/routers/auditoria.py` — 1 chamada
  - `app/routers/configuracoes.py` — 1 chamada
- **Antes:** `TemplateResponse("login.html", {"request": request})`
- **Depois:** `TemplateResponse(request, "login.html", {"request": request})`
- **Arquivo de correção:** script em lote em `scratchpad/fix_template_response.py` (sessão 2026-09-17)
- **Validação:** ✅ `GET /health` → 200, `GET /login` → 200 após correção.
