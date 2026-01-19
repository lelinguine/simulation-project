import numpy as np

class AnomalyDetector:
    """
    Détecteur d'anomalies basé sur des seuils.
    Analyse 4 capteurs : température, radiation, pluie de météorites, inondations.
    """
    def __init__(self):
        # Seuils de détection pour chaque type de capteur
        self.threshold_temp = 30.0      # Température anormale > 30°C
        self.threshold_radiation = 0.4  # Radiation anormale > 0.4
        self.threshold_meteorites = 0.3  # Pluie de météorites anormale > 0.3
        self.threshold_floods = 0.4   # Inondations anormales > 0.4
    
    def detect_anomaly(self, sensor_data, threshold=0.5):
        """
        Détecte si les données capteurs indiquent une anomalie.
        Retourne : (is_anomaly, intensity)
        """
        # Extraction des valeurs des capteurs
        if isinstance(sensor_data, np.ndarray):
            temp, radiation, meteorites, floods = sensor_data.tolist()
        else:
            temp, radiation, meteorites, floods = sensor_data
        
        # Calcul du score d'anomalie (somme pondérée)
        anomaly_score = 0.0
        
        if temp > self.threshold_temp:
            anomaly_score += 0.3 * ((temp - self.threshold_temp) / (50 - self.threshold_temp))
        
        if radiation > self.threshold_radiation:
            anomaly_score += 0.3 * ((radiation - self.threshold_radiation) / (1.0 - self.threshold_radiation))
        
        if meteorites > self.threshold_meteorites:
            anomaly_score += 0.2 * ((meteorites - self.threshold_meteorites) / (1.0 - self.threshold_meteorites))
        
        if floods > self.threshold_floods:
            anomaly_score += 0.2 * ((floods - self.threshold_floods) / (1.0 - self.threshold_floods))
        
        # Normalisation entre 0 et 1
        intensity = min(anomaly_score, 1.0)
        
        return intensity > threshold, intensity
