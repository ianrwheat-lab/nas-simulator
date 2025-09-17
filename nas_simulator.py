import streamlit as st
import random
from collections import deque
import pandas as pd

# -----------------------------
# Classes
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
        self.capacity = random.randint(0, 6)

    def move_aircraft(self, center_queue):
        moved = 0
        while self.queue and moved < self.capacity:
            ac = self.queue.popleft()
            ac.location = "CENTER"
            ac.status = "In CENTER"
            center_queue.append(ac)
            moved += 1


class Center:
    def __init__(self):
        self.capacity = 0
        self.queue = deque()

    def roll_capacity(self):
        self.capacity = random.randint(0, 6)

    def move_aircraft(self, outbound_tracons):
        moved = 0
        while self.queue and moved < self.capacity:
            ac = self.queue.popleft()
            dest_tracon = outbound_tracons[ac.origin]  # Return path
            ac.location = f"TRACON_{dest_tracon}"
            ac.status = "Returning"
            tracon_lookup[dest_tracon].queue.append(ac)
            moved += 1


# -----------------------------
# Initialization
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
# Simulation Logic
# -----------------------------
def run_simulation(rounds=5):
    global tracon_lookup

    gates, towers, tracons, center = initialize_simulation()
    tracon_lookup = tracons
    aircraft_list = []
    aircraft_id = 1

    for step in range(rounds):
        # Step 1: Gates launch aircraft
        for gate_name in ['A', 'B', 'C', 'D']:
            dest = gates[gate_name].decide_destination()
            ac = Aircraft(aircraft_id, origin=gate_name)
            ac.route = [gate_name, dest]
            ac.location = f"Tower_{dest}"
            ac.status = "Waiting for Beads"
            towers[dest].queue.append(ac)
            aircraft_list.append(ac)
            aircraft_id += 1

        # Step 2: Towers assign beads
        for tower in towers.values():
            tower.roll_capacity()
            tower.assign_beads()

        # Step 3: Move ready aircraft to TRACON
        for tower_name, tower in towers.items():
            tracon = tracons['N'] if tower_name in ['A', 'B'] else tracons['S']
            for ac in list(tower.queue):
                if ac.beads == 3 and ac.status == "Ready for TRACON":
                    ac.location = f"TRACON_{tracon.name}"
                    ac.status = "In TRACON"
                    tracon.queue.append(ac)
                    tower.queue.remove(ac)

        # Step 4: TRACONs to CENTER
        for tracon in tracons.values():
            tracon.roll_capacity()
            tracon.move_aircraft(center.queue)

        # Step 5: CENTER to return TRACON
        center.roll_capacity()
        center.move_aircraft({'A': 'N', 'B': 'N', 'C': 'S', 'D': 'S'})

    return [ac.to_dict() for ac in aircraft_list]

# -----------------------------
# Streamlit App
# -----------------------------
st.title("🛫 NAS Bead & Bowl Simulator")

st.markdown("""
Simulate aircraft flow through the National Airspace System (NAS):  
**Gates → Towers → TRACONs → CENTER → Return TRACON**
""")

rounds = st.slider("How many time steps to simulate?", 1, 20, 5)

if st.button("Run Simulation"):
    results = run_simulation(rounds)
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)
