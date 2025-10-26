<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<title>Drawit</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<style>
  :root{
    --bg:#111; --panel:#151515; --line:#222; --text:#eee;
    --btn:#222; --btn2:#2b2b2b; --btn3:#3a2f6b; --bd:#444; --bd2:#5c57a0; --sh:#0008;
    --accent:#7b6dff; --canvas:#0d0d0d;
    --bar-h:64px; --sidebar-w:240px;
  }
  [data-theme="light"]{
    --bg:#f6f7fb; --panel:#ffffff; --line:#dfe3f0; --text:#111;
    --btn:#f1f3f9; --btn2:#e8ebf5; --btn3:#dfe3ff; --bd:#cfd6ea; --bd2:#a5aef0; --sh:#0002;
    --accent:#5b55ff; --canvas:#f4f6fb;
  }
  html,body{height:100%;margin:0;background:var(--bg);color:var(--text);font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;overflow:hidden}
  .only-mobile{display:none} .only-desktop{display:initial}

  /* Top bar */
  #topbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
          padding:8px 10px;height:var(--bar-h);background:var(--panel);border-bottom:1px solid var(--line);
          position:fixed;top:0;left:0;right:0;z-index:10}
  input,button{background:var(--btn);color:var(--text);border:1px solid var(--bd);padding:6px 10px;border-radius:10px}
  button{cursor:pointer;box-shadow:0 3px 0 var(--sh),0 0 0 1px #0001 inset;
         transition:transform .12s,background-color .15s,border-color .15s,box-shadow .15s}
  button:hover{background:var(--btn2)}
  button:active{background:var(--btn3);border-color:var(--bd2);transform:translateY(1px)}
  .small{font-size:12px;opacity:.75}
  .grow{flex:1 1 auto}
  #size{width:64px}

  /* Layout */
  #sidebar{position:fixed;top:var(--bar-h);bottom:0;left:0;width:var(--sidebar-w);
           border-right:1px solid var(--line);background:var(--panel);padding:10px 10px 12px;overflow:auto;z-index:9}
  #canvas{position:fixed;top:var(--bar-h);left:var(--sidebar-w);right:0;bottom:0;background:var(--canvas);cursor:crosshair;touch-action:none}

  .section-title{font-weight:700;margin:2px 0 6px;opacity:.9}
  .subtle{font-size:12px;opacity:.75;margin:4px 0 10px}
  .card{background:var(--btn2);border:1px solid var(--bd);border-radius:12px;padding:8px 10px;margin-bottom:10px}
  .pill{display:flex;align-items:center;gap:8px;background:transparent;padding:6px 8px;border:1px solid var(--bd);border-radius:10px;margin-bottom:6px}
  .dot{width:14px;height:14px;border-radius:50%;border:1px solid #0003;box-shadow:0 0 0 1px #0002 inset}
  .iconbtn{padding:4px 6px;line-height:1;border-radius:8px}
  .poke{margin-left:auto}

  /* Toast */
  #toast{position:fixed;top:calc(var(--bar-h) + 10px);left:50%;transform:translateX(-50%);z-index:20;pointer-events:none}
  .toast{background:var(--panel);border:1px solid var(--bd);padding:10px 14px;border-radius:10px;box-shadow:0 10px 30px #0006;opacity:0}
  .toast.show{animation:fadeSlide 1.8s ease forwards}
  @keyframes fadeSlide{
    0%{opacity:0; transform:translate(-50%, -6px)}
    10%{opacity:1; transform:translate(-50%, 0)}
    80%{opacity:1}
    100%{opacity:0; transform:translate(-50%, -6px)}
  }

  /* Login overlay */
  #overlay{position:fixed;inset:0;background:rgba(0,0,0,.35);backdrop-filter:blur(6px);
           display:flex;align-items:center;justify-content:center;z-index:30}
  .login-card{width:min(92vw,420px);background:var(--panel);border:1px solid var(--bd);border-radius:16px;
              box-shadow:0 20px 60px #0008;padding:20px}
  .title{font-weight:700;font-size:28px;margin:4px 0 14px}
  .subtitle{opacity:.8;margin:-6px 0 18px}
  .field{display:flex;gap:8px}
  .field input{flex:1}
  .hint{font-size:12px;opacity:.78;margin-top:8px;display:none;color:#ff8080}
  .play{background:var(--accent);border-color:#9b92ff;color:#fff}

  /* Mobile */
  @media (max-width:900px){
    :root{--bar-h:56px}
    .only-mobile{display:initial} .only-desktop{display:none}
    #sidebar{width:min(85vw,320px);transform:translateX(-100%);transition:transform .2s ease}
    body.mobile-drawer-open #sidebar{transform:translateX(0);box-shadow:8px 0 20px #000a}
    #drawerScrim{position:fixed;inset:0;background:#0008;z-index:8;display:none}
    body.mobile-drawer-open #drawerScrim{display:block}
    #canvas{left:0}
  }
</style>
</head>
<body>
<div id="topbar">
  <button id="shareBtn" title="Copy invite link">🔗 Share</button>

  <span class="only-desktop">🖌️ Brush (Wheel)</span>
  <input id="size" type="number" min="1" max="50" step="1" value="4" aria-label="Brush size">
  <div class="only-mobile" style="display:flex;gap:6px">
    <button id="minusSize" title="Smaller">−</button>
    <button id="plusSize"  title="Bigger">+</button>
  </div>

  <button id="undo" title="Ctrl+Z">↩️ Undo (Ctrl+Z)</button>
  <button id="clear" title="C">🧹 Clear All (C)</button>

  <div class="grow"></div>

  <button id="themeToggle" title="Toggle theme">🌗 Theme</button>
  <span id="badge">Peers: 0</span>
  <span id="wsdebug" class="small" style="margin-left:8px;">Connecting...</span>
  <button id="playersBtn" class="only-mobile" style="margin-left:8px">Players</button>
</div>

<div id="sidebar" aria-label="Players drawer">
  <div class="section-title">You</div>
  <div class="subtle">This is your identity in the room</div>
  <div class="card">
    <div class="pill">
      <span class="dot" id="meDot"></span>
      <span id="meName">…</span>
    </div>
  </div>

  <div class="section-title" style="margin-top:12px">Players connected</div>
  <div class="subtle">Everyone here can draw with you</div>
  <div id="roster" style="padding:6px 0 0"></div>
</div>
<div id="drawerScrim" class="only-mobile"></div>

<canvas id="canvas"></canvas>
<div id="toast"></div>

<div id="overlay">
  <div class="login-card">
    <div class="title">Drawit</div>
    <div class="subtitle">Enter your name to start</div>
    <div class="field">
      <input id="loginName" placeholder="Your name" maxlength="24" autocomplete="name">
      <button id="playBtn" class="play">▶ Play</button>
    </div>
    <div id="nameHint" class="hint"></div>
  </div>
</div>

<script>
(function(){
  // --- DOM refs
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d', { alpha:false });
  ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.miterLimit = 2;

  const sizeInput = document.getElementById('size');
  const minusBtn  = document.getElementById('minusSize');
  const plusBtn   = document.getElementById('plusSize');

  const wsdebug   = document.getElementById('wsdebug');
  const badge     = document.getElementById('badge');
  const meName = document.getElementById('meName');
  const meDot  = document.getElementById('meDot');
  const rosterBox = document.getElementById('roster');

  const playersBtn = document.getElementById('playersBtn');
  const scrim = document.getElementById('drawerScrim');
  const themeToggle = document.getElementById('themeToggle');
  const shareBtn = document.getElementById('shareBtn');

  const undoBtn = document.getElementById('undo');
  const clearBtn= document.getElementById('clear');

  const login = document.getElementById('overlay');
  const playBtn = document.getElementById('playBtn');
  const loginName = document.getElementById('loginName');
  const nameHint = document.getElementById('nameHint');

  const toastWrap = document.getElementById('toast');
  const MOBILE_Q = window.matchMedia('(max-width: 900px)');

  // --- Hi-DPI sizing
  function fit(){
    const desktop = !MOBILE_Q.matches;
    const leftPad = desktop ? parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sidebar-w')) : 0;
    const barH = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--bar-h'));
    const w = window.innerWidth - leftPad, h = window.innerHeight - barH;
    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  window.addEventListener('resize', fit); fit();
  MOBILE_Q.addEventListener?.('change', fit);

  // --- Theme
  const root = document.documentElement;
  function applyTheme(t){ root.setAttribute('data-theme', t); localStorage.setItem('drawitTheme', t); }
  (function(){
    const saved = localStorage.getItem('drawitTheme');
    if (saved) applyTheme(saved);
    else if (window.matchMedia('(prefers-color-scheme: light)').matches) applyTheme('light');
    else applyTheme('dark');
  })();
  themeToggle.addEventListener('click', ()=> applyTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));

  // --- Mobile drawer
  const openDrawer = ()=> document.body.classList.add('mobile-drawer-open');
  const closeDrawer = ()=> document.body.classList.remove('mobile-drawer-open');
  playersBtn?.addEventListener('click', openDrawer);
  scrim?.addEventListener('click', closeDrawer);

  // --- Toast
  function showToast(text){
    const el = document.createElement('div');
    el.className = 'toast show';
    el.textContent = text;
    toastWrap.appendChild(el);
    setTimeout(()=> el.remove(), 1900);
  }

  // --- Share
  const SHARE_URL = "https://drawit-o0jo.onrender.com/";
  shareBtn.addEventListener('click', async ()=>{
    try{ await navigator.clipboard.writeText(SHARE_URL); showToast("Link copied"); }
    catch(e){ showToast("Copy failed"); }
  });

  // --- Device id
  function deviceId(){
    let d = localStorage.getItem('drawitDevice');
    if (!d){
      d = Array.from(crypto.getRandomValues(new Uint8Array(16))).map(b=>b.toString(16).padStart(2,'0')).join('');
      localStorage.setItem('drawitDevice', d);
    }
    return d;
  }

  // --- Brush controls
  const me = { id:null, name:null, color:"#ffffff", size:Number(sizeInput.value)||4 };
  const clamp = v => Math.max(1, Math.min(50, Math.round(v)));
  sizeInput.addEventListener('input', ()=>{ const v = parseFloat(sizeInput.value); if (Number.isFinite(v)) me.size = clamp(v); });
  minusBtn?.addEventListener('click', ()=>{ const v = clamp((+sizeInput.value||me.size||4)-1); sizeInput.value=v; me.size=v; });
  plusBtn?.addEventListener('click',  ()=>{ const v = clamp((+sizeInput.value||me.size||4)+1); sizeInput.value=v; me.size=v; });
  canvas.addEventListener('wheel', e=>{ e.preventDefault(); const v = clamp((+sizeInput.value||me.size||4)+(e.deltaY<0?1:-1)); sizeInput.value=v; me.size=v; }, {passive:false});

  // --- Hotkeys
  const sendClearAll = ()=> send({type:'clearAll'});
  const sendUndo = ()=> send({type:'undoMine'});
  window.addEventListener('keydown', (e)=>{
    const k = (e.key||'').toLowerCase();
    if ((e.ctrlKey||e.metaKey) && k==='z'){ e.preventDefault(); sendUndo(); }
    else if (!e.ctrlKey && !e.metaKey && k==='c'){ e.preventDefault(); sendClearAll(); }
  });

  // --- WebSocket
  let ws;
  const wsUrl = (location.protocol==='https:'?'wss://':'ws://') + location.host + '/ws';
  function send(obj){ try{ ws && ws.readyState===1 && ws.send(JSON.stringify(obj)); }catch(e){} }
  async function connect(){
    ws = new WebSocket(wsUrl);
    ws.onopen = ()=>{ wsdebug.textContent="Connected"; send({type:'hello', name: pendingName, device: deviceId()}); };
    ws.onclose = ()=>{ wsdebug.textContent="Disconnected"; setTimeout(connect, 800); };
    ws.onerror = ()=>{ wsdebug.textContent="Error"; };
    ws.onmessage = ev => handle(JSON.parse(ev.data));
  }

  function renderRoster(peers){
    rosterBox.innerHTML = "";
    badge.textContent = "Peers: " + peers.length;
    const others = peers.filter(p => p.id !== me.id);
    for (const p of others) {
      const div = document.createElement('div'); div.className="pill";
      const dot = document.createElement('span'); dot.className="dot"; dot.style.background=p.color;
      const name = document.createElement('span'); name.textContent = p.name;
      const poke = document.createElement('button'); poke.className='iconbtn poke'; poke.title='Poke'; poke.textContent='👈';
      poke.addEventListener('click', ()=> send({type:'poke', to: p.id}));
      div.appendChild(dot); div.appendChild(name); div.appendChild(poke);
      rosterBox.appendChild(div);
    }
  }

  // --- Smooth drawing (local + remote)
  function setStroke(color,size){ ctx.strokeStyle=color; ctx.lineWidth=size; }
  function drawDot(x,y,color,size){ ctx.beginPath(); ctx.arc(x,y,Math.max(1,size/2),0,Math.PI*2); ctx.fillStyle=color; ctx.fill(); }
  const mid = (a,b)=>({x:(a.x+b.x)/2, y:(a.y+b.y)/2});

  // Local (pointer events)
  let drawing=false, last=null, lastMid=null, sid=0;
  const pos = e => { const r = canvas.getBoundingClientRect(); return { x:e.clientX-r.left, y:e.clientY-r.top }; };

  canvas.addEventListener('pointerdown', e=>{
    e.preventDefault();
    canvas.setPointerCapture(e.pointerId);
    drawing = true; last = pos(e); lastMid = last; sid = (sid+1)|0;
    drawDot(last.x,last.y, me.color, me.size);
    send({type:'dot', x:last.x, y:last.y, size:me.size, sid});
  });
  canvas.addEventListener('pointermove', e=>{
    if (!drawing) return;
    const p = pos(e); const m1 = mid(last,p);
    setStroke(me.color, me.size);
    ctx.beginPath(); ctx.moveTo(lastMid.x,lastMid.y); ctx.quadraticCurveTo(last.x,last.y,m1.x,m1.y); ctx.stroke();
    send({type:'draw', x0:last.x, y0:last.y, x1:p.x, y1:p.y, size:me.size, sid});
    last = p; lastMid = m1;
  });
  function endPointer(){ drawing=false; last=null; lastMid=null; }
  canvas.addEventListener('pointerup', endPointer);
  canvas.addEventListener('pointercancel', endPointer);
  canvas.addEventListener('lostpointercapture', endPointer);

  // Remote smoothing with sid separation
  const remoteState = new Map(); // id -> {sid,last:{x,y},mid:{x,y}}
  function stepSmooth(id, sid, x0,y0, x1,y1, color,size){
    let s = remoteState.get(id);
    if (!s || s.sid !== sid){
      s = { sid, last:{x:x0,y:y0}, mid:{x:x0,y:y0} };
      remoteState.set(id, s);
    }
    const m1 = { x:(x0+x1)/2, y:(y0+y1)/2 };
    setStroke(color,size);
    ctx.beginPath(); ctx.moveTo(s.mid.x, s.mid.y); ctx.quadraticCurveTo(x0,y0,m1.x,m1.y); ctx.stroke();
    s.last = {x:x1,y:y1}; s.mid = m1;
  }

  function replaySmooth(events){
    remoteState.clear();
    ctx.clearRect(0,0,canvas.width,canvas.height);
    for (const e of (events||[])){
      if (e.type==='dot'){ drawDot(e.x,e.y,e.color,e.size); }
      else if (e.type==='draw'){ stepSmooth(e.from, (e.sid??0), e.x0,e.y0,e.x1,e.y1, e.color,e.size); }
    }
  }

  // --- Messages
  const handle = (msg)=>{
    if (!msg || !msg.type) return;

    if (msg.type === 'needName') {
      nameHint.style.display='block';
      nameHint.textContent = (msg.reason==='short') ? 'Name must be at least 3 characters'
                         : (msg.reason==='chars') ? 'Only letters, numbers, spaces, - and _ are allowed'
                         : 'Please enter a valid name';
      login.style.display='flex'; loginName.focus(); loginName.select(); return;
    }
    if (msg.type === 'banned') {
      nameHint.style.display='block'; nameHint.textContent='Blocked: already logged in on this device';
      login.style.display='flex'; return;
    }

    if (msg.type === 'welcome') {
      me.id = msg.id; me.name = msg.name; me.color = msg.color;
      meName.textContent = me.name; meDot.style.background = me.color;
      login.style.display='none'; nameHint.style.display='none'; return;
    }
    if (msg.type === 'roster') { renderRoster(msg.peers||[]); return; }

    if (msg.type === 'history') { replaySmooth(msg.events); return; }
    if (msg.type === 'rebuild') { replaySmooth(msg.events); return; }

    if (msg.type === 'draw') { stepSmooth(msg.from, (msg.sid??0), msg.x0,msg.y0, msg.x1,msg.y1, msg.color,msg.size); return; }
    if (msg.type === 'dot')  { drawDot(msg.x,msg.y,msg.color,msg.size); return; }
    if (msg.type === 'boop') { showToast(`${msg.fromName} booped you!`); return; }
  };

  // --- Login
  let pendingName = "";
  const validChars = s => /^[A-Za-z0-9 _-]+$/.test(s);
  function tryPlay(){
    const n = (loginName.value||"").trim();
    if (n.length<3){ nameHint.style.display='block'; nameHint.textContent='Name must be at least 3 characters'; return; }
    if (!validChars(n)){ nameHint.style.display='block'; nameHint.textContent='Only letters, numbers, spaces, - and _ are allowed'; return; }
    pendingName = n; nameHint.style.display='none'; connect();
  }
  playBtn.addEventListener('click', tryPlay);
  loginName.addEventListener('keydown', e=>{ if (e.key==='Enter') tryPlay(); });
  setTimeout(()=> loginName.focus(), 50);

  // --- Top buttons
  undoBtn.addEventListener('click', ()=> send({type:'undoMine'}));
  clearBtn.addEventListener('click', ()=> send({type:'clearAll'}));
})();
</script>
</body>
</html>
