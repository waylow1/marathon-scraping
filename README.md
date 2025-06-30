# 📸 Gestionnaire de Téléchargement et Traitement de Photos

Ce projet permet de télécharger automatiquement des photos, de les placer dans une file d’attente (queue), puis de les traiter via un système de worker asynchrone.

---

## 🚀 Fonctionnement général

1. **Téléchargement des photos**  
   Les photos sont récupérées depuis une source externe (API, dossier, etc.) grâce à un script dédié.  
   Chaque photo téléchargée est ajoutée à une file d’attente pour traitement ultérieur.

2. **Mise en file d’attente (Queue)**  
   Le système utilise une queue (par exemple Redis, RabbitMQ, ou une simple liste Python) pour stocker les tâches à traiter.  
   Cela permet de séparer le téléchargement du traitement, et d’assurer une gestion efficace même avec un grand nombre de photos.

3. **Traitement par Worker**  
   Un worker indépendant récupère les photos dans la queue et effectue les opérations nécessaires (remove watermark).  
   Ce worker fonctionne en tâche de fond et peut être lancé séparément.

---

## 🛠️ Lancement du projet

### 1. Télécharger et mettre en queue les photos

Lance la commande suivante dans le terminal intégré de VS Code :

```
uv run python3 -m src.main
```

Cela va télécharger les photos et les placer dans la file d’attente.

### 2. Démarrer le worker

Dans un autre terminal, lance :

```
uv run python3 -m src.worker --dossard {num_dossard}
```

Le worker va alors traiter automatiquement les photos présentes dans la queue.

---

## ✨ Astuces

- Tu peux surveiller la progression dans le panneau **Output** de VS Code.
- Les logs détaillés sont disponibles dans le terminal où tu as lancé chaque script.
- Si tu veux arrêter le worker, utilise `Ctrl+C` dans le terminal correspondant.

---
