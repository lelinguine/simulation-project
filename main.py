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
# 7. SIMULATION PRINCIPALE
# ------------------------------

def create_test_environment():
    """Crée un environnement de test avec plusieurs anomalies."""
    env = Environment(width=100, height=100)
    
    # Ajout d'anomalies diverses
    env.add_anomaly(Anomaly(x=30, y=70, intensity=0.9, radius=10, type='pollution'))
    env.add_anomaly(Anomaly(x=75, y=25, intensity=0.85, radius=8, type='radiation'))
    env.add_anomaly(Anomaly(x=50, y=50, intensity=0.7, radius=12, type='effondrement'))
    env.add_anomaly(Anomaly(x=20, y=20, intensity=0.6, radius=6, type='pollution'))
    env.add_anomaly(Anomaly(x=80, y=80, intensity=0.75, radius=9, type='radiation'))
    
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
            control.print_status(drones)
            exploration_pct = (env.exploration_map.sum() / env.exploration_map.size) * 100
            print(f"\nProgression : {exploration_pct:.1f}% de la zone explorée")
    
    # 6. Rapport final
    print("\n" + "="*60)
    print("SIMULATION TERMINÉE - RAPPORT FINAL")
    print("="*60)
    
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
# 8. VISUALISATION (OPTIONNEL)
# ------------------------------

def visualize_final_state(env, drones, control):
    """Crée une visualisation de l'état final de la simulation."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Carte d'exploration
    ax1.imshow(env.exploration_map, cmap='Greens', origin='lower', alpha=0.6)
    ax1.set_title('Carte d\'Exploration', fontsize=14, fontweight='bold')
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    
    # Anomalies réelles
    for anomaly in env.anomalies:
        circle = Circle((anomaly.x, anomaly.y), anomaly.radius, 
                           color='red', alpha=0.3, label='Anomalie')
        ax1.add_patch(circle)
        ax1.plot(anomaly.x, anomaly.y, 'rx', markersize=10, markeredgewidth=2)
    
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
# 9. POINT D'ENTRÉE PRINCIPAL
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
