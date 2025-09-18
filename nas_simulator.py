import streamlit as st
import random
from collections import deque
import pandas as pd

# -----------------------------
# Aircraft Class
# -----------------------------
class Aircraft:
    def __init__(self, id, origin, destination, route, spawn_roll):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.route = route
        self.location = route[0] if route else destination
        self.beads = 0
        self.status = "In System"
        self.spawn_roll = spawn_roll

    def to_dict(self):
        return {
            "Aircraft ID": self.id,
            "Origin": self.origin,
            "Destination": self.destination,
            "Location": self.location,
            "Beads": self.beads,
            "Status": self.status,
            "Next Stop": self.route[1] if len(self.route) > 1 else "Arrived",
            "Spawn Roll": self.spawn_roll,
        }

# -----------------------------
# Node Class
# -----------------------------
class Node:
    def __init__(self, name, bead_threshold, is_tower=False, is_queue=False, queue_type=None):
        self.name = name
        self.capacity = 0
        self.dice_rolls = []
        self.queue = deque()
        self.bead_threshold = bead_threshold
        self.is_tower = is_tower
        self.is_queue = is_queue
        self.queue_type = queue_type  # "arrival" or "departure"

    def roll_capacity(self, dice_count=1):
        if self.is_queue:
            return
        penalty_dice = [1, 2, 3, 4, 4, 4]
        self.dice_rolls = []
        for _ in range(dice_count):
            if len(self.queue) >= 3:
                self.dice_rolls.append(random.choice(penalty_dice))
            else:
                self.dice_rolls.append(random.randint(1, 6))
        self.capacity = sum(self.dice_rolls)

    def assign_beads(self):
        if self.is_queue:
            return
        if not self.queue:
            return

        while self.capacity > 0:
            all_filled = True
            for aircraft in self.queue:
                if aircraft.beads < self.bead_threshold:
                    aircraft.beads += 1
                    self.capacity -= 1
                    all_filled = False
                    if self.capacity == 0:
                        break
            if all_filled:
                break

        for aircraft in self.queue:
            if aircraft.beads >= self.bead_threshold:
                aircraft.status = "Ready to Move"

    def move_ready_aircraft(self, node_map):
        if self.is_tower or self.is_queue:
            return

        for aircraft in list(self.queue):
            if aircraft.status == "Ready to Move":
                self.queue.remove(aircraft)
                aircraft.beads = 0
                if aircraft.route:
                    aircraft.route.pop(0)

                if aircraft.route:
                    next_stop = aircraft.route[0]
                    if node_map[next_stop].is_tower and len(node_map[next_stop].queue) < 2:
                        aircraft.location = next_stop
                        aircraft.status = "In System"
                        node_map[next_stop].queue.append(aircraft)
                    elif node_map[next_stop].is_tower:
                        queue_name = f"PreTowerArr_{next_stop[-1]}" if "TRACON" in self.name else f"PreTowerDep_{next_stop[-1]}"
                        aircraft.location = queue_name
                        aircraft.status = "In System"
                        node_map[queue_name].queue.append(aircraft)
                    else:
                        aircraft.location = next_stop
                        aircraft.status = "In System"
                        node_map[next_stop].queue.append(aircraft)
                else:
                    aircraft.location = aircraft.destination
                    aircraft.status = "Arrived"
                    node_map[aircraft.destination].queue.append(aircraft)

# -----------------------------
# Initialization
# -----------------------------
def initialize_simulation():
    nodes = {
        'Tower_A': Node('Tower_A', 3, is_tower=True),
        'Tower_B': Node('Tower_B', 3, is_tower=True),
        'Tower_C': Node('Tower_C', 3, is_tower=True),
        'Tower_D': Node('Tower_D', 3, is_tower=True),
        'TRACON_N': Node('TRACON_N', 2),
        'TRACON_S': Node('TRACON_S', 2),
        'CENTER': Node('CENTER', 2),
        'A': Node('A', 0),
        'B': Node('B', 0),
        'C': Node('C', 0),
        'D': Node('D', 0),
        # PreTower queues
        'PreTowerArr_A': Node('PreTowerArr_A', 0, is_queue=True, queue_type="arrival"),
        'PreTowerDep_A': Node('PreTowerDep_A', 0, is_queue=True, queue_type="departure"),
        'PreTowerArr_B': Node('PreTowerArr_B', 0, is_queue=True, queue_type="arrival"),
        'PreTowerDep_B': Node('PreTowerDep_B', 0, is_queue=True, queue_type="departure"),
        'PreTowerArr_C': Node('PreTowerArr_C', 0, is_queue=True, queue_type="arrival"),
        'PreTowerDep_C': Node('PreTowerDep_C', 0, is_queue=True, queue_type="departure"),
        'PreTowerArr_D': Node('PreTowerArr_D', 0, is_queue=True, queue_type="arrival"),
        'PreTowerDep_D': Node('PreTowerDep_D', 0, is_queue=True, queue_type="departure"),
    }
    return nodes

def generate_route(origin, destination):
    tower_origin = f"Tower_{origin}"
    tower_dest = f"Tower_{destination}"
    if origin in ['A', 'B']:
        tracon_out = "TRACON_S"
        tracon_in = "TRACON_N"
    else:
        tracon_out = "TRACON_N"
        tracon_in = "TRACON_S"
    return [f"PreTowerDep_{origin}", tower_origin, tracon_out, "CENTER", tracon_in, f"PreTowerArr_{destination}", tower_dest, destination]

def get_destination_from_roll(origin, roll):
    if origin in ['A', 'B']:
        return 'C' if roll <= 3 else 'D'
    elif origin in ['C', 'D']:
        return 'A' if roll <= 3 else 'B'
    else:
        raise ValueError(f"Invalid origin gate: {origin}")

# -----------------------------
# Streamlit State Initialization
# -----------------------------
if 'nodes' not in st.session_state:
    st.session_state.nodes = initialize_simulation()
    st.session_state.aircraft_list = []
    st.session_state.aircraft_id = 1
    st.session_state.step = 1
    st.session_state.phase = 1  # 1 = Roll, 2 = Beads, 3 = Move

# -----------------------------
# Sub-Step Execution
# -----------------------------
def run_substep():
    nodes = st.session_state.nodes
    aircraft_list = st.session_state.aircraft_list
    aircraft_id = st.session_state.aircraft_id
    step = st.session_state.step
    phase = st.session_state.phase

    if phase == 1:
        for name, node in nodes.items():
            node.roll_capacity(2 if 'TRACON' in name or name == 'CENTER' else 1)

        for gate in ['A','B','C','D']:
            if nodes[gate].dice_rolls:
                spawn_roll = nodes[gate].dice_rolls[0]
                destination = get_destination_from_roll(gate, spawn_roll)
                route = generate_route(gate, destination)
                ac = Aircraft(aircraft_id, gate, destination, route, spawn_roll)
                nodes[route[0]].queue.append(ac)
                aircraft_list.append(ac)
                aircraft_id += 1

    elif phase == 2:
        for node in nodes.values():
            node.assign_beads()

    elif phase == 3:
        # Step 3A – free capacity
        for node in nodes.values():
            node.move_ready_aircraft(nodes)

        # Step 3B – refill towers from pre-queues
        for tower in ['Tower_A', 'Tower_B', 'Tower_C', 'Tower_D']:
            while len(nodes[tower].queue) < 2:
                arr_queue = nodes[f"PreTowerArr_{tower[-1]}"]
                dep_queue = nodes[f"PreTowerDep_{tower[-1]}"]
                moved = False
                if arr_queue.queue:
                    ac = arr_queue.queue.popleft()
                    ac.location = tower
                    ac.status = "In System"
                    nodes[tower].queue.append(ac)
                    moved = True
                elif dep_queue.queue:
                    ac = dep_queue.queue.popleft()
                    ac.location = tower
                    ac.status = "In System"
                    nodes[tower].queue.append(ac)
                    moved = True
                if not moved:
                    break

        st.session_state.step += 1

    st.session_state.phase = 1 if st.session_state.phase == 3 else st.session_state.phase + 1
    st.session_state.aircraft_id = aircraft_id

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🛫 NAS Bead & Bowl Simulator - 3 Phase Mode with Pre-Tower Queues")

st.markdown("""
Each turn now breaks into **three sub-steps**:

1. **🎲 Roll Dice** for each node (and spawn aircraft)
2. **💎 Distribute Beads** based on dice
3. **✈️ Move Aircraft**  
   - Step 3A: Free capacity (aircraft leave towers and other nodes)  
   - Step 3B: Fill towers from PreTower queues (Arrivals prioritized over Departures)

🚨 Towers max capacity = **2 aircraft**  
🚨 Nodes with **3+ aircraft** are penalized with reduced dice values (1,2,3,4,4,4)
""")

st.write(f"**Current Step:** {st.session_state.step}  |  **Phase:** {st.session_state.phase} (1=Roll, 2=Beads, 3=Move)")

if st.button("Run Next Sub-Step"):
    run_substep()

results = [ac.to_dict() for ac in st.session_state.aircraft_list]
df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)

# -----------------------------
# Node Status Table
# -----------------------------
node_status = []
for name, node in st.session_state.nodes.items():
    node_status.append({
        "Node": name,
        "Aircraft Count": len(node.queue),
        "Penalized": (not node.is_queue) and len(node.queue) >= 3,
        "Dice Roll(s)": str(node.dice_rolls) if not node.is_queue else "N/A",
        "Total Capacity": node.capacity if not node.is_queue else "N/A"
    })

st.markdown("### 📊 Node Status Overview")

# Convert to DataFrame
df_status = pd.DataFrame(node_status)

# Optional: highlight towers at full capacity
def highlight_full(val, node_name):
    if "Tower" in node_name and val == 2:
        return "background-color: salmon; color: white"
    return ""

styled_df = df_status.style.apply(
    lambda row: [highlight_full(row["Aircraft Count"], row["Node"]) for _ in row],
    axis=1
)

st.dataframe(styled_df, use_container_width=True)
