# FertIntelligence Fert AI

Microserviço de IA agronômica do projeto FertIntelligence.

## Objetivo

Assistente técnico baseado em RAG para responder perguntas sobre fertilidade do solo, interpretação de análise de solo, calagem, gessagem, adubação e recomendação de fertilizantes.

## Stack atual

- Python
- FastAPI
- DeepSeek API
- FAISS
- PyPDF
- NumPy

## Rodando localmente

1. Crie o arquivo `.env` com as variáveis da DeepSeek.
2. Instale as dependências com `pip install -r requirements.txt`.
3. Gere o índice RAG com `python -m app.rag.ingest`.
4. Suba o servidor com `uvicorn main:app --reload --host 0.0.0.0 --port 8001`.

## Endpoints

- `GET /api/ai/health`
- `POST /api/ai/chat`

## Variáveis de ambiente

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`

## Observação

Este MVP usa embeddings lexicais locais com hashing + FAISS para evitar dependências pesadas como Torch, Transformers, Sentence Transformers e CUDA.
