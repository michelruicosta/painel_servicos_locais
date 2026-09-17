# Pendências — Painel Serviços Locais

_Atualizado em: 2026-09-17_

---

## 🟡 ATENÇÃO (verificar na próxima sessão)

### Outros projetos com Starlette ≥ 1.6 podem estar quebrando silenciosamente
- **O que é:** a API de `TemplateResponse` mudou no Starlette 1.6.0. Qualquer projeto com FastAPI + Jinja2 que use a API antiga (`TemplateResponse("nome.html", context)`) vai quebrar com `TypeError: unhashable type: 'dict'` ao renderizar o primeiro template.
- **Projetos a verificar:** todos os projetos gerenciados pelo painel que usam templates HTML.
- **Como verificar:** `grep -r "TemplateResponse(" <projeto>/app --include="*.py"` — procurar chamadas onde o primeiro arg é uma string (não `request`).
- **Ação:** aplicar o mesmo script de correção em lote usado no findabc (está em `documentações/` ou no registro de correções).

---

## ✅ Resolvido nesta sessão (2026-09-17)

- [x] Internal Server Error em `http://127.0.0.1:8010/login` — findabc (54 chamadas TemplateResponse corrigidas)
- [x] Serviço findabc preso em "Ligando..." ao reiniciar pelo painel (conflito de porta 8010)
- [x] Conflito de portas estrutural para todos os serviços do painel (`desligar_servico` + `iniciar_processo`)
- [x] `abrir.vbs` usando pythonw.exe do sistema em vez do venv

---

## 📋 Backlog (sem urgência)

_(vazio — adicionar conforme surgirem itens)_
