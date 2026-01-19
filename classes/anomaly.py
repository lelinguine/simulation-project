import numpy as np
from dataclasses import dataclass

@dataclass
class Anomaly:
    """Représente une anomalie dans l'environnement."""
    x: float
    y: float
    intensity: float  # 0.0 à 2.0+
    radius: float
    type: str  # 'pollution', 'radiation', 'effondrement', etc.
    creation_time: float = 0.0  # Temps de création
    is_propagating: bool = True  # Si l'anomalie peut se propager
    propagation_cooldown: float = 0.0  # Temps avant prochaine propagation
    
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
    
    def evolve(self, current_time, environment, delta_time=1.0):
        """
        Fait évoluer l'anomalie dans le temps.
        - Propagation : création de nouvelles anomalies à proximité
        """
        # PROPAGATION (création de nouvelles anomalies)
        if self.is_propagating and self.intensity > 0.5:
            self.propagation_cooldown -= delta_time
            
            if self.propagation_cooldown <= 0:
                # Probabilité de propagation basée sur l'intensité (réduite pour simulation longue)
                if np.random.random() < 0.03 * self.intensity * delta_time:
                    # Créer une nouvelle anomalie à proximité
                    angle = np.random.random() * 2 * np.pi
                    distance = self.radius * np.random.uniform(0.8, 1.5)
                    
                    new_x = self.x + distance * np.cos(angle)
                    new_y = self.y + distance * np.sin(angle)
                    
                    # Vérifier que c'est dans l'environnement
                    if 0 <= new_x < environment.width and 0 <= new_y < environment.height:
                        new_anomaly = Anomaly(
                            x=new_x,
                            y=new_y,
                            intensity=self.intensity * 0.6,  # Intensité réduite
                            radius=self.radius * 0.8,
                            type=self.type,
                            creation_time=current_time,
                            is_propagating=True,
                            propagation_cooldown=300.0  # Cooldown de 300 secondes (5min)
                        )
                        environment.add_anomaly(new_anomaly)
                        
                        # Reset cooldown (augmenté pour ralentir la propagation)
                        self.propagation_cooldown = 600.0 + np.random.uniform(0, 300)
        
        return 'keep'  # Garder l'anomalie
