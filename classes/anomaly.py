import numpy as np
from dataclasses import dataclass

@dataclass
class Anomaly:
    """Représente une anomalie dans l'environnement."""
    x: float
    y: float
    intensity: float  # 0.0 à 1.0
    radius: float
    type: str  # 'pluie_meteorites', 'radiation', 'inondations', etc.
    
    def get_sensor_reading(self, drone_x, drone_y):
        """
        Calcule les valeurs des capteurs en fonction de la distance au drone.
        Retourne : [température, radiation, pluie de météorites, inondations]
        """
        distance = np.sqrt((drone_x - self.x)**2 + (drone_y - self.y)**2)
        
        # Influence diminue avec la distance (modèle gaussien)
        influence = self.intensity * np.exp(-(distance**2) / (2 * self.radius**2))
        
        # Valeurs de base (environnement normal)
        base_temp = 20.0
        base_radiation = 0.1
        base_meteorites = 0.1
        base_floods = 0.1
        
        # Modification selon le type d'anomalie
        if self.type == 'pluie_meteorites':
            return [base_temp + 10*influence, base_radiation, 
                   base_meteorites + influence, base_floods]
        elif self.type == 'radiation':
            return [base_temp + 15*influence, base_radiation + influence, 
                   base_meteorites, base_floods]
        elif self.type == 'inondations':
            return [base_temp + 5*influence, base_radiation, 
                   base_meteorites + influence*0.3, base_floods + influence]
        else:
            return [base_temp + 8*influence, base_radiation + influence*0.5, 
                   base_meteorites + influence*0.5, base_floods + influence*0.5]
    
    def evolve(self, step):
        """
        Fait évoluer l'anomalie au fil du temps.
        Chaque type d'anomalie a un comportement spécifique.
        """
        if self.type == 'pluie_meteorites':
            # Pluie de météorites : intensité variable (fluctuations)
            variation = np.sin(step * 0.1) * 0.15
            self.intensity = max(0.3, min(1.0, self.intensity + variation))
            
        elif self.type == 'radiation':
            # Radiation : se propage lentement (rayon augmente)
            if step % 20 == 0:  # Tous les 20 pas de temps
                self.radius = min(self.radius + 0.2, 20)  # Max 20
                # Intensité diminue légèrement avec la propagation
                self.intensity = max(0.4, self.intensity - 0.01)
                
        elif self.type == 'inondations':
            # Inondations : s'étend puis se résorbe
            if step < 100:
                # Phase d'expansion
                if step % 15 == 0:
                    self.radius = min(self.radius + 0.5, 18)
                    self.intensity = min(1.0, self.intensity + 0.02)
            else:
                # Phase de résorption
                if step % 25 == 0:
                    self.radius = max(5, self.radius - 0.3)
                    self.intensity = max(0.3, self.intensity - 0.015)
