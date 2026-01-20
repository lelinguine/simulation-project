import numpy as np
import random
import config

class Drone:
    """
    Drone autonome avec cartes personnelles et stratégies:
    
    CARTES PERSONNELLES:
    - Chaque drone a sa propre carte d'exploration
    - Communication avec autres drones dans périmètre (partage infos)
    - Transmission en temps réel au centre de contrôle
    - Synchronisation complète à la base
    
    VÉRIFICATION BATTERIE:
    - Avant chaque action: vérifier batterie suffisante pour action + retour
    - Communication de l'action prévue aux drones voisins (éviter doublons)
    
    STRATÉGIES (config.ROBOT_STRATEGY):
    - 'action': Explore → si anomalie détectée → traite immédiatement → reprend
    - 'exploration': Explore 100% carte AVANT de traiter anomalies
    - 'mixte': Explore → si anomalie → va vers elle, si plus urgente en route → traite urgente d'abord
    """
    
    def __init__(self, drone_id, x, y, detector, base_x=0, base_y=0, 
                 vision_radius=5.0, movement_cost=0.5):
        """
        Initialise un drone avec des paramètres configurables.
        
        Args:
            drone_id: Identifiant unique
            x, y: Position initiale
            detector: Détecteur d'anomalies (AnomalyDetector)
            base_x, base_y: Position de la base
            vision_radius: Rayon de vision circulaire (détection anomalies)
            movement_cost: Batterie consommée par déplacement
        
        Note: Les coûts de traitement sont définis dans config (TREATMENT_COST_WEAK/INTENSE)
        """
        self.id = drone_id
        self.x = x
        self.y = y
        self.base_x = base_x
        self.base_y = base_y
        self.detector = detector
        
        # Paramètres de mouvement
        self.speed = 2.0
        self.vision_radius = vision_radius
        self.movement_cost = movement_cost
        
        # État du drone
        self.battery = 150.0
        self.battery_max = 150.0
        self.is_at_base = False
        self.path_history = [(x, y)]
        self.events = []  # Historique détaillé des déplacements
        
        # Carte personnelle du monde exploré (UNIQUEMENT CE DRONE)
        self.personal_exploration_map = {}  # Position -> booléen exploré
        self.personal_anomaly_map = {}  # Position -> {'intensity': float, 'anomaly': obj}
        
        # Anomalies à traiter (détectées par ce drone ou reçues par communication)
        self.detected_anomalies = []  # Liste d'anomalies à traiter
        self.anomalies_treated = []  # Liste des anomalies déjà traitées
        self.anomalies_being_treated_by_others = {}  # {pos: drone_id} anomalies en cours par d'autres
        self.direct_detections = set()  # Positions des anomalies détectées DIRECTEMENT par ce drone (pas par transmission)
        
        # Zones d'exploration ciblées par d'autres drones
        self.zones_being_explored_by_others = {}  # {pos: drone_id} zones ciblées par d'autres
        
        # Cible actuelle
        self.target_x = None
        self.target_y = None
        self.target_anomaly = None  # Si en train de traiter une anomalie
        
        # Flag pour détecter quand on ne peut plus explorer depuis la base
        self.exploration_blocked_from_base = False
        
        # Statistiques d'activité (compteurs de tours)
        self.activity_stats = {
            'recharging': 0,      # À la base en recharge
            'moving': 0,          # En déplacement vers cible
            'exploring': 0,       # En exploration active
            'treating': 0,        # En traitement d'anomalie
            'waiting': 0          # En attente (aucune action possible)
        }
        
        # Référence au centre de contrôle (sera défini après initialisation)
        self.control_center = None

    def log_event(self, action, start_pos, end_pos, battery_after):
        """Enregistre un événement de déplacement ou de retour."""
        self.events.append({
            'step': getattr(self, 'current_step', None),
            'action': action,
            'start_x': start_pos[0],
            'start_y': start_pos[1],
            'end_x': end_pos[0],
            'end_y': end_pos[1],
            'battery': battery_after
        })
        
    def calculate_distance(self, x1, y1, x2, y2):
        """Calcule la distance euclidienne."""
        return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
    
    def calculate_return_cost(self):
        """
        Calcule le coût (batterie) pour retourner à la base depuis la position actuelle.
        """
        distance = self.calculate_distance(self.x, self.y, self.base_x, self.base_y)
        # Coût énergie = distance * coût unitaire (indépendant de la vitesse)
        return distance * self.movement_cost
    
    def can_still_explore(self, environment):
        """
        Détermine s'il reste des zones non explorées atteignables.
        
        Logique :
        1. Vérifie d'abord si le robot PEUT revenir à la base avec sa batterie actuelle
        2. Si non → exploration impossible (robot bloqué)
        3. Si oui → suppose que le robot recharge à la base jusqu'à 85% du max
        4. Identifie les zones non explorées (échantillonnage de la carte)
        5. Pour chaque zone : calcule coût = distance(base→zone) + distance(zone→base)
        6. Si au moins une zone est atteignable avec 85% de batterie, retourne True
        7. Sinon, l'exploration est physiquement impossible → retourne False
        
        Returns:
            bool: True si exploration encore possible, False sinon
        """
        # ÉTAPE 1 : Vérifier d'abord si le robot peut revenir à la base
        return_cost = self.calculate_return_cost()
        if self.battery < return_cost:
            # Robot bloqué, ne peut pas revenir à la base !
            return False  # Exploration impossible
        
        # ÉTAPE 2 : Hypothèse : robot revient à la base et recharge jusqu'à 85%
        effective_battery = self.battery_max * config.BATTERY_DEPARTURE_THRESHOLD
        
        # ÉTAPE 3 : Échantillonner la carte pour trouver des zones non explorées
        unexplored_zones = []
        for y in range(0, environment.height, 10):
            for x in range(0, environment.width, 10):
                if environment.exploration_map[y, x] == 0:
                    unexplored_zones.append((x, y))
        
        # Si tout est exploré, pas besoin de continuer
        if not unexplored_zones:
            return False
        
        # ÉTAPE 4 : Calculer la batterie nécessaire pour atteindre chaque zone non explorée
        # depuis la base et revenir
        for zone_x, zone_y in unexplored_zones:
            # Distance base → zone
            dist_to_zone = self.calculate_distance(self.base_x, self.base_y, zone_x, zone_y)
            # Distance zone → base (retour)
            dist_back = dist_to_zone  # Même distance pour le retour
            
            # Coût total pour un aller-retour (distance * coût unitaire)
            total_distance = dist_to_zone + dist_back
            total_cost = total_distance * self.movement_cost
            
            # Si au moins une zone est accessible avec la batterie de départ réelle, exploration possible
            if total_cost <= effective_battery:
                return True
        
        # Aucune zone n'est atteignable → exploration impossible
        return False
    
    def should_return_to_base(self):
        """
        Décide si le drone doit retourner à la base.
        TOUJOURS vérifier d'abord si la batterie courante suffit pour revenir.
        Si non, retour immédiat (situation d'urgence).
        """
        return_cost = self.calculate_return_cost()
        
        # Urgence : batterie insuffisante pour revenir → retour immédiat
        if self.battery < return_cost:
            return True
        
        # Si à la base et batterie très faible (< 15%), rester à la base
        if self.is_at_base and self.battery < (self.battery_max * 0.15):
            return True
        
        return False
    
    def can_perform_action(self, action_cost):
        """
        Vérifie si le drone peut effectuer une action donnée.
        
        Args:
            action_cost: Coût en batterie de l'action prévue
        
        Returns:
            True si batterie_après_action >= coût_retour_base
        """
        battery_after_action = self.battery - action_cost
        return_cost = self.calculate_return_cost()
        return battery_after_action >= return_cost
    
    def announce_next_action(self, action_type, target_pos, other_drones, anomaly_info=None):
        """
        Communique l'action prévue aux drones à proximité.
        Appelée APRÈS vérification batterie et sélection d'action.
        
        Args:
            action_type: 'treat_anomaly', 'explore', 'return_base'
            target_pos: (x, y) de la cible
            other_drones: Liste des autres drones
            anomaly_info: Info de l'anomalie si action = treat_anomaly
        """
        self.next_planned_action = {
            'type': action_type,
            'target': target_pos,
            'drone_id': self.id,
            'anomaly': anomaly_info
        }
        
        # Communiquer aux drones proches
        for other_drone in other_drones:
            if other_drone.id == self.id:
                continue
            
            distance = self.calculate_distance(
                self.x, self.y,
                other_drone.x, other_drone.y
            )
            
            if distance <= config.COMMUNICATION_RADIUS:
                other_drone.receive_action_announcement(self.next_planned_action)
    
    def receive_action_announcement(self, action_info):
        """
        Reçoit l'annonce d'action d'un autre drone.
        Marque l'anomalie comme "en cours de traitement" pour ne pas la cibler.
        Marque aussi les zones d'exploration ciblées pour éviter les doublons.
        """
        target_pos = action_info['target']
        pos_key = (int(target_pos[0]), int(target_pos[1]))
        drone_id = action_info['drone_id']
        
        if action_info['type'] == 'treat_anomaly':
            # Marquer comme en cours de traitement par l'autre drone
            self.anomalies_being_treated_by_others[pos_key] = drone_id
            
            # En mode exploration, GARDER l'anomalie en backup au cas où l'autre échoue
            # Dans les autres modes, la retirer pour éviter les doublons
            if config.ROBOT_STRATEGY != 'exploration':
                self.detected_anomalies = [
                    a for a in self.detected_anomalies 
                    if (int(a['position'][0]), int(a['position'][1])) != pos_key
                ]
            
            # Si c'était ma cible, annuler et chercher autre chose
            if self.target_anomaly and (int(self.target_x), int(self.target_y)) == pos_key:
                self.target_anomaly = None
                self.target_x = None
                self.target_y = None
        
        elif action_info['type'] == 'explore':
            # Marquer la zone comme étant explorée par un autre drone
            # On marque une zone autour de la cible (rayon de vision)
            target_x, target_y = target_pos
            for dx in range(-15, 16):  # Rayon de vision approximatif
                for dy in range(-15, 16):
                    if dx*dx + dy*dy <= 15*15:  # Cercle de rayon vision_radius
                        zone_key = (int(target_x + dx), int(target_y + dy))
                        self.zones_being_explored_by_others[zone_key] = drone_id
            
            # Si ma cible est dans cette zone, annuler et chercher ailleurs
            if self.target_x is not None and self.target_y is not None:
                my_pos_key = (int(self.target_x), int(self.target_y))
                if my_pos_key in self.zones_being_explored_by_others:
                    self.target_x = None
                    self.target_y = None
                    self.target_anomaly = None
    
    def share_exploration_map(self, other_drone):
        """
        Partage sa carte d'exploration avec un autre drone.
        Inclut : zones explorées + anomalies détectées + anomalies en traitement par d'autres + cible actuelle
        """
        # Partager les zones explorées
        for pos, explored in self.personal_exploration_map.items():
            if explored and pos not in other_drone.personal_exploration_map:
                other_drone.personal_exploration_map[pos] = True
        
        # Partager les anomalies détectées
        for pos, anomaly_data in self.personal_anomaly_map.items():
            if pos not in other_drone.personal_anomaly_map:
                other_drone.personal_anomaly_map[pos] = anomaly_data
                # Ajouter à la liste des anomalies à traiter si pertinent
                # Vérifier que ce n'est pas déjà dans la liste (éviter les doublons lors de communications répétées)
                anomaly_pos = anomaly_data.get('position')
                already_in_detected = any(a.get('position') == anomaly_pos for a in other_drone.detected_anomalies)
                if not already_in_detected and pos not in self.anomalies_being_treated_by_others:
                    other_drone.detected_anomalies.append(anomaly_data)
        
        # Partager les anomalies en cours de traitement par d'autres
        for pos, drone_id in self.anomalies_being_treated_by_others.items():
            other_drone.anomalies_being_treated_by_others[pos] = drone_id
        
        # Partager MA CIBLE ACTUELLE pour éviter que l'autre drone aille au même endroit
        if self.target_x is not None and self.target_y is not None and self.target_anomaly is None:
            # Seulement si c'est une cible d'exploration (pas une anomalie)
            # Marquer une zone autour de ma cible comme "en cours d'exploration par moi"
            for dx in range(-15, 16):
                for dy in range(-15, 16):
                    if dx*dx + dy*dy <= 225:  # Rayon 15 (vision_radius)
                        zone_key = (int(self.target_x + dx), int(self.target_y + dy))
                        if 0 <= zone_key[0] < 100 and 0 <= zone_key[1] < 100:  # Limites de la carte
                            other_drone.zones_being_explored_by_others[zone_key] = self.id
    
    def sync_with_control_center(self, control_center):
        """
        Synchronise avec le centre de contrôle (100% des infos).
        APPELÉE quand le drone est à la base et s'apprête à partir en mission.
        """
        if not self.is_at_base:
            return False
        
        # Recevoir TOUTES les informations du centre de contrôle
        # CARTE D'EXPLORATION GLOBALE
        for y in range(control_center.global_exploration_map.shape[0]):
            for x in range(control_center.global_exploration_map.shape[1]):
                if control_center.global_exploration_map[y, x] == 1:
                    pos_key = (x, y)
                    if pos_key not in self.personal_exploration_map:
                        self.personal_exploration_map[pos_key] = True
        
        # ANOMALIES DÉTECTÉES GLOBALES
        for pos, anomaly_data in control_center.global_anomaly_map.items():
            if pos not in self.personal_anomaly_map:
                self.personal_anomaly_map[pos] = anomaly_data
                # Ajouter aux anomalies à traiter si pas déjà traitée ET pas déjà dans la liste
                anomaly_obj = anomaly_data.get('anomaly')
                anomaly_pos = anomaly_data.get('position')
                already_in_detected = any(a.get('position') == anomaly_pos for a in self.detected_anomalies)
                if anomaly_obj is not None and not anomaly_obj.treated and not already_in_detected:
                    self.detected_anomalies.append(anomaly_data)
        
        return True
    
    def detect_anomalies_in_range(self, environment):
        """
        Détecte les anomalies dans le rayon de vision.
        Une case est explorée SI elle est dans le rayon de vision ET vide (pas d'anomalie).
        """
        detected = []
        
        for anomaly in environment.anomalies:
            # Ignorer les anomalies déjà traitées
            if getattr(anomaly, 'treated', False):
                continue
            distance = self.calculate_distance(
                self.x, self.y, 
                anomaly.x, anomaly.y
            )
            
            # Si dans le rayon de vision, anomalie détectée
            if distance <= self.vision_radius:
                detected.append({
                    'anomaly': anomaly,
                    'intensity': anomaly.intensity,
                    'is_intense': anomaly.is_intense(),
                    'distance': distance,
                    'position': (anomaly.x, anomaly.y)
                })

        # Marquer TOUTE la zone visible comme explorée (anomalie ou pas)
        x_min = max(0, int(self.x - self.vision_radius))
        x_max = min(environment.width - 1, int(self.x + self.vision_radius))
        y_min = max(0, int(self.y - self.vision_radius))
        y_max = min(environment.height - 1, int(self.y + self.vision_radius))
        vr2 = self.vision_radius * self.vision_radius
        for xi in range(x_min, x_max + 1):
            for yi in range(y_min, y_max + 1):
                if (xi - self.x) ** 2 + (yi - self.y) ** 2 <= vr2:
                    self.personal_exploration_map[(xi, yi)] = True
                    environment.mark_explored(xi, yi, radius=0)  # radius=0 : marquer uniquement cette case
        
        return detected
    
    def communicate_with_nearby_drones(self, other_drones, reverse_order=False):
        """
        Communique avec les drones à proximité au DÉBUT de chaque tour.
        Partage : carte d'exploration + anomalies détectées
        
        Args:
            other_drones: Liste de tous les drones
            reverse_order: Si True, traite les drones dans l'ordre inverse pour propagation transitive
        
        Note: Cette fonction est appelée deux fois chaque tour:
        - D'abord en ordre normal: A→B→C (A partage avec B, B partage avec C)
        - Puis en ordre inverse: C→B→A (C partage avec B, B partage avec A)
        Cela assure que les informations circulent dans les deux sens et se propagent transitivement.
        """
        drones_list = list(other_drones)
        if reverse_order:
            drones_list = drones_list[::-1]  # Inverser l'ordre
        
        for other_drone in drones_list:
            if other_drone.id == self.id:
                continue
            
            distance = self.calculate_distance(
                self.x, self.y,
                other_drone.x, other_drone.y
            )
            
            # Si dans le rayon de communication
            if distance <= config.COMMUNICATION_RADIUS:
                # Partager ma carte avec l'autre drone
                self.share_exploration_map(other_drone)
                # Recevoir sa carte
                other_drone.share_exploration_map(self)
    
    def communicate_discovery(self, other_drones, anomaly_info):
        """
        Communique la découverte d'une anomalie aux drones à proximité.
        Les drones dans le rayon de vision reçoivent l'information.
        """
        for other_drone in other_drones:
            if other_drone.id == self.id:
                continue  # Ne pas se parler à soi-même
            
            distance = self.calculate_distance(
                self.x, self.y,
                other_drone.x, other_drone.y
            )
            
            # Si dans le rayon de communication (rayon de vision)
            if distance <= config.COMMUNICATION_RADIUS:
                # L'autre drone reçoit l'information
                other_drone.receive_anomaly_info(anomaly_info)
    
    def receive_anomaly_info(self, anomaly_info):
        """Reçoit l'information d'une anomalie d'un autre drone par communication."""
        # Vérifier qu'on ne la connaît pas déjà
        pos = anomaly_info['position']
        pos_key = (int(pos[0]), int(pos[1]))
        
        if pos_key not in self.personal_anomaly_map:
            # Stocker le dictionnaire COMPLET, pas juste l'intensité
            self.personal_anomaly_map[pos_key] = anomaly_info
            self.detected_anomalies.append(anomaly_info)
            # NE PAS ajouter à direct_detections car c'est une TRANSMISSION, pas une détection directe
    
    def treat_anomaly(self, anomaly_info):
        """
        Traite une anomalie (action avec temps de scan approfondi).
        Coût : DEEP_SCAN_TIME secondes pour anomalie faible (10s)
               DEEP_SCAN_TIME * 1.5 secondes pour anomalie intense (15s)
        
        Consomme de la batterie basée sur le temps de traitement.
        Sécurité : traite seulement si on peut revenir à la base APRÈS traitement
        """
        # Déterminer le coût selon l'intensité
        anomaly_obj = anomaly_info.get('anomaly')
        
        # Sécurité : vérifier que l'objet anomalie existe et n'a pas déjà été traité
        if anomaly_obj is None or getattr(anomaly_obj, 'treated', False):
            # L'anomalie n'existe plus ou est déjà traitée
            pos = anomaly_info.get('position')
            if pos:
                self.detected_anomalies = [
                    a for a in self.detected_anomalies
                    if a.get('position') != pos
                ]
            return False
        
        # Calculer le temps de traitement en secondes
        if anomaly_obj.intensity == 2:  # Intense
            treatment_time = config.DEEP_SCAN_TIME * 1.5  # 15 secondes
        else:  # Faible
            treatment_time = config.DEEP_SCAN_TIME  # 10 secondes
        
        # Calculer le coût batterie basé sur le temps
        treatment_cost = config.BATTERY_DRAIN_PER_SECOND * treatment_time
        
        # Calculer le coût pour revenir à la base APRÈS traitement
        distance_to_base = self.calculate_distance(self.x, self.y, self.base_x, self.base_y)
        return_cost = distance_to_base * self.movement_cost
        total_cost = treatment_cost + return_cost
        
        # Vérifier qu'on a assez de batterie pour traiter ET revenir (sécurité pour tous les modes)
        if self.battery >= total_cost:
            self.battery -= treatment_cost
            # Marquer l'anomalie réelle comme traitée
            anomaly_obj.treated = True
            anomaly_obj.being_treated_by = -1  # Réinitialiser le traitement
            
            # Retirer de la liste "en cours de traitement"
            pos_key = (int(anomaly_obj.x), int(anomaly_obj.y))
            if pos_key in self.anomalies_being_treated_by_others:
                del self.anomalies_being_treated_by_others[pos_key]
            
            return True
        else:
            # Pas assez de batterie pour traiter ET revenir
            # Ne PAS marquer comme en cours, retourner plutôt à la base
            return False
    
    def select_next_target(self, environment, other_drones):
        """
        Sélectionne la prochaine cible selon la STRATÉGIE configurée.
        
        STRATÉGIE 'action':
            - Explore vers case non explorée la plus proche
            - Si anomalie détectée → traite IMMÉDIATEMENT
            - Puis reprend exploration
        
        STRATÉGIE 'exploration':
            - Explore 100% de la carte
            - IGNORE les anomalies détectées
            - Une fois carte à 100% → traite anomalies par intensité décroissante
        
        STRATÉGIE 'mixte':
            - Explore vers case non explorée
            - Si anomalie détectée → se dirige vers elle
            - EN ROUTE : si détecte anomalie plus urgente (intense) → traite d'abord la plus urgente
            - Revient traiter la première après
        """
        strategy = config.ROBOT_STRATEGY
        
        # ========== STRATÉGIE EXPLORATION ==========
        if strategy == 'exploration':
            # Calculer le % d'exploration actuel
            current_exploration_pct = (environment.exploration_map.sum() / environment.exploration_map.size)
            
            # Vérifier si carte à 100%
            exploration_complete = current_exploration_pct >= 0.999
            
            # DÉTECTION DIRECTE : Si on est à la base et on vient de détecter qu'aucune zone n'est accessible
            exploration_impossible = self.exploration_blocked_from_base
            
            if not exploration_complete and not exploration_impossible:
                # Continuer d'explorer, IGNORER les anomalies
                self._select_exploration_target(environment)
                # Vérifier APRÈS sélection si on s'est bloqués
                exploration_impossible = self.exploration_blocked_from_base
            
            if exploration_complete or exploration_impossible:
                # Carte complète OU exploration impossible → TENTER de traiter anomalies
                self._select_anomaly_target_by_priority()
                
                # Si aucune anomalie accessible non plus → rester à la base en attente
                if self.target_anomaly is None and not exploration_complete and exploration_impossible:
                    # Garder la cible à la base pour rester en attente
                    self.target_x = self.base_x
                    self.target_y = self.base_y
        
        # ========== STRATÉGIE ACTION ==========
        elif strategy == 'action':
            # PRIORITÉ 1 : Si déjà en train de traiter une anomalie, continuer
            if self.target_anomaly is not None:
                anomaly_obj = self.target_anomaly.get('anomaly')
                if anomaly_obj and not getattr(anomaly_obj, 'treated', False):
                    # Continuer vers cette anomalie
                    pass  # Garder la cible actuelle
                else:
                    # Anomalie déjà traitée, réinitialiser
                    self.target_anomaly = None
            
            # PRIORITÉ 2 : Chercher anomalies INTENSE accessibles
            if self.target_anomaly is None:
                intense_anomalies = []
                for anom in self.detected_anomalies:
                    anom_obj = anom.get('anomaly')
                    if anom_obj and anom_obj.intensity == 2 and not getattr(anom_obj, 'treated', False):
                        pos = anom.get('position')
                        dist_to = self.calculate_distance(self.x, self.y, pos[0], pos[1])
                        dist_back = self.calculate_distance(pos[0], pos[1], self.base_x, self.base_y)
                        treatment = config.TREATMENT_COST_INTENSE
                        total_cost = (dist_to + dist_back) * self.movement_cost + treatment
                        
                        if self.battery >= total_cost:
                            intense_anomalies.append((anom, dist_to))
                
                # Traiter l'anomalie intense la plus proche
                if intense_anomalies:
                    intense_anomalies.sort(key=lambda x: x[1])  # Trier par distance
                    self.target_anomaly = intense_anomalies[0][0]
                    pos = self.target_anomaly.get('position')
                    self.target_x = pos[0]
                    self.target_y = pos[1]
            
            # PRIORITÉ 3 : Si pas d'anomalie intense, chercher anomalies FAIBLE accessibles
            if self.target_anomaly is None:
                weak_anomalies = []
                for anom in self.detected_anomalies:
                    anom_obj = anom.get('anomaly')
                    if anom_obj and anom_obj.intensity == 1 and not getattr(anom_obj, 'treated', False):
                        pos = anom.get('position')
                        dist_to = self.calculate_distance(self.x, self.y, pos[0], pos[1])
                        dist_back = self.calculate_distance(pos[0], pos[1], self.base_x, self.base_y)
                        treatment = config.TREATMENT_COST_WEAK
                        total_cost = (dist_to + dist_back) * self.movement_cost + treatment
                        
                        if self.battery >= total_cost:
                            weak_anomalies.append((anom, dist_to))
                
                # Traiter l'anomalie faible la plus proche
                if weak_anomalies:
                    weak_anomalies.sort(key=lambda x: x[1])  # Trier par distance
                    self.target_anomaly = weak_anomalies[0][0]
                    pos = self.target_anomaly.get('position')
                    self.target_x = pos[0]
                    self.target_y = pos[1]
            
            # PRIORITÉ 4 : Si pas d'anomalie accessible, explorer
            if self.target_anomaly is None:
                self._select_exploration_target(environment)
                
                # Si exploration aussi bloquée → rester à la base en attente
                if self.exploration_blocked_from_base:
                    self.target_x = self.base_x
                    self.target_y = self.base_y
                    self.target_anomaly = None  # IMPORTANT : pas d'anomalie accessible
        
        # ========== STRATÉGIE MIXTE ==========
        elif strategy == 'mixte':
            # Si anomalie connue → aller vers elle
            if self.detected_anomalies:
                # Trier par intensité (intense = 2 avant faible = 1)
                self.detected_anomalies.sort(
                    key=lambda a: (a.get('intensity', 0), -a.get('distance', 999)),
                    reverse=True
                )
                
                # Si déjà en route vers une anomalie
                if self.target_anomaly:
                    # Vérifier s'il y a une plus urgente (intense vs faible)
                    current_intensity = self.target_anomaly.get('intensity', 0)
                    best_anomaly = self.detected_anomalies[0]
                    best_intensity = best_anomaly.get('intensity', 0)
                    
                    # Si anomalie plus intense détectée → changer de cible
                    if best_intensity > current_intensity:
                        self.target_anomaly = best_anomaly
                        self.target_x = best_anomaly['position'][0]
                        self.target_y = best_anomaly['position'][1]
                else:
                    # Pas encore de cible anomalie, prendre la plus urgente
                    best_anomaly = self.detected_anomalies[0]
                    self.target_anomaly = best_anomaly
                    self.target_x = best_anomaly['position'][0]
                    self.target_y = best_anomaly['position'][1]
            else:
                # Pas d'anomalie → explorer
                self._select_exploration_target(environment)
        
        else:
            # Stratégie par défaut = action
            if self.detected_anomalies:
                self._select_anomaly_target_by_priority()
            else:
                self._select_exploration_target(environment)
    
    def _select_exploration_target(self, environment):
        """Sélectionne la case non explorée la plus proche ET accessible avec la batterie actuelle."""
        # Chercher dans la carte globale pour les zones non explorées
        unexplored = np.argwhere(environment.exploration_map == 0)
        
        if len(unexplored) == 0:
            # Toute la carte explorée → retour base
            self.target_x = self.base_x
            self.target_y = self.base_y
            self.target_anomaly = None
            return
        
        # Nettoyer les zones réservées par d'autres qui sont maintenant explorées
        self.zones_being_explored_by_others = {
            pos: drone_id for pos, drone_id in self.zones_being_explored_by_others.items()
            if (0 <= pos[0] < environment.width and 0 <= pos[1] < environment.height and
                environment.exploration_map[pos[1], pos[0]] == 0)  # Seulement si pas encore explorée et dans limites
        }
        
        # Trouver la plus proche accessible qui n'est PAS ciblée par un autre drone
        # ET qui est accessible avec la batterie actuelle
        best_target = None
        best_dist = float('inf')
        
        for point in unexplored:
            pos_key = (point[1], point[0])
            
            # Ignorer si cette zone est déjà ciblée par un autre drone
            if pos_key in self.zones_being_explored_by_others:
                continue
            
            # Calculer distance et coût batterie pour aller à cette zone ET revenir à la base
            dist_to_target = self.calculate_distance(point[1], point[0], self.x, self.y)
            dist_target_to_base = self.calculate_distance(point[1], point[0], self.base_x, self.base_y)
            
            total_distance = dist_to_target + dist_target_to_base
            total_cost = total_distance * self.movement_cost
            
            # FILTRAGE : Garder seulement les zones accessibles avec la batterie actuelle
            if self.battery < total_cost:
                continue  # Zone inaccessible, ignorer
            
            # Prendre la plus proche parmi les zones accessibles
            if dist_to_target < best_dist:
                best_dist = dist_to_target
                best_target = point
        
        if best_target is not None:
            self.target_x = best_target[1]
            self.target_y = best_target[0]
            self.target_anomaly = None
            self.exploration_blocked_from_base = False  # On a trouvé une zone, débloqué
            if len(unexplored) < 1000:  # Afficher seulement vers la fin
                zones_evitees = sum(1 for p in unexplored if (p[1], p[0]) in self.zones_being_explored_by_others)
        else:
            # Aucune zone accessible avec la batterie actuelle
            # Si on est à la base → exploration complètement bloquée
            if self.is_at_base:
                self.exploration_blocked_from_base = True
            else:
                self.exploration_blocked_from_base = False
            
            self.target_x = self.base_x
            self.target_y = self.base_y
            self.target_anomaly = None
    
    def _select_anomaly_target_by_priority(self):
        """Sélectionne l'anomalie la plus urgente (intense > faible) ET accessible avec la batterie actuelle."""
        # D'abord utiliser les anomalies personnelles détectées
        available_anomalies = [
            a for a in self.detected_anomalies
            if (int(a['position'][0]), int(a['position'][1])) not in self.anomalies_being_treated_by_others
            and a.get('anomaly') is not None
            and not getattr(a.get('anomaly'), 'treated', False)
            and getattr(a.get('anomaly'), 'being_treated_by', -1) == -1
        ]
        
        # Si aucune anomalie personnelle, utiliser les anomalies du centre de contrôle
        if not available_anomalies and self.control_center:
            available_anomalies = [
                a for pos, a in self.control_center.global_anomaly_map.items()
                if pos not in self.anomalies_being_treated_by_others
                and a.get('anomaly') is not None
                and not getattr(a.get('anomaly'), 'treated', False)
                and getattr(a.get('anomaly'), 'being_treated_by', -1) == -1
            ]
        
        # FILTRE : Garder seulement les anomalies accessibles avec batterie actuelle
        accessible_anomalies = []
        for anom in available_anomalies:
            pos = anom.get('position')
            if pos:
                # Calculer coût total : aller + traiter + retour
                distance_to_anomaly = self.calculate_distance(self.x, self.y, pos[0], pos[1])
                distance_to_base_from_anomaly = self.calculate_distance(pos[0], pos[1], self.base_x, self.base_y)
                anomaly_obj = anom.get('anomaly')
                treatment_cost = config.TREATMENT_COST_INTENSE if anomaly_obj.intensity == 2 else config.TREATMENT_COST_WEAK
                
                total_cost = (distance_to_anomaly + distance_to_base_from_anomaly) * self.movement_cost + treatment_cost
                
                if self.battery >= total_cost:
                    accessible_anomalies.append(anom)
        
        if not accessible_anomalies:
            # Aucune anomalie accessible, retourner à la base
            self.target_x = self.base_x
            self.target_y = self.base_y
            self.target_anomaly = None
            return
        
        # Trier par intensité décroissante
        accessible_anomalies.sort(
            key=lambda a: a.get('intensity', 0),
            reverse=True
        )
        
        best_anomaly = accessible_anomalies[0]
        self.target_anomaly = best_anomaly
        self.target_x = best_anomaly['position'][0]
        self.target_y = best_anomaly['position'][1]
    
    def move_towards_target(self, environment):
        """Déplace le drone vers la cible."""
        if self.target_x is None or self.target_y is None:
            return
        
        # ⚠️ SÉCURITÉ ABSOLUE : Si batterie déjà insuffisante pour revenir, NE PAS BOUGER
        return_cost = self.calculate_return_cost()
        if self.battery <= return_cost and (self.target_x != self.base_x or self.target_y != self.base_y):
            # Déjà en situation critique → forcer retour à la base SANS se déplacer
            self.target_x = self.base_x
            self.target_y = self.base_y
            self.target_anomaly = None
            return  # NE PAS SE DÉPLACER
        
        # ⚠️ SÉCURITÉ PRÉVENTIVE : Vérifier AVANT de se déplacer
        # Calculer le coût du prochain mouvement
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance_to_target = np.sqrt(dx**2 + dy**2)
        next_move_distance = min(self.speed, distance_to_target)
        next_move_cost = next_move_distance * self.movement_cost
        
        # Si ce mouvement nous empêcherait de revenir → aller à la base immédiatement
        if self.battery - next_move_cost < return_cost and (self.target_x != self.base_x or self.target_y != self.base_y):
            self.target_x = self.base_x
            self.target_y = self.base_y
            self.target_anomaly = None
        
        prev_x, prev_y = self.x, self.y
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = np.sqrt(dx**2 + dy**2)
        
        if distance < self.speed:
            # Arrivé à la cible
            self.x = self.target_x
            self.y = self.target_y
        else:
            # Avancer d'un pas
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
        
        # Contraintes de l'environnement
        self.x = max(0, min(self.x, environment.width))
        self.y = max(0, min(self.y, environment.height))
        
        # Consommer batterie proportionnellement à la distance parcourue
        distance_traveled = np.hypot(self.x - prev_x, self.y - prev_y)
        
        # Temps de déplacement = distance / vitesse (en secondes)
        movement_time = distance_traveled / self.speed if self.speed > 0 else 0
        
        # Consommation batterie = drain par seconde * temps + coût mouvement
        battery_drain = (config.BATTERY_DRAIN_PER_SECOND * movement_time * config.TIME_PER_TURN) + (self.movement_cost * distance_traveled)
        self.battery -= battery_drain
        self.battery = max(0, self.battery)  # Empêcher batterie négative
        
        # Marquer le chemin comme exploré pour éviter les trous
        steps = max(int(np.hypot(self.x - prev_x, self.y - prev_y) * 2), 1)
        for i in range(steps + 1):
            xi = prev_x + (self.x - prev_x) * (i / steps)
            yi = prev_y + (self.y - prev_y) * (i / steps)
            exploration_key = (int(xi), int(yi))
            self.personal_exploration_map[exploration_key] = True
            environment.mark_explored(xi, yi)
        
        action = 'return_to_base' if (self.target_x == self.base_x and self.target_y == self.base_y) else 'move'
        self.log_event(action, (prev_x, prev_y), (self.x, self.y), self.battery)

        # Enregistrer dans l'historique
        self.path_history.append((self.x, self.y))
    
    def update(self, environment, other_drones, step):
        """
        Mise à jour du drone à chaque pas de temps.
        Logique principale du comportement autonome.
        """
        self.current_step = step
        
        # Déterminer l'activité pour ce tour (sera mise à jour dans les différentes phases)
        current_activity = None
        
        # PHASE 0 : COMMUNICATION avec drones proches (DÉBUT DU TOUR)
        # Passage 1: Communication normale (A→B→C)
        self.communicate_with_nearby_drones(other_drones, reverse_order=False)
        
        # Passage 2: Communication inverse (C→B→A) pour propagation transitive
        self.communicate_with_nearby_drones(other_drones, reverse_order=True)
        
        # Vérifier si à la base
        dist_to_base = self.calculate_distance(
            self.x, self.y,
            self.base_x, self.base_y
        )
        self.is_at_base = dist_to_base < 3.0
        
        # Recharge à la base
        if self.is_at_base:
            old_battery = self.battery
            # Recharge basée sur BATTERY_RECHARGE_RATE (calculé pour 10 min de recharge)
            # Chaque tour = TIME_PER_TURN secondes
            recharge_amount = config.BATTERY_RECHARGE_RATE * config.TIME_PER_TURN
            self.battery = min(self.battery_max, self.battery + recharge_amount)
            # Compter comme "recharging" UNIQUEMENT si la batterie augmente (vraie recharge)
            if self.battery > old_battery:
                current_activity = 'recharging'
        
        # PHASE 1 : Détection des anomalies dans le rayon de vision
        detected = self.detect_anomalies_in_range(environment)
        
        for anomaly_det in detected:
            # Vérifier si ce n'est pas déjà dans la liste
            pos = anomaly_det['position']
            pos_key = (int(pos[0]), int(pos[1]))
            
            if pos_key not in self.personal_anomaly_map:
                # Stocker le dictionnaire COMPLET, pas juste l'intensité
                self.personal_anomaly_map[pos_key] = anomaly_det
                self.detected_anomalies.append(anomaly_det)
                self.direct_detections.add(pos_key)  # DÉTECTION DIRECTE par les capteurs !
                
                # EN MODE ACTION : interrompre l'exploration pour traiter immédiatement
                if config.ROBOT_STRATEGY == 'action' and self.target_anomaly is None:
                    # Vérifier que cette anomalie est accessible ET qu'on a assez de batterie
                    distance_to_anomaly = self.calculate_distance(self.x, self.y, pos[0], pos[1])
                    distance_to_base_from_anomaly = self.calculate_distance(pos[0], pos[1], self.base_x, self.base_y)
                    anomaly_obj = anomaly_det.get('anomaly')
                    treatment_cost = config.TREATMENT_COST_INTENSE if anomaly_obj.intensity == 2 else config.TREATMENT_COST_WEAK
                    total_cost = (distance_to_anomaly + distance_to_base_from_anomaly) * self.movement_cost + treatment_cost
                    
                    # Vérifier si cette anomalie est THÉORIQUEMENT accessible (même avec batterie max)
                    if total_cost <= self.battery_max:
                        if self.battery >= total_cost:
                            # Assez de batterie maintenant: aller traiter cette anomalie
                            self.target_anomaly = anomaly_det
                            self.target_x = pos[0]
                            self.target_y = pos[1]
                        else:
                            # Pas assez de batterie maintenant, mais possible après recharge
                            # Retourner à la base d'abord pour recharger
                            self.target_x = self.base_x
                            self.target_y = self.base_y
                            self.target_anomaly = anomaly_det  # Mémoriser qu'on doit revenir pour traiter
                    # Sinon : anomalie impossible (cost > BATTERY_MAX), ne rien faire
                
                # Communiquer la découverte aux autres drones
                self.communicate_discovery(other_drones, anomaly_det)
        
        # PHASE 2 : Décider de l'action
        
        # 2A : Vérifier si doit retourner à la base
        if self.should_return_to_base():
            self.target_x = self.base_x
            self.target_y = self.base_y
            self.target_anomaly = None
        
        # 2B : Si à la base et batterie rechargée, réinitialiser
        elif self.is_at_base and self.battery > (self.battery_max * config.BATTERY_DEPARTURE_THRESHOLD) and (self.target_x is None or self.target_y is None or (self.target_x == self.base_x and self.target_y == self.base_y)):
            # SYNCHRONISATION complète avec le centre avant de partir
            self.sync_with_control_center(self.control_center) if self.control_center else None
            self.select_next_target(environment, other_drones)
            # exploration_pct calculable si besoin de logs : (environment.exploration_map.sum() / environment.exploration_map.size) * 100
        
        # 2C : Si pas de cible, en sélectionner une
        elif self.target_x is None or self.target_y is None:
            self.select_next_target(environment, other_drones)
        
        # 2D : Si à proximité de la cible
        elif self.calculate_distance(self.x, self.y, self.target_x, self.target_y) < 3.0:
            # Si c'est une anomalie à traiter
            if self.target_anomaly is not None:
                # Déterminer le coût de traitement selon l'intensité
                anomaly_obj = self.target_anomaly.get('anomaly')
                if anomaly_obj is not None:
                    treatment_cost = config.TREATMENT_COST_INTENSE if anomaly_obj.intensity == 2 else config.TREATMENT_COST_WEAK
                else:
                    treatment_cost = config.TREATMENT_COST_WEAK
                
                # Calculer le coût de retour à la base APRÈS traitement
                distance_to_base = self.calculate_distance(self.x, self.y, self.base_x, self.base_y)
                return_cost = distance_to_base * self.movement_cost
                total_cost = treatment_cost + return_cost
                
                # Vérifier si on a assez de batterie pour traiter ET revenir à la base
                if self.battery >= total_cost:
                    if self.treat_anomaly(self.target_anomaly):
                        # Traitement réussi
                        if self.target_anomaly in self.detected_anomalies:
                            self.detected_anomalies.remove(self.target_anomaly)
                        
                        # Communiquer qu'on traite l'anomalie
                        self.communicate_discovery(other_drones, {
                            **self.target_anomaly,
                            'status': 'treated'
                        })
                        
                        self.target_anomaly = None
                        current_activity = 'treating'
                else:
                    # Pas assez de batterie pour traiter et revenir → abandonner cette anomalie
                    self.target_anomaly = None
                    self.target_x = self.base_x
                    self.target_y = self.base_y
                    current_activity = 'moving'
            
            # Sélectionner nouvelle cible
            self.select_next_target(environment, other_drones)
        
        # PHASE 3 : Exécuter le mouvement
        # Stratégie : Permettre l'exploration tant que possible, mais revenir à temps
        return_cost = self.calculate_return_cost()
        
        # Déterminer l'activité AVANT le mouvement
        if current_activity is None:
            # PRIORITÉ 1 : Si déjà à la base avec target=base et pas d'anomalie = WAITING (rien à faire)
            if self.is_at_base and self.target_x == self.base_x and self.target_y == self.base_y and self.target_anomaly is None:
                current_activity = 'waiting'
            # PRIORITÉ 2 : Si a une anomalie cible = MOVING vers anomalie
            elif self.target_anomaly is not None:
                current_activity = 'moving'
            # PRIORITÉ 3 : Si se déplace vers la base (mais pas encore arrivé) = MOVING vers base
            elif not self.is_at_base and self.target_x == self.base_x and self.target_y == self.base_y:
                current_activity = 'moving'
            # PRIORITÉ 4 : Sinon c'est EXPLORING
            else:
                current_activity = 'exploring'
        
        if self.is_at_base:
            # À la base : NE PAS bouger si batterie insuffisante pour partir
            if self.battery >= (self.battery_max * config.BATTERY_DEPARTURE_THRESHOLD):
                self.move_towards_target(environment)
            # Sinon, rester à la base en attente (current_activity déjà défini)
        else:
            # En mission : VÉRIFIER si on peut encore continuer vers la cible
            # Calculer le coût pour continuer vers la cible actuelle + revenir
            if self.target_x is not None and self.target_y is not None:
                dist_to_target = self.calculate_distance(self.x, self.y, self.target_x, self.target_y)
                dist_target_to_base = self.calculate_distance(self.target_x, self.target_y, self.base_x, self.base_y)
                
                # Coût si on continue : aller à la cible + revenir de là-bas (distance * coût unitaire)
                cost_continue = (dist_to_target + dist_target_to_base) * self.movement_cost
                
                # Si on n'a plus assez pour continuer vers la cible ET revenir → abandonner et rentrer
                if self.battery < cost_continue and (self.target_x != self.base_x or self.target_y != self.base_y):
                    self.target_x = self.base_x
                    self.target_y = self.base_y
                    self.target_anomaly = None
            
            # Maintenant on peut bouger (vers la base ou vers la cible si assez de batterie)
            if self.battery > return_cost:
                self.move_towards_target(environment)
                # Déterminer si c'est exploration ou mouvement (mais ne pas remplacer recharging)
                if current_activity is None:  # Si pas déjà défini
                    if self.target_anomaly is not None or (self.target_x == self.base_x and self.target_y == self.base_y):
                        current_activity = 'moving'
                    else:
                        current_activity = 'exploring'
            else:
                # Pas assez de batterie, forcer le retour à la base
                self.target_x = self.base_x
                self.target_y = self.base_y
                self.target_anomaly = None
                self.move_towards_target(environment)
                current_activity = 'moving'
        
        # Enregistrer l'activité de ce tour
        self.activity_stats[current_activity] += 1
