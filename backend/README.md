UHG Claims Service (Backend)

Stack
- FastAPI
- MongoDB Atlas (via Motor)
- Pydantic v2

Run locally
1. Create .env in this folder with:
   - MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority
   - DB_NAME=uhg_claims
2. Create a venv and install deps:
   - python -m venv venv
   - source venv/bin/activate
   - pip install -r requirements.txt
3. Start the API:
   - uvicorn app.main:app --reload --port 8080

API
- GET /health -> {"status":"ok"}
- POST /claims -> create claim
- GET /claims -> list claims
- GET /claims/{id} -> get one
- PATCH /claims/{id} -> update fields
- DELETE /claims/{id} -> delete

Notes
- Uses simple collection `claims`. Indexing can be added as needed.
- All IDs are MongoDB ObjectId strings in responses.

