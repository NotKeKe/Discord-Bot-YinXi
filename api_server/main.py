from pathlib import Path

from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from routers import player
import src as _ # for load logger

app = FastAPI()

app.include_router(player.router)

TEMPLATES_DIR = Path(__file__).parent / "templates"
ASSETS_DIR = Path(__file__).parent / "assets"
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount('/assets', StaticFiles(directory=ASSETS_DIR), name='assets')
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {'request': request})

@app.get('/discord', response_class=RedirectResponse)
async def direct_to_discord_server():
    return RedirectResponse('https://discord.gg/MhtxWJu')

@app.get('/github', response_class=RedirectResponse)
async def direct_to_yinxi_github():
    return RedirectResponse('https://github.com/NotKeKe/Discord-Bot-YinXi')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000, log_config=None)