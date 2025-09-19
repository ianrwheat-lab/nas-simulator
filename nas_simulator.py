import streamlit as st
import random
import pandas as pd
from collections import deque

# -----------------------------
# Node Class
# -----------------------------
class Node:
    def __init__(self, name, dice=1):
        self.name = name
        self.dice = dice
        self.queue = deque()
        self.last_roll = 0  # track dice roll result
        self.special_count = 0  # track how many times special dice used

    def roll_capacity(self, disable_gc2_special=False):
        threshold = 7 * self.dice
        self.last_roll = 0

        # If special dice are disabled for GC2, always use normal dice
        if self.name == "Ground Controller 2" and disable_gc2_special:
            for _ in range(self.dice):
                self.last_roll += random.randint(1, 6)
            return self.last_roll

        # Otherwise use normal congestion logic
        if len(self.queue) >= threshold:
            for _ in range(self.dice):
                self.last_roll += random.choice([1, 2, 3, 4, 4, 4])
            self.special_count += 1
        else:
            for _ in range(self.dice):
                self.last_roll += random.randint(1, 6)

        return self.last_roll

    def __len__(self):
        return len(self.queue)

# -----------------------------
# Initialize Session State
# -----------------------------
if "nodes" not in st.session_state:
    st.session_state.nodes = []

if "turn" not in st.session_state:
    st.session_state.turn = 0

if "moves" not in st.session_state:
    st.session_state.moves = {}

# -----------------------------
# Sidebar Controls
# -----------------------------
st.sidebar.header("Game Settings")

# Number of Center nodes
num_centers = st.sidebar.number_input("Number of Center Nodes", min_value=1, max_value=5, value=2)

# Starting aircraft setting
start_aircraft = st.sidebar.number_input("Starting Aircraft per Node", min_value=0, max_value=20, value=4)

# Toggle rules
match_io_rule = st.sidebar.checkbox("Match Gate 1 input to Ground Controller 2 output (real-time)", value=False)
disable_gc2_special = st.sidebar.checkbox("Disable Special Dice for Ground Controller 2", value=False)

# Auto-run settings
auto_turns = st.sidebar.number_input("Turns to Run Automatically", min_value=1, max_value=100, value=10)

# Reset button
if st.sidebar.button("Reset Game"):
    st.session_state.nodes = []
    st.session_state.turn = 0
    st.session_state.moves = {}

# -----------------------------
# Build Node Chain
# -----------------------------
node_names = [
    "Gate 1",
    "Ground Controller 1",
    "Local Controller 1",
    "TRACON 1",
]
node_names += [f"Center {i+1}" for i in range(num_centers)]
node_names += [
    "TRACON 2",
    "Local Controller 2",
    "Ground Controller 2",
    "Gate 2 (Completed Flights)",
]

# Initialize nodes if empty or structure changed
if not st.session_state.nodes or len(st.session_state.nodes) != len(node_names):
    st.session_state.nodes = [Node(name) for name in node_names]
    # Preload chosen number of aircraft at every node except Gate 1 and Gate 2
    for node in st.session_state.nodes:
        if node.name not in ["Gate 1", "Gate 2 (Completed Flights)"]:
            for _ in range(start_aircraft):
                node.queue.append("Aircraft")

# Dice controls for each node (except completed Gate 2)
for node in st.session_state.nodes[:-1]:
    node.dice = st.sidebar.selectbox(f"{node.name} Dice", [1, 2], index=0, key=f"dice_{node.name}")

# -----------------------------
# Simulation Step: Roll Dice
# -----------------------------
if st.button("Roll Dice"):
    for node in st.session_state.nodes[:-1]:  # exclude Gate 2
        node.roll_capacity(disable_gc2_special)
    st.session_state.moves = {"Action": "Rolled dice"}

# -----------------------------
# Simulation Step: Move Aircraft
# -----------------------------
if st.button("Move Aircraft"):
    st.session_state.turn += 1
    moves = {}
    transfers = [[] for _ in st.session_state.nodes]

    gc2_to_gate2 = 0  # track GC2 -> Gate 2 this turn

    # Decide movements (but don’t apply yet)
    for i in range(len(st.session_state.nodes) - 1):  # up to Gate 2
        node = st.session_state.nodes[i]
        next_node = st.session_state.nodes[i + 1]

        if len(node.queue) > 0:
            capacity = node.last_roll
            moved = min(capacity, len(node.queue))
            for _ in range(moved):
                ac = node.queue.popleft()
                transfers[i + 1].append(ac)
            moves[node.name] = f"Will move {moved} forward"

            # Track Ground Controller 2 -> Gate 2 flow
            if node.name == "Ground Controller 2":
                gc2_to_gate2 = moved
        else:
            moves[node.name] = "No aircraft to move"

    # Apply movements all at once
    for i, incoming in enumerate(transfers):
        for ac in incoming:
            st.session_state.nodes[i].queue.append(ac)

    # Real-time Ground Controller 1 release
    gate1 = st.session_state.nodes[0]
    if match_io_rule:
        release_count = gc2_to_gc1
        for _ in range(release_count):
            gc1.queue.append("Aircraft")
        moves[gc1.name] = f"Released {release_count} (matched GC2->Gate2 this turn)"
    else:
        release_count = gc1.last_roll
        for _ in range(release_count):
            gate1.queue.append("Aircraft")
        moves[gate1.name] = f"Released {release_count} (by dice)"

    # Store results in session state
    st.session_state.moves = moves

# -----------------------------
# Simulation Step: Auto Run
# -----------------------------
if st.sidebar.button("Run Multiple Turns"):
    for _ in range(auto_turns):
        # Phase 1: Roll dice
        for node in st.session_state.nodes[:-1]:
            node.roll_capacity(disable_gc2_special)

        st.session_state.turn += 1
        moves = {}
        transfers = [[] for _ in st.session_state.nodes]
        gc2_to_gate2 = 0

        # Decide movements
        for i in range(len(st.session_state.nodes) - 1):
            node = st.session_state.nodes[i]
            next_node = st.session_state.nodes[i + 1]

            if len(node.queue) > 0:
                capacity = node.last_roll
                moved = min(capacity, len(node.queue))
                for _ in range(moved):
                    ac = node.queue.popleft()
                    transfers[i + 1].append(ac)
                moves[node.name] = f"Will move {moved} forward"

                if node.name == "Ground Controller 2":
                    gc2_to_gate2 = moved
            else:
                moves[node.name] = "No aircraft to move"

        # Apply movements
        for i, incoming in enumerate(transfers):
            for ac in incoming:
                st.session_state.nodes[i].queue.append(ac)

        # Real-time Gate 1 release
        gate1 = st.session_state.nodes[0]
        if match_io_rule:
            release_count = gc2_to_gate2
            for _ in range(release_count):
                gate1.queue.append("Aircraft")
            moves[gate1.name] = f"Released {release_count} (matched GC2->Gate2 this turn)"
        else:
            release_count = gate1.last_roll
            for _ in range(release_count):
                gate1.queue.append("Aircraft")
            moves[gate1.name] = f"Released {release_count} (by dice)"

        st.session_state.moves = moves

# -----------------------------
# Display Queues + Dice Rolls
# -----------------------------
data = {
    "Node": [node.name for node in st.session_state.nodes],
    "Aircraft in Queue": [len(node) for node in st.session_state.nodes],
    "Last Dice Roll": [
        node.last_roll if node.name != "Gate 2 (Completed Flights)" else "-"
        for node in st.session_state.nodes
    ],
    "Special Dice Used (times)": [
        node.special_count if node.name != "Gate 2 (Completed Flights)" else "-"
        for node in st.session_state.nodes
    ],
}
df = pd.DataFrame(data)

st.write("### Current System State")
st.dataframe(df, use_container_width=True)

# -----------------------------
# Display WIP + TMI Counts
# -----------------------------
wip_count = sum(len(node) for node in st.session_state.nodes if node.name != "Gate 2 (Completed Flights)")
tmi_count = sum(node.special_count for node in st.session_state.nodes if node.name != "Gate 2 (Completed Flights)")

st.metric("WIP Count", wip_count)
st.metric("TMI Count", tmi_count)

# -----------------------------
# Display Turn Results (after system state)
# -----------------------------
if st.session_state.moves:
    st.write(f"### Turn {st.session_state.turn} Results")
    st.write(st.session_state.moves)

