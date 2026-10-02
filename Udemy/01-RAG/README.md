# PDF RAG Chat

A small retrieval-augmented generation example that indexes `rag/nodejs.pdf` in Qdrant and answers questions about it using OpenAI.

## Requirements

- Python 3.11 or newer
- Docker Desktop with Docker Compose
- An OpenAI API key with access to `gpt-5-mini` and `text-embedding-3-large`

Python package versions are pinned in [`requirements.txt`](requirements.txt).

## Setup (Windows PowerShell)

Run these commands from the `01-RAG` directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in this directory with your API key:

```dotenv
OPENAI_API_KEY=your_openai_api_key
```

Keep `.env` private and do not commit it to source control.

## Run

Start Qdrant:

```powershell
docker compose -f .\rag\docker-compose.yml up -d
```

Index the PDF. Do this before the first chat, and again after changing the source PDF:

```powershell
python .\rag\index.py
```

Start the question-and-answer loop:

```powershell
python .\rag\chat_recursive_ask.py
```

To ask one question and exit instead, run:

```powershell
python .\rag\chat.py
```

Qdrant is expected at `http://localhost:6333`. To stop it:

```powershell
docker compose -f .\rag\docker-compose.yml down
```
