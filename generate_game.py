import json, os

levels = []
for i in range(1, 6):
    fname = f"level_0{i}.json"
    if os.path.exists(fname):
        with open(fname) as f:
            levels.append(json.load(f))

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playable Dungeon - Live AI Dialogue</title>
    <style>
        body {
            background-color: #0f111a;
            color: #e2e8f0;
            font-family: monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 20px;
        }
        .main-layout {
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }
        canvas {
            background-color: #000000;
            border: 4px solid #334155;
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
        }
        .ui-panel {
            max-width: 400px;
            width: 100%;
            background: #1a1d2d;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #334155;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .stat-bar {
            background: #0f111a;
            padding: 10px;
            border-radius: 6px;
            font-size: 1rem;
            border-left: 4px solid #10b981;
        }
        .combat-log {
            background: #090a0f;
            color: #10b981;
            height: 140px;
            overflow-y: auto;
            padding: 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            border: 1px solid #2d3748;
            line-height: 1.4;
        }
        .chat-box {
            background: #090a0f;
            border: 1px solid #3b82f6;
            border-radius: 6px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .chat-history {
            height: 120px;
            overflow-y: auto;
            font-size: 0.85rem;
            color: #38bdf8;
            line-height: 1.3;
        }
        .chat-input-container {
            display: flex;
            gap: 6px;
        }
        input[type="text"] {
            flex: 1;
            background: #1e293b;
            border: 1px solid #475569;
            color: #fff;
            padding: 6px;
            border-radius: 4px;
            font-family: monospace;
        }
        button {
            background: #2563eb;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #1d4ed8; }
        .controls { color: #e5b25d; font-size: 0.9rem; }
    </style>
</head>
<body>

    <h1 id="floor-title" style="color: #e5b25d;">Loading Floor...</h1>

    <div class="main-layout">
        <canvas id="gameCanvas" width="480" height="480"></canvas>

        <div class="ui-panel">
            <div class="stat-bar">
                ❤️ <b>HP:</b> <span id="player-hp">100</span> / 100 | ⚔️ <b>Atk:</b> 15<br>
                👁️ <b>Vision:</b> 3 Tiles
            </div>

            <div class="controls">🎮 <b>WASD/Arrows</b> to move</div>
            
            <div class="chat-box">
                <div style="color:#38bdf8; font-weight:bold;" id="chat-header">💬 Live AI Dialogue (Ollama)</div>
                <div id="chat-history" class="chat-history">Walk next to an NPC or boss to chat...</div>
                <div class="chat-input-container">
                    <input type="text" id="chat-input" placeholder="Type a message..." disabled>
                    <button id="send-btn" onclick="sendChatMessage()" disabled>Send</button>
                </div>
            </div>

            <div style="font-weight:bold; font-size:0.9rem; color:#10b981;">Combat Log:</div>
            <div id="combat-log" class="combat-log">Awaiting action...</div>
        </div>
    </div>

    <script>
        const campaign = """ + json.dumps(levels) + """;
        const OLLAMA_ENDPOINT = "http://127.0.0.1:11435/api/generate";
        
        const canvas = document.getElementById("gameCanvas");
        const ctx = canvas.getContext("2d");
        
        let currentFloorIndex = 0;
        const TILE_SIZE = 40;
        const VISION_RADIUS = 3;
        
        let player = { x: 0, y: 0, hp: 100, maxHp: 100, atk: 15 };
        let grid = [];
        let exploredGrid = [];
        let cols = 10, rows = 10;
        let activeNpcPersona = null;

        function logMessage(msg) {
            const log = document.getElementById("combat-log");
            log.innerHTML += `> ${msg}<br>`;
            log.scrollTop = log.scrollHeight;
        }

        function appendChat(speaker, text) {
            const history = document.getElementById("chat-history");
            history.innerHTML += `<b>${speaker}:</b> ${text}<br>`;
            history.scrollTop = history.scrollHeight;
        }

        function loadFloor(index) {
            if (index >= campaign.length) {
                alert("CONGRATULATIONS! You defeated the campaign!");
                currentFloorIndex = 0;
                player.hp = 100;
                loadFloor(0);
                return;
            }
            
            const level = campaign[index];
            cols = level.grid_size[0];
            rows = level.grid_size[1];
            
            canvas.width = cols * TILE_SIZE;
            canvas.height = rows * TILE_SIZE;
            
            grid = Array(rows).fill().map(() => Array(cols).fill("floor"));
            exploredGrid = Array(rows).fill().map(() => Array(cols).fill(false));
            
            (level.objects || []).forEach(obj => {
                if (obj.x >= 0 && obj.x < cols && obj.y >= 0 && obj.y < rows) {
                    grid[obj.y][obj.x] = obj.type;
                    
                    if (obj.type === "spawn") {
                        player.x = obj.x;
                        player.y = obj.y;
                    }
                }
            });

            // Set up NPC Chat Persona
            const nar = level.narrative || {};
            const npc = nar.npc_dialogue || {};
            activeNpcPersona = {
                name: npc.npc_name || "Dungeon Spirit",
                lore: nar.floor_lore || "A mysterious dark cavern.",
                greeting: npc.quote || "Beware of what lurks in the shadows."
            };

            document.getElementById("floor-title").innerText = `Floor ${index + 1}: ${level.level_name}`;
            document.getElementById("player-hp").innerText = player.hp;
            document.getElementById("chat-header").innerText = `💬 Chat with ${activeNpcPersona.name}`;
            
            // Enable Chat Input
            document.getElementById("chat-input").disabled = false;
            document.getElementById("send-btn").disabled = false;
            
            document.getElementById("chat-history").innerHTML = "";
            appendChat(activeNpcPersona.name, activeNpcPersona.greeting);
            
            logMessage(`<span style="color:#e5b25d">Entered Floor ${index + 1}: ${level.level_name}</span>`);
            drawFrame();
        }

        // --- REAL-TIME OLLAMA API CALL ---
        async function sendChatMessage() {
            const inputEl = document.getElementById("chat-input");
            const userMsg = inputEl.value.trim();
            if (!userMsg) return;

            appendChat("Player", userMsg);
            inputEl.value = "";

            const systemPrompt = `You are an NPC named ${activeNpcPersona.name} located in a dark dungeon floor. Lore context: ${activeNpcPersona.lore}. Respond in 1-2 concise, atmospheric sentences. Stay strictly in character!`;

            try {
                const response = await fetch(OLLAMA_ENDPOINT, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        model: "qwen2.5:14b",
                        system: systemPrompt,
                        prompt: userMsg,
                        stream: false,
                        options: { temperature: 0.7 }
                    })
                });

                if (!response.ok) throw new Error("Ollama endpoint unreachable");
                const data = await response.json();
                appendChat(activeNpcPersona.name, data.response || "...");
            } catch (err) {
                appendChat("System", "<span style="color:#ef4444">Failed to reach local Ollama on port 11435. Is Ollama running?</span>");
            }
        }

        // Allow pressing Enter in chat input
        document.getElementById("chat-input").addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendChatMessage();
        });

        function resolveCombat(enemyX, enemyY) {
            const level = campaign[currentFloorIndex];
            const enemyList = level.mechanics?.enemies || [{ name: "Skeletal Warrior", hp: 30, damage: 8 }];
            
            const enemyTemplate = enemyList[Math.floor(Math.random() * enemyList.length)];
            let enemyHp = enemyTemplate.hp;
            const enemyDmg = enemyTemplate.damage;
            const enemyName = enemyTemplate.name;

            logMessage(`<span style="color:#ef4444"><b>COMBAT!</b> ${enemyName} (HP: ${enemyHp}, DMG: ${enemyDmg})</span>`);

            while (enemyHp > 0 && player.hp > 0) {
                enemyHp -= player.atk;
                logMessage(`You strike for ${player.atk} dmg! (${Math.max(0, enemyHp)} enemy HP)`);

                if (enemyHp <= 0) {
                    logMessage(`<span style="color:#10b981">Defeated ${enemyName}!</span>`);
                    grid[enemyY][enemyX] = "floor";
                    break;
                }

                player.hp -= enemyDmg;
                document.getElementById("player-hp").innerText = Math.max(0, player.hp);
                logMessage(`<span style="color:#f87171">${enemyName} hits for ${enemyDmg} dmg!</span>`);

                if (player.hp <= 0) {
                    alert("You were slain! Restarting floor...");
                    player.hp = player.maxHp;
                    loadFloor(currentFloorIndex);
                    return false;
                }
            }
            return true;
        }

        window.addEventListener("keydown", (e) => {
            // Disable key movement if user is typing in chat input
            if (document.activeElement === document.getElementById("chat-input")) return;
            if (player.hp <= 0) return;

            let nextX = player.x;
            let nextY = player.y;

            if (e.key === "ArrowUp" || e.key === "w") nextY--;
            if (e.key === "ArrowDown" || e.key === "s") nextY++;
            if (e.key === "ArrowLeft" || e.key === "a") nextX--;
            if (e.key === "ArrowRight" || e.key === "d") nextX++;

            if (nextX < 0 || nextX >= cols || nextY < 0 || nextY >= rows) return;

            const targetTile = grid[nextY][nextX];
            if (targetTile === "wall") return; 

            if (targetTile === "enemy") {
                const won = resolveCombat(nextX, nextY);
                if (!won) return;
            }

            player.x = nextX;
            player.y = nextY;

            if (targetTile === "exit") {
                currentFloorIndex++;
                loadFloor(currentFloorIndex);
                return;
            }
            
            if (targetTile === "chest") {
                grid[nextY][nextX] = "floor";
                player.hp = Math.min(player.maxHp, player.hp + 20);
                document.getElementById("player-hp").innerText = player.hp;
                logMessage(`<span style="color:#f59e0b">Opened chest! Healed +20 HP!</span>`);
            }

            drawFrame();
        });

        function drawFrame() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            for (let y = 0; y < rows; y++) {
                for (let x = 0; x < cols; x++) {
                    const dist = Math.hypot(x - player.x, y - player.y);
                    const isCurrentlyVisible = dist <= VISION_RADIUS;

                    if (isCurrentlyVisible) exploredGrid[y][x] = true;
                    const isExplored = exploredGrid[y][x];

                    if (!isExplored) {
                        ctx.fillStyle = "#000000";
                        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
                        continue;
                    }

                    const tile = grid[y][x];
                    
                    if (isCurrentlyVisible) {
                        ctx.fillStyle = "#1e293b";
                        if (tile === "wall") ctx.fillStyle = "#334155";
                        else if (tile === "spawn") ctx.fillStyle = "#064e3b";
                        else if (tile === "exit") ctx.fillStyle = "#7f1d1d";
                    } else {
                        ctx.fillStyle = "#0f172a";
                        if (tile === "wall") ctx.fillStyle = "#1e293b";
                        else if (tile === "spawn") ctx.fillStyle = "#022c22";
                        else if (tile === "exit") ctx.fillStyle = "#450a0a";
                    }
                    
                    ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
                    
                    if (isCurrentlyVisible) {
                        if (tile === "enemy") {
                            ctx.fillStyle = "#7c3aed";
                            ctx.beginPath();
                            ctx.arc(x * TILE_SIZE + TILE_SIZE/2, y * TILE_SIZE + TILE_SIZE/2, TILE_SIZE/3, 0, Math.PI*2);
                            ctx.fill();
                        }
                        if (tile === "chest") {
                            ctx.fillStyle = "#d97706";
                            ctx.fillRect(x * TILE_SIZE + 8, y * TILE_SIZE + 12, TILE_SIZE - 16, TILE_SIZE - 20);
                        }
                    }
                }
            }
            
            // Draw Player
            ctx.fillStyle = "#06b6d4";
            ctx.fillRect(player.x * TILE_SIZE + 4, player.y * TILE_SIZE + 4, TILE_SIZE - 8, TILE_SIZE - 8);
        }

        if (campaign.length > 0) loadFloor(0);
    </script>
</body>
</html>
"""

with open("playable_dungeon.html", "w") as f:
    f.write(html_content)

print("Live AI Dialogue Engine Compiled: Updated playable_dungeon.html")
