import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import random
from datetime import datetime

# Import des classes depuis le dossier classes
from classes import AnomalyDetector, Anomaly, Environment, Drone, ControlCenter

#==============================================================================
# SYSTÈME AUTONOME DE DRONES COOPÉRATIFS
# Projet IA pour les Systèmes Complexes 2025
#==============================================================================


# ------------------------------
# SIMULATION PRINCIPALE
# ------------------------------

def create_test_environment():
    """Crée un environnement de test avec plusieurs anomalies."""
    env = Environment(width=100, height=100)
    
    # Fonction helper pour trouver des positions près de l'eau
    def find_water_positions(env, num_positions=3):
        """Trouve des positions près de rivières ou lacs pour les inondations."""
        water_positions = []
        # Rechercher toutes les positions d'eau
        for y in range(env.height):
            for x in range(env.width):
                if env.terrain_map[y, x] in [2, 3]:  # Rivière ou lac
                    water_positions.append((x, y))
        
        # Sélectionner aléatoirement des positions d'eau
        selected = []
        if len(water_positions) > 0:
            for _ in range(min(num_positions, len(water_positions))):
                idx = random.randint(0, len(water_positions) - 1)
                pos = water_positions[idx]
                selected.append(pos)
                # Retirer les positions proches pour éviter les chevauchements
                water_positions = [p for p in water_positions 
                                 if np.sqrt((p[0]-pos[0])**2 + (p[1]-pos[1])**2) > 15]
        return selected
    
    # Ajout d'anomalies diverses
    # Pluies de météorites (peuvent apparaître n'importe où)
    env.add_anomaly(Anomaly(x=30, y=70, intensity=0.9, radius=10, type='pluie_meteorites'))
    env.add_anomaly(Anomaly(x=20, y=20, intensity=0.6, radius=6, type='pluie_meteorites'))
    
    # Radiation (peuvent apparaître n'importe où)
    env.add_anomaly(Anomaly(x=75, y=25, intensity=0.85, radius=8, type='radiation'))
    env.add_anomaly(Anomaly(x=80, y=80, intensity=0.75, radius=9, type='radiation'))
    
    # Inondations (uniquement près des rivières et lacs)
    water_pos = find_water_positions(env, num_positions=2)
    for pos in water_pos:
        # Ajouter un léger décalage aléatoire
        offset_x = random.uniform(-3, 3)
        offset_y = random.uniform(-3, 3)
        env.add_anomaly(Anomaly(
            x=pos[0] + offset_x, 
            y=pos[1] + offset_y, 
            intensity=random.uniform(0.65, 0.85), 
            radius=random.uniform(8, 12), 
            type='inondations'
        ))
    
    return env


def run_simulation(num_drones=5, num_steps=200, visualize=False):
    """
    Exécute la simulation complète du système de drones.
    """
    print("\n" + "="*60)
    print("SIMULATION : SYSTÈME DE DRONES COOPÉRATIFS")
    print("="*60)
    
    # 1. Créer le détecteur d'anomalies
    detector = AnomalyDetector()
    print("Détecteur d'anomalies initialisé")
    print("="*60 + "\n")
    
    # 2. Créer l'environnement
    env = create_test_environment()
    print(f"Environnement créé : {env.width}x{env.height}")
    print(f"Anomalies présentes : {len(env.anomalies)}\n")
    
    # 3. Créer le centre de contrôle
    base_x, base_y = 10, 10
    control = ControlCenter(base_x, base_y)
    
    # 4. Créer les drones
    drones = []
    for i in range(num_drones):
        # Position initiale : légèrement dispersée autour de la base
        x = base_x + random.uniform(-5, 5)
        y = base_y + random.uniform(-5, 5)
        drone = Drone(i, x, y, detector, base_x, base_y)
        drones.append(drone)
    
    print(f"{num_drones} drones créés et déployés\n")
    
    # 5. Boucle de simulation
    print("DÉBUT DE LA SIMULATION")
    print("-" * 60)
    
    for step in range(num_steps):
        # Évolution des anomalies
        for anomaly in env.anomalies:
            anomaly.evolve(step)
        
        # Mise à jour de chaque drone
        for drone in drones:
            drone.update(env, drones)
            
            # Transmission au centre de contrôle (depuis n'importe où)
            if step % 10 == 0:  # Transmission périodique
                control.receive_transmission(drone)
            
            # Réception des mises à jour (seulement à la base)
            if drone.is_at_base:
                control.send_update_to_drone(drone)
        
        # Affichage périodique
        if step % 50 == 0:
            control.analyze_interventions(env)
            control.print_status(drones)
            exploration_pct = (env.exploration_map.sum() / env.exploration_map.size) * 100
            print(f"\nProgression : {exploration_pct:.1f}% de la zone explorée")
    
    # 6. Rapport final
    print("\n" + "="*60)
    print("SIMULATION TERMINÉE - RAPPORT FINAL")
    print("="*60)
    
    # Analyse des interventions requises
    control.analyze_interventions(env)
    control.print_status(drones)
    
    exploration_pct = (env.exploration_map.sum() / env.exploration_map.size) * 100
    print(f"\nSTATISTIQUES FINALES :")
    print(f"   - Zone explorée : {exploration_pct:.1f}%")
    print(f"   - Anomalies réelles : {len(env.anomalies)}")
    print(f"   - Anomalies détectées : {len(control.global_anomaly_map)}")
    print(f"   - Transmissions totales : {len(control.received_transmissions)}")
    
    # Calcul de la précision
    total_detections = sum(len(d.detected_anomalies) for d in drones)
    print(f"   - Détections totales : {total_detections}")
    
    return env, drones, control


# ------------------------------
# VISUALISATION (OPTIONNEL)
# ------------------------------

def visualize_final_state(env, drones, control):
    """Crée une visualisation de l'état final de la simulation."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Carte de terrain avec couleurs selon le type d'environnement
    # Création d'une carte de couleurs pour le terrain
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
    
    ax1.imshow(terrain_colors, origin='lower')
    
    # Overlay de la carte d'exploration (en semi-transparent)
    ax1.imshow(env.exploration_map, cmap='Greens', origin='lower', alpha=0.3)
    ax1.set_title('Carte d\'Exploration et Terrain', fontsize=14, fontweight='bold')
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    
    # Anomalies réelles avec couleurs selon le type
    anomaly_colors = {
        'pluie_meteorites': ('#FF6B00', 'orange'),  # Orange
        'radiation': ('#FFD700', 'yellow'),          # Jaune doré
        'inondations': ('#00CED1', 'darkturquoise')  # Turquoise
    }
    
    # Pour éviter les doublons dans la légende
    added_labels = set()
    
    for anomaly in env.anomalies:
        color_hex, color_name = anomaly_colors.get(anomaly.type, ('#FF0000', 'red'))
        label = f'{anomaly.type.replace("_", " ").title()}' if anomaly.type not in added_labels else None
        
        circle = Circle((anomaly.x, anomaly.y), anomaly.radius, 
                           color=color_hex, alpha=0.3, label=label)
        ax1.add_patch(circle)
        ax1.plot(anomaly.x, anomaly.y, 'x', color=color_hex, markersize=10, 
                markeredgewidth=2)
        
        if anomaly.type not in added_labels and label:
            added_labels.add(anomaly.type)
    
    # Trajectoires des drones
    cmap = plt.get_cmap('rainbow')
    colors = cmap(np.linspace(0, 1, len(drones)))
    for drone, color in zip(drones, colors):
        path = np.array(drone.path_history)
        ax1.plot(path[:, 0], path[:, 1], '-', color=color, alpha=0.5, linewidth=1)
        ax1.plot(drone.x, drone.y, 'o', color=color, markersize=10, 
                label=f'Drone {drone.id}')
    
    # Base
    ax1.plot(control.base_x, control.base_y, 's', color='blue', 
            markersize=15, label='Base', markeredgewidth=2, markeredgecolor='black')
    
    ax1.legend(loc='upper right', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Carte des anomalies détectées
    anomaly_grid = np.zeros((env.height, env.width))
    for pos, intensity in control.global_anomaly_map.items():
        if 0 <= pos[0] < env.width and 0 <= pos[1] < env.height:
            anomaly_grid[pos[1], pos[0]] = intensity
    
    im = ax2.imshow(anomaly_grid, cmap='hot', origin='lower', vmin=0, vmax=1)
    ax2.set_title('Anomalies Détectées', fontsize=14, fontweight='bold')
    ax2.set_xlabel('X')
    ax2.set_ylabel('Y')
    plt.colorbar(im, ax=ax2, label='Intensité')
    
    # Zones prioritaires
    priority_zones = control.get_priority_zones()
    for zone in priority_zones[:10]:
        ax2.plot(zone['position'][0], zone['position'][1], 'y*', 
                markersize=15, markeredgewidth=1, markeredgecolor='black')
    
    plt.tight_layout()
    
    # Génération d'un nom de fichier unique avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
    
    # Exécuter la simulation
    env, drones, control = run_simulation(
        num_drones=5,      # Nombre de drones dans l'essaim
        num_steps=200,     # Nombre de pas de simulation
        visualize=False
    )
    
    # Visualisation optionnelle
    try:
        visualize_final_state(env, drones, control)
    except Exception as e:
        print(f"\nVisualisation non disponible : {e}")
        print("   (Installation de matplotlib requise pour la visualisation)")
    
    print("\n" + "="*60)
    print("Programme terminé avec succès !")
    print("="*60 + "\n")
