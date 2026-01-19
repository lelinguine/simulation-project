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
        
        # État du drone avec gestion temporelle
        self.activity_time = 0.0  # en secondes
        self.max_activity_time = 30 * 60  # 30 minutes = 1800 secondes
        self.recharge_time = 0.0
        self.max_recharge_time = 10 * 60  # 10 minutes = 600 secondes
        self.is_charging = False
        self.is_at_base = False
        self.has_returned_to_base = False  # Indicateur de retour à la base au moins une fois
        self.detected_anomalies = []  # Anomalies détectées par ce drone
        self.anomaly_queue = []  # File d'attente des anomalies à analyser
        self.path_history = [(x, y)]
        
        # Carte d'exploration individuelle (100x100 par défaut)
        self.exploration_map = None  # Sera initialisée lors du premier update
        
        # Paramètres de mouvement
        self.speed = 2.0
        self.measurement_time = 0.0  # Temps de mesure actuel
        self.measurement_duration = 10.0  # 10 secondes pour mesure approfondie
        self.is_measuring = False
        self.direction_x = 1.0  # Direction de mouvement (normalisée)
        self.direction_y = 0.0
        
        # Mode d'exploration
        self.target_x = None
        self.target_y = None
        self.mode = 'explore'  # 'explore', 'return', 'charging', 'measuring'
        
    def move_towards(self, target_x, target_y, environment, delta_time=1.0):
        """Déplace le drone vers une cible."""
        dx = target_x - self.x
        dy = target_y - self.y
        distance = np.sqrt(dx**2 + dy**2)
        
        if distance < self.speed:
            self.x = target_x
            self.y = target_y
        else:
            # Mettre à jour la direction du drone
            self.direction_x = dx / distance
            self.direction_y = dy / distance
            self.x += self.direction_x * self.speed
            self.y += self.direction_y * self.speed
        
        # Contraintes de l'environnement
        self.x = max(0, min(self.x, environment.width))
        self.y = max(0, min(self.y, environment.height))
        
        # Consommation énergétique quasi-nulle (tend vers 0)
        self.activity_time += delta_time * 0.01  # Très faible consommation pour déplacement
        
        # Marquer comme exploré dans la carte locale du drone (rayon 3)
        if self.exploration_map is not None:
            self.mark_explored_local(self.x, self.y, environment.width, environment.height)
        self.path_history.append((self.x, self.y))
        
    def scan_area(self, environment, delta_time=1.0):
        """Scanne un carré 5×5 centré sur le drone pour détecter des anomalies."""
        # Si déjà en train de mesurer, continuer
        if self.is_measuring:
            self.measurement_time += delta_time
            if self.measurement_time >= self.measurement_duration:
                # Mesure terminée
                self.is_measuring = False
                self.measurement_time = 0.0
                return True, getattr(self, '_measuring_intensity', 0.0)
            return False, 0.0  # Encore en mesure
        
        # Scanner toutes les anomalies dans la zone de détection 5×5
        for anomaly in environment.anomalies:
            # Vérifier si l'anomalie est dans la zone de scan du drone (carré 5×5)
            dist_x = abs(anomaly.x - self.x)
            dist_y = abs(anomaly.y - self.y)
            
            # Si l'anomalie est dans le carré 5×5 (rayon 2.5 unités)
            if dist_x <= 2.5 and dist_y <= 2.5:
                pos = (int(anomaly.x), int(anomaly.y))
                
                # Vérifier si cette anomalie exacte est déjà dans les détections
                already_scanned = any(
                    a['position'][0] == pos[0] and a['position'][1] == pos[1]
                    for a in self.detected_anomalies
                )
                
                # Vérifier si déjà dans la file d'attente
                in_queue = any(
                    a['position'][0] == pos[0] and a['position'][1] == pos[1]
                    for a in self.anomaly_queue
                )
                
                # Ajouter à la queue si nouvelle (pas encore scannée ni en attente)
                if not already_scanned and not in_queue:
                    self.anomaly_queue.append({
                        'position': pos,
                        'intensity': anomaly.intensity
                    })
        
        return False, 0.0
    
    def mark_explored_local(self, x, y, width, height):
        """Marque un carré 5×5 centré sur le drone comme exploré dans la carte locale."""
        # Initialiser la carte si nécessaire
        if self.exploration_map is None:
            self.exploration_map = np.zeros((height, width))
        
        x_int, y_int = int(x), int(y)
        # Carré 5×5 : de -2 à +2
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                nx, ny = x_int + dx, y_int + dy
                if 0 <= nx < width and 0 <= ny < height:
                    self.exploration_map[ny, nx] = 1
    
    def select_exploration_target(self, environment, other_drones):
        """
        Sélectionne une nouvelle cible d'exploration.
        Stratégie : zones non explorées (selon la carte locale) les plus éloignées des autres drones.
        """
        # Initialiser la carte locale si nécessaire
        if self.exploration_map is None:
            self.exploration_map = np.zeros((environment.height, environment.width))
        
        # Recherche de zones non explorées dans la carte locale
        unexplored = np.argwhere(self.exploration_map == 0)
        
        if len(unexplored) == 0:
            # Tout est exploré, patrouille aléatoire pour détecter de nouvelles anomalies
            # Choisir une position aléatoire sur la carte
            self.target_x = np.random.uniform(5, environment.width - 5)
            self.target_y = np.random.uniform(5, environment.height - 5)
            return
        
        # Stratégie améliorée : sélectionner une cible éloignée mais accessible
        if random.random() < 0.2:  # 20% aléatoire pour diversifier
            idx = random.randint(0, len(unexplored)-1)
            target = unexplored[idx]
            self.target_x = target[1]
            self.target_y = target[0]
        else:
            # Sélectionner une zone éloignée en évitant les zones des autres drones
            max_score = -1
            best_target = unexplored[0]
            
            # Sous-échantillonner pour performance
            sample_size = min(100, len(unexplored))
            samples = unexplored[np.random.choice(len(unexplored), sample_size, replace=False)]
            
            for point in samples:
                # Distance à la position actuelle
                dist_to_self = np.sqrt((point[1] - self.x)**2 + (point[0] - self.y)**2)
                
                # Distance aux autres drones (favoriser zones éloignées)
                min_dist_to_others = float('inf')
                for other in other_drones:
                    if other.id != self.id:
                        dist = np.sqrt((point[1] - other.x)**2 + (point[0] - other.y)**2)
                        min_dist_to_others = min(min_dist_to_others, dist)
                
                # Score : privilégier zones moyennement éloignées et loin des autres
                score = min(dist_to_self, 40) + 0.5 * min(min_dist_to_others, 30)
                
                if score > max_score:
                    max_score = score
                    best_target = point
            
            self.target_x = best_target[1]
            self.target_y = best_target[0]
    
    def update(self, environment, other_drones, delta_time=1.0, control_center=None):
        """Mise à jour de l'état du drone à chaque pas de temps."""
        # Initialiser la carte d'exploration locale si nécessaire
        if self.exploration_map is None:
            self.exploration_map = np.zeros((environment.height, environment.width))
        
        # Vérifier si à la base
        dist_to_base = np.sqrt((self.x - self.base_x)**2 + (self.y - self.base_y)**2)
        self.is_at_base = dist_to_base < 3.0
        
        # Gestion de la recharge à la base (10 minutes)
        if self.is_at_base and self.is_charging:
            # Marquer comme ayant retourné à la base
            self.has_returned_to_base = True
            
            # Synchronisation avec le centre de contrôle au début de la recharge
            if self.recharge_time == 0.0 and control_center:
                # Transmettre les découvertes au centre
                control_center.receive_transmission(self)
                # Recevoir la carte globale du centre
                control_center.send_update_to_drone(self)
            
            self.recharge_time += delta_time
            if self.recharge_time >= self.max_recharge_time:
                # Recharge complète
                self.is_charging = False
                self.recharge_time = 0.0
                self.activity_time = 0.0
                self.mode = 'explore'
                self.target_x = None
            return  # Ne fait rien pendant la recharge
        
        # Gestion de la mesure approfondie (10 secondes)
        if self.mode == 'measuring':
            self.activity_time += delta_time
            is_complete, intensity = self.scan_area(environment, delta_time)
            if is_complete:
                # Mesure terminée, enregistrer l'anomalie
                anomaly_info = {
                    'position': self._measuring_position,
                    'intensity': intensity,
                    'timestamp': len(self.path_history)
                }
                self.detected_anomalies.append(anomaly_info)
                self.mode = 'explore'
            return  # Ne bouge pas pendant la mesure
        
        # Vérifier si besoin de recharger (30 minutes d'activité)
        if self.activity_time >= self.max_activity_time:
            # Temps d'activité écoulé : retour à la base
            self.mode = 'return'
            self.target_x = self.base_x
            self.target_y = self.base_y
            
            # Si arrivé à la base, commencer la recharge
            if self.is_at_base:
                self.is_charging = True
                self.mode = 'charging'
                return
        
        # Gestion des modes
        if self.mode == 'explore':
            # Incrémenter le temps d'activité
            self.activity_time += delta_time
            
            # Scanner la zone actuelle (ajoute des anomalies à la queue)
            is_anomaly, intensity = self.scan_area(environment, delta_time)
            
            # PRIORITÉ 1 : Traiter la queue d'anomalies
            if len(self.anomaly_queue) > 0:
                target_anomaly = self.anomaly_queue[0]
                
                # Définir la cible vers cette anomalie
                self.target_x = target_anomaly['position'][0]
                self.target_y = target_anomaly['position'][1]
                
                # Vérifier si on est au-dessus
                dist_to_anomaly = np.sqrt((self.x - self.target_x)**2 + (self.y - self.target_y)**2)
                if dist_to_anomaly < 1.0:
                    # Démarrer la mesure et retirer de la queue
                    self.is_measuring = True
                    self.measurement_time = 0.0
                    self._measuring_intensity = target_anomaly['intensity']
                    self._measuring_position = target_anomaly['position']
                    self.anomaly_queue.pop(0)
                    self.mode = 'measuring'
                    return  # Ne pas bouger, on mesure
            
            # PRIORITÉ 2 : Exploration normale (seulement si pas d'anomalie en queue)
            elif self.target_x is None or self.target_y is None:
                # Pas de cible, en choisir une nouvelle
                self.select_exploration_target(environment, other_drones)
            else:
                # Vérifier si on est arrivé à la cible d'exploration
                dist_to_target = np.sqrt((self.x - self.target_x)**2 + (self.y - self.target_y)**2)
                if dist_to_target < 2.0:
                    # Arrivé à destination, nouvelle cible
                    self.select_exploration_target(environment, other_drones)
        
        elif self.mode == 'return':
            # En cours de retour vers la base
            self.activity_time += delta_time
            if self.is_at_base:
                self.is_charging = True
                self.mode = 'charging'
                return
        
        # Déplacement vers la cible
        if self.target_x is not None and self.target_y is not None and self.mode != 'measuring':
            self.move_towards(self.target_x, self.target_y, environment, delta_time)
    
    def can_receive_updates(self):
        """Vérifie si le drone peut recevoir des mises à jour."""
        # Le drone ne peut recevoir des mises à jour qu'à la base
        return self.is_at_base
    
    @property
    def status_text(self):
        """Retourne le statut textuel du drone."""
        sync_indicator = "[✓]" if self.has_returned_to_base else "[✗]"
        if self.is_charging:
            return f"{sync_indicator} Recharge ({self.recharge_time:.0f}s/{self.max_recharge_time:.0f}s)"
        elif self.is_measuring:
            return f"{sync_indicator} Mesure ({self.measurement_time:.0f}s/{self.measurement_duration:.0f}s)"
        elif self.is_at_base:
            return f"{sync_indicator} À la base"
        else:
            return f"{sync_indicator} En mission ({self.activity_time:.0f}s/{self.max_activity_time:.0f}s)"
