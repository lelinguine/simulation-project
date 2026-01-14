import torch
import numpy as np
import random

class Drone:
    """
    Drone autonome capable d'explorer, détecter des anomalies et communiquer.
    """
    def __init__(self, drone_id, x, y, detector_net, base_x=0, base_y=0):
        self.id = drone_id
        self.x = x
        self.y = y
        self.base_x = base_x
        self.base_y = base_y
        self.detector = detector_net
        
        # État du drone
        self.battery = 100.0
        self.is_at_base = False
        self.detected_anomalies = []  # Anomalies détectées par ce drone
        self.path_history = [(x, y)]
        
        # Paramètres de mouvement
        self.speed = 2.0
        self.detection_radius = 5.0
        self.communication_range = 50.0
        
        # Mode d'exploration
        self.target_x = None
        self.target_y = None
        self.mode = 'explore'  # 'explore', 'return', 'investigate'
        
    def move_towards(self, target_x, target_y, environment):
        """Déplace le drone vers une cible."""
        dx = target_x - self.x
        dy = target_y - self.y
        distance = np.sqrt(dx**2 + dy**2)
        
        if distance < self.speed:
            self.x = target_x
            self.y = target_y
        else:
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
        
        # Contraintes de l'environnement
        self.x = max(0, min(self.x, environment.width))
        self.y = max(0, min(self.y, environment.height))
        
        # Consommation de batterie
        self.battery -= 0.5
        
        # Marquer comme exploré
        environment.mark_explored(self.x, self.y)
        self.path_history.append((self.x, self.y))
        
    def scan_area(self, environment):
        """Scanne la zone actuelle pour détecter des anomalies."""
        sensor_data = environment.get_sensor_data(self.x, self.y)
        is_anomaly, intensity = self.detector.detect_anomaly(sensor_data)
        
        if is_anomaly:
            # Enregistrer l'anomalie détectée
            anomaly_info = {
                'position': (self.x, self.y),
                'intensity': intensity,
                'sensor_data': sensor_data.tolist() if isinstance(sensor_data, torch.Tensor) else sensor_data,
                'timestamp': len(self.path_history)
            }
            self.detected_anomalies.append(anomaly_info)
            return True, intensity
        return False, 0.0
    
    def select_exploration_target(self, environment, other_drones):
        """
        Sélectionne une nouvelle cible d'exploration.
        Stratégie : zones non explorées les plus éloignées des autres drones.
        """
        # Recherche de zones non explorées
        unexplored = np.argwhere(environment.exploration_map == 0)
        
        if len(unexplored) == 0:
            # Tout est exploré, retour à la base
            self.mode = 'return'
            self.target_x = self.base_x
            self.target_y = self.base_y
            return
        
        # Sélectionner une cible aléatoire parmi les zones non explorées
        # (stratégie simple, peut être améliorée)
        if random.random() < 0.3:  # 30% aléatoire pour diversifier
            idx = random.randint(0, len(unexplored)-1)
            target = unexplored[idx]
            self.target_x = target[1]
            self.target_y = target[0]
        else:
            # Sélectionner la zone la plus éloignée
            max_dist = 0
            best_target = unexplored[0]
            for point in unexplored[::10]:  # Sous-échantillonnage pour performance
                dist = np.sqrt((point[1] - self.x)**2 + (point[0] - self.y)**2)
                if dist > max_dist:
                    max_dist = dist
                    best_target = point
            self.target_x = best_target[1]
            self.target_y = best_target[0]
    
    def update(self, environment, other_drones):
        """Mise à jour de l'état du drone à chaque pas de temps."""
        # Vérifier si à la base
        dist_to_base = np.sqrt((self.x - self.base_x)**2 + (self.y - self.base_y)**2)
        self.is_at_base = dist_to_base < 3.0
        
        # Recharge à la base
        if self.is_at_base:
            self.battery = min(100.0, self.battery + 5.0)
        
        # Gestion des modes
        if self.battery < 20.0:
            # Batterie faible : retour à la base
            self.mode = 'return'
            self.target_x = self.base_x
            self.target_y = self.base_y
        elif self.mode == 'explore':
            # Scanner la zone actuelle
            is_anomaly, intensity = self.scan_area(environment)
            
            # Sélectionner une nouvelle cible si nécessaire
            if self.target_x is None or self.target_y is None:
                self.select_exploration_target(environment, other_drones)
            elif np.sqrt((self.x - self.target_x)**2 + (self.y - self.target_y)**2) < 3.0:
                self.select_exploration_target(environment, other_drones)
        
        # Déplacement vers la cible
        if self.target_x is not None and self.target_y is not None:
            self.move_towards(self.target_x, self.target_y, environment)
        
        # Si batterie rechargée à la base, reprendre l'exploration
        if self.is_at_base and self.battery > 80.0 and self.mode == 'return':
            self.mode = 'explore'
            self.target_x = None
    
    def can_transmit_to_control(self):
        """Vérifie si le drone peut transmettre au centre de contrôle."""
        # Le drone peut toujours transmettre depuis sa position actuelle
        return True
    
    def can_receive_updates(self):
        """Vérifie si le drone peut recevoir des mises à jour."""
        # Le drone ne peut recevoir des mises à jour qu'à la base
        return self.is_at_base
