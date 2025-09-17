import streamlit as st
import random
from collections import deque
import pandas as pd

# -----------------------------
# Aircraft Class
# -----------------------------
class Aircraft:
    def __init__(self, id, origin, destination, route):
        self.id = id
        self.origin = origin
        self.destination = destination
        self.route = route  # List of stages to pass through
        self.location = route[0]  # Start at first location in route
        self.beads = 0
        self.status = "In System"

    def to_dict(self):
        return {
            "Aircraft ID": self.id,
            "Origin": self.origin,
            "Destination": self.destination,
            "Location": self.location,
            "Beads": self.beads,
            "Status": self.status,
            "Next Stop": self.route[1] if len(self.route) > 1 else "Arrived",
        }

# -----------------------------
# Entity Classes
# -----------------------------
class Node:
    def __init__(self, name, bead_threshold):
        self.name = name
        self.capacity = 0
        self.queue = deque()
        self.bead_threshold = bead_threshold

    def roll_capacity(self, dice_count=1):
        self.capacity = sum(random.randint(1, 6) for _ in range(dice_count))

    def assign_beads(self):
        for aircraft in list(self.queue):
            while aircraft.beads < self.bead_threshold and self.capacity > 0:
                aircraft.beads += 1
                self.capacity -= 1
            if aircraft.beads >= self.bead_threshold:
                aircraft.status = "Ready to Move"

    def move_ready_aircraft(self, node_map):
        for aircraft in list(self.queue):
            if aircraft.status == "Ready to Move":
                self.queue.remove(aircraft)
                aircraft.beads = 0
                aircraft.route.pop(0)
                if aircraft.route:
                    next_stop = aircraft.route[0]
                    aircraft.location = next_stop
                    aircraft.status = "In System"
                    node_map[next_stop].queue.append(aircraft)
                else:
                    aircraft.location = aircraft.destination
                    aircraft.status = "Arrived"

# -----------------------------
# Initialization
# -----------------------------
def initialize_simulation():
    nodes = {
        'Tower_A': Node('Tower_A', 3),
        'Tower_B': Node('Tower_B', 3),
        'Tower_C': Node('Tower_C', 3),
        'Tower_D': Node('Tower_D', 3),
        'TRACON_N': Node('TRACON_N', 2),
        'TRACON_S': Node('TRACON_S', 2),
        'CENTER': Node('CENTER', 2),
    }
    return nodes

# -----------------------------
# Routing Logic
# -----------------------------
def generate_route(origin, destination):
    tower_origin = f"Tower_{origin}"
    tower_dest = f"Tower_{destination}"
    if origin in ['A', 'B']:
        tracon_out = "TRACON_S"
        tracon_in = "TRACON_N"
    else:
        tracon_out = "TRACON_N"
        tracon_in = "TRACON_S"
    return [tower_origin, tracon_out, "CENTER", tracon_in, tower_dest]

# -----------------------------
# Simulation State
# -----------------------------
if 'nodes' not in st.session_state:
    st.session_state.nodes = initialize_simulation()
    st.session_state.aircraft_list = []
    st.session_state.aircraft_id = 1
    st.session_state.step = 1

# -----------------------------
# Turn Logic
# -----------------------------
def run_step():
    nodes = st.session_state.nodes
    aircraft_list = st.session_state.aircraft_list
    aircraft_id = st.session_state.aircraft_id
    step = st.session_state.step

    spawn_gates = ['A', 'B'] if step % 2 == 1 else ['C', 'D']

    for gate in spawn_gates:
        roll = random.randint(1, 6)
        destination = 'C' if roll <= 3 else 'D' if gate in ['A', 'B'] else 'A' if roll <= 3 else 'B'
        route = generate_route(gate, destination)
        ac = Aircraft(aircraft_id, gate, destination, route)
        nodes[route[0]].queue.append(ac)
        aircraft_list.append(ac)
        aircraft_id += 1

    # Roll capacity and move aircraft through all nodes
    for name, node in nodes.items():
        node.roll_capacity(2 if 'TRACON' in name or name == 'CENTER' else 1)
        node.assign_beads()
        node.move_ready_aircraft(nodes)

    st.session_state.aircraft_id = aircraft_id
    st.session_state.step += 1

# -----------------------------
# Streamlit App
# -----------------------------
st.title("🛫 NAS Bead & Bowl Simulator - Gate to Gate")

st.markdown("""
Each aircraft now routes from **origin gate** to **destination gate**:

- **Towers** need 3 beads
- **TRACONs/CENTER** need 2 beads
- Routing: `Tower → TRACON → CENTER → TRACON → Tower → Gate`
- Direction determined by dice roll at spawn
""")

if st.button("Run One Step"):
    run_step()

results = [ac.to_dict() for ac in st.session_state.aircraft_list]
df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)
