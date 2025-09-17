import streamlit as st
import random

# Constants
GATE_NODES = ["A", "B", "C", "D"]
TOWER_NODES = ["Tower_A", "Tower_B", "Tower_C", "Tower_D"]
TOWER_HOLDING_NODES = [f"{tower}_Holding" for tower in TOWER_NODES]
TRACON_NODES = ["TRACON_S", "TRACON_N"]
CENTER_NODE = "CENTER"
ALL_NODES = GATE_NODES + TOWER_NODES + TOWER_HOLDING_NODES + TRACON_NODES + [CENTER_NODE]

REVERSE_GATE_MAP = {"C": ["A", "B"], "D": ["A", "B"], "A": ["C", "D"], "B": ["C", "D"]}

BEAD_REQUIREMENTS = {
    "GATE": 3,
    "TOWER": 3,
    "TRACON": 2,
    "CENTER": 2,
    "HOLDING": 0
}

class Aircraft:
    def __init__(self, origin, destination, route):
        self.origin = origin
        self.destination = destination
        self.route = route
        self.current_node = origin
        self.beads_needed = BEAD_REQUIREMENTS[self.get_node_type(origin)]

    def get_node_type(self, node):
        if node in GATE_NODES:
            return "GATE"
        elif node in TOWER_NODES:
            return "TOWER"
        elif node in TRACON_NODES:
            return "TRACON"
        elif node == CENTER_NODE:
            return "CENTER"
        elif node in TOWER_HOLDING_NODES:
            return "HOLDING"
        return "UNKNOWN"

class Node:
    def __init__(self, name):
        self.name = name
        self.aircraft = []
        self.dice_roll = 0
        self.beads_to_assign = 0

    def roll_dice(self):
        if self.name in TRACON_NODES or self.name == CENTER_NODE:
            self.dice_roll = random.randint(1, 6) + random.randint(1, 6)
        elif self.name in GATE_NODES or self.name in TOWER_NODES:
            self.dice_roll = random.randint(1, 6)
        else:
            self.dice_roll = 0
        self.beads_to_assign = self.dice_roll

    def distribute_beads(self):
        if not self.aircraft:
            return
        idx = 0
        while self.beads_to_assign > 0:
            self.aircraft[idx % len(self.aircraft)].beads_needed = max(0, self.aircraft[idx % len(self.aircraft)].beads_needed - 1)
            self.beads_to_assign -= 1
            idx += 1

    def move_aircraft(self, nodes):
        movable = [ac for ac in self.aircraft if ac.beads_needed == 0]
        for ac in movable:
            self.aircraft.remove(ac)
            if ac.route:
                next_node_name = ac.route[0]
                next_node = nodes[next_node_name]

                # Gate to Tower logic — holding queue if tower full
                if next_node_name in TOWER_NODES:
                    if len(next_node.aircraft) < 2:
                        next_node.aircraft.append(ac)
                        ac.route.pop(0)
                        ac.current_node = next_node.name
                        ac.beads_needed = BEAD_REQUIREMENTS[ac.get_node_type(next_node.name)]
                    else:
                        # Tower full → go to holding node
                        holding_name = f"{next_node_name}_Holding"
                        nodes[holding_name].aircraft.append(ac)
                        ac.route.insert(0, holding_name)
                        ac.current_node = holding_name
                        ac.beads_needed = BEAD_REQUIREMENTS["HOLDING"]

                # Holding to Tower logic
                elif self.name in TOWER_HOLDING_NODES and next_node_name in TOWER_NODES:
                    if len(next_node.aircraft) < 2:
                        next_node.aircraft.append(ac)
                        ac.route.pop(0)
                        ac.current_node = next_node.name
                        ac.beads_needed = BEAD_REQUIREMENTS[ac.get_node_type(next_node.name)]
                        continue  # exit early so we don't re-append to holding

                else:
                    next_node.aircraft.append(ac)
                    ac.route.pop(0)
                    ac.current_node = next_node.name
                    ac.beads_needed = BEAD_REQUIREMENTS[ac.get_node_type(next_node.name)]


def generate_route(start_gate, dest_gate):
    gate_tower = f"Tower_{start_gate}"
    tracon_from = "TRACON_S" if start_gate in ["A", "B"] else "TRACON_N"
    tracon_to = "TRACON_S" if dest_gate in ["A", "B"] else "TRACON_N"
    tower_dest = f"Tower_{dest_gate}"
    return [f"{gate_tower}_Holding", gate_tower, tracon_from, CENTER_NODE, tracon_to, f"{tower_dest}_Holding", tower_dest, dest_gate]

def spawn_aircraft(nodes):
    for gate in GATE_NODES:
        dice_value = nodes[gate].dice_roll
        destination = REVERSE_GATE_MAP[gate][0] if dice_value <= 3 else REVERSE_GATE_MAP[gate][1]
        route = generate_route(gate, destination)
        ac = Aircraft(origin=gate, destination=destination, route=route)
        nodes[gate].aircraft.append(ac)

def initialize_nodes():
    return {name: Node(name) for name in ALL_NODES}

# Streamlit App
st.title("✈️ NAS Flow Simulator with Holding Queues")

if "step" not in st.session_state:
    st.session_state.step = 0
    st.session_state.nodes = initialize_nodes()

# Roll Dice Phase
if st.button("Step 1: Roll Dice"):
    for node in st.session_state.nodes.values():
        node.roll_dice()

# Distribute Beads Phase
if st.button("Step 2: Distribute Beads"):
    for node in st.session_state.nodes.values():
        node.distribute_beads()

# Move Aircraft Phase
if st.button("Step 3: Move Aircraft"):
    for node in st.session_state.nodes.values():
        node.move_aircraft(st.session_state.nodes)

# Spawn aircraft every round
if st.button("✈️ Spawn Aircraft at All Gates"):
    spawn_aircraft(st.session_state.nodes)

# Display Status Table
st.subheader("📊 Node Status Overview")
data = []
for name, node in st.session_state.nodes.items():
    data.append({
        "Node": name,
        "Aircraft Count": len(node.aircraft),
        "Dice Roll": node.dice_roll
    })

import pandas as pd
st.dataframe(pd.DataFrame(data))
