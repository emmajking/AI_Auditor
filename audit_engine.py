"""
AI_AUDITOR - Moteur d'audit fiscal avec IA locale (Edge-first)
Par Jek AI Neural Engine

ARCHITECTURE EDGE:
- Tous les algos tournent LOCALEMENT
- Zéro appels cloud (sauf Ollama optionnel)
- LPRPDE compliant automatiquement
- Fonctionne offline
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import os
import logging
from pathlib import Path
import json
import re
from typing import Union, List, Dict, Tuple, Optional
from tqdm import tqdm
import requests
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import sqlite3
from dataclasses import dataclass
from enum import Enum

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_auditor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
EXCEL_ROW_OFFSET = 2
DUPLICATE_WINDOW_SIZE = 15
MAX_AMOUNT_THRESHOLD = 1_000_000
TPS_RATE_QC = 0.05
TVQ_RATE_QC = 0.09975
TAX_TOLERANCE = 0.05


class AnomalyType(Enum):
    """Types d'anomalies détectées"""
    DOUBLON = "Doublon de facture"
    TPS_ECART = "Écart TPS"
    TVQ_ECART = "Écart TVQ"
    MONTANT_ELEVE = "Montant élevé suspect"
    DATE_INCOHERENT = "Incohérence date"
    FRAUDE_ADRESSE = "Fraude: Même adresse"
    FRAUDE_DOCUMENT = "Fraude: Document manquant"
    FRAUDE_PATTERN = "Fraude: Pattern suspect"
    EXEMPTION_INCORRECTE = "Exemption TPS/TVQ incorrecte"


@dataclass
class Anomaly:
    """Représente une anomalie détectée"""
    anomaly_type: AnomalyType
    description: str
    vendor: str
    amount: float
    impact_estimation: float
    risk_level: str
    recommendation: str
    confidence: float
    timestamp: datetime = None
    
    def to_dict(self) -> Dict:
        """Convertir en dict pour export"""
        return {
            'Type': self.anomaly_type.value,
            'Description': self.description,
            'Fournisseur': self.vendor,
            'Montant': round(self.amount, 2),
            'Impact_Estimation': round(self.impact_estimation, 2),
            'Risque': self.risk_level,
            'Recommandation': self.recommendation,
            'Confiance': round(self.confidence, 1),
            'Date_Detection': self.timestamp.isoformat() if self.timestamp else datetime.now().isoformat()
        }


class OllamaClient:
    """Client pour Ollama LOCAL - Aucune donnée externe"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model
        self.cache = {}
        self.available = self._test_connection()
    
    def _test_connection(self) -> bool:
        """Vérifie qu'Ollama est accessible (optionnel)"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                logger.info(f"✅ Ollama connecté - Modèle: {self.model}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ Ollama non disponible: {e}")
        return False
    
    def query(self, prompt: str, use_cache: bool = True) -> Optional[str]:
        """Envoie une requête à Ollama LOCAL"""
        if not self.available:
            return None
        
        if use_cache and prompt in self.cache:
            return self.cache[prompt]
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 150
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                if use_cache:
                    self.cache[prompt] = result
                return result
        except Exception as e:
            logger.warning(f"Erreur requête Ollama: {e}")
        
        return None


class AuditEngineAI:
    """Moteur d'audit fiscal intelligent - EDGE FIRST"""
    
    def __init__(self, config_path: Optional[str] = None, use_ai: bool = True):
        """
        Initialiser moteur audit
        
        Args:
            config_path: Chemin au config.json
            use_ai: Activer Ollama (optionnel, fallback sans IA)
        """
        self.config = self._load_config(config_path)
        self.use_ai = use_ai
        self.ollama = OllamaClient() if use_ai else None
        self.ml_fraud_detector = MLFraudDetector()
        self.db = LocalDatabase()
        self.anomalies: List[Anomaly] = []
        
        logger.info(f"🚀 AuditEngineAI initialized (AI: {use_ai})")
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Charger configuration"""
        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)
        
        return {
            "TPS_RATE": TPS_RATE_QC,
            "TVQ_RATE": TVQ_RATE_QC,
            "TOLERANCE_TAX": TAX_TOLERANCE,
            "DATE_TOLERANCE_DAYS": 3,
            "MONTANT_TOLERANCE_PCT": 0.05,
            "FUZZY_THRESHOLD": 85,
            "EXEMPTIONS": {
                "export": ["exportation", "international", "usa"],
                "zero_rated": ["aliments", "produit laitier", "viande"],
                "detaxe": ["medicament", "sante", "education", "assurance"]
            }
        }
    
    def process_dataframe(self, df: pd.DataFrame, client_name: str) -> Tuple[List[Dict], Optional[str]]:
        """
        Traiter un fichier audit complet
        
        Returns:
            (anomalies_list, error_message)
        """
        try:
            self.anomalies = []
            
            # Nettoyage données
            df = self._clean_dataframe(df)
            
            if df.empty:
                return [], "Aucune donnée valide dans le fichier"
            
            logger.info(f"📊 Traitement: {len(df)} transactions pour {client_name}")
            
            # Détections en séquence
            self._detect_duplicates(df)
            self._detect_tax_anomalies(df)
            self._detect_high_amounts(df)
            self._detect_date_anomalies(df)
            self._detect_fraud_patterns(df)
            
            # Sauvegarde en database
            self.db.save_audit(client_name, self.anomalies)
            
            logger.info(f"✅ Audit complété: {len(self.anomalies)} anomalies trouvées")
            
            return [a.to_dict() for a in self.anomalies], None
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement: {e}")
            return [], str(e)
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoyer et normaliser les données"""
        df = df.copy()
        
        # Rename colonnes standard (case-insensitive)
        column_map = {
            'date': 'DATE',
            'description': 'DESCRIPTION',
            'vendor': 'DESCRIPTION',
            'fournisseur': 'DESCRIPTION',
            'debit': 'DEBIT',
            'amount': 'DEBIT',
            'montant': 'DEBIT',
            'tps': 'TPS',
            'gst': 'TPS',
            'tvq': 'TVQ',
            'qst': 'TVQ'
        }
        
        # Rename avec gestion des erreurs
        for old, new in column_map.items():
            for col in df.columns:
                if col.lower().strip() == old:
                    df.rename(columns={col: new}, inplace=True)
        
        # Nettoyer données avec vérifications
        if 'DATE' in df.columns:
            try:
                df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
            except Exception as e:
                logger.warning(f"Erreur conversion DATE: {e}")
        
        for col in ['DEBIT', 'TPS', 'TVQ']:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except Exception as e:
                    logger.warning(f"Erreur conversion {col}: {e}")
        
        # Nettoyer DESCRIPTION avec check
        if 'DESCRIPTION' in df.columns:
            try:
                df['DESCRIPTION'] = df['DESCRIPTION'].astype(str).str.strip().str.upper()
            except Exception as e:
                logger.warning(f"Erreur nettoyage DESCRIPTION: {e}")
                df['DESCRIPTION'] = df['DESCRIPTION'].astype(str)
        
        # Supprimer lignes nulles
        try:
            df = df.dropna(subset=['DESCRIPTION', 'DEBIT'])
        except Exception as e:
            logger.warning(f"Erreur dropna: {e}")
        
        return df
    
    def _detect_duplicates(self, df: pd.DataFrame) -> None:
        """Détecter doublon factures"""
        if 'DESCRIPTION' not in df.columns or 'DEBIT' not in df.columns:
            return
        
        checked = set()
        
        for idx, row in df.iterrows():
            if idx in checked:
                continue
            
            desc = str(row['DESCRIPTION'])
            amount = float(row['DEBIT'])
            
            # Fuzzy match
            matches = process.extract(
                desc,
                df['DESCRIPTION'].unique(),
                scorer=fuzz.token_sort_ratio,
                limit=5
            )
            
            for matched_desc, score in matches:
                if score >= self.config['FUZZY_THRESHOLD']:
                    # Vérifier montants similaires
                    similar_rows = df[
                        (df['DESCRIPTION'] == matched_desc) &
                        (abs(df['DEBIT'] - amount) / (amount or 1) < 0.05)
                    ]
                    
                    if len(similar_rows) > 1:
                        for _, dup_row in similar_rows.iterrows():
                            if dup_row.name != idx and dup_row.name not in checked:
                                anomaly = Anomaly(
                                    anomaly_type=AnomalyType.DOUBLON,
                                    description=f"Doublon détecté: {desc}",
                                    vendor=desc,
                                    amount=amount,
                                    impact_estimation=amount * TVQ_RATE_QC,
                                    risk_level="MOYEN",
                                    recommendation="Vérifier si c'est un doublon ou deux transactions légitimes",
                                    confidence=float(score)
                                )
                                self.anomalies.append(anomaly)
                                checked.add(dup_row.name)
            
            checked.add(idx)
    
    def _detect_tax_anomalies(self, df: pd.DataFrame) -> None:
        """Détecter écarts TPS/TVQ"""
        for idx, row in df.iterrows():
            amount = float(row.get('DEBIT', 0))
            reported_tps = float(row.get('TPS', 0))
            reported_tvq = float(row.get('TVQ', 0))
            
            # Calculer taxes attendues
            expected_tps = amount * self.config['TPS_RATE']
            expected_tvq = amount * self.config['TVQ_RATE']
            
            # TPS écart
            if abs(reported_tps - expected_tps) > expected_tps * self.config['TOLERANCE_TAX']:
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.TPS_ECART,
                    description=f"TPS écart: ${reported_tps:.2f} vs ${expected_tps:.2f}",
                    vendor=str(row.get('DESCRIPTION', 'N/A')),
                    amount=amount,
                    impact_estimation=abs(reported_tps - expected_tps),
                    risk_level="MOYEN",
                    recommendation="Vérifier numéro TPS fournisseur ou exemption",
                    confidence=85.0
                )
                self.anomalies.append(anomaly)
            
            # TVQ écart
            if abs(reported_tvq - expected_tvq) > expected_tvq * self.config['TOLERANCE_TAX']:
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.TVQ_ECART,
                    description=f"TVQ écart: ${reported_tvq:.2f} vs ${expected_tvq:.2f}",
                    vendor=str(row.get('DESCRIPTION', 'N/A')),
                    amount=amount,
                    impact_estimation=abs(reported_tvq - expected_tvq),
                    risk_level="MOYEN",
                    recommendation="Vérifier numéro TVQ fournisseur ou exemption",
                    confidence=85.0
                )
                self.anomalies.append(anomaly)
    
    def _detect_high_amounts(self, df: pd.DataFrame) -> None:
        """Détecter montants élevés suspects"""
        if 'DEBIT' not in df.columns:
            return
        
        mean_amount = df['DEBIT'].mean()
        std_amount = df['DEBIT'].std()
        threshold = mean_amount + (3 * std_amount)
        
        for idx, row in df.iterrows():
            amount = float(row['DEBIT'])
            
            if amount > threshold:
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.MONTANT_ELEVE,
                    description=f"Montant élevé: ${amount:,.2f} (moyenne: ${mean_amount:,.2f})",
                    vendor=str(row.get('DESCRIPTION', 'N/A')),
                    amount=amount,
                    impact_estimation=amount * 0.1,  # 10% risque
                    risk_level="BAS",
                    recommendation="Vérifier si montant justifié ou erreur data",
                    confidence=70.0
                )
                self.anomalies.append(anomaly)
    
    def _detect_date_anomalies(self, df: pd.DataFrame) -> None:
        """Détecter incohérences dates"""
        if 'DATE' not in df.columns:
            return
        
        today = pd.Timestamp.now()
        
        for idx, row in df.iterrows():
            date = row['DATE']
            
            if pd.isna(date):
                continue
            
            # Date future
            if date > today:
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.DATE_INCOHERENT,
                    description=f"Date future détectée: {date.date()}",
                    vendor=str(row.get('DESCRIPTION', 'N/A')),
                    amount=float(row.get('DEBIT', 0)),
                    impact_estimation=0,
                    risk_level="BAS",
                    recommendation="Vérifier date transaction",
                    confidence=95.0
                )
                self.anomalies.append(anomaly)
            
            # Date très ancienne (>3 ans)
            elif (today - date).days > 1095:
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.DATE_INCOHERENT,
                    description=f"Date très ancienne: {date.date()}",
                    vendor=str(row.get('DESCRIPTION', 'N/A')),
                    amount=float(row.get('DEBIT', 0)),
                    impact_estimation=0,
                    risk_level="BAS",
                    recommendation="Vérifier si donnée erronée",
                    confidence=80.0
                )
                self.anomalies.append(anomaly)
    
    def _detect_fraud_patterns(self, df: pd.DataFrame) -> None:
        """Détecter patterns fraude (Local ML)"""
        
        # Pattern 1: Montants ronds (suspect d'estimation vs réels)
        df_with_round = df.copy()
        df_with_round['is_round'] = df_with_round['DEBIT'].apply(lambda x: x % 1000 == 0)
        
        round_pct = (df_with_round['is_round'].sum() / len(df_with_round)) * 100
        if round_pct > 30:  # >30% montants ronds = suspect
            anomaly = Anomaly(
                anomaly_type=AnomalyType.FRAUDE_PATTERN,
                description=f"{round_pct:.1f}% des montants sont ronds (1000$, 5000$, etc)",
                vendor="Multiple fournisseurs",
                amount=df['DEBIT'].sum(),
                impact_estimation=df['DEBIT'].sum() * 0.05,
                risk_level="MOYEN",
                recommendation="Montants ronds peuvent indiquer estimations vs factures réelles",
                confidence=75.0
            )
            self.anomalies.append(anomaly)
        
        # Pattern 2: Clustering près fin d'année (tax manipulation)
        if 'DATE' in df.columns:
            year_end = pd.Timestamp(datetime.now().year, 12, 31)
            window_start = year_end - timedelta(days=30)
            window_end = year_end + timedelta(days=30)
            
            around_year_end = df[
                (df['DATE'] >= window_start) &
                (df['DATE'] <= window_end)
            ]
            
            if len(around_year_end) > len(df) * 0.25:  # >25% près cutoff
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.FRAUDE_PATTERN,
                    description="Clustering anormal près fin d'année",
                    vendor="Multiple fournisseurs",
                    amount=around_year_end['DEBIT'].sum(),
                    impact_estimation=around_year_end['DEBIT'].sum() * 0.02,
                    risk_level="BAS",
                    recommendation="Vérifier si timing manipulé pour avantages fiscaux",
                    confidence=65.0
                )
                self.anomalies.append(anomaly)
        
        # Pattern 3: ML Anomaly detection
        try:
            ml_anomalies = self.ml_fraud_detector.detect(df)
            self.anomalies.extend(ml_anomalies)
        except Exception as e:
            logger.warning(f"ML fraud detection skipped: {e}")


class MLFraudDetector:
    """Détection fraude avec Machine Learning (Local)"""
    
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
    
    def detect(self, df: pd.DataFrame) -> List[Anomaly]:
        """Détecter anomalies avec ML"""
        anomalies = []
        
        if len(df) < 10:
            return anomalies
        
        try:
            # Feature engineering
            X = self._engineer_features(df)
            
            if X is None or X.empty:
                return anomalies
            
            # Fit + predict
            X_scaled = self.scaler.fit_transform(X)
            predictions = self.model.fit_predict(X_scaled)
            scores = self.model.score_samples(X_scaled)
            
            # Extract anomalies
            for idx, (pred, score) in enumerate(zip(predictions, scores)):
                if pred == -1:  # Anomaly
                    row = df.iloc[idx]
                    anomaly = Anomaly(
                        anomaly_type=AnomalyType.FRAUDE_PATTERN,
                        description=f"Anomalie ML détectée (score: {abs(score):.2f})",
                        vendor=str(row.get('DESCRIPTION', 'N/A')),
                        amount=float(row.get('DEBIT', 0)),
                        impact_estimation=float(row.get('DEBIT', 0)) * 0.05,
                        risk_level="BAS",
                        recommendation="Vérifier cette transaction",
                        confidence=abs(score) * 100 / 10  # Normalize to 0-100
                    )
                    anomalies.append(anomaly)
        
        except Exception as e:
            logger.warning(f"ML detection error: {e}")
        
        return anomalies
    
    def _engineer_features(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Créer features pour ML"""
        features = pd.DataFrame()
        
        try:
            if 'DEBIT' in df.columns:
                features['amount'] = df['DEBIT'].values
            
            if 'DESCRIPTION' in df.columns:
                # Frequency of vendor
                vendor_counts = df['DESCRIPTION'].value_counts()
                features['vendor_frequency'] = df['DESCRIPTION'].map(vendor_counts).values
            
            if 'DATE' in df.columns:
                features['day_of_week'] = df['DATE'].dt.dayofweek.values
                features['hour'] = df['DATE'].dt.hour.fillna(12).values
            
            # Add amount std dev by vendor
            if 'DESCRIPTION' in df.columns and 'DEBIT' in df.columns:
                vendor_std = df.groupby('DESCRIPTION')['DEBIT'].std()
                features['amount_std'] = df['DESCRIPTION'].map(vendor_std).fillna(0).values
            
            return features[features.columns[features.nunique() > 1]]  # Remove constant columns
        
        except Exception as e:
            logger.warning(f"Feature engineering error: {e}")
            return None


class LocalDatabase:
    """Base de données SQLite - Stockage LOCAL uniquement"""
    
    def __init__(self, db_path: str = "ai_auditor.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialiser database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY,
                    client_name TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    anomalies_count INTEGER,
                    total_impact REAL,
                    status TEXT DEFAULT 'completed'
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY,
                    audit_id INTEGER,
                    type TEXT,
                    description TEXT,
                    vendor TEXT,
                    amount REAL,
                    impact REAL,
                    risk_level TEXT,
                    recommendation TEXT,
                    confidence REAL,
                    FOREIGN KEY(audit_id) REFERENCES audits(id)
                )
            """)
            
            conn.commit()
    
    def save_audit(self, client_name: str, anomalies: List[Anomaly]) -> int:
        """Sauvegarder audit + anomalies"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            total_impact = sum(a.impact_estimation for a in anomalies)
            
            cursor.execute("""
                INSERT INTO audits (client_name, anomalies_count, total_impact)
                VALUES (?, ?, ?)
            """, (client_name, len(anomalies), total_impact))
            
            audit_id = cursor.lastrowid
            
            for anomaly in anomalies:
                cursor.execute("""
                    INSERT INTO anomalies 
                    (audit_id, type, description, vendor, amount, impact, risk_level, recommendation, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    audit_id,
                    anomaly.anomaly_type.value,
                    anomaly.description,
                    anomaly.vendor,
                    anomaly.amount,
                    anomaly.impact_estimation,
                    anomaly.risk_level,
                    anomaly.recommendation,
                    anomaly.confidence
                ))
            
            conn.commit()
            return audit_id
    
    def get_audit_history(self, client_name: str, limit: int = 50) -> List[Dict]:
        """Récupérer historique audits"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, client_name, timestamp, anomalies_count, total_impact
                FROM audits
                WHERE client_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (client_name, limit))
            
            columns = ['id', 'client_name', 'timestamp', 'anomalies_count', 'total_impact']
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_year_comparison(self, client_name: str) -> Dict:
        """Comparer anomalies year-to-year"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    strftime('%Y', timestamp) as year,
                    COUNT(*) as audit_count,
                    SUM(anomalies_count) as total_anomalies,
                    SUM(total_impact) as total_impact
                FROM audits
                WHERE client_name = ?
                GROUP BY year
                ORDER BY year DESC
                LIMIT 2
            """, (client_name,))
            
            rows = cursor.fetchall()
            if len(rows) >= 2:
                return {
                    'current_year': dict(zip(['year', 'audits', 'anomalies', 'impact'], rows[0])),
                    'previous_year': dict(zip(['year', 'audits', 'anomalies', 'impact'], rows[1]))
                }
            
            return {}


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Exemple d'utilisation
    engine = AuditEngineAI(use_ai=True)
    
    # Créer données test
    test_data = {
        'DATE': ['2024-01-15', '2024-01-15', '2024-02-01'],
        'DESCRIPTION': ['Amazon AWS', 'Amazon AWS', 'Bell Canada'],
        'DEBIT': [500, 500, 150],
        'TPS': [20, 20, 7.5],
        'TVQ': [45, 45, 15]
    }
    
    df = pd.DataFrame(test_data)
    df['DATE'] = pd.to_datetime(df['DATE'])
    
    anomalies, error = engine.process_dataframe(df, "Test Client")
    
    if error:
        print(f"❌ Erreur: {error}")
    else:
        print(f"✅ {len(anomalies)} anomalies trouvées:")
        for anom in anomalies:
            print(f"  - {anom['Type']}: {anom['Description']}")
