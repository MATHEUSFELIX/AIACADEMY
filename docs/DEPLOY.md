# Publicar MasterAI Academy para testes

Não é possível publicar sem uma conta sua (Vercel / Railway / Render). Ordem recomendada: **backend primeiro**, depois **frontend** com a URL da API.

## 1. Backend (Railway ou Render)

### Railway

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** (ou Dockerfile).
2. **Root directory / service:** pasta `backend`.
3. **Dockerfile:** `Dockerfile` (já existe em `backend/`).
4. **Variáveis de ambiente** (mínimo):

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | Postgres (Railway Postgres ou externo, ex. Supabase) |
| `SUPABASE_JWT_SECRET` | JWT Secret do projeto Supabase |
| `SUPABASE_URL` | URL do projeto |
| `SUPABASE_SERVICE_KEY` | Service role |
| `REDIS_URL` | Redis (addon ou URL externa) |
| `OLLAMA_API_KEY` | Se usar LLM padrão Ollama Cloud |
| `LLM_PROVIDER` | `ollama_cloud` ou `anthropic` |
| `SECRET_KEY` | String aleatória |
| `CHROMADB_TOKEN` | Se usar Chroma no compose; em cloud pode apontar Chroma hospedado ou ajustar código |

5. Railway define `PORT` automaticamente — o `Dockerfile` já usa `uvicorn` na porta exposta.
6. Anote a URL pública, ex.: `https://seu-backend.up.railway.app`.

7. Rodar migrações/seed: use **Railway shell** ou job one-off com `python -m scripts.seed_lessons` e `DATABASE_URL` correto.

### Render

Semelhante: **Web Service** com root `backend`, build **Docker**, health check `/health`.

## 2. Frontend (Vercel)

1. [vercel.com](https://vercel.com) → **Add New…** → **Project** → importe o repositório Git.
2. **Root Directory:** `frontend`.
3. **Framework:** Next.js (automático).
4. **Environment Variables:**

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | URL do backend (passo 1), ex. `https://seu-backend.up.railway.app` |
| `NEXT_PUBLIC_SUPABASE_URL` | Igual ao `SUPABASE_URL` do backend |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Anon key do Supabase |

5. **Deploy.** A URL será algo como `https://masterai-academy-xxx.vercel.app`.

## 3. GitHub Actions (build automático)

O workflow `.github/workflows/deploy-frontend-vercel.yml` faz **build** no push. Opcionalmente configure **Repository variables** (`NEXT_PUBLIC_*`) para o build usar URLs reais em vez dos placeholders.

Para **deploy automático na Vercel**, descomente o passo no workflow e adicione secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (após `vercel link` local ou painel Vercel).

## 4. CORS

No backend, defina **`CORS_ALLOW_ORIGINS`** (lista separada por vírgulas), por exemplo:

`https://masterai-academy-xxx.vercel.app,https://outro-dominio.com`

Em `development`, `localhost:3000` já é permitido; em produção entram também `https://masterai.academy` e os hosts dessa variável.

## 5. Teste rápido sem hospedar tudo

- **Frontend:** `cd frontend && npm run dev`
- **Backend:** `cd backend` + uvicorn / Docker
- Túnel público (ex. [ngrok](https://ngrok.com)) só para demo temporária.
