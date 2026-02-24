# 🚀 AI_AUDITOR Québec v2.0

**Plateforme d'audit fiscal automatisé avec IA locale**

[![Edge-First](https://img.shields.io/badge/Architecture-Edge%20First-blue.svg)](https://ai-auditor.ca)
[![LPRPDE](https://img.shields.io/badge/Compliance-LPRPDE-green.svg)](https://ai-auditor.ca)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Qu'est-ce que c'est?

AI_Auditor est une plateforme propulsé et managé par JEK, la first IA souveraine canadienne,  intelligente d'audit fiscal qui fonctionne **100% LOCALEMENT** sur votre ordinateur.

Aucune donnée sensible ne quitte jamais votre cabinet.

### ✨ Fonctionnalités principales

- 🔍 **Détection d'anomalies** - TPS/TVQ, doublons, montants suspects
- 🤖 **IA Locale** - Explications intelligentes avec Ollama (optionnel)
- 📄 **Rapports Pro** - PDF, Word, Excel professionnels
- 📊 **Dashboard** - Visualisations temps réel
- 💾 **Base de données** - Historique audit local
- 🔐 **Sécurité** - LPRPDE compliant, données locales
- 🚀 **Fast** - Traitement en secondes, pas de latence réseau

## 🚀 Installation rapide (5 min)

### Prérequis
- Python 3.9+
- pip (gestionnaire paquets Python)
- Git (optionnel)

### Étape 1: Cloner ou télécharger
```bash
git clone https://github.com/jek-ai/ai-auditor.git
cd ai-auditor
```

### Étape 2: Installer dépendances
```bash
pip install -r requirements.txt
```

### Étape 3: Lancer l'app
```bash
streamlit run app_ultimate.py
```

L'app s'ouvre automatiquement à `http://localhost:8501`

### Étape 4: Se connecter
```
Username: demo
Mot de passe: (Demander à support@ai-auditor.ca)
```

## 📖 Guide d'utilisation

### Workflow principal: 5 étapes simples

#### 1️⃣ **Login**
- Entrez vos identifiants
- Dashboard s'affiche

#### 2️⃣ **Upload fichier Excel**
```
Colonnes requises:
- DATE (format: YYYY-MM-DD ou DD-MM-YYYY)
- DESCRIPTION (nom fournisseur)
- DEBIT (montant facture)
- TPS (taxes fédérales)
- TVQ (taxes provinciales)

Exemple:
Date        | Description   | Debit  | TPS  | TVQ
2024-01-15  | Amazon AWS    | 500.00 | 25   | 49.88
2024-01-15  | Bell Canada   | 150.00 | 7.50 | 14.96
```

#### 3️⃣ **Lancer audit**
- Cliquez "🚀 Lancer audit"
- Attendez quelques secondes
- Résultats s'affichent

#### 4️⃣ **Analyser résultats**
- Tableau détaillé avec anomalies
- Graphiques impacts
- Filtres par type/risque

#### 5️⃣ **Générer rapport**
- Sélectionner format (PDF/Word/Excel)
- Cliquer "📥 Générer rapport"
- Télécharger

## 🎯 Anomalies détectées

### Types d'anomalies

| Type | Description | Exemple |
|------|-------------|---------|
| **Doublon** | Deux factures identiques | Amazon $500 x2 |
| **Écart TPS** | TPS ne correspond pas au montant | 5% attendu, 3% trouvé |
| **Écart TVQ** | TVQ incorrecte | 9.975% attendu, 8% trouvé |
| **Montant élevé** | Transaction anormalement haute | $50,000 vs moyenne $500 |
| **Date incohérente** | Date future ou très ancienne | 2099-01-01 ou 2010-01-01 |
| **Fraude pattern** | Patterns suspects (ML) | >30% montants ronds |
| **Fraude adresse** | Même adresse, noms différents | Same address, 5 vendors |

### Niveaux de risque

- 🟢 **BAS** - À vérifier, probablement OK
- 🟡 **MOYEN** - À investiguer
- 🔴 **CRITIQUE** - Action immédiate

## 🤖 IA locale (Ollama)

### Installation Ollama (optionnel)

1. Télécharger depuis [ollama.ai](https://ollama.ai)
2. Installer et lancer
3. Télécharger modèle:
```bash
ollama pull llama3.2
```

### Chat IA dans l'app

Une fois Ollama lancé, l'onglet "Chat IA" devient actif:

- Posez questions sur anomalies
- Obtenez explications intelligentes
- Tout fonctionne LOCALEMENT

**Sans Ollama?** Pas de problème - app fonctionne sans IA, avec fallback sur règles simples.

## 📊 Dashboard - Statistiques

- **Audits ce mois** - Nombre d'audits réalisés
- **Transactions** - Total factures analysées
- **Anomalies** - Total anomalies détectées
- **Impact détecté** - Valeur total à investiguer

## 🔧 Configuration avancée

Modifier `config.json`:

```json
{
  "TPS_RATE": 0.05,           // Taux TPS (5%)
  "TVQ_RATE": 0.09975,        // Taux TVQ Québec (9.975%)
  "TOLERANCE_TAX": 0.05,      // Tolérance écart (5%)
  "FUZZY_THRESHOLD": 85,      // Seuil doublon fuzzy match
  "OLLAMA_MODEL": "llama3.2"  // Modèle IA à utiliser
}
```

## 🔐 Sécurité & Conformité

### ✅ LPRPDE Compliant

- Aucune donnée envoyée à serveurs externes
- Base de données SQLite locale uniquement
- Chiffrement optionnel des fichiers
- Logs d'audit complets

### ✅ Offboarding de données

Données conservées localement. Pour supprimer:

```bash
# Supprimer base de données
rm ai_auditor.db

# Supprimer logs
rm ai_auditor.log
```

## 🚀 Déploiement (Production)

### Option 1: Streamlit Cloud (gratuit)
```bash
git push origin main
# Visit https://streamlit.io/cloud
```

### Option 2: Heroku
```bash
heroku login
heroku create ai-auditor
git push heroku main
```

### Option 3: Docker (Recommandé)
```bash
docker build -t ai-auditor .
docker run -p 8501:8501 ai-auditor
```

`Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app_ultimate.py"]
```

## 📞 Support

- **Email:** support@ai-auditor.ca
- **Chat:** En-app messaging
- **Heures:** Lun-Ven 9h-17h EST
- **Réponse:** <4h

## 🐛 Dépannage

### Issue: "ModuleNotFoundError"
```bash
# Assurez-vous d'avoir install requirements
pip install -r requirements.txt
```

### Issue: "Connection refused" (Ollama)
```bash
# Ollama n'est pas lancé
# Sur Mac/Linux:
ollama serve

# Sur Windows:
# Lancer application Ollama.exe
```

### Issue: "Permission denied" (Database)
```bash
# Vérifiez que vous avez permission écriture dans dossier
chmod 755 ai_auditor.db
```

### Issue: Port 8501 déjà utilisé
```bash
# Utiliser port différent
streamlit run app_ultimate.py --server.port 8502
```

## 📝 Architecture

```
AI_AUDITOR/
├── app_ultimate.py          # Interface Streamlit (UI)
├── audit_engine.py          # Moteur audit (Core algorithms)
├── report_generator.py      # Génération rapports
├── config.json              # Configuration
├── requirements.txt         # Dépendances Python
├── ai_auditor.db           # Base de données SQLite (LOCAL)
├── ai_auditor.log          # Logs (LOCAL)
└── README.md               # Ce fichier
```

## 🏗️ Structure code

### `audit_engine.py`
- `AuditEngineAI` - Moteur principal
- `OllamaClient` - Client IA locale
- `MLFraudDetector` - Détection fraude ML
- `LocalDatabase` - Stockage local

### `app_ultimate.py`
- Interface Streamlit
- Gestion authentification
- Upload fichiers
- Affichage résultats

### `report_generator.py`
- Génération PDF
- Génération Word (éditable)
- Génération Excel
- Formatting professionnel

## 📊 Modèle de données

### Anomaly (objet)
```python
{
    'Type': str,              # Type d'anomalie
    'Description': str,       # Description détaillée
    'Fournisseur': str,       # Nom fournisseur
    'Montant': float,         # Montant transaction
    'Impact_Estimation': float,  # Impact financier
    'Risque': str,            # BAS/MOYEN/CRITIQUE
    'Recommandation': str,    # Action recommandée
    'Confiance': float        # 0-100 confidence
}
```

## 🎓 Examples d'utilisation

### Example 1: Audit simple PME
```bash
1. Upload factures.xlsx (100 lignes)
2. Lancer audit (5 sec)
3. Découvrir $2,500 d'écarts TPS
4. Générer rapport PDF
5. Envoyer au client
```

### Example 2: Audit grosse entreprise
```bash
1. Upload factures_2024.xlsx (5000 lignes)
2. Lancer audit (30 sec)
3. 47 anomalies détectées
4. $125,000 impact potentiel
5. Exporter Excel pour analyse
```

## 🔄 Intégrations futures (Roadmap)

- ✅ QB/Sage sync (Q2 2024)
- ✅ API REST (Q3 2024)
- ✅ Mobile app (Q4 2024)
- ✅ White-label (2025)

## 📄 License

MIT License - Voir `LICENSE` file

## 🙋 Contributing

Vous avez une idée? Bug? Feature request?

Email: dev@ai-auditor.ca

## 🎯 Roadmap

### V2.0 (Current)
- [x] Core audit engine
- [x] Streamlit UI
- [x] Report generation
- [x] Ollama integration
- [x] Local database

### V2.1 (Next)
- [ ] QuickBooks integration
- [ ] Sage integration
- [ ] Mobile app (React Native)
- [ ] Zapier integration

### V3.0 (Future)
- [ ] White-label version
- [ ] API REST
- [ ] Advanced ML models
- [ ] Multi-language support

## 📞 Contact

**AI_Auditor Team**
- 📧 Email: hello@ai-auditor.ca
- 🌐 Web: https://ai-auditor.ca
- 💬 Support: support@ai-auditor.ca

---

**Made with ❤️ by Jek AI Neural Engine**

Edge-first. Compliant. Local. Secure.

