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
        # 0 dice -> no change; used for passive queues if ever called
        if dice_count <= 0:
            self.dice_rolls = []
            self.capacity = 0
            return
        self.dice_rolls = [random.randint(1, 6) for _ in range(dice_count)]
        self.capacity = sum(self.dice_rolls)

    def assign_beads(self):
        if not self.queue:
            return

        # Bead distribution (capacity units) to fill up to bead_threshold
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

        # Mark ready when threshold reached
        for aircraft in self.queue:
            if aircraft.beads >= self.bead_threshold:
                aircraft.status = "Ready to Move"

    def move_ready_aircraft(self, node_map):
        """
        General move:
        - For normal nodes: move to next stop if allowed (respect Tower caps).
        - For prequeues (PreTowerArr_* / PreTowerDep_*): only move into paired Tower if Tower has space.
          Route is only popped when a move actually happens.
        """
        if not self.queue:
            return

        ready = [ac for ac in list(self.queue) if ac.status == "Ready to Move"]

        for aircraft in ready:
            # Must have a route and current node should match
            if not aircraft.route or aircraft.route[0] != self.name:
                continue

            is_pre_arr = self.name.startswith("PreTowerArr_")
            is_pre_dep = self.name.startswith("PreTowerDep_")

            # ----- Prequeue special handling -----
            if is_pre_arr or is_pre_dep:
                # Expect Tower_* to be next hop (route[1])
                if len(aircraft.route) < 2:
                    continue  # nowhere to go
                next_stop = aircraft.route[1]
                if not next_stop.startswith("Tower_"):
                    # Defensive: prequeues should feed Tower only
                    continue

                tower_node = node_map[next_stop]
                max_q = tower_node.max_queue if tower_node.max_queue is not None else float("inf")
                if len(tower_node.queue) < max_q:
                    # Move into Tower now (pop current prequeue)
                    self.queue.remove(aircraft)
                    aircraft.beads = 0
                    aircraft.route.pop(0)  # remove current prequeue node
                    aircraft.location = next_stop
                    aircraft.status = "In System"
                    tower_node.queue.append(aircraft)
                else:
                    # Tower full: hold. Do not pop route.
                    continue
                # Done with this aircraft
                continue

            # ----- General case (non-prequeue nodes) -----
            if len(aircraft.route) < 2:
                # No next hop: arrive at destination
                self.queue.remove(aircraft)
                aircraft.beads = 0
                aircraft.route.pop(0)  # remove current node
                aircraft.location = aircraft.destination
                aircraft.status = "Arrived"
                node_map[aircraft.destination].queue.append(aircraft)
                continue

            next_stop = aircraft.route[1]

            # If next is a Tower, enforce its queue cap
            if next_stop.startswith("Tower_"):
                tower_node = node_map[next_stop]
                max_q = tower_node.max_queue if tower_node.max_queue is not None else float("inf")
                if len(tower_node.queue) >= max_q:
                    # Blocked by Tower capacity → hold here
                    continue

            # Move forward (safe to pop)
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
