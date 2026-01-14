class ControlCenter:
    """
    Centre de contrôle pour coordonner l'essaim de drones.
    """
    def __init__(self, base_x, base_y):
        self.base_x = base_x
        self.base_y = base_y
        self.global_anomaly_map = {}  # Position -> intensité
        self.received_transmissions = []
        
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
            'timestamp': len(self.received_transmissions)
        }
        self.received_transmissions.append(transmission)
        
        # Mise à jour de la carte globale des anomalies
        for anomaly in drone.detected_anomalies:
            pos = anomaly['position']
            key = (int(pos[0]), int(pos[1]))
            if key not in self.global_anomaly_map or \
               self.global_anomaly_map[key] < anomaly['intensity']:
                self.global_anomaly_map[key] = anomaly['intensity']
        
        return True
    
    def send_update_to_drone(self, drone):
        """
        Envoie une mise à jour au drone.
        Le drone doit être à la base pour recevoir.
        """
        if not drone.can_receive_updates():
            return False
        
        # Transmission de la carte globale
        # (Dans une vraie implémentation, on pourrait synchroniser les données)
        return True
    
    def get_priority_zones(self):
        """Identifie les zones nécessitant une intervention."""
        priority_zones = []
        for pos, intensity in self.global_anomaly_map.items():
            if intensity > 0.7:  # Seuil d'intervention
                priority_zones.append({
                    'position': pos,
                    'intensity': intensity,
                    'priority': 'HIGH'
                })
            elif intensity > 0.5:
                priority_zones.append({
                    'position': pos,
                    'intensity': intensity,
                    'priority': 'MEDIUM'
                })
        return sorted(priority_zones, key=lambda x: x['intensity'], reverse=True)
    
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
            print(f"  Drone {drone.id}: {status} | "
                  f"Pos: ({drone.x:.1f}, {drone.y:.1f}) | "
                  f"Batterie: {drone.battery:.1f}% | "
                  f"Mode: {drone.mode}")
        
        priority_zones = self.get_priority_zones()
        if priority_zones:
            print(f"\nZONES PRIORITAIRES ({len(priority_zones)}) :")
            for i, zone in enumerate(priority_zones[:5]):
                print(f"  {i+1}. Position {zone['position']} | "
                      f"Intensité: {zone['intensity']:.2f} | "
                      f"Priorité: {zone['priority']}")
