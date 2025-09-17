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
    def __init__(self, name, bead_threshold, max_queue=None):
        self.name = name
        self.capacity = 0
        self.dice_rolls = []
        self.queue = deque()
        self.bead_threshold = bead_threshold
        self.max_queue = max_queue  # For Towers: cap their queue length

    def roll_capacity(self, dice_count=1):
        self.dice_rolls = [random.randint(1, 6) for _ in range(dice_count)]
        self.capacity = sum(self.dice_rolls)

    def assign_beads(self):
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
        if not self.queue:
            return

        # Snapshot of ready aircraft (avoid churn while iterating)
        ready = [ac for ac in list(self.queue) if ac.status == "Ready to Move"]

        for aircraft in ready:
            # Must have a route and current node should match
            if not aircraft.route or aircraft.route[0] != self.name:
                continue

            # --- Special handling for PreTower_* nodes ---
            if self.name.startswith("PreTower_"):
                # Expect the next hop to be the matched Tower_* (route[1])
                if len(aircraft.route) < 2:
                    continue  # nowhere to go

                next_stop = aircraft.route[1]

                # PreTower should only feed Tower; enforce capacity
                if next_stop.startswith("Tower_"):
                    tower_node = node_map[next_stop]
                    max_q = tower_node.max_queue if tower_node.max_queue is not None else float("inf")
                    if len(tower_node.queue) < max_q:
                        # Move into Tower now (only now pop route)
                        self.queue.remove(aircraft)
                        aircraft.beads = 0
                        aircraft.route.pop(0)  # remove current PreTower_*
                        aircraft.location = next_stop
                        aircraft.status = "In System"
                        tower_node.queue.append(aircraft)
                    else:
                        # Tower full → hold in PreTower (do not pop route)
                        continue
                else:
                    # Defensive: PreTower should only feed a Tower
                    continue

            # --- General case for all other nodes ---
            else:
                # If there's no next hop, we're effectively arriving
                if len(aircraft.route) < 2:
                    self.queue.remove(aircraft)
                    aircraft.beads = 0
                    aircraft.route.pop(0)  # remove current node
                    aircraft.location = aircraft.destination
                    aircraft.status = "Arrived"
                    node_map[aircraft.destination].queue.append(aircraft)
                    continue

                next_stop = aircraft.route[1]

                # If next is a Tower with a queue cap, enforce it
                if next_stop.startswith("Tower_"):
                    tower_node = node_map[next_stop]
                    max_q = tower_node.max_queue if tower_node.max_queue is not None else float("inf")
                    if len(tower_node.queue) >= max_q:
                        # Blocked by Tower capacity → hold here; do not pop route
                        continue

                # Move forward (now safe to pop)
                self.queue.remove(aircraft)
                aircraft.beads = 0
                aircraft.route.pop(0)  # remove current node
                aircraft.location = next_stop
                aircraft.status = "In System"
                node_map[next_stop].queue.append(aircraft)

# -----------------------------
# Initialization
# -----------------------------
def initialize_simulation():
    nodes = {
        # Towers: bead_threshold=3, queue cap=2
        'Tower_A': Node('Tower_A', 3, max_queue=2),
        'Tower_B': Node('Tower_B', 3, max_queue=2),
        'Tower_C': Node('Tower_C', 3, max_queue=2),
        'Tower_D': Node('Tower_D', 3, max_queue=2),

        # PreTower holding queues (FIFO, no beads, uncapped)
        'PreTower_A': Node('PreTower_A', 0),
        'PreTower_B': Node('PreTower_B', 0),
        'PreTower_C': Node('PreTower_C', 0),
        'PreTower_D': Node('PreTower_D', 0),

        # Enroute facilities
        'TRACON_N': Node('TRACON_N', 2),
        'TRACON_S': Node('TRACON_S', 2),
        'CENTER': Node('CENTER', 2),

        # Gates (used for spawning & final arrival only)
        'A': Node('A', 0),
        'B': Node('B', 0),
        'C': Node('C', 0),
        'D': Node('D', 0),
    }
    return nodes

def generate_route(origin, destination):
    pre_tower_origin = f"PreTower_{origin}"
    tower_origin = f"Tower_{origin}"
    tower_dest = f"Tower_{destination}"
    pre_tower_dest = f"PreTower_{destination}"

    if origin in ['A', 'B']:
        tracon_out = "TRACON_S"
        tracon_in = "TRACON_N"
    else:
        tracon_out = "TRACON_N"
        tracon_in = "TRACON_S"

    # Gate → PreTower(origin) → Tower(origin) → TRACON_out → CENTER → TRACON_in
    # → PreTower(dest) → Tower(dest) → Gate(dest)
    return [pre_tower_origin, tower_origin, tracon_out, "CENTER", tracon_in, pre_tower_dest, tower_dest, destination]

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
        # Roll capacities
        for name, node in nodes.items():
            node.roll_capacity(2 if 'TRACON' in name or name == 'CENTER' else 1)

        # Spawn aircraft from Gate to PreTower
        for gate in ['A','B','C','D']:
            if nodes[gate].dice_rolls:
                spawn_roll = nodes[gate].dice_rolls[0]
                destination = get_destination_from_roll(gate, spawn_roll)
                route = generate_route(gate, destination)
                ac = Aircraft(aircraft_id, gate, destination, route, spawn_roll)
                nodes[route[0]].queue.append(ac)  # into PreTower_*
                aircraft_list.append(ac)
                aircraft_id += 1

    elif phase == 2:
        # Assign beads everywhere (PreTower bead_threshold=0 -> Ready each cycle)
        for node in nodes.values():
            node.assign_beads()

    elif phase == 3:
        # Two-pass move: free capacity first, then let PreTowers feed Towers
        # Pass 1: move everything except PreTower_*
        for name, node in nodes.items():
            if not name.startswith("PreTower_"):
                node.move_ready_aircraft(nodes)

        # Pass 2: now move PreTower_* into Towers if space opened
        for name, node in nodes.items():
            if name.startswith("PreTower_"):
                node.move_ready_aircraft(nodes)

        st.session_state.step += 1

    # Advance phase
    st.session_state.phase = 1 if st.session_state.phase == 3 else st.session_state.phase + 1
    st.session_state.aircraft_id = aircraft_id

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🛫 NAS Bead & Bowl Simulator — PreTower Hold & Tower Cap")

st.markdown("""
**Three sub-steps per turn:**
1. **🎲 Roll Dice** for each node (and spawn aircraft)
2. **💎 Distribute Beads** based on dice
3. **✈️ Move Aircraft** (PreTowers only release to Towers if Towers have space)
""")

st.write(f"**Current Step:** {st.session_state.step}  |  **Phase:** {st.session_state.phase} (1=Roll, 2=Beads, 3=Move)")

col1, col2 = st.columns(2)
with col1:
    if st.button("Run Next Sub-Step"):
        run_substep()
with col2:
    if st.button("🔁 Reset Simulation"):
        st.session_state.clear()
        st.experimental_rerun()

# Aircraft table
results = [ac.to_dict() for ac in st.session_state.aircraft_list]
df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)

# Node status table
node_status = []
for name, node in st.session_state.nodes.items():
    node_status.append({
        "Node": name,
        "Aircraft Count": len(node.queue),
        "Dice Roll(s)": node.dice_rolls,
        "Total Capacity": node.capacity
    })

st.markdown("### 📊 Node Status Overview")
st.dataframe(pd.DataFrame(node_status), use_container_width=True)
