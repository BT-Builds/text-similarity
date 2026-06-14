import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import difflib

app = FastAPI(title="Text Similarity API", version="1.0.0")
# === BT Builds Standard Middleware (auto-injected) ===
from fastapi.middleware.cors import CORSMiddleware as _BTCors
app.add_middleware(_BTCors, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], expose_headers=["X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset"])

@app.middleware("http")
async def _bt_add_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "btbuilds"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: Optional[str] = Depends(API_KEY_HEADER)):
    if api_key is None or api_key == "":
        api_key = os.environ.get("API_KEY", "free-demo-key")
    return api_key

class SimilarityRequest(BaseModel):
    text1: str
    text2: str
    method: Optional[str] = "ratio"

class BulkItem(BaseModel):
    text1: str
    text2: str
    method: Optional[str] = "ratio"

class BulkRequest(BaseModel):
    items: List[BulkItem]

def calculate_similarity(text1: str, text2: str, method: str = "ratio") -> float:
    if method == "ratio":
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    elif method == "quick_ratio":
        return difflib.SequenceMatcher(None, text1, text2).quick_ratio()
    elif method == "real_quick_ratio":
        return difflib.SequenceMatcher(None, text1, text2).real_quick_ratio()
    else:
        return difflib.SequenceMatcher(None, text1, text2).ratio()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/similarity")
async def similarity(request: SimilarityRequest, api_key: str = Depends(get_api_key)):
    return {"similarity": calculate_similarity(request.text1, request.text2, request.method)}

@app.post("/is-duplicate")
async def is_duplicate(request: SimilarityRequest, threshold: float = 0.95, api_key: str = Depends(get_api_key)):
    similarity_score = calculate_similarity(request.text1, request.text2, request.method)
    return {"is_duplicate": similarity_score >= threshold, "similarity": similarity_score}

@app.post("/bulk/similarity")
async def bulk_similarity(request: BulkRequest, api_key: str = Depends(get_api_key)):
    items = request.items
    if len(items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    for item in items:
        try:
            result = calculate_similarity(item.text1, item.text2, item.method)
            results.append({"input": item.model_dump(), "output": {"similarity": result}, "error": None})
            successful += 1
        except Exception as e:
            results.append({"input": item.model_dump(), "output": None, "error": str(e)})
    
    return {"results": results, "total": len(items), "successful": successful}

@app.post("/bulk/is-duplicate")
async def bulk_is_duplicate(request: BulkRequest, threshold: float = 0.95, api_key: str = Depends(get_api_key)):
    items = request.items
    if len(items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    for item in items:
        try:
            similarity_score = calculate_similarity(item.text1, item.text2, item.method)
            result = {"is_duplicate": similarity_score >= threshold, "similarity": similarity_score}
            results.append({"input": item.model_dump(), "output": result, "error": None})
            successful += 1
        except Exception as e:
            results.append({"input": item.model_dump(), "output": None, "error": str(e)})
    
    return {"results": results, "total": len(items), "successful": successful}