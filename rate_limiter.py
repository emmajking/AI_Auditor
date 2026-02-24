"""
RATE LIMITER - 3 tests gratuits par IP
Empêche l'abuse de la version démo gratuite
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Tuple
import streamlit as st


logger = logging.getLogger(__name__)


class FreeTrialLimiter:
    """
    Gère les limites de tests gratuits par IP
    
    Rules:
    - 3 audits gratuits par adresse IP
    - Reset après 24 heures (optionnel)
    - Email pour débloquer plus
    """
    
    def __init__(self, db_path: str = "free_trial.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Créer database si n'existe pas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS free_trials (
                    id INTEGER PRIMARY KEY,
                    ip_address TEXT UNIQUE,
                    audit_count INTEGER DEFAULT 0,
                    last_audit DATETIME,
                    first_audit DATETIME,
                    email TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            conn.commit()
    
    def get_client_ip(self) -> str:
        """Récupérer l'adresse IP du client"""
        # Pour Streamlit Cloud
        if hasattr(st, 'session_state') and 'client_ip' in st.session_state:
            return st.session_state.client_ip
        
        # Fallback: utiliser header X-Forwarded-For
        try:
            from streamlit.server.server import Server
            session = Server.get_current_session()
            if session:
                return str(session.client_state.ip_address or "0.0.0.0")
        except:
            pass
        
        return "0.0.0.0"  # Fallback
    
    def check_limit(self, ip_address: str) -> Tuple[bool, int, str]:
        """
        Vérifier si l'IP peut faire un test
        
        Returns:
            (can_audit: bool, tests_remaining: int, message: str)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Chercher l'IP
            cursor.execute(
                "SELECT audit_count, last_audit, email FROM free_trials WHERE ip_address = ?",
                (ip_address,)
            )
            
            result = cursor.fetchone()
            
            if result is None:
                # Première visite
                cursor.execute(
                    """INSERT INTO free_trials (ip_address, audit_count, first_audit, last_audit)
                       VALUES (?, ?, ?, ?)""",
                    (ip_address, 0, datetime.now(), datetime.now())
                )
                conn.commit()
                
                return True, 3, "✅ Bienvenue! Vous avez 3 tests gratuits"
            
            audit_count, last_audit, email = result
            tests_remaining = 3 - audit_count
            
            if audit_count >= 3:
                return False, 0, """
❌ LIMITE ATTEINTE
Vous avez déjà utilisé 3 tests gratuits.

Options:
1. Installer la version on-premise ($999/mois)
2. Attendre 24h pour reset (email: support@ai-auditor.ca)
3. Contacter: sales@ai-auditor.ca pour accès VIP
                """
            
            return True, tests_remaining, f"✅ Vous avez {tests_remaining} test(s) restant(s)"
    
    def increment_usage(self, ip_address: str, email: str = None) -> bool:
        """Incrémenter l'usage après un audit"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """UPDATE free_trials 
                   SET audit_count = audit_count + 1, 
                       last_audit = ?,
                       email = COALESCE(?, email)
                   WHERE ip_address = ?""",
                (datetime.now(), email, ip_address)
            )
            
            conn.commit()
            return cursor.rowcount > 0
    
    def reset_after_24h(self, ip_address: str) -> bool:
        """Reset après 24h (si utilisateur demande)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT last_audit FROM free_trials WHERE ip_address = ?",
                (ip_address,)
            )
            
            result = cursor.fetchone()
            if result is None:
                return False
            
            last_audit = datetime.fromisoformat(result[0])
            hours_passed = (datetime.now() - last_audit).total_seconds() / 3600
            
            if hours_passed >= 24:
                cursor.execute(
                    """UPDATE free_trials 
                       SET audit_count = 0, last_audit = ?
                       WHERE ip_address = ?""",
                    (datetime.now(), ip_address)
                )
                conn.commit()
                return True
            
            return False
    
    def get_stats(self) -> dict:
        """Statistiques globales des tests gratuits"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_ips,
                    SUM(audit_count) as total_audits,
                    COUNT(CASE WHEN audit_count >= 3 THEN 1 END) as exhausted_ips,
                    COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as with_emails
                FROM free_trials
            """)
            
            result = cursor.fetchone()
            
            return {
                'total_ips': result[0] or 0,
                'total_audits': result[1] or 0,
                'exhausted_ips': result[2] or 0,
                'with_emails': result[3] or 0,
                'conversion_rate': (result[3] or 0) / max((result[0] or 1), 1) * 100
            }


# ═══════════════════════════════════════════════════════════════
#           INTÉGRATION DANS app_ultimate.py
# ═══════════════════════════════════════════════════════════════

"""
À AJOUTER DANS app_ultimate.py EN HAUT:

from rate_limiter import FreeTrialLimiter

# Initialize limiter
trial_limiter = FreeTrialLimiter()
"""

# Dans la section audit (Tab 1):

def show_audit_tab_with_limit():
    """Audit tab avec vérification de limite"""
    
    st.markdown("## 🔍 Audit Fiscal Automatisé")
    
    # VÉRIFIER LIMITE
    ip_address = get_client_ip()  # À implémenter
    can_audit, tests_remaining, message = trial_limiter.check_limit(ip_address)
    
    # Afficher statut
    if can_audit:
        st.success(f"✅ {tests_remaining} test(s) gratuit(s) restant(s)")
    else:
        st.error(message)
        st.stop()  # Stop exécution
    
    # ... Rest of audit code ...
    
    # Après audit réussi:
    if st.button("🚀 Lancer audit", use_container_width=True):
        with st.spinner("⏳ Analyse en cours..."):
            anomalies, error = engine.process_dataframe(df, client_name)
            
            if not error:
                # ✅ Audit réussi - incrémenter usage
                user_email = st.session_state.get('user_email', None)
                trial_limiter.increment_usage(ip_address, user_email)
                
                st.success("✅ Audit complet!")
                
                # Afficher tests restants
                _, remaining, _ = trial_limiter.check_limit(ip_address)
                st.info(f"📊 {remaining} test(s) restant(s) aujourd'hui")


def get_client_ip():
    """Récupérer IP du client"""
    try:
        # Pour Streamlit Cloud/deployed
        headers = st.context.headers
        if "X-Forwarded-For" in headers:
            return headers["X-Forwarded-For"].split(",")[0].strip()
        
        if "Host" in headers:
            return headers["Host"]
        
    except Exception:
        pass
        return '0.0.0.0'


# Admin dashboard pour voir stats (optionnel):

def show_admin_stats():
    """Afficher stats des tests gratuits (admin seulement)"""
    
    if st.session_state.get('is_admin'):
        st.markdown("### 📊 Free Trial Stats")
        
        stats = trial_limiter.get_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total IPs", stats['total_ips'])
        with col2:
            st.metric("Total Audits", stats['total_audits'])
        with col3:
            st.metric("Limite Atteinte", stats['exhausted_ips'])
        with col4:
            st.metric("Conversion %", f"{stats['conversion_rate']:.1f}%")
        
        st.markdown("---")
        
        # Option: Reset manually
        if st.button("🔄 Reset all (admin)"):
            # Implémenter reset all
            pass


# ═══════════════════════════════════════════════════════════════
#       VARIANTES / OPTIONS AVANCÉES
# ═══════════════════════════════════════════════════════════════

"""
OPTION 1: Reset après 24h (Actuel)
- Users get 3 tests
- After 24h, reset to 3
- Encourage daily usage

OPTION 2: Rolling window (14 jours)
- 5 tests per 14-day period
- More generous
- Better for UX

OPTION 3: Email-based limit
- 3 tests per email
- But: users create fake emails
- Need verification

OPTION 4: Tiered limit
- 3 free tests
- After, pay $1 per test (paywall)
- Or pay $999/mois for unlimited
- Better revenue model

RECOMMANDATION: Option 1 (simple) + track emails for sales
"""


# ═══════════════════════════════════════════════════════════════
#       CONVERSION MESSAGING
# ═══════════════════════════════════════════════════════════════

"""
Quand utilisateur atteint 3 tests gratuits:

MESSAGE #1 (After test 2):
"Vous aimez AI_Auditor? 
 1 test gratuit restant. 
 Prêt à passer au complet? $999/mois ou installez on-premise"

MESSAGE #2 (After test 3):
"Bravo! Vous avez testé 3 audits.
 
 Options:
 1. Install on-premise ($999/mois) ← RECOMMANDÉ
 2. Cloud subscription ($499/mois)
 3. Attendre 24h pour reset
 
 Sales: sales@ai-auditor.ca"

CALL-TO-ACTION:
- Email: sales@ai-auditor.ca
- Chat: Contact us button
- Phone: Numéro sales
- Calendly: Book demo
"""


# ═══════════════════════════════════════════════════════════════
#       ALTERNATIVE: CLOUD DB (pour scalabilité)
# ═══════════════════════════════════════════════════════════════

"""
Si tu déploies sur Heroku/Streamlit Cloud et tu veux persister data:

Option A: SQLite local (current) - Good for <1000 IPs
Option B: PostgreSQL - Good for >1000 IPs

Code avec PostgreSQL:
"""

"""import os
import psycopg2"""

"""class FreeTrialLimiterPostgres:"""
    #"""Même interface, mais avec PostgreSQL"""
    
    #def __init__(self):
  #      self.conn_string = os.getenv("DATABASE_URL")
    
   # def check_limit(self, ip_address: str) -> Tuple[bool, int, str]:
    #    with psycopg2.connect(self.conn_string) as conn:
     #       cursor = conn.cursor()
            # Same SQL, different backend
      #      pass


# ═══════════════════════════════════════════════════════════════
#       DASHBOARD POUR VOIR LES CONVERSIONS
# ═══════════════════════════════════════════════════════════════

"""
Table pour tracker conversions:

CREATE TABLE conversions (
    id INTEGER PRIMARY KEY,
    ip_address TEXT,
    email TEXT,
    converted_at DATETIME,
    plan TEXT,  -- 'free', 'startup', 'growth', 'enterprise'
    value DECIMAL
);

Puis dashboard pour voir:
- Total demos: 247
- Converted: 12 (5%)
- Revenue from demo: $5,988 (12 × $499)
"""
