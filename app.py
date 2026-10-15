"""FastAPI operational view for ReflexDB synthetic demo."""
import argparse
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from reflexdb import synthetic, load_csv, run

app = FastAPI(title="ReflexDB Emerging Intelligence", version="0.1.0")
ROOT = Path(__file__).resolve().parent
DATA = None

@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/api/overview")
def overview():
    return DATA

@app.get("/api/episodes")
def episodes(state: str = "EMERGING", limit: int = 30):
    items = DATA["episodes"]
    if state != "ALL":
        items = [e for e in items if e["lifecycle_state"] == state]
    return {"items": items[:max(1, min(200, limit))]}

@app.get("/api/episodes/{episode_id}")
def episode(episode_id: str):
    ep = next((e for e in DATA["episodes"] if e["episode_id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return {"episode": ep, "history": [h for h in DATA["history"] if h["episode_id"] == episode_id]}

if __name__ == "__main__":
    import uvicorn
    p = argparse.ArgumentParser()
    p.add_argument("--csv")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    DATA = run(load_csv(args.csv) if args.csv else synthetic())
    uvicorn.run(app, host="127.0.0.1", port=args.port)
else:
    DATA = run(synthetic())
