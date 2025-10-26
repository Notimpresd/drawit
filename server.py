# server.py — aiohttp single-port HTTP + WebSocket
# requirements.txt: aiohttp>=3.9
import os, json, random, string, re
from pathlib import Path
from aiohttp import web

PORT = int(os.environ.get("PORT", "8000"))

clients = set()
users = {}            # ws -> {"id","name","color","device"}
device_to_ws = {}     # device_id -> ws  (block multiple logins from same device)
HISTORY = []
MAX_EVENTS = 8000

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
    info = users.pop(ws, None)
    clients.discard(ws)
    if info:
        did = info.get("device")
        if did and device_to_ws.get(did) is ws:
            device_to_ws.pop(did, None)
        # prune that user's strokes
        HISTORY[:] = [e for e in HISTORY if e.get("from") != info["id"]]
    await send_roster()
    await broadcast({"type":"rebuild","events":HISTORY})

# ---------------- HTTP ----------------
async def index(request: web.Request):
    return web.FileResponse(Path(__file__).with_name("index.html"))

async def index_redirect(request: web.Request):
    raise web.HTTPPermanentRedirect("/")

# --------------- WebSocket ---------------
async def ws_handler(request: web.Request):
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    clients.add(ws)

    uid = "".join(random.choices(string.ascii_lowercase+string.digits, k=8))
    color = rand_color()
    info = {"id":uid, "name":None, "color":color, "device":None}  # filled on "hello"

    try:
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            data = msg.json(loads=json.loads)
            t = data.get("type")

            # First message must be hello with name + deviceId
            if t == "hello" and info["name"] is None:
                raw_name  = str(data.get("name",""))
                device_id = str(data.get("device","")).strip()[:64]
                if not device_id:
                    await ws.send_json({"type":"needName","reason":"device"})
                    continue
                cleaned = sanitize_name(raw_name)  # empty if <3 or illegal chars
                if not cleaned:
                    reason = "short" if len((raw_name or "").strip()) < 3 else "chars"
                    await ws.send_json({"type":"needName","reason":reason})
                    continue

                # duplicate device? ban this attempt
                if device_id in device_to_ws and device_to_ws[device_id] in users:
                    await ws.send_json({"type":"banned","reason":"duplicate_device"})
                    await ws.close()
                    break

                # unique name
                others = {u["name"] for u in users.values() if u["name"]}
                base, new_name, suffix = cleaned, cleaned, 1
                while new_name in others:
                    suf = f"-{suffix}"
                    if len(base)+len(suf) > 24:
                        base = base[:max(3,24-len(suf))]
                    new_name = base + suf
                    suffix += 1

                info["name"] = new_name
                info["device"] = device_id
                users[ws] = info
                device_to_ws[device_id] = ws

                await ws.send_json({"type":"welcome", **info})
                await send_roster()
                if HISTORY:
                    await ws.send_json({"type":"history","events":HISTORY})
                continue

            # Ignore until named
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
                target_ws = next((w for w,u in users.items() if u["id"]==target_id), None)
                if target_ws:
                    try:
                        await target_ws.send_json({"type":"boop","fromId":info["id"],"fromName":info["name"]})
                    except Exception:
                        pass

    finally:
        await remove_client(ws)

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/index.html", index_redirect)  # discourage sharing /index.html
app.router.add_get("/ws", ws_handler)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
