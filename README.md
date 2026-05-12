# eFake ou Não É?

Plataforma local de verificação de fake news. Cole uma URL ou texto de notícia e o sistema retorna um score de credibilidade, cruzando fact-checkers brasileiros com heurísticas automáticas.

---

## Sumário

- [Como funciona](#como-funciona)
- [Stack](#stack)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Instalação](#instalação)
- [Uso](#uso)
- [API](#api)
- [Sistema de pontuação](#sistema-de-pontuação)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Deploy futuro (VPS / Raspberry Pi)](#deploy-futuro-vps--raspberry-pi)
- [Notas para desenvolvimento futuro](#notas-para-desenvolvimento-futuro)

---

## Como funciona

```
URL ou texto da notícia
         │
         ▼
   POST /analyze
         │
         ├── 1. Cache (SQLite) → retorna imediato se já analisado antes
         │
         ├── 2. Scraping paralelo dos fact-checkers
         │       ├── Agência Lupa        (lupa.uol.com.br)
         │       ├── Aos Fatos           (aosfatos.org)
         │       ├── AFP Checamos        (checamos.afp.com)
         │       └── Boatos.org          (boatos.org)
         │
         ├── 3. Heurísticas automáticas
         │       ├── Domínio na lista negra (data/fake_domains.txt)
         │       ├── Idade do domínio via WHOIS (< 90 dias = suspeito)
         │       ├── Palavras sensacionalistas em PT-BR
         │       └── Padrões suspeitos na URL
         │
         └── 4. Score 0–100 → veredicto + salva no banco
```

Cada análise é cacheada por hash SHA-256 do input. Segunda consulta do mesmo conteúdo retorna instantaneamente com `"cached": true`.

---

## Stack

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend | Python + FastAPI | 3.14 / 0.136 |
| Scraping | httpx + BeautifulSoup4 + lxml | async |
| Banco | SQLite via aiosqlite | — |
| WHOIS | python-whois | — |
| Frontend | HTML + CSS + JS vanilla | sem framework |
| Servidor | Uvicorn | 0.46 |

> **Nota para o assistente:** Jinja2 foi descartado por incompatibilidade com Python 3.14 (TypeError no LRU cache). O HTML é servido via `FileResponse` diretamente. Não reintroduza Jinja2 sem testar na versão 3.14.

---

## Estrutura do projeto

```
efake-ou-naoe/
│
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI app — rotas e lifespan (init do banco)
│   ├── models.py        # Pydantic: AnalyzeRequest, AnalyzeResult, Signals, HistoryItem
│   ├── database.py      # SQLite async: init_db, get_cached, save_analysis, get_history
│   ├── analyzer.py      # Orquestrador: chama scrapers + heurísticas → score final
│   │
│   ├── scrapers/
│   │   ├── base.py      # BaseScraper: httpx async, timeout 10s, graceful fail
│   │   ├── lupa.py      # Agência Lupa
│   │   ├── aosfatos.py  # Aos Fatos
│   │   ├── afp.py       # AFP Checamos
│   │   └── boatos.py    # Boatos.org (presença = suspeito por padrão)
│   │
│   └── heuristics/
│       ├── domain.py    # Lista negra, TLDs suspeitos, WHOIS
│       ├── language.py  # Regex de palavras sensacionalistas PT-BR
│       └── scoring.py   # Pesos de cada sinal → score 0–100
│
├── frontend/
│   ├── templates/
│   │   └── index.html   # SPA única página
│   └── static/
│       ├── css/style.css
│       └── js/app.js    # fetch /analyze e /history, render de resultados
│
├── data/
│   ├── fake_domains.txt         # Domínios sabidamente falsos (um por linha)
│   └── sensationalist_words.txt # Palavras/frases de alerta em PT-BR
│
├── efake.db         # SQLite — gerado automaticamente, gitignored
├── requirements.txt
├── .gitignore
└── run.py           # Entry point: `python run.py`
```

---

## Instalação

```bash
git clone git@github.com:profevine/efake-ou-naoe.git
cd efake-ou-naoe

python -m venv .venv

# Python 3.14 requer --no-build-isolation para lxml e pydantic-core
.venv/bin/pip install --no-build-isolation lxml pydantic
.venv/bin/pip install -r requirements.txt
```

> **Nota para o assistente:** O `pip install -r requirements.txt` sozinho falha no Python 3.14 porque lxml e pydantic-core não compilam sem `--no-build-isolation`. Sempre instale esses dois separadamente primeiro.

---

## Uso

```bash
python run.py
# Servidor em http://localhost:8000
```

Abra `http://localhost:8000` no navegador, cole uma URL ou texto e clique em **Verificar**.

---

## API

### `POST /analyze`

```json
// Request
{ "input": "https://exemplo.com/noticia" }
// ou
{ "input": "Texto da notícia aqui..." }

// Response
{
  "input": "...",
  "score": 74,
  "verdict": "fake",           // "credible" | "suspicious" | "fake"
  "label": "Provavelmente falso",
  "signals": {
    "fact_checkers": [
      { "source": "Agência Lupa", "result": "FALSO", "title": "...", "url": "..." }
    ],
    "domain_blacklisted": true,
    "domain_age_days": 45,
    "sensationalist_words": ["URGENTE", "EXCLUSIVO"],
    "suspicious_url_pattern": false
  },
  "cached": false,
  "analyzed_at": "2026-05-12T12:00:00Z"
}
```

### `GET /history`

Retorna as últimas 50 análises do banco.

### `GET /health`

```json
{ "status": "ok" }
```

---

## Sistema de pontuação

| Sinal | Pontos |
|-------|--------|
| Fact-checker: FALSO | +40 |
| Fact-checker: ENGANOSO | +25 |
| Fact-checker: VERDADEIRO | −30 |
| Fact-checker: INCONCLUSIVO | +5 |
| Domínio na lista negra ou TLD suspeito | +35 |
| Domínio com menos de 90 dias (WHOIS) | +15 |
| 5+ palavras sensacionalistas | +45 |
| 3–4 palavras sensacionalistas | +25 |
| 1–2 palavras sensacionalistas | +10 |
| Padrão suspeito na URL | +10 |

| Score | Veredicto |
|-------|-----------|
| 0–40 | ✅ Provavelmente verdadeiro |
| 41–65 | ⚠️ Suspeito — verifique as fontes |
| 66–100 | 🔴 Provavelmente falso |

> **Nota para o assistente:** Os pesos foram calibrados assumindo que fact-checkers são o sinal primário. Sem internet, a pontuação máxima via heurísticas é ~70 (domínio blacklisted + 5+ palavras sensacionalistas). Os limiares de corte estão em `backend/heuristics/scoring.py:verdict_from_score`.

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `EFAKE_HOST` | `127.0.0.1` | Host do servidor |
| `EFAKE_PORT` | `8000` | Porta do servidor |
| `EFAKE_DB` | `efake.db` | Caminho do banco SQLite |

Para expor na rede local:

```bash
EFAKE_HOST=0.0.0.0 python run.py
```

---

## Deploy futuro (VPS / Raspberry Pi)

O projeto foi desenhado para ser portável sem refatoração:

1. **SQLite** já funciona no Raspberry Pi sem instalação extra
2. **Host configurável** via `EFAKE_HOST=0.0.0.0`
3. Para produção, trocar `reload=True` por `workers=2` em `run.py`
4. Sugestão de stack no VPS:

```
Nginx (proxy reverso, porta 80/443)
    └── Uvicorn (porta 8000, processo gerenciado por systemd ou supervisor)
```

Exemplo de unit file systemd:

```ini
[Unit]
Description=eFake ou Não É?
After=network.target

[Service]
WorkingDirectory=/opt/efake-ou-naoe
ExecStart=/opt/efake-ou-naoe/.venv/bin/python run.py
Environment=EFAKE_HOST=127.0.0.1
Environment=EFAKE_PORT=8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Notas para desenvolvimento futuro

### O que está implementado
- Scraping de 4 fact-checkers brasileiros com graceful fail (se um cair, os outros continuam)
- Cache por hash SHA-256 do input — evita re-análise e re-scraping
- Heurísticas: lista negra de domínios, TLDs suspeitos, WHOIS, linguagem sensacionalista, padrão de URL
- Histórico persistido em SQLite
- UI com abas Verificar / Histórico, barra de score colorida, sinais detalhados

### Próximos passos sugeridos
- **Expandir `data/fake_domains.txt`**: adicionar mais domínios a partir de listas públicas como o projeto [Farol do Jornalismo](https://farol.jor.br)
- **Melhorar os scrapers**: os seletores CSS dos fact-checkers podem mudar; considerar testes de integração periódicos
- **Extração de título**: para textos sem URL, extrair o título da primeira linha para melhorar a query nos fact-checkers
- **Suporte a PDF/imagem**: extrair texto de prints de notícias (OCR via pytesseract)
- **Rate limiting**: evitar sobrecarga dos fact-checkers com muitas requisições em sequência
- **LLM opcional**: adicionar análise por Ollama como camada extra quando disponível, sem quebrar o fluxo offline

### Arquivos mais prováveis de precisar ajuste
| Arquivo | Motivo |
|---------|--------|
| `backend/scrapers/*.py` | Seletores CSS mudam com redesigns dos sites |
| `data/fake_domains.txt` | Lista precisa ser mantida atualizada |
| `data/sensationalist_words.txt` | Adicionar novos padrões conforme surgem |
| `backend/heuristics/scoring.py` | Ajuste fino dos pesos conforme testes reais |
