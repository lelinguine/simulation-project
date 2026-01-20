import numpy as np
import random
from dataclasses import dataclass
import config

@dataclass
class Anomaly:
    """Représente une anomalie dans l'environnement."""
    x: float
    y: float
    intensity: int  # 1 = faible, 2 = forte
    radius: float
    type: str  # 'pluie_meteorites', 'radiation', 'inondations', etc.
    treated: bool = False  # Indique si l'anomalie a été neutralisée
    being_treated_by: int = -1  # ID du drone en train de traiter (-1 = personne)
    
    def is_intense(self):
        """Retourne True si l'anomalie est intense (intensité == 2)."""
        return self.intensity == 2
    
    def get_sensor_reading(self, drone_x, drone_y):
        """
        Calcule les valeurs des capteurs en fonction de la distance au drone.
        Retourne : [température, radiation, pluie de météorites, inondations]
        """
        distance = np.sqrt((drone_x - self.x)**2 + (drone_y - self.y)**2)
        
        # Influence diminue avec la distance (modèle gaussien)
        # Normaliser intensity: 1=0.5, 2=1.0
        normalized_intensity = self.intensity / 2.0
        influence = normalized_intensity * np.exp(-(distance**2) / (2 * self.radius**2))
        
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
    
    def evolve(self, step, environment):
        """
        Fait évoluer l'anomalie au fil du temps.
        
        - Snowball: anomalie faible peut devenir intense
        - Spread: anomalie intense peut propager sur cases adjacentes
        - Comportement spécifique selon le type
        
        Args:
            step: Numéro du tour actuel
            environment: Référence à l'environnement pour propager
        """
        if self.treated:
            return  # Anomalie déjà traitée, pas d'évolution
        
        # SNOWBALL : Anomalie faible → intense
        if self.intensity == 1:  # Si faible
            if np.random.random() < config.ANOMALY_SNOWBALL_CHANCE:
                # Passe de faible à intense
                self.intensity = 2  # Devient intense
        
        # SPREAD : Anomalie intense propage sur cases adjacentes
        if self.intensity == 2:  # Si intense
            if np.random.random() < config.ANOMALY_SPREAD_CHANCE:
                # Tenter de propager sur une case adjacente aléatoire
                # Chercher les cases voisines disponibles
                available_neighbors = []
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue  # Pas de propagation sur soi-même
                        
                        new_x = int(self.x + dx)
                        new_y = int(self.y + dy)
                        
                        # Vérifier que la case est dans les limites
                        if not (0 <= new_x < environment.width and 0 <= new_y < environment.height):
                            continue
                        
                        # Vérifier qu'il n'y a pas déjà d'anomalie à cette position exacte
                        can_spread = True
                        
                        # Vérifier pas sur la base
                        if hasattr(environment, 'base_x') and hasattr(environment, 'base_y'):
                            dist_to_base = np.sqrt((new_x - environment.base_x)**2 + (new_y - environment.base_y)**2)
                            if dist_to_base < 2.0:  # Très proche de la base
                                can_spread = False
                        
                        # Vérifier pas d'autre anomalie à cette MÊME position (tolérance 0.5)
                        if can_spread:
                            for other_anomaly in environment.anomalies:
                                if (abs(new_x - int(other_anomaly.x)) <= 0 and 
                                    abs(new_y - int(other_anomaly.y)) <= 0):
                                    can_spread = False
                                    break
                        
                        if can_spread:
                            available_neighbors.append((new_x, new_y))
                
                # Si au moins une case voisine est disponible, propager
                if available_neighbors:
                    new_x, new_y = random.choice(available_neighbors)
                    # Créer nouvelle anomalie FAIBLE
                    new_anomaly = Anomaly(
                        x=float(new_x),
                        y=float(new_y),
                        intensity=1,  # Toujours faible lors de propagation
                        radius=self.radius * 0.8,  # Rayon légèrement réduit
                        type=self.type,
                        treated=False
                    )
                    environment.anomalies.append(new_anomaly)
        
        # Comportement spécifique au type d'anomalie
        # Note: avec intensité 1 ou 2, pas de variation continue
        # Les variations se font via snowball (1→2) uniquement
            
        elif self.type == 'radiation':
            # Radiation : se propage lentement (rayon augmente)
            if step % 20 == 0:  # Tous les 20 pas de temps
                self.radius = min(self.radius + 0.2, 20)  # Max 20
                
        elif self.type == 'inondations':
            # Inondations : s'étend puis se résorbe
            if step < 100:
                # Phase d'expansion
                if step % 15 == 0:
                    self.radius = min(self.radius + 0.5, 18)
            else:
                # Phase de résorption
                if step % 25 == 0:
                    self.radius = max(5, self.radius - 0.3)
    
    def get_intervention_type(self):
        """
        Détermine le type d'intervention nécessaire selon l'anomalie et son intensité.
        Retourne : dict avec 'type' (HUMAN/ROBOT), 'urgency' (LOW/MEDIUM/HIGH/CRITICAL)
                   et 'description' de l'action recommandée
        
        Intensité: 1=faible, 2=intense
        """
        is_intense = (self.intensity == 2)
        
        if self.type == 'radiation':
            if is_intense:
                return {
                    'type': 'HUMAN',
                    'urgency': 'CRITICAL',
                    'description': 'Équipe spécialisée avec protection anti-radiation requise',
                    'equipment': ['Combinaisons protection', 'Détecteurs radiation', 'Équipe décontamination']
                }
            else:
                return {
                    'type': 'ROBOT',
                    'urgency': 'MEDIUM',
                    'description': 'Surveillance robotique et mesures préventives',
                    'equipment': ['Drone surveillance', 'Balises périmètre']
                }
        
        elif self.type == 'inondations':
            if is_intense:
                return {
                    'type': 'HUMAN',
                    'urgency': 'HIGH',
                    'description': 'Équipe évacuation et pompage d\'urgence',
                    'equipment': ['Pompes haute capacité', 'Équipe sauvetage', 'Barrières anti-inondation']
                }
            else:
                return {
                    'type': 'ROBOT',
                    'urgency': 'LOW',
                    'description': 'Surveillance automatique du niveau d\'eau',
                    'equipment': ['Capteurs automatiques', 'Système d\'alerte']
                }
        
        elif self.type == 'pluie_meteorites':
            if is_intense:
                return {
                    'type': 'HUMAN',
                    'urgency': 'CRITICAL',
                    'description': 'Évacuation immédiate et équipe d\'intervention d\'urgence',
                    'equipment': ['Équipe évacuation', 'Unité médicale', 'Protection anti-débris']
                }
            else:
                return {
                    'type': 'ROBOT',
                    'urgency': 'MEDIUM',
                    'description': 'Inspection robotique de la zone d\'impact',
                    'equipment': ['Drones inspection', 'Capteurs thermiques']
                }
        
        # Type inconnu
        return {
            'type': 'HUMAN',
            'urgency': 'MEDIUM',
            'description': 'Inspection humaine pour évaluation',
            'equipment': ['Équipe reconnaissance']
        }
