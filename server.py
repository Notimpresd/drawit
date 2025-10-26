# server.py
import os, json, re, uuid, random, asyncio
from aiohttp import web, WSMsgType

PORT = int(os.environ.get("PORT", "8000"))

# ---- In-memory state ----
peers = {}          # peer_id -> {"ws", "name", "color", "device"}
device_to_peer = {} # device_id -> peer_id
history = []        # list of drawing events (dot/draw)

NAME_RE = re.compile(r"^[A-Za-z0-9 _-]{3,24}$")
COLORS = ["#ff7675","#74b9ff","#55efc4","#ffeaa7","#a29bfe","#fd79a8","#e17055","#00cec9","#6c5ce7","#fdcb6e"]

def roster_payload():
    return [{"id": pid, "name": p["name"], "color": p["color"]} for pid,p in peers.items()]

async def broadcast(obj, skip=None):
    dead = []
    data = json.dumps(obj)
    for pid, p in list(peers.items()):
        if skip and pid in skip:
            continue
        try:
            await p["ws"].send_str(data)
        except Exception:
            dead.append(pid)
    for pid in dead:
        await remove_peer(pid)

async def remove_peer(pid):
    p = peers.pop(pid, None)
    if not p:
        return
    if p.get("device") and device_to_peer.get(p["device"]) == pid:
        device_to_peer.pop(p["device"], None)
    await broadcast({"type":"roster", "peers": roster_payload()})

async def index(request):
    return web.FileResponse("index.html")

async def health(request):
    return web.Response(text="ok")

async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    peer_id = None

    async for msg in ws:
        if msg.type != WSMsgType.TEXT:
            continue
        try:
            data = json.loads(msg.data)
        except Exception:
            continue

        mtype = data.get("type")

        if mtype == "hello" and peer_id is None:
            name = (data.get("name") or "").strip()
            device = (data.get("device") or "").strip()

            if not NAME_RE.fullmatch(name):
                await ws.send_json({"type":"needName","reason":"short" if len(name)<3 else "chars"})
                await ws.close()
                break

            if device and device in device_to_peer:
                await ws.send_json({"type":"banned"})
                await ws.close()
                break

            peer_id = uuid.uuid4().hex[:8]
            color = random.choice(COLORS)
            peers[peer_id] = {"ws": ws, "name": name, "color": color, "device": device or None}
            if device:
                device_to_peer[device] = peer_id

            await ws.send_json({"type":"welcome","id":peer_id,"name":name,"color":color})
            await ws.send_json({"type":"roster","peers": roster_payload()})
            await ws.send_json({"type":"history","events": history})
            await broadcast({"type":"roster","peers": roster_payload()}, skip={peer_id})
            continue

        if peer_id is None:
            continue

        if mtype == "dot":
            e = {"type":"dot","x":data.get("x"),"y":data.get("y"),
                 "size": int(data.get("size") or 4),
                 "color": peers[peer_id]["color"]}
            history.append({**e, "from": peer_id})
            await broadcast({**e, "from": peer_id})
            continue

        if mtype == "draw":
            e = {"type":"draw",
                 "x0": data.get("x0"), "y0": data.get("y0"),
                 "x1": data.get("x1"), "y1": data.get("y1"),
                 "size": int(data.get("size") or 4),
                 "sid": int(data.get("sid") or 0),
                 "color": peers[peer_id]["color"]}
            ev = {**e, "from": peer_id}
            history.append(ev)
            await broadcast(ev)
            continue

        if mtype == "undoMine":
            for i in range(len(history)-1, -1, -1):
                ev = history[i]
                if isinstance(ev, dict) and ev.get("from") == peer_id:
                    sid_to_remove = ev.get("sid")
                    j = len(history)-1
                    while j >= 0:
                        if history[j].get("from")==peer_id and history[j].get("sid")==sid_to_remove:
                            history.pop(j)
                        j -= 1
                    break
            await broadcast({"type":"rebuild","events": history})
            continue

        if mtype == "clearAll":
            history.clear()
            await broadcast({"type":"rebuild","events": history})
            continue

        if mtype == "poke":
            to = data.get("to")
            if to and to in peers:
                try:
                    await peers[to]["ws"].send_json({"type":"boop","from":peer_id,"fromName":peers[peer_id]["name"]})
                except Exception:
                    pass
            continue

    if peer_id:
        await remove_peer(peer_id)
    return ws

def make_app():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_get("/ws", ws_handler)
    app.router.add_static("/", path=".", show_index=False)
    return app

if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=PORT)
