import numpy as np
import random
import os

# Import des classes depuis le dossier classes
from classes import AnomalyDetector, Anomaly, Environment, Drone, ControlCenter

# Codes couleur ANSI pour le terminal
class Colors:
    RED = '\033[91m'      # Anomalies réelles
    YELLOW = '\033[93m'   # Anomalies détectées par les drones
    CYAN = '\033[96m'     # Anomalies connues par la base
    GREEN = '\033[92m'    # Drones et leur zone de détection
    RESET = '\033[0m'     # Reset couleur

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


def clear_screen():
    """Efface l'écran du terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_simulation_grid(env, drones, control, step, num_steps, initial_info=""):
    """Affiche l'état de la simulation sous forme de grille ASCII dans le terminal."""
    clear_screen()
    
    # Dimensions de la grille d'affichage (réduire pour tenir dans le terminal)
    display_width = min(80, env.width)
    display_height = min(40, env.height)
    scale_x = env.width / display_width
    scale_y = env.height / display_height
    
    # Créer la grille vide
    grid = [[' ' for _ in range(display_width)] for _ in range(display_height)]
    
    # Marquer les zones explorées (depuis la carte globale du centre de contrôle)
    if control.global_exploration_map is not None:
        for y in range(display_height):
            for x in range(display_width):
                real_x = int(x * scale_x)
                real_y = int(y * scale_y)
                if real_y < control.global_exploration_map.shape[0] and real_x < control.global_exploration_map.shape[1]:
                    if control.global_exploration_map[real_y, real_x] > 0:
                        grid[display_height - 1 - y][x] = '·'  # Zone explorée
    
    # Placer les anomalies réelles (en rouge - priorité basse, affichées en premier)
    for anomaly in env.anomalies:
        grid_x = int(anomaly.x / scale_x)
        grid_y = display_height - 1 - int(anomaly.y / scale_y)
        if 0 <= grid_y < display_height and 0 <= grid_x < display_width:
            if anomaly.type == 'pollution':
                grid[grid_y][grid_x] = f"{Colors.RED}☢{Colors.RESET}"
            elif anomaly.type == 'radiation':
                grid[grid_y][grid_x] = f"{Colors.RED}☣{Colors.RESET}"
            else:
                grid[grid_y][grid_x] = f"{Colors.RED}⚠{Colors.RESET}"
    
    # Placer les anomalies détectées par les drones (en jaune - priorité moyenne, écrase rouge)
    for drone in drones:
        for anomaly_info in drone.detected_anomalies:
            pos = anomaly_info['position']
            grid_x = int(pos[0] / scale_x)
            grid_y = display_height - 1 - int(pos[1] / scale_y)
            if 0 <= grid_y < display_height and 0 <= grid_x < display_width:
                grid[grid_y][grid_x] = f"{Colors.YELLOW}☣{Colors.RESET}"  # Symbole jaune pour détectées
    
    # Placer les anomalies connues par la base (en cyan - priorité haute, écrase tout)
    for pos, intensity in control.global_anomaly_map.items():
        grid_x = int(pos[0] / scale_x)
        grid_y = display_height - 1 - int(pos[1] / scale_y)
        if 0 <= grid_y < display_height and 0 <= grid_x < display_width:
            grid[grid_y][grid_x] = f"{Colors.CYAN}☢{Colors.RESET}"  # Symbole cyan pour connues
    
    # Placer la base
    base_grid_x = int(control.base_x / scale_x)
    base_grid_y = display_height - 1 - int(control.base_y / scale_y)
    if 0 <= base_grid_y < display_height and 0 <= base_grid_x < display_width:
        grid[base_grid_y][base_grid_x] = '█'
    
    # Placer les drones (en dernier pour qu'ils soient visibles)
    for i, drone in enumerate(drones):
        drone_grid_x = int(drone.x / scale_x)
        drone_grid_y = display_height - 1 - int(drone.y / scale_y)
        
        # Afficher la zone de détection 5×5 autour du drone (de -2 à +2)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                gx = drone_grid_x + dx
                gy = drone_grid_y + dy
                if 0 <= gy < display_height and 0 <= gx < display_width:
                    if grid[gy][gx] == ' ' or grid[gy][gx] == '·':
                        grid[gy][gx] = f"{Colors.GREEN}o{Colors.RESET}"
        
        # Placer le drone par-dessus la zone (en vert)
        if 0 <= drone_grid_y < display_height and 0 <= drone_grid_x < display_width:
            grid[drone_grid_y][drone_grid_x] = f"{Colors.GREEN}{str(i)}{Colors.RESET}"
    
    # Afficher les infos initiales si fournies
    if initial_info:
        print(initial_info)
    
    # Afficher l'en-tête
    print("="*80)
    print(f"  SIMULATION - Tour {step+1}/{num_steps}".center(80))
    print("="*80)
    
    # Afficher la grille
    print("┌" + "─" * display_width + "┐")
    for row in grid:
        print("│" + ''.join(row) + "│")
    print("└" + "─" * display_width + "┘")
    
    # Légende
    print("\nLÉGENDE :")
    print(f"  {Colors.GREEN}0-9{Colors.RESET} = Drones  |  {Colors.GREEN}o{Colors.RESET} = Zone détection | █ = Base")
    print(f"  {Colors.RED}⚠{Colors.RESET} = Anomalies réelles")
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} = Anomalies détectées par les drones")
    print(f"  {Colors.CYAN}⚠{Colors.RESET} = Anomalies connues par la base")
    print("  · = Exploré (zones connues par le centre de contrôle)")
    print("  [✓] = Drone synchronisé (retour base au moins 1×)")
    
    # Statistiques
    if control.global_exploration_map is not None:
        exploration_pct = (control.global_exploration_map.sum() / control.global_exploration_map.size) * 100
    else:
        exploration_pct = 0.0
    current_time_sim = step * 1.0  # secondes
    time_min = int(current_time_sim // 60)
    time_sec = int(current_time_sim % 60)
    print(f"\nSTATISTIQUES :")
    print(f"  Temps simulé : {time_min}min {time_sec}s")
    print(f"  Exploration : {exploration_pct:.1f}%")
    print(f"  Anomalies actives : {len(env.anomalies)}")
    print(f"  Anomalies détectées : {len(control.global_anomaly_map)}")
    
    # État des drones
    print(f"\nÉTAT DES DRONES :")
    for drone in drones:
        print(f"  Drone {drone.id}: {drone.status_text}")
    
    print("="*80)


# ------------------------------
# SIMULATION PRINCIPALE
# ------------------------------

def create_test_environment():
    """Crée un environnement de test avec plusieurs anomalies."""
    env = Environment(width=100, height=100)
    
    # Ajout d'anomalies diverses avec intensités plus fortes et rayons plus grands
    env.add_anomaly(Anomaly(x=30, y=70, intensity=1.5, radius=15, type='pollution'))
    env.add_anomaly(Anomaly(x=75, y=25, intensity=1.3, radius=12, type='radiation'))
    env.add_anomaly(Anomaly(x=50, y=50, intensity=1.2, radius=18, type='effondrement'))
    env.add_anomaly(Anomaly(x=20, y=20, intensity=1.0, radius=10, type='pollution'))
    env.add_anomaly(Anomaly(x=80, y=80, intensity=1.4, radius=14, type='radiation'))
    
    return env


def run_simulation(num_drones=5, num_steps=200, seed=None, display_interval=10):
    """
    Exécute la simulation complète du système de drones.
    
    Args:
        num_drones: Nombre de drones
        num_steps: Nombre de tours de simulation
        seed: Seed pour la reproductibilité (None = aléatoire)
        display_interval: Intervalle d'affichage de la grille (en tours)
    """
    # 0. Fixer le seed si fourni
    set_global_seed(seed)
    
    # 1. Créer le détecteur d'anomalies
    detector = AnomalyDetector()
    
    # 2. Créer l'environnement
    env = create_test_environment()
    
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
        # Améliorer les paramètres des drones
        drone.speed = 3.0  # Vitesse augmentée
        # Initialiser avec des temps d'activité différents pour décaler les retours (0 à 1500s)
        drone.activity_time = random.uniform(0, 1500)
        drones.append(drone)
    
    # Assigner des zones initiales différentes à chaque drone pour meilleure couverture
    zone_targets = [
        (25, 75),   # Nord-Ouest
        (75, 75),   # Nord-Est  
        (50, 50),   # Centre
        (25, 25),   # Sud-Ouest
        (75, 25),   # Sud-Est
        (15, 50),   # Ouest
        (85, 50),   # Est
    ]
    for i, drone in enumerate(drones):
        if i < len(zone_targets):
            drone.target_x, drone.target_y = zone_targets[i]
    
    # 5. Préparation des informations permanentes
    initial_info = f"""{'='*60}
   PROJET IA - SYSTÈME AUTONOME DE DRONES COOPÉRATIFS
{'='*60}
Seed: {seed if seed else 'Aléatoire'} | Drones: {num_drones} | Carte: {env.width}x{env.height} | Anomalies initiales: {len(env.anomalies)}
"""
    
    delta_time = 1.0  # Chaque tour = 1 seconde
    current_time = 0.0
    
    for step in range(num_steps):
        current_time = step * delta_time
        
        # Évolution de l'environnement (anomalies)
        env.update(current_time, delta_time)
        
        # Mise à jour de chaque drone
        for drone in drones:
            drone.update(env, drones, delta_time, control)
        
        # Affichage dynamique de la grille
        if step % display_interval == 0:
            display_simulation_grid(env, drones, control, step, num_steps, initial_info)
    
    # Affichage final
    display_simulation_grid(env, drones, control, num_steps-1, num_steps, initial_info)
    
    # 6. Rapport final
    print("\n" + "="*60)
    print("SIMULATION TERMINÉE - RAPPORT FINAL")
    print("="*60)
    
    control.print_status(drones)
    
    if control.global_exploration_map is not None:
        exploration_pct = (control.global_exploration_map.sum() / control.global_exploration_map.size) * 100
    else:
        exploration_pct = 0.0
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
# POINT D'ENTRÉE PRINCIPAL
# ------------------------------

if __name__ == "__main__":
    # Exécuter la simulation avec visualisation en terminal
    env, drones, control = run_simulation(
        num_drones=7,           # Nombre de drones dans l'essaim
        num_steps=5000,         # Nombre de pas de simulation (5000 secondes = 1h 23min)
        seed=42,                # Seed pour reproductibilité (None = aléatoire)
        display_interval=50     # Affichage toutes les 50 tours
    )
    
    print("\n" + "="*60)
    print("Programme terminé avec succès !")
    print("="*60 + "\n")
