import numpy as np

class ControlCenter:
    """
    Centre de contrôle pour coordonner l'essaim de drones.
    """
    def __init__(self, base_x, base_y, map_width=100, map_height=100):
        self.base_x = base_x
        self.base_y = base_y
        self.global_anomaly_map = {}  # Position -> info anomalie (anomalies actuelles)
        self.detected_anomaly_positions = set()  # Historique de TOUTES les positions détectées (même après traitement)
        self.global_exploration_map = np.zeros((map_height, map_width))  # Carte d'exploration globale
        self.received_transmissions = []
        self.intervention_zones = []  # Zones nécessitant une intervention
        
    def receive_transmission(self, drone):
        """
        Reçoit les données d'un drone.
        Les drones peuvent transmettre depuis n'importe où.
        """
        transmission = {
            'drone_id': drone.id,
            'position': (drone.x, drone.y),
            'battery': drone.battery,
            'anomalies': drone.detected_anomalies.copy(),
            'exploration': drone.personal_exploration_map.copy(),
            'timestamp': len(self.received_transmissions)
        }
        self.received_transmissions.append(transmission)
        
        # Mise à jour de la carte globale d'EXPLORATION
        for pos in drone.personal_exploration_map.keys():
            x, y = int(pos[0]), int(pos[1])
            if 0 <= x < self.global_exploration_map.shape[1] and 0 <= y < self.global_exploration_map.shape[0]:
                self.global_exploration_map[y, x] = 1
        
        # Mise à jour de la carte globale des ANOMALIES
        for anomaly in drone.detected_anomalies:
            pos = anomaly['position']
            key = (int(pos[0]), int(pos[1]))
            if key not in self.global_anomaly_map:
                self.global_anomaly_map[key] = anomaly
            # Enregistrer dans l'historique des détections
            self.detected_anomaly_positions.add(key)
        
        return True
    
    def send_update_to_drone(self, drone):
        """
        Envoie une mise à jour au drone.
        Le drone doit être à la base pour recevoir.
        """
        if not drone.is_at_base:
            return False
        
        # Transmission de la carte globale
        # (Dans une vraie implémentation, on pourrait synchroniser les données)
        return True
    
    def get_priority_zones(self):
        """Identifie les zones nécessitant une intervention."""
        priority_zones = []
        for pos, anomaly_info in self.global_anomaly_map.items():
            intensity = anomaly_info.get('intensity', 0)  # Extrait l'intensité du dict (1=faible, 2=intense)
            if intensity == 2:  # Anomalie intense
                priority_zones.append({
                    'position': pos,
                    'intensity': intensity,
                    'priority': 'HIGH'
                })
            elif intensity == 1:  # Anomalie faible
                priority_zones.append({
                    'position': pos,
                    'intensity': intensity,
                    'priority': 'MEDIUM'
                })
        return sorted(priority_zones, key=lambda x: x['intensity'], reverse=True)
    
    def analyze_interventions(self, environment):
        """
        Analyse les anomalies détectées et détermine les interventions requises.
        Classe par type d'intervention (humaine vs robotique) et urgence.
        Marque aussi les anomalies impossibles à traiter (trop loin, pas assez de batterie).
        """
        self.intervention_zones = []
        
        # Pour chaque anomalie détectée, trouver l'anomalie réelle correspondante
        for anomaly_real in environment.anomalies:
            # Vérifier si cette anomalie a été détectée (chercher dans l'historique des détections)
            detected = False
            anom_pos = (int(anomaly_real.x), int(anomaly_real.y))
            
            if anom_pos in self.detected_anomaly_positions:
                detected = True
                
                # Vérifier si l'anomalie a été traitée
                treated_successfully = getattr(anomaly_real, 'treated', False)
                treatability = "TREATED" if treated_successfully else "NOT_TREATED"
                
                intervention = anomaly_real.get_intervention_type()
                self.intervention_zones.append({
                    'position': (anomaly_real.x, anomaly_real.y),
                    'type': anomaly_real.type,
                    'intensity': anomaly_real.intensity,
                    'radius': anomaly_real.radius,
                    'intervention_type': intervention['type'],
                    'urgency': intervention['urgency'],
                    'description': intervention['description'],
                    'equipment': intervention['equipment'],
                    'detected': True,
                    'treatability': treatability
                })
            
            if not detected:
                # Anomalie non encore détectée
                intervention = anomaly_real.get_intervention_type()
                self.intervention_zones.append({
                    'position': (anomaly_real.x, anomaly_real.y),
                    'type': anomaly_real.type,
                    'intensity': anomaly_real.intensity,
                    'radius': anomaly_real.radius,
                    'intervention_type': intervention['type'],
                    'urgency': intervention['urgency'],
                    'description': intervention['description'],
                    'equipment': intervention['equipment'],
                    'detected': False,
                    'treatability': 'UNKNOWN'
                })
        
        # Trier par urgence : CRITICAL > HIGH > MEDIUM > LOW
        urgency_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        self.intervention_zones.sort(key=lambda x: urgency_order.get(x['urgency'], 4))
        
        return self.intervention_zones
    
    def get_intervention_summary(self):
        """
        Génère un résumé des interventions requises.
        """
        if not self.intervention_zones:
            return None
        
        summary = {
            'total': len(self.intervention_zones),
            'detected': sum(1 for z in self.intervention_zones if z['detected']),
            'human': sum(1 for z in self.intervention_zones if z['intervention_type'] == 'HUMAN'),
            'robot': sum(1 for z in self.intervention_zones if z['intervention_type'] == 'ROBOT'),
            'critical': sum(1 for z in self.intervention_zones if z['urgency'] == 'CRITICAL'),
            'high': sum(1 for z in self.intervention_zones if z['urgency'] == 'HIGH'),
            'medium': sum(1 for z in self.intervention_zones if z['urgency'] == 'MEDIUM'),
            'low': sum(1 for z in self.intervention_zones if z['urgency'] == 'LOW')
        }
        return summary
    
    def print_status(self, drones):
        """Affiche l'état du système."""
        print("\n" + "="*60)
        print("CENTRE DE CONTRÔLE - ÉTAT DU SYSTÈME")
        print("="*60)
        print(f"Position de la base : ({self.base_x}, {self.base_y})")
        print(f"Nombre de drones actifs : {len(drones)}")
        print(f"Transmissions reçues : {len(self.received_transmissions)}")
        print(f"Anomalies détectées : {len(self.global_anomaly_map)}")
        
        print("\nÉTAT DES DRONES :")
        for drone in drones:
            status = "BASE" if drone.is_at_base else "MISSION"
            mode = "Traite anomalie" if drone.target_anomaly else "Explore"
            num_anomalies = len(drone.detected_anomalies)
            print(f"  Drone {drone.id}: {status} | "
                  f"Pos: ({drone.x:.1f}, {drone.y:.1f}) | "
                  f"Batterie: {drone.battery:.1f}% | "
                  f"Mode: {mode} | "
                  f"Anomalies détectées: {num_anomalies}")
        
        priority_zones = self.get_priority_zones()
        if priority_zones:
            print(f"\nZONES PRIORITAIRES ({len(priority_zones)}) :")
            for i, zone in enumerate(priority_zones[:5]):
                intensity_str = 'Intense (2)' if zone['intensity'] == 2 else 'Faible (1)'
                print(f"  {i+1}. Position {zone['position']} | "
                      f"Intensité: {intensity_str} | "
                      f"Priorité: {zone['priority']}")
        
        # Affichage des interventions requises
        if self.intervention_zones:
            summary = self.get_intervention_summary()
            print(f"\n{'='*60}")
            print("INTERVENTIONS REQUISES")
            print(f"{'='*60}")
            print(f"Total: {summary['total']} | Détectées: {summary['detected']} | "
                  f"Humaines: {summary['human']} | Robotiques: {summary['robot']}")
            print(f"Urgence - CRITICAL: {summary['critical']} | HIGH: {summary['high']} | "
                  f"MEDIUM: {summary['medium']} | LOW: {summary['low']}")
            
            print("\nDÉTAILS DES INTERVENTIONS PRIORITAIRES :")
            for i, zone in enumerate(self.intervention_zones[:5]):
                status = "[DETECTE]" if zone['detected'] else "[NON DETECTE]"
                intensity_str = 'Intense (2)' if zone['intensity'] == 2 else 'Faible (1)'
                print(f"\n  [{i+1}] {status} - {zone['type'].upper().replace('_', ' ')}")
                print(f"      Position: ({zone['position'][0]:.1f}, {zone['position'][1]:.1f}) | "
                      f"Intensité: {intensity_str} | Rayon: {zone['radius']:.1f}m")
                print(f"      Intervention: {zone['intervention_type']} | Urgence: {zone['urgency']}")
                print(f"      Action: {zone['description']}")
                print(f"      Équipement: {', '.join(zone['equipment'])}")
