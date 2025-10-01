# === server.py ===
# Prototype FastAPI + WebSocket pour Last-Man-Standing
import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import random
import math

app = FastAPI()

# =====================
# Game state
# =====================
clients = {}  # websocket -> {name, lives}
alive_clients = []
rules_active = []
available_rules = [1,2,3,4,5,6]
MULTIPLIERS = [0.5,0.6,0.7,0.8,0.9,1.1,1.2,1.3,1.4,1.5]
current_multiplier = None
ROUND = 0
DEFAULT_ROUND_TIME = 45
forbidden_numbers = set()
game_started = False  # le jeu ne démarre que quand le premier joueur clique sur "Lancer la partie"

# =====================
# HTML frontend (simple)
# =====================
html = """
<!DOCTYPE html>
<html>
<head>
<title>Last-Man-Standing Web</title>
<style>
body{font-family:sans-serif;margin:20px}
#log{border:1px solid #ccc;padding:10px;height:300px;overflow:auto}
</style>
</head>
<body>
<h2>Last-Man-Standing</h2>
<div>
Pseudo: <input id="name"/><button onclick="join()">Rejoindre</button>
</div>
<div id="game" style="display:none">
<p id="info"></p>
<button id="start_btn" onclick="startGame()" style="display:none">Lancer la partie</button>
<p id="round_info"></p>
<p>Nombres interdits: <span id="forbidden"></span></p>
<input type="number" id="number_input" min="0" max="100"/><button onclick="sendNumber()">Envoyer</button>
<h3>Vies</h3>
<ul id="lives_list"></ul>
<div id="log"></div>
</div>
<script>
var ws;
var is_first_player = false;
function join(){
    var name = document.getElementById('name').value;
    ws = new WebSocket('ws://' + location.host + '/ws');
    ws.onopen = function(){
        ws.send(JSON.stringify({'type':'join','name':name}));
        document.getElementById('game').style.display='block';
    };
    ws.onmessage = function(event){
        var m = JSON.parse(event.data);
        handleMessage(m);
    };
}
function handleMessage(m){
    if(m.type=='info'){
        document.getElementById('info').innerText = m.text;
        var log = document.getElementById('log');
        log.innerHTML += '<div>'+m.text+'</div>';
        log.scrollTop = log.scrollHeight;
        // si c'est le premier joueur, afficher le bouton "Lancer la partie"
        if(m.text.includes('a rejoint la partie') && !is_first_player){
            // si c'est le premier joueur connecté
            is_first_player = true;
            document.getElementById('start_btn').style.display='block';
        }
    } else if(m.type=='round_start'){
        document.getElementById('round_info').innerText = 'Round '+m.round+': multiplier='+m.multiplier+', temps='+m.time+'s';
        document.getElementById('forbidden').innerText = m.forbidden.join(',');
    } else if(m.type=='round_result'){
        var ul = document.getElementById('lives_list');
        ul.innerHTML = '';
        m.lives.forEach(p => {
            var li = document.createElement('li');
            li.innerText = p.name+': '+p.lives;
            ul.appendChild(li);
        });
        var log = document.getElementById('log');
        log.innerHTML += '<div>Round '+m.round+' cible='+m.target+', plus proches: '+m.closest.join(',')+', éliminés: '+m.eliminated.join(',')+'</div>';
        if(m.new_rules.length>0){
            log.innerHTML += '<div>Nouvelles règles activées: '+m.new_rules.join(',')+'</div>';
        }
        log.scrollTop = log.scrollHeight;
    }
}
function sendNumber(){
    var v = parseInt(document.getElementById('number_input').value);
    ws.send(JSON.stringify({'type':'answer','value':v}));
}
function startGame(){
    ws.send(JSON.stringify({'type':'start_game'}));
    document.getElementById('start_btn').style.display='none';
}
</script>
</body>
</html>
"""

# =====================
# Game functions
# =====================
async def broadcast(message):
    remove = []
    for ws in clients:
        try:
            await ws.send_json(message)
        except:
            remove.append(ws)
    for ws in remove:
        await disconnect(ws)

async def disconnect(ws):
    if ws in clients:
        name = clients[ws]['name']
        del clients[ws]
        await broadcast({'type':'info','text': f'{name} a quitté la partie'})

async def game_loop():
    global ROUND,current_multiplier,forbidden_numbers
    await asyncio.sleep(1)
    # assign lives
    n_players = len(clients)
    initial_lives = max(n_players*3,10 if n_players<=3 else n_players*3)
    for ws in clients:
        clients[ws]['lives'] = initial_lives
    current_multiplier = random.choice(MULTIPLIERS)
    await broadcast({'type':'info','text': f'Jeu démarré: {n_players} joueurs, {initial_lives} vies chacun. Multiplicateur initial = {current_multiplier}'})

    while True:
        ROUND += 1
        alive = [info for info in clients.values() if info['lives']>0]
        if len(alive)<=1:
            if alive:
                winner = [ws for ws, info in clients.items() if info['lives']>0][0]
                await broadcast({'type':'info','text': f'Le gagnant est {clients[winner]["name"]}!'})
            break

        # round parameters
        if 1 in rules_active:
            multiplier = random.choice(MULTIPLIERS)
        else:
            multiplier = current_multiplier
        if 4 in rules_active:
            round_time = random.randint(7,30)
        else:
            round_time = DEFAULT_ROUND_TIME
        if 6 in rules_active:
            forbidden_numbers = set(random.sample(range(101),20))
        else:
            forbidden_numbers = set()

        await broadcast({'type':'round_start','round':ROUND,'multiplier':multiplier,'time':round_time,'forbidden': list(forbidden_numbers)})

        # collect answers
        answers = {}
        end_time = asyncio.get_event_loop().time()+round_time
        while asyncio.get_event_loop().time()<end_time:
            for ws, info in clients.items():
                if 'answer' in info:
                    v = info.pop('answer')
                    if 0<=v<=100 and v not in forbidden_numbers:
                        answers[info['name']] = v
            await asyncio.sleep(0.1)

        # compute target
        if answers:
            avg = sum(answers.values())/len(answers)
        else:
            avg = 0
        target = int(round(avg*multiplier))

        # closest players
        distances = {info['name']: abs(answers.get(info['name'],-9999)-target) for info in clients.values() if info['lives']>0}
        if distances:
            min_dist = min(distances.values())
            closest = [n for n,d in distances.items() if d==min_dist]
        else:
            closest = []
        # apply lives
        eliminated_now = []
        for ws, info in clients.items():
            if info['lives']>0:
                if info['name'] in closest:
                    continue
                info['lives'] -= 1
                if info['lives']<=0:
                    eliminated_now.append(info['name'])
                    # activate new rule
                    if available_rules:
                        r = random.choice(available_rules)
                        available_rules.remove(r)
                        rules_active.append(r)
        lives_summary = [{'name':info['name'],'lives':info['lives']} for info in clients.values()]
        await broadcast({'type':'round_result','round':ROUND,'target':target,'closest':closest,'eliminated':eliminated_now,'lives':lives_summary,'active_rules':rules_active,'new_rules':[]})
        await asyncio.sleep(2)

# =====================
# Routes
# =====================
@app.get('/')
async def get():
    return HTMLResponse(html)

@app.websocket('/ws')
async def websocket_endpoint(ws: WebSocket):
    global game_started
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            t = data.get('type')
            if t=='join':
                name = data.get('name','Joueur')
                clients[ws] = {'name':name,'lives':None}
                await broadcast({'type':'info','text': f'{name} a rejoint la partie'})
            elif t=='start_game' and not game_started:
                game_started = True
                asyncio.create_task(game_loop())
                await broadcast({'type':'info','text': 'Le jeu a été lancé !'})
            elif t=='answer':
                if ws in clients:
                    clients[ws]['answer'] = data.get('value')
    except WebSocketDisconnect:
        await disconnect(ws)

# =====================
# Run server
# =====================
if __name__=='__main__':
    uvicorn.run(app,host='0.0.0.0',port=8000)


