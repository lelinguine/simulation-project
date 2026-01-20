import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import random
from datetime import datetime
import os
import csv

# Import des classes depuis le dossier classes
from classes import AnomalyDetector, Anomaly, Environment, Drone, ControlCenter
import config

#==============================================================================
# SYSTÈME AUTONOME DE DRONES COOPÉRATIFS
# Projet IA pour les Systèmes Complexes 2025
#==============================================================================


# ------------------------------
# UTILITAIRES DE CONFIGURATION
# ------------------------------

def set_global_seed(seed):
    """Fixe l'aléatoire pour numpy et random si un seed est fourni."""
    if seed is None:
        return
    np.random.seed(seed)
    random.seed(seed)

def get_base_position(map_width, map_height, base_config):
    """
    Calcule la position de la base selon la configuration.
    
    Args:
        map_width, map_height: Dimensions de la carte
        base_config: Position fixe (x, y), cardinale ('N', 'S', 'E', 'O', etc.), ou 'A'/'RANDOM'
    
    Returns:
        (base_x, base_y)
    """
    if isinstance(base_config, tuple):
        # Position fixe
        return base_config
    
    if isinstance(base_config, str):
        base_config = base_config.upper()
        positions = {
            'N': (map_width // 2, map_height - 5),
            'S': (map_width // 2, 5),
            'E': (map_width - 5, map_height // 2),
            'O': (5, map_height // 2),
            'NE': (map_width - 10, map_height - 10),
            'NO': (10, map_height - 10),
            'SE': (map_width - 10, 10),
            'SO': (10, 10),
        }
        
        if base_config in positions:
            return positions[base_config]
        elif base_config in ('A', 'RANDOM'):
            return (random.randint(5, map_width - 5), random.randint(5, map_height - 5))
    
    # Par défaut
    return (10, 10)


# ------------------------------
# SIMULATION PRINCIPALE
# ------------------------------

def create_test_environment():
    """Crée un environnement de test avec plusieurs anomalies."""
    # Calculer la position de la base d'abord
    base_x, base_y = get_base_position(config.MAP_WIDTH, config.MAP_HEIGHT, config.BASE_POSITION)
    
    env = Environment(width=config.MAP_WIDTH, height=config.MAP_HEIGHT, base_x=base_x, base_y=base_y)
    
    # Fonction helper pour générer une position d'anomalie valide
    def generate_anomaly_position(existing_positions, base_x, base_y):
        """
        Génère une position aléatoire pour une anomalie respectant les contraintes:
        - Distance minimale entre anomalies
        - Pas sur la base
        """
        max_attempts = 500  # Augmenter les tentatives
        for _ in range(max_attempts):
            x = random.randint(5, env.width - 5)
            y = random.randint(5, env.height - 5)
            
            # Vérifier distance minimale de la base
            if np.sqrt((x - base_x)**2 + (y - base_y)**2) < config.ANOMALY_MIN_DISTANCE_FROM_BASE:
                continue
            
            # Vérifier distance minimale entre anomalies
            valid = True
            for ex, ey in existing_positions:
                if np.sqrt((x - ex)**2 + (y - ey)**2) < config.ANOMALY_MIN_DISTANCE:
                    valid = False
                    break
            
            if valid:
                return (x, y)
        
        # Si impossible après 500 tentatives, chercher les points les plus éloignés
        # Génération dégradée : contraintes non satisfaites
        
        # Chercher le point le plus éloigné de toutes les anomalies existantes
        best_pos = None
        best_dist = 0
        for _ in range(100):
            x = random.randint(5, env.width - 5)
            y = random.randint(5, env.height - 5)
            
            # Distance minimale à la base
            if np.sqrt((x - base_x)**2 + (y - base_y)**2) < config.ANOMALY_MIN_DISTANCE_FROM_BASE:
                continue
            
            # Distance minimale aux autres anomalies
            min_dist_to_others = min(
                [np.sqrt((x - ex)**2 + (y - ey)**2) for ex, ey in existing_positions],
                default=float('inf')
            )
            
            if min_dist_to_others > best_dist:
                best_dist = min_dist_to_others
                best_pos = (x, y)
        
        return best_pos if best_pos else (random.randint(20, env.width - 20), random.randint(20, env.height - 20))
    
    # Générer les anomalies avec types aléatoires selon la configuration
    anomalies_to_create = []
    for _ in range(config.NUM_ANOMALIES):
        # Choisir aléatoirement un type parmi les types disponibles
        anom_type = random.choice(config.ANOMALY_TYPES)
        anomalies_to_create.append(anom_type)
    
    # Créer les anomalies avec positions valides
    anomaly_positions = []
    for anom_type in anomalies_to_create:
        x, y = generate_anomaly_position(anomaly_positions, base_x, base_y)
        anomaly_positions.append((x, y))
        
        # Intensité: 50% chance d'être faible (1) ou forte (2)
        intensity = random.choice([config.ANOMALY_WEAK_INTENSITY, config.ANOMALY_INTENSE_INTENSITY])
        
        # Radius selon le type
        if anom_type == 'pluie_meteorites':
            radius = random.uniform(6, 10)
        elif anom_type == 'radiation':
            radius = random.uniform(8, 10)
        else:  # inondations
            radius = random.uniform(8, 12)
        
        env.add_anomaly(Anomaly(x=x, y=y, intensity=intensity, radius=radius, type=anom_type))
    
    return env, base_x, base_y


def run_simulation():
    """
    Exécute la simulation complète du système de drones en utilisant la configuration.
    """
    print("\n" + "="*60)
    print("SIMULATION : SYSTÈME DE DRONES COOPÉRATIFS")
    print("="*60)
    print(f"\nParamètres de simulation (CONFIG):")
    print(f"  - Drones : {config.NUM_DRONES}")
    print(f"  - Tours max : {config.MAX_TURNS}")
    print(f"  - Seed : {config.SEED}")
    print(f"  - Stratégie robots : {config.ROBOT_STRATEGY}")
    print(f"\nParamètres de TEMPS (Objectif 4) :")
    print(f"  - Temps par tour : {config.TIME_PER_TURN} seconde(s)")
    print(f"  - Autonomie : {config.AUTONOMY_TIME} secondes ({config.AUTONOMY_TIME // 60} min)")
    print(f"  - Recharge : {config.RECHARGE_TIME} secondes ({config.RECHARGE_TIME // 60} min)")
    print(f"  - Deep scan : {config.DEEP_SCAN_TIME} secondes")
    print(f"\nParamètres de BATTERIE :")
    print(f"  - Rayon vision : {config.VISION_RADIUS}")
    print(f"  - Rayon communication : {config.COMMUNICATION_RADIUS}")
    print(f"  - Coût traitement faible : {config.TREATMENT_COST_WEAK:.4f} batterie ({config.DEEP_SCAN_TIME}s)")
    print(f"  - Coût traitement intense : {config.TREATMENT_COST_INTENSE:.4f} batterie ({config.DEEP_SCAN_TIME * 1.5}s)")
    print(f"  - Drain batterie/sec : {config.BATTERY_DRAIN_PER_SECOND:.4f}")
    print(f"  - Batterie max : {config.BATTERY_MAX}")
    print(f"  - Recharge/tour : {config.BATTERY_RECHARGE_RATE:.4f}")
    print(f"  - Position base : {config.BASE_POSITION}")
    print(f"  - Anomalies : {config.NUM_ANOMALIES}")
    print(f"  - Distance min anomalies : {config.ANOMALY_MIN_DISTANCE}")
    print("="*60 + "\n")
    
    # 0. Fixer l'aléatoire si demandé
    set_global_seed(config.SEED)

    # 1. Créer le détecteur d'anomalies
    detector = AnomalyDetector()
    print("Détecteur d'anomalies initialisé")
    print("="*60 + "\n")
    
    # 2. Créer l'environnement (récupère aussi base_x, base_y)
    env, base_x, base_y = create_test_environment()
    print(f"Environnement créé : {env.width}x{env.height}")
    print(f"Base positionnée à : ({base_x}, {base_y})")
    print(f"Anomalies présentes : {len(env.anomalies)}\n")
    
    # Sauvegarder les anomalies initiales pour la visualisation finale
    initial_anomalies = env.anomalies.copy()
    
    # 3. Créer le centre de contrôle
    control = ControlCenter(base_x, base_y, env.width, env.height)
    
    # 4. Créer les drones avec les paramètres configurables
    drones = []
    for i in range(config.NUM_DRONES):
        # Position initiale : exactement à la base
        x = base_x
        y = base_y
        drone = Drone(
            i, x, y, detector, base_x, base_y,
            vision_radius=config.VISION_RADIUS,
            movement_cost=config.MOVEMENT_COST
        )
        drone.battery = config.BATTERY_MAX
        drone.battery_max = config.BATTERY_MAX
        drone.speed = config.DRONE_SPEED
        drone.control_center = control  # Référence au centre de contrôle
        drones.append(drone)
    
    print(f"{config.NUM_DRONES} drones créés et déployés\n")
    
    # 5. Boucle de simulation
    print("DÉBUT DE LA SIMULATION")
    print("-" * 60)
    print(f"\nSTRATÉGIE : {config.ROBOT_STRATEGY.upper()}")
    if config.ROBOT_STRATEGY == 'action':
        print("→ Explore, si anomalie détectée → traite immédiatement → reprend exploration")
    elif config.ROBOT_STRATEGY == 'exploration':
        print("→ Explore 100% carte AVANT de traiter anomalies")
    elif config.ROBOT_STRATEGY == 'mixte':
        print("→ Explore, si anomalie → va vers elle, si plus urgente → traite urgente d'abord")
    print("\nCommunication entre robots à chaque tour (rayon:", config.COMMUNICATION_RADIUS, ")")
    print("Cas possible: 2 robots peuvent couvrir même zone s'ils sont trop éloignés.\n")
    
    step = 0
    max_steps = config.MAX_TURNS
    
    # Compteurs de statistiques
    all_detected_positions = []  # Toutes les détections (avec doublons possibles)
    max_anomalies_seen = len(env.anomalies)  # Maximum d'anomalies présentes simultanément
    total_anomalies_created = len(env.anomalies)  # Total créées (init + propagation)
    
    # ========== TRACKERS POUR LES STATISTIQUES ==========
    all_robots_blocked_turn = None  # Tour à partir duquel TOUS les robots sont à la base inactifs
    
    while True:
        # Évolution des anomalies (AVEC propagation et snowball)
        prev_count = len(env.anomalies)
        for anomaly in env.anomalies:
            anomaly.evolve(step, env)
        
        # Compter nouvelles anomalies créées par propagation
        new_count = len(env.anomalies)
        if new_count > prev_count:
            total_anomalies_created += (new_count - prev_count)
            max_anomalies_seen = max(max_anomalies_seen, new_count)
        
        # NE PAS supprimer les anomalies traitées : les laisser pour la visualisation
        # Elles restent dans env.anomalies avec le flag treated = True
        
        # Nettoyage des anomalies traitées dans le centre de contrôle aussi
        # Garder seulement les anomalies NON-traitées
        remaining_positions = {(a.x, a.y) for a in env.anomalies if not getattr(a, 'treated', False)}
        control.global_anomaly_map = {
            pos: anom for pos, anom in control.global_anomaly_map.items()
            if pos in remaining_positions
        }
        
        # Mise à jour de chaque drone
        for drone in drones:
            drone.update(env, drones, step)
            
            # Enregistrer toutes les positions détectées
            for anomaly_info in drone.detected_anomalies:
                pos = anomaly_info.get('position')
                if pos and pos not in all_detected_positions:
                    all_detected_positions.append(pos)
            
            # Transmission au centre de contrôle à CHAQUE TOUR (en temps réel)
            control.receive_transmission(drone)
            
            # Réception des mises à jour (seulement à la base)
            if drone.is_at_base:
                control.send_update_to_drone(drone)
        
        # Affichage périodique
        if step % 50 == 0:
            control.analyze_interventions(env)
            control.print_status(drones)
            # progression affichée via print_status
        
        # Vérifier si TOUS les robots sont bloqués à la base (peu importe l'état de la mission)
        # Un robot est bloqué s'il est à la base, avec la base pour cible, et pas d'anomalie à traiter
        all_blocked = all(
            drone.is_at_base and 
            drone.target_x == drone.base_x and 
            drone.target_y == drone.base_y and 
            drone.target_anomaly is None
            for drone in drones
        )
        if all_blocked and all_robots_blocked_turn is None:
            all_robots_blocked_turn = step + 1  # Enregistrer le premier tour où TOUS sont bloqués

        # Conditions d'arrêt
        exploration_pct = (env.exploration_map.sum() / env.exploration_map.size) * 100
        
        # Compter anomalies NON-traitées
        untreated_anomalies = sum(1 for a in env.anomalies if not getattr(a, 'treated', False))
        
        # Arrêt si 100% exploré ET plus d'anomalies NON-traitées
        if exploration_pct >= 100.0 and untreated_anomalies == 0:
            print(f"\nMission accomplie : Carte 100% explorée et toutes les anomalies traitées en {step+1} tours")
            break
        
        # Arrêt si MAX_TURNS atteint
        if step + 1 >= max_steps:
            print(f"\nSimulation complète : {max_steps} tours atteints (exploration {exploration_pct:.1f}%, anomalies non-traitées: {untreated_anomalies})")
            break

        step += 1
    
    # 6. Rapport final
    print("\n" + "="*60)
    print("SIMULATION TERMINÉE - RAPPORT FINAL")
    print("="*60)
    
    # Analyse des interventions requises
    control.analyze_interventions(env)
    control.print_status(drones)

    exploration_pct = (env.exploration_map.sum() / env.exploration_map.size) * 100
    steps_done = step + 1  # step est 0-indexé dans la boucle
    
    # Compter les détections avec doublons : pour chaque anomalie, combien de drones l'ont détectée directement
    # Si 2 drones détectent la même anomalie sans commu, c'est 2 détections
    detected_by_drone = {}  # {position: nombre de drones qui l'ont détectée}
    for drone in drones:
        for pos in drone.direct_detections:
            detected_by_drone[pos] = detected_by_drone.get(pos, 0) + 1
    total_detections_with_duplicates = sum(detected_by_drone.values())
    
    # Compter les anomalies traitées vs détectées par les robots
    treated_anomalies = sum(1 for a in env.anomalies if getattr(a, 'treated', False))
    detected_anomalies = len(all_detected_positions)  # Anomalies détectées par les robots
    
    # Anomalies impossibles à traiter = parmi celles DÉTECTÉES par les robots, celles trop loin ET NON traitées
    from math import hypot
    impossible_anomalies = 0
    impossible_list = []
    for pos in all_detected_positions:
        anom_info = control.global_anomaly_map.get(pos)
        if anom_info:
            anom_obj = anom_info.get('anomaly')
            if anom_obj:
                # Ne compter que si l'anomalie n'a pas été traitée
                if not getattr(anom_obj, 'treated', False):
                    intensity = anom_obj.intensity
                    treatment_cost = config.TREATMENT_COST_INTENSE if intensity == 2 else config.TREATMENT_COST_WEAK
                    
                    # Coût total avec batterie pleine pour aller traiter et revenir
                    dist_to_anom = hypot(pos[0] - base_x, pos[1] - base_y)
                    dist_anom_to_base = dist_to_anom  # Même distance pour revenir
                    total_cost = (dist_to_anom + dist_anom_to_base) * config.MOVEMENT_COST + treatment_cost
                    
                    # Si coût total dépasse batterie max, c'est IMPOSSIBLE à traiter
                    if total_cost > config.BATTERY_MAX:
                        impossible_anomalies += 1
                        impossible_list.append((pos, total_cost, intensity))
    
    print(f"\nSTATISTIQUES FINALES :")
    print(f"   - Zone explorée : {exploration_pct:.1f}%")
    print(f"   - Anomalies restantes (non-traitées) : {sum(1 for a in env.anomalies if not getattr(a, 'treated', False))}")
    print(f"   - Anomalies sur la map (créées) : {total_anomalies_created}")
    if all_robots_blocked_turn is not None:
        print(f"   - Robots bloqués à la base : à partir du tour {all_robots_blocked_turn}")
    else:
        print(f"   - Robots bloqués à la base : JAMAIS (au moins un robot restait actif)")
    print(f"   - Anomalies uniques détectées par robots : {len(all_detected_positions)}")
    print(f"   - Détections avec doublons  : {total_detections_with_duplicates}")
    print(f"   - Anomalies traitées : {treated_anomalies}")
    print(f"   - Anomalies détectées : {detected_anomalies}")
    print(f"   - Anomalies détectées impossibles à traiter : {impossible_anomalies}")
    print(f"   - Transmissions totales : {len(control.received_transmissions)}")
    print(f"   - Tours effectués : {steps_done} / {max_steps}")
    
    # Calculer les statistiques d'activité globales
    total_turns = sum(drone.activity_stats['recharging'] + 
                     drone.activity_stats['moving'] + 
                     drone.activity_stats['exploring'] + 
                     drone.activity_stats['treating'] + 
                     drone.activity_stats['waiting'] 
                     for drone in drones)
    
    if total_turns > 0:
        total_recharging = sum(d.activity_stats['recharging'] for d in drones)
        total_moving = sum(d.activity_stats['moving'] for d in drones)
        total_exploring = sum(d.activity_stats['exploring'] for d in drones)
        total_treating = sum(d.activity_stats['treating'] for d in drones)
        total_waiting = sum(d.activity_stats['waiting'] for d in drones)
        
        print(f"\n   RÉPARTITION DES ACTIVITÉS (tous robots) :")
        print(f"   - Recharge à la base : {total_recharging}/{total_turns} tours ({100*total_recharging/total_turns:.1f}%)")
        print(f"   - Déplacement : {total_moving}/{total_turns} tours ({100*total_moving/total_turns:.1f}%)")
        print(f"   - Exploration : {total_exploring}/{total_turns} tours ({100*total_exploring/total_turns:.1f}%)")
        print(f"   - Traitement anomalies : {total_treating}/{total_turns} tours ({100*total_treating/total_turns:.1f}%)")
        print(f"   - Attente (inactif) : {total_waiting}/{total_turns} tours ({100*total_waiting/total_turns:.1f}%)")

    # Stocker les tours pour la visualisation
    control.steps_done = steps_done
    control.max_steps = max_steps

    # Export des déplacements détaillés (selon configuration)
    if config.SAVE_MOVEMENTS_CSV:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs('results', exist_ok=True)
        movements_file = f"results/movements_{timestamp}.csv"
        with open(movements_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'drone_id', 'step', 'action',
                'start_x', 'start_y', 'end_x', 'end_y',
                'battery_after'
            ])
            for d in drones:
                for ev in d.events:
                    writer.writerow([
                        d.id,
                        ev.get('step'),
                        ev.get('action'),
                        ev.get('start_x'), ev.get('start_y'),
                        ev.get('end_x'), ev.get('end_y'),
                        ev.get('battery')
                    ])
        print(f"   - Déplacements exportés : {movements_file}")
    else:
        print(f"   - Déplacements : NON SAUVEGARDÉS (config SAVE_MOVEMENTS_CSV=False)")
    
    return env, drones, control, initial_anomalies


# ------------------------------
# VISUALISATION (OPTIONNEL)
# ------------------------------

def visualize_final_state(env, drones, control, initial_anomalies):
    """Crée une visualisation améliorée de l'état final de la simulation."""
    if not config.SAVE_VISUALIZATION:
        print("\nVisualisation désactivée (config SAVE_VISUALIZATION=False)")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 14))
    
    # ========== GRILLAGE DE LA CARTE ==========
    # Afficher un grillage de cases
    for x in range(0, env.width + 1, 10):
        ax.axvline(x=x, color='gray', linestyle='--', alpha=0.3, linewidth=0.5)
    for y in range(0, env.height + 1, 10):
        ax.axhline(y=y, color='gray', linestyle='--', alpha=0.3, linewidth=0.5)
    
    # ========== FOND DE LA CARTE (Terrain) ==========
    terrain_colors = np.zeros((env.height, env.width, 4))  # RGBA
    for y in range(env.height):
        for x in range(env.width):
            terrain = env.terrain_map[y, x]
            if terrain == 0:  # Plaine
                terrain_colors[y, x] = [0.95, 0.90, 0.70, 1.0]  # Beige clair
            elif terrain == 1:  # Forêt
                terrain_colors[y, x] = [0.13, 0.55, 0.13, 1.0]  # Vert forêt
            elif terrain == 2:  # Rivière
                terrain_colors[y, x] = [0.25, 0.41, 0.88, 1.0]  # Bleu rivière
            elif terrain == 3:  # Lac
                terrain_colors[y, x] = [0.00, 0.45, 0.70, 1.0]  # Bleu lac
    
    ax.imshow(terrain_colors, origin='lower', extent=[0, env.width, 0, env.height])
    
    # ========== ZONES EXPLORÉES ==========
    ax.imshow(env.exploration_map, cmap='Greens', origin='lower', alpha=0.2, 
              extent=[0, env.width, 0, env.height])
    
    # ========== ANOMALIES RÉELLES ==========
    # Symboles pour les anomalies
    anomaly_symbols = {
        'pluie_meteorites': '*',    # Étoile
        'radiation': 'D',            # Losange
        'inondations': 'P'           # Pentagone
    }
    
    anomaly_colors_map = {
        'pluie_meteorites': '#FF6B00',  # Orange
        'radiation': '#FFD700',          # Jaune doré
        'inondations': '#00CED1'         # Turquoise
    }
    
    added_labels = set()
    
    
    # Utiliser les anomalies initiales pour la visualisation (pas celles supprimées après traitement)
    for anomaly in initial_anomalies:
        symbol = anomaly_symbols.get(anomaly.type, 'o')
        
        # Vérifier si l'anomalie a été découverte
        # Essayer plusieurs formes de clé pour matcher
        anom_pos = (int(anomaly.x), int(anomaly.y))
        anom_pos_round = (round(anomaly.x), round(anomaly.y))
        is_discovered = (anom_pos in control.detected_anomaly_positions or 
                        anom_pos_round in control.detected_anomaly_positions)
        
        # Couleur : grise si non découverte, sinon sa couleur propre
        color = anomaly_colors_map.get(anomaly.type, '#FF0000')
        display_color = color if is_discovered else '#AAAAAA'  # Gris clair si non découvert
        
        label = f'{anomaly.type.replace("_", " ").title()}' if anomaly.type not in added_labels else None
        
        # ========== SYMBOLE AVEC BORDURE NOIRE SEULEMENT SI TRAITÉE ==========
        edge_width = 1.5 if anomaly.treated else 0  # Bordure fine seulement si traitée
        ax.plot(anomaly.x, anomaly.y, symbol, 
               color=display_color,
               markersize=20, 
               markeredgewidth=edge_width, 
               markeredgecolor='black' if anomaly.treated else display_color, 
               label=label)
        
        # ========== TEXTE INTENSITÉ (1 ou 2) ==========
        intensity_text = str(anomaly.intensity)  # 1 ou 2
        ax.text(anomaly.x, anomaly.y, intensity_text, 
               fontsize=12, fontweight='bold', 
               ha='center', va='center',
               color='black')
        
        if anomaly.type not in added_labels and label:
            added_labels.add(anomaly.type)
    
    # ========== TRAJECTOIRES DES DRONES ==========
    cmap = plt.get_cmap('rainbow')
    colors = cmap(np.linspace(0, 1, len(drones)))
    
    for drone, color in zip(drones, colors):
        path = np.array(drone.path_history)
        
        # Tracer la trajectoire
        ax.plot(path[:, 0], path[:, 1], '-', color=color, alpha=0.6, 
               linewidth=1.5, label=f'Drone {drone.id} (trajet)')

        # Ajouter des flèches pour le sens du trajet
        if len(path) > 1:
            arrow_every = max(1, len(path) // 25)
            seg_start = path[0:-1:arrow_every]
            seg_end = path[1::arrow_every]
            dx = seg_end[:, 0] - seg_start[:, 0]
            dy = seg_end[:, 1] - seg_start[:, 1]
            ax.quiver(
                seg_start[:, 0], seg_start[:, 1], dx, dy,
                angles='xy', scale_units='xy', scale=1, width=0.0025,
                color=color, alpha=0.55
            )
        
        # Position finale du drone
        ax.plot(drone.x, drone.y, 'o', color=color, markersize=12, 
               markeredgewidth=2, markeredgecolor='black', label='_nolegend_')
        
        # Ajouter des points intermédiaires tous les N points
        if len(path) > 10:
            every_n = max(1, len(path) // 5)
            ax.plot(path[::every_n, 0], path[::every_n, 1], '.', 
                   color=color, markersize=4, alpha=0.5, label='_nolegend_')
    
    # ========== BASE ==========
    ax.plot(control.base_x, control.base_y, 's', color='blue', 
           markersize=18, label='Base', markeredgewidth=2.5, markeredgecolor='black')
    
    # ========== CONFIGURATION DE L'AFFICHAGE ==========
    ax.set_xlim(0, env.width)
    ax.set_ylim(0, env.height)
    ax.set_aspect('equal')
    ax.set_xlabel('X (unités)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y (unités)', fontsize=12, fontweight='bold')
    ax.set_title('Carte de Simulation - Anomalies et Trajectoires des Drones', 
                fontsize=14, fontweight='bold')
    
    # Légende améliorée
    ax.legend(loc='upper right', fontsize=9, framealpha=0.95)
    
    # Grille principale plus visible
    ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.3)
    
    # Ajouter du texte d'information
    info_text = f"Zone explorée: {(env.exploration_map.sum() / env.exploration_map.size) * 100:.1f}%\n"
    info_text += f"Anomalies détectées: {len(control.detected_anomaly_positions)}/{len(env.anomalies)}"
    if hasattr(control, 'steps_done') and hasattr(control, 'max_steps'):
        info_text += f"\nTours effectués: {control.steps_done}/{control.max_steps}"
    # Afficher aussi le seed s'il est défini
    if hasattr(config, 'SEED') and config.SEED is not None:
        info_text += f"\nSeed: {config.SEED}"
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
           fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    # Génération d'un nom de fichier unique avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Créer le dossier 'results' s'il n'existe pas
    os.makedirs('results', exist_ok=True)
    
    filename = f'results/simulation_{timestamp}.png'
    
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\nVisualisation sauvegardée : {filename}")
    plt.show()


# ------------------------------
# POINT D'ENTRÉE PRINCIPAL
# ------------------------------

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   PROJET IA - SYSTÈME AUTONOME DE DRONES COOPÉRATIFS")
    print("   Surveillance d'Environnements Sensibles - 2025")
    print("="*60 + "\n")
    
    # Exécuter la simulation en utilisant le fichier config.py
    env, drones, control, initial_anomalies = run_simulation()
    
    # Visualisation optionnelle
    try:
        visualize_final_state(env, drones, control, initial_anomalies)
    except Exception as e:
        print(f"\nVisualisation non disponible : {e}")
        print("   (Installation de matplotlib requise pour la visualisation)")
    
    print("\n" + "="*60)
    print("Programme terminé avec succès !")
    print("="*60 + "\n")
