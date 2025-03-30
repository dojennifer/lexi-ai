# LexiAI 🧠⚖️

*An AI-powered assistant for Ontario auto insurance underwriting compliance.*

## Overview

**LexiAI** is an experimental AI chatbot designed to assist with underwriting regulation questions in Ontario's auto insurance space. Built with a custom legal document scraper and an OpenAI assistant backend, LexiAI allows users to query documents from FSRA (Financial Services Regulatory Authority of Ontario) and Ontario Laws, and receive structured answers with regulatory citations.

## Features

- 🌐 **Web Interface** – Interactive chat UI built in HTML/CSS/JS
- 📜 **Document Scraping** – Automated tools to extract and structure content from:
  - FSRAO regulatory PDFs
  - Ontario Laws web pages
- 🧠 **AI Assistant Integration** – OpenAI Assistant API integration via Netlify functions
- 📘 **Citation & Compliance Logic** – Backend parsing to extract legal sections, definitions, and guidance

## Project Structure

```
lexi-ai/
│
├── index.html                   # Chat UI frontend
├── functions/                  
│   ├── openai-proxy.js         # Netlify serverless functions for OpenAI API
│   └── test.js                 # Basic test endpoint
│
├── data/
│   ├── fsrao_pdf_scraper.py    # Scraper + parser for FSRA PDFs
│   └── ontario_law_scraper.py  # Scraper + parser for Ontario law pages
│
└── README.md                   # (You are here)
```

## How It Works

1. **Document Scraping**\
   Python scripts extract and structure content from FSRA's PDF downloads and Ontario's law portal. Output is JSON with metadata, structured sections, and content hierarchy.

2. **OpenAI Assistant Backend**\
   `openai-proxy.js` acts as a middleman between the frontend and OpenAI’s Assistant v2 API. It handles thread creation, message flow, and polling for completions.

3. **Frontend Chat Interface**\
   A fully responsive HTML-based UI provides a friendly chat experience. It supports light/dark themes and renders citations, verdicts, and reasoning sections from the AI response.

## Getting Started

### 1. Scrape and Process Documents

```bash
cd data
python fsrao_pdf_scraper.py      # For FSRA PDFs
python ontario_law_scraper.py    # For Ontario laws
```

This will generate structured JSON files under `FSRAO_docs/` or `Ontario_docs/`.

### 2. Serve Frontend (optional)

You can open `index.html` in a browser or use a simple HTTP server:

```bash
python -m http.server
```

### 3. Deploy Netlify Functions

Ensure your environment has the OpenAI API key:

```bash
# In Netlify or local `.env` file
OPENAI_API_KEY=sk-...
```

Deploy functions under `/functions/` with Netlify CLI or console.

## Environment Variables

| Variable         | Description         |
| ---------------- | ------------------- |
| `OPENAI_API_KEY` | Your OpenAI API key |

## Credits

Developed by [Jennifer Do](https://www.linkedin.com/in/do-jennifer/)

## Disclaimer

LexiAI is a proof-of-concept tool. It may display inaccurate or incomplete legal interpretations and should not be considered a replacement for professional legal advice.

