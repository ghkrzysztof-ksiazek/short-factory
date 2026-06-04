from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from short_factory.api.metrics import router as metrics_router
from short_factory.api.routes import router
from short_factory.config.logging import setup_logging
from short_factory.config.settings import settings

setup_logging(settings.log_level)

app = FastAPI(title="Short Factory", version="0.1.0", description="AI YouTube Shorts production pipeline")
app.include_router(router)
app.include_router(metrics_router)


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    """Minimal admin UI for topic queue, scripts, and analytics."""
    return """<!DOCTYPE html>
<html>
<head>
  <title>Short Factory Admin</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
    h1 { color: #1a1a2e; }
    section { margin: 2rem 0; padding: 1rem; border: 1px solid #ddd; border-radius: 8px; }
    button { padding: 0.5rem 1rem; margin: 0.25rem; cursor: pointer; background: #1a1a2e; color: white; border: none; border-radius: 4px; }
    button:hover { background: #16213e; }
    pre { background: #f5f5f5; padding: 1rem; overflow: auto; max-height: 300px; }
  </style>
</head>
<body>
  <h1>Short Factory Admin</h1>
  <section>
    <h2>Pipeline Actions</h2>
    <button onclick="post('/jobs/research/run')">Run Research</button>
    <button onclick="post('/jobs/scripts/run')">Generate Scripts</button>
    <button onclick="post('/jobs/pipeline/run')">Run Full Pipeline</button>
    <button onclick="post('/analytics/optimize')">Run Optimization</button>
  </section>
  <section>
    <h2>Topics</h2>
    <button onclick="get('/topics?limit=10')">Load Top Topics</button>
  </section>
  <section>
    <h2>Scripts</h2>
    <button onclick="get('/scripts?limit=10')">Load Scripts</button>
  </section>
  <section>
    <h2>Analytics</h2>
    <button onclick="get('/analytics/summary')">Load Summary</button>
  </section>
  <section>
    <h2>Output</h2>
    <pre id="output">Click a button to fetch data...</pre>
  </section>
  <script>
    async function get(path) {
      const r = await fetch(path);
      document.getElementById('output').textContent = JSON.stringify(await r.json(), null, 2);
    }
    async function post(path) {
      const r = await fetch(path, { method: 'POST' });
      document.getElementById('output').textContent = JSON.stringify(await r.json(), null, 2);
    }
  </script>
</body>
</html>"""


def run():
    import uvicorn

    uvicorn.run("short_factory.api.main:app", host="0.0.0.0", port=8000, reload=True)
