import streamlit as st
import random
from collections import deque
import pandas as pd

# -----------------------------
# Aircraft Class
# -----------------------------
class Aircraft:
    def __init__(self, id, origin):
        self.id = id
        self.origin = origin
        self.location = origin
        self.beads = 0
        self.status = "At Gate"
        self.route = []

    def to_dict(self):
        return {
            "Aircraft ID": self.id,
            "Origin": self.origin,
            "Location": self.location,
            "Beads": self.beads,
            "Status": self.status,
            "Route": " → ".join(self.route)
        }

# -----------------------------
# System Entities
# -----------------------------
class Gate:
    def __init__(self, name):
        self.name = name

    def decide_destination(self):
        roll = random.randint(1, 6)
        if self.name in ['A', 'B']:
            return 'C' if roll <= 3 else 'D'
        elif self.name in ['C', 'D']:
            return 'A' if roll <= 3 else 'B'

class Tower:
    def __init__(self, name):
        self.name = name
        self.capacity = 0
        self.queue = deque()

    def roll_capacity(self):
        self.capacity = random.randint(0, 6)

    def assign_beads(self):
        for aircraft in list(self.queue):
            while aircraft.beads < 3 and self.capacity > 0:
                aircraft.beads += 1
                self.capacity -= 1
            if aircraft.beads == 3:
                aircraft.status = "Ready for TRACON"

class Tracon:
    def __init__(self, name):
        self.name = name
        self.capacity = 0
        self.queue = deque()

    def roll_capacity(self):
        self.capacity = random.randint(1, 6) + random.randint(1, 6)

    def assign_beads(self):
        for aircraft in list(self.queue):
            while aircraft.beads < 2 and self.capacity > 0:
                aircraft.beads += 1
                self.capacity -= 1
            if aircraft.beads == 2:
                aircraft.status = "Ready for CENTER"

    def move_aircraft(self, center_queue):
        moved = 0
        for ac in list(self.queue):
            if ac.beads == 2 and moved < self.capacity:
                self.queue.remove(ac)
                ac.location = "CENTER"
                ac.status = "In CENTER"
                center_queue.append(ac)
                moved += 1

class Center:
    def __init__(self):
        self.capacity = 0
        self.queue = deque()

    def roll_capacity(self):
        self.capacity = random.randint(1, 6) + random.randint(1, 6)

    def assign_beads(self):
        for aircraft in list(self.queue):
            while aircraft.beads < 2 and self.capacity > 0:
                aircraft.beads += 1
                self.capacity -= 1
            if aircraft.beads == 2:
                aircraft.status = "Returning"

    def move_aircraft(self, outbound_tracons):
        moved = 0
        for ac in list(self.queue):
            if ac.beads == 2 and moved < self.capacity:
                self.queue.remove(ac)
                dest_tracon = outbound_tracons[ac.origin]
                ac.location = f"TRACON_{dest_tracon}"
                ac.status = "Returning"
                tracon_lookup[dest_tracon].queue.append(ac)
                moved += 1

# -----------------------------
# Initialization Function
# -----------------------------
def initialize_simulation():
    gates = {name: Gate(name) for name in ['A', 'B', 'C', 'D']}
    towers = {name: Tower(name) for name in ['A', 'B', 'C', 'D']}
    tracons = {
        'N': Tracon('N'),
        'S': Tracon('S')
    }
    center = Center()
    return gates, towers, tracons, center

# -----------------------------
# Simulation State
# -----------------------------
if 'gates' not in st.session_state:
    st.session_state.gates, st.session_state.towers, st.session_state.tracons, st.session_state.center = initialize_simulation()
    st.session_state.aircraft_list = []
    st.session_state.aircraft_id = 1
    st.session_state.step = 1

# -----------------------------
# Single Step Logic
# -----------------------------
def run_step():
    global tracon_lookup
    gates = st.session_state.gates
    towers = st.session_state.towers
    tracons = st.session_state.tracons
    center = st.session_state.center
    aircraft_list = st.session_state.aircraft_list
    aircraft_id = st.session_state.aircraft_id
    step = st.session_state.step

    tracon_lookup = tracons
    spawn_gates = ['A', 'B'] if step % 2 == 1 else ['C', 'D']

    for gate_name in spawn_gates:
        dest = gates[gate_name].decide_destination()
        ac = Aircraft(aircraft_id, origin=gate_name)
        ac.route = [gate_name, f"Tower_{dest}"]
        ac.location = f"Tower_{dest}"
        ac.status = "Waiting for Beads"
        towers[dest].queue.append(ac)
        aircraft_list.append(ac)
        aircraft_id += 1

    for tower in towers.values():
        tower.roll_capacity()
        tower.assign_beads()

    for tower_name, tower in towers.items():
        tracon = tracons['N'] if tower_name in ['A', 'B'] else tracons['S']
        for ac in list(tower.queue):
            if ac.beads == 3 and ac.status == "Ready for TRACON":
                ac.location = f"TRACON_{tracon.name}"
                ac.status = "In TRACON"
                ac.beads = 0
                tracon.queue.append(ac)
                tower.queue.remove(ac)

    for tracon in tracons.values():
        tracon.roll_capacity()
        tracon.assign_beads()
        tracon.move_aircraft(center.queue)

    center.roll_capacity()
    center.assign_beads()
    center.move_aircraft({'A': 'N', 'B': 'N', 'C': 'S', 'D': 'S'})

    st.session_state.aircraft_id = aircraft_id
    st.session_state.step += 1

# -----------------------------
# Streamlit App
# -----------------------------
st.title("🛫 NAS Bead & Bowl Simulator - Step Mode")

st.markdown("""
Simulate aircraft flow through the National Airspace System (NAS):
- **Step through each round manually**
- **Alternating gate spawns**
- **Two-dice capacity for TRACONs and CENTER**
- **Dynamic bead needs: 3 at Towers, 2 at TRACON & CENTER**
""")

if st.button("Run One Step"):
    run_step()

results = [ac.to_dict() for ac in st.session_state.aircraft_list]
df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)
