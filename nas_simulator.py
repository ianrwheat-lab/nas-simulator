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
    def __init__(self, name, bead_threshold, capacity=None, is_pretower=False):
        self.name = name
        self.capacity = 0
        self.dice_rolls = []
        self.queue = deque()
        self.bead_threshold = bead_threshold
        self.max_capacity = capacity  # Used for Towers
        self.is_pretower = is_pretower

    def roll_capacity(self, dice_count=1):
        # Pre-queues and towers don't roll dice
        if self.is_pretower or self.max_capacity is not None:
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
        if not self.queue or self.is_pretower:
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
        # Pre-queues do not self-release; handled in Phase 3B
        if self.is_pretower:
            return

        for aircraft in list(self.queue):
            if aircraft.status == "Ready to Move":
                # Towers enforce max_capacity
                if self.max_capacity is not None:
                    if len(self.queue) > self.max_capacity:
                        continue
                self.queue.remove(aircraft)
                aircraft.beads = 0
                if aircraft.route:
                    aircraft.route.pop(0)

                if aircraft.route:
                    next_stop = aircraft.route[0]
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
        # Towers (capacity=2)
        'Tower_A': Node('Tower_A', 3, capacity=2),
        'Tower_B': Node('Tower_B', 3, capacity=2),
        'Tower_C': Node('Tower_C', 3, capacity=2),
        'Tower_D': Node('Tower_D', 3, capacity=2),
        # Pre-Tower Queues
        'PreTowerArr_A': Node('PreTowerArr_A', 0, is_pretower=True),
        'PreTowerDep_A': Node('PreTowerDep_A', 0, is_pretower=True),
        'PreTowerArr_B': Node('PreTowerArr_B', 0, is_pretower=True),
        'PreTowerDep_B': Node('PreTowerDep_B', 0, is_pretower=True),
        'PreTowerArr_C': Node('PreTowerArr_C', 0, is_pretower=True),
        'PreTowerDep_C': Node('PreTowerDep_C', 0, is_pretower=True),
        'PreTowerArr_D': Node('PreTowerArr_D', 0, is_pretower=True),
        'PreTowerDep_D': Node('PreTowerDep_D', 0, is_pretower=True),
        # Other Nodes
        'TRACON_N': Node('TRACON_N', 2),
        'TRACON_S': Node('TRACON_S', 2),
        'CENTER': Node('CENTER', 2),
        'A': Node('A', 0),
        'B': Node('B', 0),
        'C': Node('C', 0),
        'D': Node('D', 0),
    }
    return nodes

def generate_route(origin, destination):
    tower_origin = f"Tower_{origin}"
    tower_dest = f"Tower_{destination}"
    predep_origin = f"PreTowerDep_{origin}"
    prearr_dest = f"PreTowerArr_{destination}"

    if origin in ['A', 'B']:
        tracon_out = "TRACON_S"
        tracon_in = "TRACON_N"
    else:
        tracon_out = "TRACON_N"
        tracon_in = "TRACON_S"

    return [predep_origin, tower_origin, tracon_out, "CENTER", tracon_in, prearr_dest, tower_dest, destination]

def get_destination_from_roll(origin, roll):
    if origin in ['A', 'B']:
        return 'C' if roll <= 3 else 'D'
    elif origin in ['C', 'D']:
        return 'A' if roll <= 3 else 'B'
    else:
        raise ValueError(f"Invalid origin gate: {origin}")

# -----------------------------
# Phase 3 Movement Refinement
# -----------------------------
def move_phase(nodes):
    # Step 3A: normal releases
    for node in nodes.values():
        node.move_ready_aircraft(nodes)

    # Step 3B: refill towers from pre-queues
    for tower in ['A', 'B', 'C', 'D']:
        tower_node = nodes[f'Tower_{tower}']
        arr_q = nodes[f'PreTowerArr_{tower}']
        dep_q = nodes[f'PreTowerDep_{tower}']

        while len(tower_node.queue) < tower_node.max_capacity:
            if arr_q.queue:
                ac = arr_q.queue.popleft()
                ac.location = tower_node.name
                tower_node.queue.append(ac)
            elif dep_q.queue:
                ac = dep_q.queue.popleft()
                ac.location = tower_node.name
                tower_node.queue.append(ac)
            else:
                break

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
        # Roll all node capacities
        for name, node in nodes.items():
            node.roll_capacity(2 if 'TRACON' in name or name == 'CENTER' else 1)

        # Spawn aircraft
        for gate in ['A','B','C','D']:
            if nodes[gate].dice_rolls:
                spawn_roll = nodes[gate].dice_rolls[0]
                destination = get_destination_from_roll(gate, spawn_roll)
                route = generate_route(gate, destination)
                ac = Aircraft(aircraft_id, gate, destination, route, spawn_roll)
                nodes[route[0]].queue.append(ac)  # enters PreTowerDep first
                aircraft_list.append(ac)
                aircraft_id += 1

    elif phase == 2:
        for node in nodes.values():
            node.assign_beads()

    elif phase == 3:
        move_phase(nodes)  # refined Step 3A + 3B
        st.session_state.step += 1

    st.session_state.phase = 1 if st.session_state.phase == 3 else st.session_state.phase + 1
    st.session_state.aircraft_id = aircraft_id

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🛫 NAS Bead & Bowl Simulator - Pre-Tower Queues Edition")

st.markdown("""
### Simulation Flow
1. **🎲 Roll Dice** (spawn + capacities)  
2. **💎 Distribute Beads**  
3. **✈️ Move Aircraft**  
   - Step 3A: free capacity  
   - Step 3B: refill towers from Pre-Queues (Arrivals > Departures)  
""")

st.write(f"**Current Step:** {st.session_state.step} | **Phase:** {st.session_state.phase}")

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
        "Penalized": (len(node.queue) >= 3 and not node.is_pretower),
        "Dice Roll(s)": node.dice_rolls,
        "Total Capacity": node.capacity if not node.is_pretower else "N/A",
        "Max Capacity": node.max_capacity if node.max_capacity else "∞"
    })

st.markdown("### 📊 Node Status Overview")
st.dataframe(pd.DataFrame(node_status), use_container_width=True)
