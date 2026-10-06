class MetricsCollector:
    def __init__(self):
        self.l1_hits = 0
        self.l2_hits = 0
        self.misses = 0
        self.loader_calls = 0

    def record_l1_hit(self):
        self.l1_hits += 1

    def record_l2_hit(self):
        self.l2_hits += 1

    def record_miss(self):
        self.misses += 1

    def record_loader_call(self):
        self.loader_calls += 1