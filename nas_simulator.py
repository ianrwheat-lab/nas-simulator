def assign_beads(self):
    # Pre-queues do not assign beads
    if self.is_pretower or not self.queue or self.capacity <= 0:
        return

    # Round robin, FIFO order
    while self.capacity > 0:
        any_given = False
        for ac in self.queue:
            if ac.status != "Arrived" and ac.beads < self.bead_threshold and self.capacity > 0:
                ac.beads += 1
                self.capacity -= 1
                any_given = True
        # If no one received a bead this cycle, stop to avoid infinite loop
        if not any_given:
            break

    # After distribution, mark those who reached threshold as ready
    for ac in self.queue:
        if ac.status != "Arrived" and ac.beads >= self.bead_threshold:
            ac.status = "Ready to Move"
