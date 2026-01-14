import torch

class AnomalyDetector:
    """
    Détecteur d'anomalies basé sur des seuils.
    Analyse 5 capteurs : température, radiation, pollution, mouvement, bruit.
    """
    def __init__(self):
        # Seuils de détection pour chaque type de capteur
        self.threshold_temp = 30.0      # Température anormale > 30°C
        self.threshold_radiation = 0.4  # Radiation anormale > 0.4
        self.threshold_pollution = 0.3  # Pollution anormale > 0.3
        self.threshold_movement = 0.4   # Mouvement anormal > 0.4
        self.threshold_noise = 0.4      # Bruit anormal > 0.4
    
    def detect_anomaly(self, sensor_data, threshold=0.5):
        """
        Détecte si les données capteurs indiquent une anomalie.
        Retourne : (is_anomaly, intensity)
        """
        # Extraction des valeurs des capteurs
        if isinstance(sensor_data, torch.Tensor):
            temp, radiation, pollution, movement, noise = sensor_data.tolist()
        else:
            temp, radiation, pollution, movement, noise = sensor_data
        
        # Calcul du score d'anomalie (somme pondérée)
        anomaly_score = 0.0
        
        if temp > self.threshold_temp:
            anomaly_score += 0.3 * ((temp - self.threshold_temp) / (50 - self.threshold_temp))
        
        if radiation > self.threshold_radiation:
            anomaly_score += 0.3 * ((radiation - self.threshold_radiation) / (1.0 - self.threshold_radiation))
        
        if pollution > self.threshold_pollution:
            anomaly_score += 0.2 * ((pollution - self.threshold_pollution) / (1.0 - self.threshold_pollution))
        
        if movement > self.threshold_movement:
            anomaly_score += 0.1 * ((movement - self.threshold_movement) / (1.0 - self.threshold_movement))
        
        if noise > self.threshold_noise:
            anomaly_score += 0.1 * ((noise - self.threshold_noise) / (1.0 - self.threshold_noise))
        
        # Normalisation entre 0 et 1
        intensity = min(anomaly_score, 1.0)
        
        return intensity > threshold, intensity
