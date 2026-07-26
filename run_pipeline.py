import os
import json
import requests
import heapq
from typing import List, Tuple, Optional
from pydantic import BaseModel

class EnemyStat(BaseModel):
    name: str
    hp: int
    damage: int
    speed: float

class GameMechanics(BaseModel):
    game_title: str
    theme: str
    player_hp: int
    enemies: List[EnemyStat]
    loot_drop_chance: float

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11435/api/generate")
MODEL_NAME = os.getenv("DEFAULT_MODEL", "qwen2.5:14b")

def query_agent(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "system": system_prompt,
        "prompt": user_prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2}
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to reach Ollama at {OLLAMA_URL}: {e}")
        return ""

def clean_json_string(raw_str: str) -> str:
    cleaned = raw_str.strip()
    if "```" in cleaned:
        lines_list = cleaned.splitlines()
        json_lines = []
        in_block = False
        for line in lines_list:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                json_lines.append(line)
        cleaned = "\n".join(json_lines)
    return cleaned.strip()

# --- 1. SYSTEMS AGENT ---
def run_systems_agent(concept: str, floor_num: int) -> dict:
    system_prompt = (
        "You are an expert Game Systems Designer. Generate game mechanics in strictly valid JSON format matching: "
        "{\"game_title\": \"str\", \"theme\": \"str\", \"player_hp\": 100, \"enemies\": [{\"name\": \"str\", \"hp\": 50, \"damage\": 10, \"speed\": 1.5}], \"loot_drop_chance\": 0.25}. "
        f"IMPORTANT: This is Floor {floor_num}/5. Scale enemy HP and damage appropriately for this floor depth."
    )
    raw_output = query_agent(system_prompt, f"Campaign Concept: {concept}, Depth Level: {floor_num}")
    cleaned = clean_json_string(raw_output)
    return json.loads(cleaned) if cleaned else {}

# --- 2. LEVEL ARCHITECT ---
def run_level_agent(mechanics: dict, floor_num: int, grid_dim: int, feedback: str = "") -> dict:
    system_prompt = (
        f"You are a Level Architect designing Floor {floor_num} of a dungeon campaign. "
        f"Design a strictly valid JSON level layout using a {grid_dim}x{grid_dim} grid size matching: "
        "{\"level_name\": \"str\", \"grid_size\": [" + str(grid_dim) + ", " + str(grid_dim) + "], \"objects\": [{\"type\": \"spawn\", \"x\": 0, \"y\": 0}]}. "
        "Allowed types: spawn, exit, enemy, chest, wall. "
        f"Must include 1 spawn, 1 exit, and several walls, enemies, and chests suited for a {grid_dim}x{grid_dim} floor."
    )
    user_prompt = f"Floor {floor_num} Mechanics: {json.dumps(mechanics)}"
    if feedback:
        user_prompt += f"\n\n[CRITICAL PREVIOUS FAILURE]: {feedback}\nFix placement and regenerate valid JSON."

    raw_output = query_agent(system_prompt, user_prompt)
    cleaned = clean_json_string(raw_output)
    return json.loads(cleaned) if cleaned else {}

# --- 3. NARRATIVE AGENT ---
def run_narrative_agent(mechanics: dict, level_layout: dict, floor_num: int) -> dict:
    system_prompt = (
        "You are an expert Game Narrative Designer. Generate story lore and dialogue in strictly valid JSON format matching: "
        "{\"floor_lore\": \"str\", \"npc_dialogue\": {\"npc_name\": \"str\", \"quote\": \"str\"}, \"boss_intro\": \"str\"}. "
        f"Tailor the narrative style to Floor {floor_num}/5 of the campaign."
    )
    context = {
        "floor": floor_num,
        "theme": mechanics.get("theme", "Dark Dungeon"),
        "level_name": level_layout.get("level_name", f"Floor {floor_num}"),
        "enemy_types": [e.get("name") for e in mechanics.get("enemies", [])]
    }
    raw_output = query_agent(system_prompt, f"Narrative Context: {json.dumps(context)}")
    cleaned = clean_json_string(raw_output)
    return json.loads(cleaned) if cleaned else {}

# --- 4. A* PATHFINDING ALGORITHM ---
def a_star_search(grid_size: Tuple[int, int], walls: set, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    width, height = grid_size
    def heuristic(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}

    while open_set:
        current = heapq.heappop(open_set)[1]
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        neighbors = [(current[0]+1, current[1]), (current[0]-1, current[1]), (current[0], current[1]+1), (current[0], current[1]-1)]
        for nx, ny in neighbors:
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in walls:
                tentative_g = g_score[current] + 1
                if (nx, ny) not in g_score or tentative_g < g_score[(nx, ny)]:
                    came_from[(nx, ny)] = current
                    g_score[(nx, ny)] = tentative_g
                    heapq.heappush(open_set, (tentative_g + heuristic((nx, ny), goal), (nx, ny)))
    return None

# --- 5. DYNAMIC QA VALIDATION ---
def validate_level(level_data: dict, grid_dim: int) -> tuple[bool, str]:
    objects = level_data.get("objects", [])
    if not objects: return False, "No objects generated in layout."
    
    spawn, exit_pos = None, None
    walls = set()

    for obj in objects:
        obj_type = obj.get("type")
        x, y = obj.get("x", -1), obj.get("y", -1)
        if x < 0 or x >= grid_dim or y < 0 or y >= grid_dim:
            return False, f"Object {obj} placed outside {grid_dim}x{grid_dim} bounds."
            
        if obj_type == "spawn": spawn = (x, y)
        elif obj_type == "exit": exit_pos = (x, y)
        elif obj_type == "wall": walls.add((x, y))

    if not spawn: return False, "Missing spawn point."
    if not exit_pos: return False, "Missing exit point."

    path = a_star_search((grid_dim, grid_dim), walls, spawn, exit_pos)
    if not path:
        return False, f"Path blocked! No open route between spawn {spawn} and exit {exit_pos}."

    return True, f"Valid! Path length: {len(path)-1} steps on a {grid_dim}x{grid_dim} floor."

# --- 6. CAMPAIGN PIPELINE EXECUTION ---
if __name__ == "__main__":
    concept = "A dark fantasy dungeon crawler featuring skeletal warriors and cursed chest loot."
    print("=== STARTING MULTI-AGENT CAMPAIGN GENERATOR (WITH NARRATIVE CREW) ===")
    print(f"Target Endpoint: {OLLAMA_URL} | Model: {MODEL_NAME}\n")

    grid_configs = {1: 8, 2: 8, 3: 10, 4: 12, 5: 12}
    MAX_ATTEMPTS = 3

    for floor in range(1, 6):
        grid_dim = grid_configs[floor]
        print(f"--- GENERATING FLOOR {floor}/5 ({grid_dim}x{grid_dim} Grid) ---")
        
        # 1. Systems Agent
        mechanics = run_systems_agent(concept, floor)
        if not mechanics:
            print(f"Aborting: Systems Agent failed on Floor {floor}.")
            break

        # 2. Level Architect with QA Loop
        feedback = ""
        floor_valid = False
        final_level = {}

        for attempt in range(1, MAX_ATTEMPTS + 1):
            level = run_level_agent(mechanics, floor, grid_dim, feedback=feedback)
            if not level: continue

            valid, message = validate_level(level, grid_dim)
            if valid:
                floor_valid = True
                final_level = level
                print(f"Floor {floor} Passed Level QA (Attempt {attempt}): {message}")
                break
            else:
                print(f"Floor {floor} Level QA Retry (Attempt {attempt}): {message}")
                feedback = message

        if not floor_valid:
            print(f"Failed to generate layout for Floor {floor}.")
            break

        # 3. Narrative Agent
        print(f"Generating narrative and dialogue for Floor {floor}...")
        narrative = run_narrative_agent(mechanics, final_level, floor)
        
        # Merge mechanics and narrative directly into final output JSON
        final_level["mechanics"] = mechanics
        final_level["narrative"] = narrative

        filename = f"level_0{floor}.json"
        with open(filename, "w") as f:
            json.dump(final_level, f, indent=2)
        print(f"Successfully saved {filename} with narrative & lore!\n")

    print("=== CAMPAIGN GENERATION COMPLETE ===")
