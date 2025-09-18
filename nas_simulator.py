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
        self.capacity = 0                 # dice-derived bead budget (resets each Phase 1)
        self.dice_rolls = []
        self.queue = deque()
        self.bead_threshold = bead_threshold
        self.max_capacity = capacity      # occupancy cap for towers (e.g., 2)
        self.is_pretower = is_pretower

    def roll_capacity(self, dice_count=1):
        # Only pre-queues skip dice. Towers DO roll dice (their occupancy cap is separate).
        if self.is_pretower:
            self.dice_rolls = []
            self.capacity = 0
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
        # Pre-queues do not assign beads
        if self.is_pretower or not self.queue or self.capacity <= 0:
            return

        # Distribute beads to non-arrived aircraft until threshold met or capacity exhausted
        while self.capacity > 0:
            all_filled = True
            for ac in self.queue:
                if ac.status != "Arrived" and ac.beads < self.bead_threshold:
                    ac.beads += 1
                    self.capacity -= 1
                    all_filled = False
                    if self.capacity == 0:
                        break
            if all_filled:
                break

        # Mark ready only if not arrived
        for ac in self.queue:
            if ac.status != "Arrived" and ac.beads >= self.bead_threshold:
                ac.status = "Ready to Move"

    def _bypass_pretower_if_tower_has_space(self, node_map, next_stop_name):
        """
        If next_stop is a PreTower* node and the paired Tower has space (< max_capacity),
        bypass the pre-queue and push directly into the Tower. Returns True if bypassed.
        """
        if not (next_stop_name.startswith("PreTowerArr_") or next_stop_name.startswith("PreTowerDep_")):
            return False

        tower_suffix = next_stop_name.split("_")[-1]  # 'A','B','C','D'
        tower_name = f"Tower_{tower_suffix}"
        tower_node = node_map[tower_name]

        # If tower has space, we bypass
        if tower_node.max_capacity is not None and len(tower_node.queue) < tower_node.max_capacity:
            return tower_name
        return False

    def move_ready_aircraft(self, node_map):
        # Pre-queues do not self-release; handled in Phase 3B
        if self.is_pretower:
            return

        for aircraft in list(self.queue):
            if aircraft.status != "Ready to Move":
                continue

            # Consume this node's step in the route
            if aircraft.route:
                aircraft.route.pop(0)

            # Determine intended next stop (if any)
            if aircraft.route:
                next_stop = aircraft.route[0]

                # If headed to a pre-queue, consider bypass to tower when tower has space
                bypass_tower = self._bypass_pretower_if_tower_has_space(node_map, next_stop)
                self.queue.remove(aircraft)
                aircraft.beads = 0
                aircraft.status = "In System"

                if bypass_tower:
                    # We are bypassing the pre-queue: pop the pre-queue step too
                    if aircraft.route and (aircraft.route[0].startswith("PreTowerArr_") or aircraft.route[0].startswith("PreTowerDep_")):
                        aircraft.route.pop(0)  # remove the pre-queue step
                    # Next should be the Tower step; pop it as we "arrive" there
                    if aircraft.route and aircraft.route[0] == bypass_tower:
                        # Do not pop here; staying consistent: current step is the tower
                        pass
                    aircraft.location = bypass_tower
                    node_map[bypass_tower].queue.append(aircraft)
                else:
                    # Normal move into next_stop
                    aircraft.location = next_stop
                    node_map[next_stop].queue.append(aircraft)
            else:
                # Arrived at destination (final gate). Keep in gate queue but never move again.
                self.queue.remove(aircraft)
                aircraft.beads = 0
                aircraft.status = "Arrived"
                aircraft.location = aircraft.destination
                node_map[aircraft.destination].queue.append(aircraft)

# -----------------------------
# Initialization
# -----------------------------
def initialize_simulation():
    nodes = {
        # Towers (occupancy capped at 2; still roll dice for beads)
        'Tower_A': Node('Tower_A', 3, capacity=2),
        'Tower_B': Node('Tower_B', 3, capacity=2),
        'Tower_C': Node('Tower_C', 3, capacity=2),
        'Tower_D': Node('Tower_D', 3, capacity=2),
        # Pre-Tower Queues (no dice/beads; pure holding)
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
        # Gates: used only as final destination parking in this version
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

    # Route includes pre-queues, but Step 3A may bypass them if tower has space at that moment.
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
    # Step 3A: normal releases from all non-prequeue nodes (with pre-queue bypass where possible)
    for node in nodes.values():
        node.move_ready_aircraft(nodes)

    # Step 3B: refill towers strictly from pre-queues (Arrivals > Departures), FIFO, while space remains
    for t in ['A', 'B', 'C', 'D']:
        tower_node = nodes[f'Tower_{t}']
        arr_q = nodes[f'PreTowerArr_{t}']
        dep_q = nodes[f'PreTowerDep_{t}']

        while tower_node.max_capacity is not None and len(tower_node.queue) < tower_node.max_capacity:
            moved = False
            if arr_q.queue:
                ac = arr_q.queue.popleft()
                # pop the current pre-queue step from route
                if ac.route and ac.route[0] == arr_q.name:
                    ac.route.pop(0)
                # next step should be the tower itself; do not pop tower step here
                ac.location = tower_node.name
                ac.status = "In System"
                ac.beads = 0
                tower_node.queue.append(ac)
                moved = True
            elif dep_q.queue:
                ac = dep_q.queue.popleft()
                if ac.route and ac.route[0] == dep_q.name:
                    ac.route.pop(0)
                ac.location = tower_node.name
                ac.status = "In System"
                ac.beads = 0
                tower_node.queue.append(ac)
                moved = True
            if not moved:
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
    phase = st.session_state.phase

    if phase == 1:
        # Roll capacities (2 dice for TRACON/CENTER, 1 for others incl. Towers; pre-queues skip)
        for name, node in nodes.items():
            node.roll_capacity(2 if ('TRACON' in name or name == 'CENTER') else 1)

        # Spawn aircraft using gate die #1 to choose destination, then place into PreTowerDep_*
        for gate in ['A','B','C','D']:
            if nodes[gate].dice_rolls:
                spawn_roll = nodes[gate].dice_rolls[0]
                destination = get_destination_from_roll(gate, spawn_roll)
                route = generate_route(gate, destination)
                ac = Aircraft(aircraft_id, gate, destination, route, spawn_roll)
                nodes[route[0]].queue.append(ac)  # enters PreTowerDep_* first
                aircraft_list.append(ac)
                aircraft_id += 1

    elif phase == 2:
        for node in nodes.values():
            node.assign_beads()

    elif phase == 3:
        move_phase(nodes)
        st.session_state.step += 1

    # Advance phase
    st.session_state.phase = 1 if st.session_state.phase == 3 else st.session_state.phase + 1
    st.session_state.aircraft_id = aircraft_id

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🛫 NAS Bead & Bowl Simulator - Pre-Tower Queues Edition")

st.markdown("""
**Phases per Turn**
1) 🎲 Roll Dice (and spawn)  
2) 💎 Distribute Beads  
3) ✈️ Move  
   - 3A: release from nodes (bypass pre-queues if tower has space)  
   - 3B: refill towers from pre-queues (Arrivals > Departures, FIFO)  
""")

st.write(f"**Current Step:** {st.session_state.step} | **Phase:** {st.session_state.phase} (1=Roll, 2=Beads, 3=Move)")

if st.button("Run Next Sub-Step"):
    run_substep()

# Aircraft table
results = [ac.to_dict() for ac in st.session_state.aircraft_list]
st.dataframe(pd.DataFrame(results), use_container_width=True)

# Node status overview
node_status = []
for name, node in st.session_state.nodes.items():
    node_status.append({
        "Node": name,
        "Aircraft Count": len(node.queue),
        "Penalized": (len(node.queue) >= 3 and not node.is_pretower),
        "Dice Roll(s)": node.dice_rolls if node.dice_rolls else "-",
        "Bead Capacity Left": node.capacity if not node.is_pretower else "N/A",
        "Tower Max Occ": node.max_capacity if node.max_capacity is not None else "—",
    })

st.markdown("### 📊 Node Status Overview")
st.dataframe(pd.DataFrame(node_status), use_container_width=True)
