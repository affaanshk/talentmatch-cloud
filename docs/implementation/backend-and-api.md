# Backend and API

The backend is implemented with FastAPI. Its startup routine initializes the PostgreSQL schema. The API exposes endpoints for resume upload, status/history retrieval, text-based recommendations, skill extraction/comparison, and optional generated career advice.

## Resume upload validation

`POST /upload-resume` accepts a PDF and applies these checks:
- filename has a `.pdf` extension
- file is not empty
- file size does not exceed 5 MB
- file begins with the PDF signature
- extracted text is not empty

After validation, the API creates an upload record, stores the file object, enqueues the upload identifier, and responds with HTTP `202 Accepted`.

## Endpoint summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Basic API health/message |
| POST | `/upload-resume` | Validate, store, and enqueue resume |
| GET | `/uploads` | List recent upload records |
| GET | `/uploads/{upload_id}` | Get upload state and result |
| POST | `/recommend` | Run recommendation from resume text |
| POST | `/extract-skills` | Extract skills from text |
| POST | `/compare-skills` | Compare two skill lists |
| POST | `/career-advice` | Generate career guidance using configured Gemini service |

FastAPI's interactive Swagger UI is served at `/docs`.

## Development considerations

The current API enables permissive CORS (`*`) and the Compose configuration uses a local development database password. These settings are suitable only for the recorded local development setup; a public deployment needs restricted CORS, proper secret management, authentication, authorization, and operational safeguards.
