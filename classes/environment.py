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
        self.last_random_spawn_time = 0.0
        self.random_spawn_interval = 1800.0  # Une nouvelle anomalie tous les 30 minutes
        
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
    
    def update(self, current_time, delta_time=1.0):
        """
        Met à jour l'état de l'environnement.
        - Évolution des anomalies existantes (propagation uniquement)
        - Apparition aléatoire de nouvelles anomalies
        """
        # 1. Évolution des anomalies existantes (propagation)
        for anomaly in self.anomalies:
            anomaly.evolve(current_time, self, delta_time)
        
        # 2. Apparition aléatoire de nouvelles anomalies
        if current_time - self.last_random_spawn_time > self.random_spawn_interval:
            if np.random.random() < 0.1:  # 10% de chance
                # Créer une nouvelle anomalie aléatoire
                types = ['pollution', 'radiation', 'effondrement']
                new_type = np.random.choice(types)
                
                new_anomaly = Anomaly(
                    x=np.random.uniform(10, self.width - 10),
                    y=np.random.uniform(10, self.height - 10),
                    intensity=np.random.uniform(0.8, 1.5),
                    radius=np.random.uniform(8, 15),
                    type=new_type,
                    creation_time=current_time,
                    is_propagating=True
                )
                self.add_anomaly(new_anomaly)
                self.last_random_spawn_time = current_time
