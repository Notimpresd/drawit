# server.py  — single-port HTTP + WebSocket
# pip install websockets
import asyncio, json, os, random, string
from http import HTTPStatus
from pathlib import Path
import websockets

PORT = int(os.environ.get("PORT", "8000"))

clients = set()
users = {}  # websocket -> {"id","name","color"}
HISTORY = []
MAX_EVENTS = 8000

ADJ = ["swift","brave","calm","lucky","sunny","fuzzy","witty","quiet","eager","bright",
       "merry","zesty","nifty","spicy","bouncy","snappy","kind","bold","jolly","neat"]
NOUN = ["panda","tiger","eagle","otter","koala","lynx","fox","whale","moose","hare",
        "sparrow","orca","falcon","wolf","bear","owl","yak","ibis","bison","gecko"]

def rand_name(): return random.choice(ADJ) + "-" + random.choice(NOUN) + "-" + str(random.randint(10, 99))

def rand_color():
    h = random.randint(0, 359); s=70; l=60
    def hsl_to_rgb(hh, ss, ll):
        ss/=100; ll/=100
        c=(1-abs(2*ll-1))*ss; x=c*(1-abs((hh/60)%2-1)); m=ll-c/2
        if   0<=hh<60:   r,g,b=c,x,0
        elif 60<=hh<120: r,g,b=x,c,0
        elif 120<=hh<180:r,g,b=0,c,x
        elif 180<=hh<240:r,g,b=0,x,c
        elif 240<=hh<300:r,g,b=x,0,c
        else:            r,g,b=c,0,x
        r=int((r+m)*255); g=int((g+m)*255); b=int((b+m)*255)
        return f"#{r:02x}{g:02x}{b:02x}"
    return hsl_to_rgb(h, s, l)

async def broadcast(msg):
    if isinstance(msg, dict): msg=json.dumps(msg)
    stale=[]
    for ws in list(clients):
        try: await ws.send(msg)
        except Exception: stale.append(ws)
    for ws in stale: await remove_client(ws)

async def send_roster():
    roster=[{"id":i["id"],"name":i["name"],"color":i["color"]} for i in users.values()]
    await broadcast({"type":"roster","peers":roster})

async def remove_client(ws):
    uid=None
    if ws in users:
        uid=users[ws]["id"]; del users[ws]
    if ws in clients: clients.remove(ws)
    if uid is not None:
        HISTORY[:]=[e for e in HISTORY if e.get("from")!=uid]
    await send_roster()
    await broadcast({"type":"rebuild","events":HISTORY})

async def ws_handler(websocket):
    # Only accept our WS endpoint
    if getattr(websocket, "path", "/") != "/ws":
        await websocket.close(code=1008, reason="Wrong path"); return

    uid = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    taken_names  = {u["name"] for u in users.values()}
    taken_colors = {u["color"] for u in users.values()}
    name = rand_name()
    while name in taken_names: name = rand_name()
    color = rand_color()
    tries=0
    while color in taken_colors and tries<2000: color=rand_color(); tries+=1
    info = {"id":uid,"name":name,"color":color}

    clients.add(websocket); users[websocket]=info
    try:
        await websocket.send(json.dumps({"type":"welcome", **info}))
        await send_roster()
        if HISTORY:
            await websocket.send(json.dumps({"type":"history","events":HISTORY}))

        async for message in websocket:
            try: data=json.loads(message)
            except Exception: continue
            t=data.get("type")

            if t=="draw":
                evt={"type":"draw","x0":data.get("x0"),"y0":data.get("y0"),
                     "x1":data.get("x1"),"y1":data.get("y1"),
                     "size":data.get("size"),"color":info["color"],
                     "from":info["id"],"sid":data.get("sid")}
                HISTORY.append(evt)
            elif t=="dot":
                evt={"type":"dot","x":data.get("x"),"y":data.get("y"),
                     "size":data.get("size"),"color":info["color"],
                     "from":info["id"],"sid":data.get("sid")}
                HISTORY.append(evt)
            elif t=="clearMine":
                mine=info["id"]
                HISTORY[:]=[e for e in HISTORY if not (e.get("from")==mine and e.get("type") in ("draw","dot"))]
                await broadcast({"type":"rebuild","events":HISTORY}); continue
            elif t=="undoMine":
                mine=info["id"]; last_sid=None
                for i in range(len(HISTORY)-1,-1,-1):
                    e=HISTORY[i]
                    if e.get("from")==mine and e.get("type") in ("draw","dot"):
                        last_sid=e.get("sid"); break
                if last_sid is not None:
                    HISTORY[:]=[e for e in HISTORY if not (e.get("from")==mine and e.get("sid")==last_sid)]
                await broadcast({"type":"rebuild","events":HISTORY}); continue
            else:
                continue

            if len(HISTORY)>MAX_EVENTS:
                drop=max(1,MAX_EVENTS//10); del HISTORY[:drop]
            await broadcast(evt)
    finally:
        await remove_client(websocket)

# Serve index.html and /whoami over the same port using websockets' process_request
async def process_request(path, headers):
    # /whoami helps the client build the correct share + ws URLs behind proxies/CDN
    if path == "/whoami":
        host = headers.get("Host", f"localhost:{PORT}")
        proto = headers.get("X-Forwarded-Proto", "http")
        ws_proto = "wss" if proto == "https" else "ws"
        body = json.dumps({
            "http_url": f"{proto}://{host}/index.html",
            "ws_url":   f"{ws_proto}://{host}/ws"
        }).encode("utf-8")
        return (HTTPStatus.OK,
                [("Content-Type","application/json"),
                 ("Cache-Control","no-store"),
                 ("Access-Control-Allow-Origin","*")],
                body)

    if path in ("/", "/index.html"):
        body = Path(__file__).with_name("index.html").read_bytes()
        return (HTTPStatus.OK,
                [("Content-Type","text/html; charset=utf-8"),
                 ("Cache-Control","no-store")],
                body)

    # Let the WS handshake happen only on /ws; else 404
    if path != "/ws":
        msg=b"Not found"
        return (HTTPStatus.NOT_FOUND,
                [("Content-Type","text/plain; charset=utf-8")],
                msg)

async def main():
    print(f"Serving on http://0.0.0.0:{PORT}  (WS at /ws)")
    async with websockets.serve(ws_handler, "0.0.0.0", PORT,
                                process_request=process_request,
                                ping_interval=20, ping_timeout=20):
        await asyncio.Future()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
