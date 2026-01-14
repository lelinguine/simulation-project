import torch
import torch.nn as nn # lib pour la création de reseau de neuronnes
import torch.optim as optim # lib pour les fonctions d'optimisation

#--------------------------------------------
# Explications
# Entrées : 2 valeurs boolean (0 ou 1)
# Sorties : 1 valeur  boolean
# Couche intermédiaire : 4 neurones

# Architecture:
# 2 → 4 → 1 MLP with ReLU (fonction d'activation)

# Sigmoid output for probability
# Trains with binary cross-entropy
#--------------------------------------------

# ------------------------------
# 1. Données d'entrainement
# ------------------------------

# Des entrees booleenes
X = torch.tensor([
    [0., 0.],
    [0., 1.],
    [1., 0.],
    [1., 1.]
])

# Les differentes fonctions booléenes
y_AND = torch.tensor([[0.], [0.], [0.], [1.]])
y_OR  = torch.tensor([[0.], [1.], [1.], [1.]])
y_XOR = torch.tensor([[0.], [1.], [1.], [0.]])

# On va commencer par tester avec XOR !
y = y_XOR   # change to y_AND or y_OR as needed


# ------------------------------
# 2. Definition du reseau
# ------------------------------

class BooleanNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(2, 4),   # hidden layer (2 entrées, 4 sorties)
            nn.ReLU(),         # fonction d'activation entre hidden et sortie
            nn.Linear(4, 1),   # output layer (4 entrées, 1 sortie)
            nn.Sigmoid()       # 1 sortie, valeur 0 ou 1
        )

    def forward(self, x):
        return self.model(x)

net = BooleanNet()

# ------------------------------
# 3. Etape de configuration
# ------------------------------

criterion = nn.BCELoss() # Binary Cross Entropy : adaptee pour les predicions 1 ou 0 (oui/non)
# Example : target = 1 prediction = 0.9 loss = -log(0.9) = 0.105 good prediction
#           target = 1 prediction = 0.1 loss = -log(0.1) = 2.302 bad predicion
#           target = 0 prediction = 0.0 loss = -log(1) = 0 parfait !
optimizer = optim.Adam(net.parameters(), lr=0.05) # optim moderne qui adapt le taux d'apprentissage (ici, 0.05)

# ------------------------------
# 4. Entrainement
# ------------------------------
for epoch in range(3000): # realise 3000 cycles d'apprentissage
    optimizer.zero_grad()
    pred = net(X) # feed foward
    loss = criterion(pred, y) # compare la sortie du reseau avec ce qui est attendu. Loss est l'ERREUR
    loss.backward() # calcule les gradients en utilisant la retropropagation : comment chaque poids participe à l'erreur => Si le gradient est positif, augmenter le poids augmente la perte
                                                                                       #=> Si le gradient est négatif, augmenter le poids diminue la perte
    optimizer.step() # actualise les poids en utilisant les gradients

    if epoch % 500 == 0: # on imprive la fonction de perte
        print(f"Epoch {epoch}  Loss: {loss.item():.4f}")

# ------------------------------
# 5. Etape d'inference
# ------------------------------
with torch.no_grad():
    print("\nTesting:")
    for inp in X:
        out = net(inp)
        print(f"{inp.tolist()} → {int(out > 0.5)}  (raw={out.item():.3f})")
