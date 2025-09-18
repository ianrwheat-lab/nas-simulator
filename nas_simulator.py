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

    def roll_capacity(self):
        return sum(random.randint(1, 6) for _ in range(self.dice))

    def __len__(self):
        return len(self.queue)

# -----------------------------
# Initialize Session State
# -----------------------------
if "nodes" not in st.session_state:
    st.session_state.nodes = []
    st.session_state.turn = 0

# -----------------------------
# Sidebar Controls
# -----------------------------
st.sidebar.header("Game Settings")

# Number of Center nodes
num_centers = st.sidebar.number_input("Number of Center Nodes", min_value=1, max_value=5, value=2)

# Reset button
if st.sidebar.button("Reset Game"):
    st.session_state.nodes = []
    st.session_state.turn = 0

# -----------------------------
# Build Node Chain
# -----------------------------
node_names = ["Gate 1", "Ground Controller 1", "Local Controller 1", "TRACON 1"]
node_names += [f"Center {i+1}" for i in range(num_centers)]
node_names += ["TRACON 2", "Gate 2 (Completed Flights)"]

# Initialize nodes if empty
if not st.session_state.nodes or len(st.session_state.nodes) != len(node_names):
    st.session_state.nodes = [Node(name) for name in node_names]

# Dice controls for each node (except completed Gate 2)
for node in st.session_state.nodes[:-1]:
    node.dice = st.sidebar.selectbox(f"{node.name} Dice", [1, 2], index=0, key=f"dice_{node.name}")

# -----------------------------
# Simulation Step
# -----------------------------
if st.button("Run Turn"):
    st.session_state.turn += 1
    moves = {}

    # Step 1: Gate 1 releases aircraft
    gate1 = st.session_state.nodes[0]
    release_count = gate1.roll_capacity()
    for _ in range(release_count):
        gate1.queue.append("Aircraft")
    moves[gate1.name] = f"Released {release_count}"

    # Step 2: Move aircraft through all nodes (backward order)
    for i in range(len(st.session_state.nodes) - 2, -1, -1):  # skip Gate 2 in loop
        node = st.session_state.nodes[i]
        next_node = st.session_state.nodes[i + 1]
        capacity = node.roll_capacity()
        moved = min(capacity, len(node.queue))
        for _ in range(moved):
            ac = node.queue.popleft()
            next_node.queue.append(ac)
        moves[node.name] = f"Moved {moved} forward"

    # Display results
    st.write(f"### Turn {st.session_state.turn} Results")
    st.write(moves)

# -----------------------------
# Display Queues
# -----------------------------
data = {
    "Node": [node.name for node in st.session_state.nodes],
    "Aircraft in Queue": [len(node) for node in st.session_state.nodes],
}
df = pd.DataFrame(data)

st.write("### Current System State")
st.dataframe(df, use_container_width=True)
