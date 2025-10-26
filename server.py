# server.py — aiohttp single-port HTTP + WebSocket
# requirements.txt: aiohttp>=3.9
import os, json, random, string, re
from pathlib import Path
from aiohttp import web

PORT = int(os.environ.get("PORT", "8000"))

clients = set()
users = {}   # ws -> {"id","name","color"}
HISTORY = []
MAX_EVENTS = 8000

ADJ = ["swift","brave","calm","lucky","sunny","fuzzy","witty","quiet","eager","bright",
       "merry","zesty","nifty","spicy","bouncy","snappy","kind","bold","jolly","neat"]
NOUN = ["panda","tiger","eagle","otter","koala","lynx","fox","whale","moose","hare",
        "sparrow","orca","falcon","wolf","bear","owl","yak","ibis","bison","gecko"]

def sanitize_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^A-Za-z0-9 _\-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > 24: s = s[:24]
    if len(s) < 3:  s = ""
    return s

def rand_color():
    h = random.randint(0, 359); s=70; l=60
    ss=s/100; ll=l/100
    c=(1-abs(2*ll-1))*ss; x=c*(1-abs((h/60)%2-1)); m=ll-c/2
    if   0<=h<60:   r,g,b=c,x,0
    elif 60<=h<120: r,g,b=x,c,0
    elif 120<=h<180:r,g,b=0,c,x
    elif 180<=h<240:r,g,b=0,x,c
    elif 240<=h<300:r,g,b=x,0,c
    else:            r,g,b=c,0,x
    R=int((r+m)*255); G=int((g+m)*255); B=int((b+m)*255)
    return f"#{R:02x}{G:02x}{B:02x}"

async def broadcast(msg):
    if isinstance(msg, dict): msg=json.dumps(msg)
    dead=[]
    for ws in list(clients):
        try:
            await ws.send_str(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        await remove_client(ws)

async def send_roster():
    roster=[{"id":i["id"],"name":i["name"],"color":i["color"]} for i in users.values()]
    await broadcast({"type":"roster","peers":roster})

async def remove_client(ws):
    uid=None
    if ws in users:
        uid=users[ws]["id"]; del users[ws]
    if ws in clients:
        clients.remove(ws)
    if uid is not None:
        HISTORY[:]=[e for e in HISTORY if e.get("from")!=uid]
        await send_roster()
        await broadcast({"type":"rebuild","events":HISTORY})

# ---------- HTTP ----------
async def index(request: web.Request):
    return web.FileResponse(Path(__file__).with_name("index.html"))

async def whoami(request: web.Request):
    proto = request.headers.get("X-Forwarded-Proto", request.scheme)
    host  = request.headers.get("X-Forwarded-Host", request.host)
    ws_proto = "wss" if proto == "https" else "ws"
    return web.json_response({
        "http_url": f"{proto}://{host}/index.html",
        "ws_url":   f"{ws_proto}://{host}/ws"
    }, headers={"Cache-Control":"no-store","Access-Control-Allow-Origin":"*"})

# ---------- WebSocket ----------
async def ws_handler(request: web.Request):
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    clients.add(ws)

    uid = "".join(random.choices(string.ascii_lowercase+string.digits, k=8))
    # pick a unique-ish color
    taken_colors = {u["color"] for u in users.values()}
    color = rand_color(); tries=0
    while color in taken_colors and tries<2000:
        color = rand_color(); tries+=1

    info = {"id":uid, "name":None, "color":color}  # name arrives in "hello"

    try:
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            data = msg.json(loads=json.loads)
            t = data.get("type")

            # Client sends first: {"type":"hello","name":"..."}
            if t == "hello" and info["name"] is None:
                raw = str(data.get("name",""))
                new = sanitize_name(raw)
                if not new:
                    await ws.send_json({"type":"needName","reason":"invalid"}); 
                    continue
                # enforce uniqueness
                others = {u["name"] for u in users.values()}
                base, new_name, suffix = new, new, 1
                while new_name in others:
                    suf = f"-{suffix}"
                    if len(base)+len(suf) > 24:
                        base = base[:max(3,24-len(suf))]
                    new_name = base + suf
                    suffix += 1
                info["name"] = new_name
                users[ws] = info
                await ws.send_json({"type":"welcome", **info})
                await send_roster()
                if HISTORY:
                    await ws.send_json({"type":"history","events":HISTORY})
                continue

            # Ignore gameplay until named
            if info["name"] is None:
                continue

            if t=="draw":
                evt={"type":"draw","x0":data.get("x0"),"y0":data.get("y0"),
                     "x1":data.get("x1"),"y1":data.get("y1"),
                     "size":data.get("size"),"color":info["color"],
                     "from":info["id"],"sid":data.get("sid")}
                HISTORY.append(evt)
                if len(HISTORY)>MAX_EVENTS: del HISTORY[:MAX_EVENTS//10]
                await broadcast(evt)

            elif t=="dot":
                evt={"type":"dot","x":data.get("x"),"y":data.get("y"),
                     "size":data.get("size"),"color":info["color"],
                     "from":info["id"],"sid":data.get("sid")}
                HISTORY.append(evt)
                if len(HISTORY)>MAX_EVENTS: del HISTORY[:MAX_EVENTS//10]
                await broadcast(evt)

            elif t=="clearAll":
                HISTORY.clear()
                await broadcast({"type":"rebuild","events":HISTORY})

            elif t=="undoMine":
                mine=info["id"]; last_sid=None
                for i in range(len(HISTORY)-1,-1,-1):
                    e=HISTORY[i]
                    if e.get("from")==mine and e.get("type") in ("draw","dot"):
                        last_sid=e.get("sid"); break
                if last_sid is not None:
                    HISTORY[:] = [e for e in HISTORY if not (e.get("from")==mine and e.get("sid")==last_sid)]
                await broadcast({"type":"rebuild","events":HISTORY})

            elif t=="poke":
                target_id = str(data.get("to",""))
                # find target socket
                target_ws = None
                for w,u in users.items():
                    if u["id"] == target_id:
                        target_ws = w; break
                if target_ws:
                    try:
                        await target_ws.send_json({"type":"boop","fromId":info["id"],"fromName":info["name"]})
                    except Exception:
                        pass

            elif t=="rename":
                # (Not used by new UI, but supported.)
                raw = str(data.get("name",""))
                new = sanitize_name(raw)
                if not new:
                    await ws.send_json({"type":"youRenamed","name":info["name"],"ok":False,"reason":"invalid"})
                    continue
                others = {u["name"] for w,u in users.items() if w is not ws}
                base = new; new_name = new; suffix=1
                while new_name in others:
                    suf=f"-{suffix}"
                    if len(base)+len(suf)>24: base = base[:max(3,24-len(suf))]
                    new_name = base + suf; suffix+=1
                info["name"] = new_name
                await send_roster()
                await ws.send_json({"type":"youRenamed","name":new_name,"ok":True})
    finally:
        await remove_client(ws)

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/index.html", index)
app.router.add_get("/whoami", whoami)
app.router.add_get("/ws", ws_handler)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
