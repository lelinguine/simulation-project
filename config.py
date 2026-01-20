# ============================================================================
# FICHIER DE CONFIGURATION - SYSTÈME AUTONOME DE DRONES COOPÉRATIFS
# ============================================================================

# ====================
# PARAMÈTRES DE SIMULATION
# ====================
MAX_TURNS = 300                # Nombre maximum de tours
NUM_DRONES = 5                   # Nombre de robots dans l'essaim

# ====================
# PARAMÈTRES DE BATTERIE ET ÉNERGIE
# ====================
BATTERY_MAX = 100.0                 # Capacité maximale de batterie
BATTERY_RECHARGE_RATE = 10.0        # Batterie rechargée par tour à la base
MOVEMENT_COST = 0.1                # Batterie consommée par déplacement
TREATMENT_COST_WEAK = 5.0           # Batterie consommée pour traiter une anomalie FAIBLE (intensité 1)
TREATMENT_COST_INTENSE = 15.0       # Batterie consommée pour traiter une anomalie INTENSE (intensité 2)
BATTERY_DEPARTURE_THRESHOLD = 0.85   # % de batterie max avant de quitter la base (baissé pour plus d'exploration)

# ====================
# PARAMÈTRES DE VISION ET COMMUNICATION
# ====================
VISION_RADIUS = 10.0                # Rayon de vision des robots (détection)
COMMUNICATION_RADIUS = 10.0         # Rayon de communication (peut être différent de vision)
 
# ====================
# ALÉATOIRE / REPRODUCTIBILITÉ
# ====================
# Définir un entier pour fixer l'aléatoire (ex: 42). Mettre None pour aléatoire libre.
SEED = 42

# ====================
# ANOMALIES
# ====================
NUM_ANOMALIES = 20                   # Nombre total d'anomalies à générer
ANOMALY_TYPES = [                   # Types d'anomalies disponibles (répartis aléatoirement)
    'pluie_meteorites',
    'radiation',
    'inondations'
]
ANOMALY_MIN_DISTANCE = 1.0         # Distance minimale entre deux anomalies
ANOMALY_MIN_DISTANCE_FROM_BASE = 10.0  # Distance minimale entre anomalie et base

# Intensité des anomalies (système simplifié)
ANOMALY_WEAK_INTENSITY = 1          # Intensité pour anomalie faible
ANOMALY_INTENSE_INTENSITY = 2       # Intensité pour anomalie intense

# Propagation et évolution des anomalies
ANOMALY_SPREAD_CHANCE = 0.00      # Chance (1% par défaut) qu'une anomalie intense propage sur cases adjacentes
ANOMALY_SNOWBALL_CHANCE = 0.00      # Chance (1% par défaut) qu'une anomalie faible devienne intense

# ====================
# ENVIRONNEMENT
# ====================
MAP_WIDTH = 100                     # Largeur de la carte
MAP_HEIGHT = 100                    # Hauteur de la carte

# ====================
# POSITION DE LA BASE
# ====================
# Options pour BASE_POSITION:
#   - Valeur fixe tuple: (x, y)  ex: (10, 10)
#   - Position cardinale string: 'N', 'S', 'E', 'O', 'NE', 'NO', 'SE', 'SO'
#     N  = haut centre    (50, 95)
#     S  = bas centre     (50, 5)
#     E  = est centre     (95, 50)
#     O  = ouest centre   (5, 50)
#     NE = nord-est       (90, 90)
#     NO = nord-ouest     (10, 90)
#     SE = sud-est        (90, 10)
#     SO = sud-ouest      (10, 10)
#   - 'A' ou 'RANDOM' = position aléatoire

BASE_POSITION = ("O")            # Position fixe ou stratégie ci-dessus
                                    # BASE_POSITION = 'SO'  # pour sud-ouest
                                    # BASE_POSITION = 'A'   # pour aléatoire

# ====================
# VITESSE DE MOUVEMENT
# ====================
DRONE_SPEED = 5.0                   # Unités parcourues par tour

# ====================
# STRATÉGIE DES ROBOTS
# ====================
# Stratégie des robots: 'action', 'exploration', ou 'mixte'
#   - 'action': Explore → si anomalie détectée → traite immédiatement → reprend exploration
#   - 'exploration': Explore 100% carte AVANT de traiter anomalies
#   - 'mixte': Explore → si anomalie → va vers elle, si plus urgente en route → traite urgente d'abord
ROBOT_STRATEGY = 'action'

# ====================
# VISUALISATION
# ====================
SAVE_MOVEMENTS_CSV = True           # Exporter les déplacements en CSV
SAVE_VISUALIZATION = True           # Sauvegarder l'image PNG

# ====================
# DEBUG
# ====================
VERBOSE = False                     # Afficher les logs détaillés
