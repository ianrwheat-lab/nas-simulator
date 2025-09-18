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
    def __init__(self, name, bead_threshold, max_capacity=None):
        self.name = name
        self.bead_threshold = bead_threshold
        self.capacity = 0
        self.dice_rolls = []
        self.queue = deque()
        self.max_capacity = max_capacity  # Used only for Towers

    def roll_capacity(self, dice_count=1):
        if "PreTower" in self.name:
            return  # Pre-tower nodes don’t roll dice
        penalty_dice = [1, 2, 3, 4, 4, 4]
        self.dice_rolls = []
        for _ in range(dice_count):
            if len(self.queue) >= 3:
                self.dice_rolls.append(random.choice(penalty_dice))
            else:
                self.dice_rolls.append(random.randint(1, 6))
        self.capacity = sum(self.dice_rolls)

    def assign_beads(self):
        if not self.queue or "PreTower" in self.name:
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
        for aircraft in list(self.queue):
            if aircraft.status == "Ready to Move":
                next_stop = aircraft.route[1] if len(aircraft.route) > 1 else None

                # Special logic if next stop is a Tower with max capacity
                if next_stop and next_stop.startswith("Tower_"):
                    tower_node = node_map[next_stop]
                    if len(tower_node.queue) >= 2:
                        # Redirect to pre-tower holding queue
                        if aircraft.origin == aircraft.location:
                            prequeue = node_map[f"PreTowerDep_{aircraft.origin}"]
                        else:
                            prequeue = node_map[f"PreTowerArr_{aircraft.destination}"]
                        self.queue.remove(aircraft)
                        aircraft.status = "In System"
                        prequeue.queue.append(aircraft)
                        continue

                # Proceed as usual
                self.queue.remove(aircraft)
                aircraft.beads = 0
                if aircraft.route:
                    aircraft.route.pop(0)

                if aircraft.route:
                    aircraft.location = aircraft.route[0]
                    aircraft.status = "In System"
                    node_map[aircraft.location].queue.append(aircraft)
                else:
                    aircraft.location = aircraft.destination
                    aircraft.status = "Arrived"
                    node_map[aircraft.destination].queue.append(aircraft)

# -----------------------------
# Initialization
# -----------------------------
def initialize_simulation():
    nodes = {}
    for x in ['A', 'B', 'C', 'D']:
        nodes[f'PreTowerDep_{x}'] = Node(f'PreTowerDep_{x}', 0)
        nodes[f'PreTowerArr_{x}'] = Node(f'PreTowerArr_{x}', 0)
        nodes[f'Tower_{x}'] = Node(f'Tower_{x}', 3, max_capacity=2)
        nodes[x] = Node(x, 0)

    nodes['TRACON_N'] = Node('TRACON_N', 2)
    nodes['TRACON_S'] = Node('TRACON_S', 2)
    nodes['CENTER'] = Node('CENTER', 2)
    return nodes

def generate_route(origin, destination):
    tower_origin = f"Tower_{origin}"
    tower_dest = f"Tower_{destination}"
    predep = f"PreTowerDep_{origin}"
    prearr = f"PreTowerArr_{destination}"

    if origin in ['A', 'B']:
        tracon_out = "TRACON_S"
        tracon_in = "TRACON_N"
    else:
        tracon_out = "TRACON_N"
        tracon_in = "TRACON_S"

    return [predep, tower_origin, tracon_out, "CENTER", tracon_in, prearr, tower_dest, destination]

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
        # Roll all capacities
        for name, node in nodes.items():
            node.roll_capacity(2 if 'TRACON' in name or name == 'CENTER' else 1)

        # Spawn aircraft
        for gate in ['A', 'B', 'C', 'D']:
            if nodes[gate].dice_rolls:
                spawn_roll = nodes[gate].dice_rolls[0]
                destination = get_destination_from_roll(gate, spawn_roll)
                route = generate_route(gate, destination)
                ac = Aircraft(aircraft_id, gate, destination, route, spawn_roll)
                aircraft_list.append(ac)
                nodes[route[0]].queue.append(ac)
                aircraft_id += 1

    elif phase == 2:
        for node in nodes.values():
            node.assign_beads()

    elif phase == 3:
        # Step 3A – Move all "Ready to Move" aircraft
        for node in nodes.values():
            node.move_ready_aircraft(nodes)

        # Step 3B – Pull from pre-queues into towers
        for x in ['A', 'B', 'C', 'D']:
            tower = nodes[f"Tower_{x}"]
            prearr = nodes[f"PreTowerArr_{x}"]
            predep = nodes[f"PreTowerDep_{x}"]
            while len(tower.queue) < 2:
                if prearr.queue:
                    ac = prearr.queue.popleft()
                    ac.location = tower.name
                    tower.queue.append(ac)
                elif predep.queue:
                    ac = predep.queue.popleft()
                    ac.location = tower.name
                    tower.queue.append(ac)
                else:
                    break

        st.session_state.step += 1

    st.session_state.phase = 1 if st.session_state.phase == 3 else st.session_state.phase + 1
    st.session_state.aircraft_id = aircraft_id

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🛫 NAS Bead & Bowl Simulator - Enhanced Tower Queuing")

st.markdown("""
Each turn breaks into **three sub-steps**:

1. **🎲 Roll Dice** for each node (and spawn aircraft)
2. **💎 Distribute Beads** based on dice
3. **✈️ Move Aircraft** in two stages:
   - 3A: Aircraft advance if "Ready to Move"
   - 3B: Towers refill from arrival queues, then departure queues

🚨 **Tower capacity is limited to 2 aircraft.**
🚦 **Arrivals are prioritized over departures** when refilling towers.
""")

st.write(f"**Current Step:** {st.session_state.step}  |  **Phase:** {st.session_state.phase} (1=Roll, 2=Beads, 3=Move)")

if st.button("Run Next Sub-Step"):
    run_substep()

results = [ac.to_dict() for ac in st.session_state.aircraft_list]
df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)

# Node status overview
node_status = []
for name, node in st.session_state.nodes.items():
    node_status.append({
        "Node": name,
        "Aircraft Count": len(node.queue),
        "Penalized": len(node.queue) >= 3 and "PreTower" not in name,
        "Dice Roll(s)": node.dice_rolls,
        "Total Capacity": node.capacity
    })

st.markdown("### 📊 Node Status Overview")
st.dataframe(pd.DataFrame(node_status), use_container_width=True)
