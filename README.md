# NyayaAI - AI Legal Case Analysis & Document Chat

NyayaAI is a document intelligence system for Indian legal documents. It automatically processes uploaded scanned legal PDFs using the Gemini API for visual document understanding (OCR) and LLM-powered legal extraction, summarization, and vector-search grounded chatting (RAG) using Qdrant.

## Requirements

* Node.js (v18+)
* Python 3.11+
* Docker Desktop (for Qdrant vector database)
* Google Gemini API Key

---

## 1. Environment Configuration

Create a `.env` file in the `backend` directory (or use the `.env.example` in the root):

```env
GEMINI_API_KEY=your_gemini_api_key_here
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=legal_case_chunks
PDF_STORAGE_PATH=./data/uploads
PAGES_STORAGE_PATH=./data/pages
STATE_STORAGE_PATH=./data/state
```

---

## 2. Start Qdrant

Ensure Docker Desktop is running. In the root directory of the project, run:

```bash
docker compose up -d
```
This will pull and start the Qdrant vector database container on `http://localhost:6333`.

---

## 3. Backend Setup

Open a new terminal and initialize the backend:

```bash
cd backend
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

### Start Backend

```bash
uvicorn app.main:app --reload --port 8000
```
The FastAPI server will start on `http://localhost:8000`.

---

## 4. Frontend Setup

Open another terminal and install frontend dependencies:

```bash
cd frontend
npm install
```

### Start Frontend

```bash
npm run dev
```
The Next.js application will start on `http://localhost:3000`.

---

## 5. Test the Application

1. Open `http://localhost:3000` in your browser.
2. Drag and drop the provided 59-page High Court PDF (or any legal PDF) into the upload area.
3. The UI will display the processing progress as the backend converts pages to images, queries the Gemini Vision API for OCR, embeds the chunks into Qdrant, and generates a structured JSON summary.
4. Once processing is "READY", review the **Case Summary** tab.
5. Switch to the **Chat** tab to ask questions (in English, Hindi, or Gujarati) such as:
   - "What is this case about?"
   - "Who is the petitioner?"
   - "What did the petitioner argue?"
6. The AI will respond based *only* on the document context, providing clickable `[p. X]` citations that link to the extracted source images.
