import torch
import numpy as np
from typing import List
from classes.anomaly import Anomaly

class Environment:
    """
    Environnement simulé contenant des anomalies.
    """
    def __init__(self, width=100, height=100):
        self.width = width
        self.height = height
        self.anomalies: List[Anomaly] = []
        self.exploration_map = np.zeros((height, width))  # 0 = non exploré, 1 = exploré
        
    def add_anomaly(self, anomaly: Anomaly):
        """Ajoute une anomalie à l'environnement."""
        self.anomalies.append(anomaly)
    
    def get_sensor_data(self, x, y):
        """
        Calcule les données capteurs à une position donnée.
        Combine l'influence de toutes les anomalies proches.
        """
        # Valeurs de base (environnement sain)
        sensor_data = [20.0, 0.1, 0.1, 0.1, 0.1]
        
        # Accumulation des influences de toutes les anomalies
        for anomaly in self.anomalies:
            readings = anomaly.get_sensor_reading(x, y)
            for i in range(5):
                sensor_data[i] += (readings[i] - [20.0, 0.1, 0.1, 0.1, 0.1][i])
        
        # Normalisation et limitation des valeurs
        sensor_data = [min(max(v, 0), 100) for v in sensor_data]
        
        return torch.tensor(sensor_data, dtype=torch.float32)
    
    def mark_explored(self, x, y, radius=2):
        """Marque une zone comme explorée."""
        x_int, y_int = int(x), int(y)
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                nx, ny = x_int + dx, y_int + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    self.exploration_map[ny, nx] = 1
