# visualize.py simplifié
import os

# On simule les dépendances pour éviter de charger Numpy/Pandas si possible
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

try:
    from bot.src.orchestrator.graph import build_graph
    
    app = build_graph()
    # Utilisation du rendu texte Mermaid
    print("\n" + "="*50)
    print("COPIEZ LE CODE CI-DESSOUS")
    print("="*50 + "\n")
    print(app.get_graph().draw_mermaid())
    print("\n" + "="*50)
    print("COLLEZ-LE SUR : https://mermaid.live/")
    print("="*50)
except Exception as e:
    print(f"Erreur lors de la génération : {e}")
