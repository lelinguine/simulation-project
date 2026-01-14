import numpy as np
from dataclasses import dataclass

@dataclass
class Anomaly:
    """Représente une anomalie dans l'environnement."""
    x: float
    y: float
    intensity: float  # 0.0 à 1.0
    radius: float
    type: str  # 'pollution', 'radiation', 'effondrement', etc.
    
    def get_sensor_reading(self, drone_x, drone_y):
        """
        Calcule les valeurs des capteurs en fonction de la distance au drone.
        Retourne : [température, radiation, pollution, mouvement, bruit]
        """
        distance = np.sqrt((drone_x - self.x)**2 + (drone_y - self.y)**2)
        
        # Influence diminue avec la distance (modèle gaussien)
        influence = self.intensity * np.exp(-(distance**2) / (2 * self.radius**2))
        
        # Valeurs de base (environnement normal)
        base_temp = 20.0
        base_radiation = 0.1
        base_pollution = 0.1
        base_movement = 0.1
        base_noise = 0.1
        
        # Modification selon le type d'anomalie
        if self.type == 'pollution':
            return [base_temp + 10*influence, base_radiation, 
                   base_pollution + influence, base_movement, base_noise + influence*0.5]
        elif self.type == 'radiation':
            return [base_temp + 15*influence, base_radiation + influence, 
                   base_pollution, base_movement, base_noise + influence*0.3]
        elif self.type == 'effondrement':
            return [base_temp + 5*influence, base_radiation, 
                   base_pollution + influence*0.3, base_movement + influence, base_noise + influence]
        else:
            return [base_temp + 8*influence, base_radiation + influence*0.5, 
                   base_pollution + influence*0.5, base_movement + influence*0.5, base_noise + influence*0.5]
