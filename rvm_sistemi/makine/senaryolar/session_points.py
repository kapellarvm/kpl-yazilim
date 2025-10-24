@dataclass
class SessionPoints:
    total_points: int = 0
    pending_points: int = 0
    completed_points: int = 0
    
    def add_pending(self, points: int):
        self.pending_points += points
        
    def complete_pending(self):
        self.total_points += self.pending_points
        self.completed_points += self.pending_points
        self.pending_points = 0
        
    def clear(self):
        self.total_points = 0
        self.pending_points = 0
        self.completed_points = 0