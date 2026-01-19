import numpy as np
from typing import List
from classes.anomaly import Anomaly

class Environment:
    """
    Environnement simulé contenant des anomalies et différents types de terrain.
    """
    def __init__(self, width=100, height=100, base_x=None, base_y=None):
        self.width = width
        self.height = height
        self.base_x = base_x  # Position de la base
        self.base_y = base_y
        self.anomalies: List[Anomaly] = []
        self.exploration_map = np.zeros((height, width))  # 0 = non exploré, 1 = exploré
        
        # Carte de terrain : 0=plaine, 1=forêt, 2=rivière, 3=lac
        self.terrain_map = np.zeros((height, width), dtype=int)
        self._generate_terrain()

    
    def _generate_terrain(self):
        """
        Génère un terrain varié avec forêts, rivières et lacs.
        """
        # 1. Plaines par défaut (déjà initialisé à 0)
        
        # 2. Génération de forêts (zones denses)
        num_forests = np.random.randint(3, 6)
        for _ in range(num_forests):
            center_x = np.random.randint(10, self.width - 10)
            center_y = np.random.randint(10, self.height - 10)
            radius = np.random.uniform(8, 15)
            
            for y in range(self.height):
                for x in range(self.width):
                    dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                    if dist < radius:
                        # Densité de forêt diminue avec la distance
                        prob = 1.0 - (dist / radius)
                        if np.random.random() < prob * 0.8:
                            self.terrain_map[y, x] = 1  # Forêt
        
        # 3. Génération de lacs (zones circulaires)
        num_lakes = np.random.randint(2, 4)
        for _ in range(num_lakes):
            center_x = np.random.randint(15, self.width - 15)
            center_y = np.random.randint(15, self.height - 15)
            radius = np.random.uniform(5, 10)
            
            for y in range(self.height):
                for x in range(self.width):
                    dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                    if dist < radius:
                        self.terrain_map[y, x] = 3  # Lac
        
        # 4. Génération de rivières (chemins sinueux)
        num_rivers = np.random.randint(1, 3)
        for _ in range(num_rivers):
            # Point de départ aléatoire sur un bord
            if np.random.random() < 0.5:
                x, y = 0, np.random.randint(0, self.height)
                direction = np.random.uniform(0, np.pi/2)  # Vers la droite
            else:
                x, y = np.random.randint(0, self.width), 0
                direction = np.random.uniform(np.pi/4, 3*np.pi/4)  # Vers le bas
            
            # Création de la rivière
            river_length = np.random.randint(40, 80)
            width_river = 2
            
            for _ in range(river_length):
                # Ajouter la rivière avec une certaine largeur
                for dx in range(-width_river, width_river + 1):
                    for dy in range(-width_river, width_river + 1):
                        nx, ny = int(x) + dx, int(y) + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            self.terrain_map[ny, nx] = 2  # Rivière
                
                # Avancer dans la direction avec un peu de sinuosité
                direction += np.random.uniform(-0.3, 0.3)
                x += np.cos(direction) * 1.5
                y += np.sin(direction) * 1.5
                
                # Sortie si hors limites
                if x < 0 or x >= self.width or y < 0 or y >= self.height:
                    break
    

    def get_terrain_type(self, x, y):
        """
        Retourne le type de terrain à une position donnée.
        0=plaine, 1=forêt, 2=rivière, 3=lac
        """
        x_int, y_int = int(x), int(y)
        if 0 <= x_int < self.width and 0 <= y_int < self.height:
            return self.terrain_map[y_int, x_int]
        return 0  # Plaine par défaut
    
    def get_terrain_name(self, terrain_type):
        """
        Retourne le nom du type de terrain.
        """
        terrain_names = {0: 'Plaine', 1: 'Forêt', 2: 'Rivière', 3: 'Lac'}
        return terrain_names.get(terrain_type, 'Inconnu')
        
    def add_anomaly(self, anomaly: Anomaly):
        """Ajoute une anomalie à l'environnement."""
        self.anomalies.append(anomaly)
    
    def get_sensor_data(self, x, y):
        """
        Calcule les données capteurs à une position donnée.
        Combine l'influence de toutes les anomalies proches et du terrain.
        """
        # Valeurs de base (environnement sain)
        sensor_data = [20.0, 0.1, 0.1, 0.1]
        
        # Modification selon le type de terrain
        terrain = self.get_terrain_type(x, y)
        if terrain == 1:  # Forêt
            sensor_data[0] -= 2.0  # Température légèrement plus basse
        elif terrain == 2:  # Rivière
            sensor_data[3] += 0.15  # Augmentation des inondations
            sensor_data[0] -= 3.0  # Plus frais
        elif terrain == 3:  # Lac
            sensor_data[3] += 0.1  # Légère augmentation des inondations
            sensor_data[0] -= 4.0  # Encore plus frais
        
        # Accumulation des influences de toutes les anomalies
        for anomaly in self.anomalies:
            readings = anomaly.get_sensor_reading(x, y)
            for i in range(4):
                sensor_data[i] += (readings[i] - [20.0, 0.1, 0.1, 0.1][i])
        
        # Normalisation et limitation des valeurs
        sensor_data = [min(max(v, 0), 100) for v in sensor_data]
        
        return np.array(sensor_data, dtype=np.float32)
    
    def mark_explored(self, x, y, radius=2):
        """Marque une zone comme explorée."""
        x_int, y_int = int(x), int(y)
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                nx, ny = x_int + dx, y_int + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    self.exploration_map[ny, nx] = 1
