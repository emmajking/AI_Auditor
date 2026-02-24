"""
AI_AUDITOR - Interface Streamlit complète (FIXED VERSION)
Plateforme audit fiscal avec IA locale (Edge-first)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys
import io
from pathlib import Path



# Ajouter path pour imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports modules
from audit_engine import AuditEngineAI, AnomalyType
from report_generator import ProfessionalAuditReport




# ═══════════════════════════════════════════════════════════════
#                        CONFIGURATION
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="AI_Auditor Québec",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════
#                        CSS CUSTOM
# ═══════════════════════════════════════════════════════════════

st.markdown("""
<style>
    .success-box {
        padding: 15px;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 10px 0;
        color: #155724;
    }
    
    .warning-box {
        padding: 15px;
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        border-radius: 5px;
        margin: 10px 0;
        color: #856404;
    }
    
    .danger-box {
        padding: 15px;
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        border-radius: 5px;
        margin: 10px 0;
        color: #721c24;
    }
    
    .info-box {
        padding: 15px;
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        border-radius: 5px;
        margin: 10px 0;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#                    FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def display_box(message: str, box_type: str = "info") -> None:
    """Affiche une box stylée selon le type"""
    box_class = f"{box_type}-box"
    st.markdown(f'<div class="{box_class}">{message}</div>', unsafe_allow_html=True)


@st.cache_resource
def get_audit_engine() -> AuditEngineAI:
    """Cache le moteur audit"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    return AuditEngineAI(config_path=config_path, use_ai=True)


@st.cache_resource
def get_report_generator() -> ProfessionalAuditReport:
    """Cache le générateur rapports"""
    return ProfessionalAuditReport(
        company_name="AI_Auditor Québec"
    )


# ═══════════════════════════════════════════════════════════════
#                    SIMPLE LOGIN (SANS STREAMLIT AUTH)
# ═══════════════════════════════════════════════════════════════




def check_login() -> bool:
    """Simple login check"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_name = None
    
    return st.session_state.logged_in


def login_page():
    """Page de login simple"""
    st.markdown("# 🔐 AI_Auditor Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.markdown("## Connexion")
        
        # Credentials de démo
        DEMO_CREDS = {
            'demo': {
                'password': 'demo123',
                'name': 'Marie Tremblay',
                'email': 'joseskuate@ai-auditor.ca',
                'cabinet': 'Comptabilité ABC'
            }
        }
        
        username = st.text_input("👤 Username", placeholder="demo")
        password = st.text_input("🔑 Password", type="password", placeholder="demo123")
        
        if st.button("Connexion", use_container_width=True, type="primary"):
            if username in DEMO_CREDS:
                if password == DEMO_CREDS[username]['password']:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_name = DEMO_CREDS[username]['name']
                    st.session_state.user_email = DEMO_CREDS[username]['email']
                    st.session_state.user_cabinet = DEMO_CREDS[username]['cabinet']
                    st.success("✅ Connexion réussie!")
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect")
            else:
                st.error("❌ Utilisateur non trouvé")
        
        st.markdown("---")
        st.markdown("### 📝 Compte démo")
        st.info("""
        **Username:** demo  
        **Password:** demo123
        """)


# ═══════════════════════════════════════════════════════════════
#                          MAIN APP
# ═══════════════════════════════════════════════════════════════

if not check_login():
    login_page()
else:
    # --- USER LOGGED IN ---
    
    # Load resources
    engine = get_audit_engine()
    report_gen = get_report_generator()
    
    # Initialize session state for user
    username = st.session_state.username
    user_name = st.session_state.user_name
    
    if 'stats' not in st.session_state:
        st.session_state.stats = {}
    
    if username not in st.session_state.stats:
        st.session_state.stats[username] = {
            'audits_mois': 0,
            'total_transactions': 0,
            'total_anomalies': 0,
            'impact_total': 0.0,
            'last_audit': None
        }
    
    user_stats = st.session_state.stats[username]
    
    # ═══════════════════════════════════════════════════════════════
    #                          SIDEBAR
    # ═══════════════════════════════════════════════════════════════
    
    with st.sidebar:
        st.title(f"👋 {user_name}")
        
        st.markdown("---")
        st.write(f"**Cabinet:** {st.session_state.user_cabinet}")
        st.write(f"**Email:** {st.session_state.user_email}")
        
        st.markdown("---")
        st.markdown("### 📊 Statistiques")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Audits", user_stats['audits_mois'])
            st.metric("Anomalies", user_stats['total_anomalies'])
        with col2:
            st.metric("Transactions", user_stats['total_transactions'])
            st.metric("Impact", f"${user_stats['impact_total']:,.0f}")
        
        st.markdown("---")
        
        if st.button("Déconnexion", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        
        st.markdown("---")
        st.markdown("### ℹ️ À propos")
        st.write("""
        **AI_Auditor v2.0**
        
        Plateforme d'audit fiscal automatisé, propulsé par Jek_ai
                 neural engine.
        
        📧 [Support](mailto:support@ai-auditor.ca)
        """)
    
    # ═══════════════════════════════════════════════════════════════
    #                    CONTENU PRINCIPAL
    # ═══════════════════════════════════════════════════════════════
    
    st.markdown("# 🚀 AI_Auditor - Audit Fiscal Automatisé")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "🔍 Audit Automatisé",
        "💬 Chat IA",
        "⚙️ Paramètres"
    ])
    
    # ═══════════════════════════════════════════════════════════════
    #              TAB 1: AUDIT AUTOMATISÉ
    # ═══════════════════════════════════════════════════════════════
    
    with tab1:
        st.markdown("## 🔍 Audit Fiscal Automatisé")
        
        display_box("""
        <strong>Détection automatique d'anomalies TPS/TVQ</strong><br>
        Upload votre fichier Excel et laissez l'IA analyser en quelques secondes.
        """, "info")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📤 Charger fichier")
            uploaded_file = st.file_uploader(
                "Sélectionnez un fichier Excel",
                type=['xlsx', 'xls', 'csv']
            )
        
        with col2:
            st.markdown("### 📋 Client")
            client_name = st.text_input(
                "Nom du client",
                value="",
                placeholder="ABC Inc"
            )
        
        if uploaded_file is not None and client_name:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ Fichier chargé: {len(df)} lignes")
                
                with st.expander("👀 Aperçu données"):
                    st.dataframe(df.head(10))
                
                if st.button("🚀 Lancer audit", use_container_width=True):
                    with st.spinner("⏳ Analyse en cours..."):
                        anomalies, error = engine.process_dataframe(df, client_name)
                        
                        if error:
                            st.error(f"❌ Erreur: {error}")
                        else:
                            # Update stats
                            user_stats['audits_mois'] += 1
                            user_stats['total_transactions'] += len(df)
                            user_stats['total_anomalies'] += len(anomalies)
                            user_stats['impact_total'] += sum(a['Impact_Estimation'] for a in anomalies)
                            user_stats['last_audit'] = datetime.now()
                            
                            st.session_state.stats[username] = user_stats
                            
                            st.markdown("---")
                            st.markdown("## 📊 Résultats Audit")
                            
                            # Métriques
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Anomalies", len(anomalies))
                            with col2:
                                st.metric("Impact", f"${sum(a['Impact_Estimation'] for a in anomalies):,.0f}")
                            with col3:
                                avg_conf = np.mean([a['Confiance'] for a in anomalies]) if anomalies else 0
                                st.metric("Confiance", f"{avg_conf:.1f}%")
                            with col4:
                                high_risk = sum(1 for a in anomalies if a['Risque'] == 'CRITIQUE')
                                st.metric("Critiques", high_risk)
                            
                            if anomalies:
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    type_counts = pd.Series([a['Type'] for a in anomalies]).value_counts()
                                    fig = px.pie(
                                        values=type_counts.values,
                                        names=type_counts.index,
                                        title="Anomalies par type"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                with col2:
                                    vendor_impact = {}
                                    for a in anomalies:
                                        vendor = a['Fournisseur']
                                        vendor_impact[vendor] = vendor_impact.get(vendor, 0) + a['Impact_Estimation']
                                    
                                    top_vendors = sorted(vendor_impact.items(), key=lambda x: x[1], reverse=True)[:10]
                                    
                                    fig = px.bar(
                                        x=[v[0] for v in top_vendors],
                                        y=[v[1] for v in top_vendors],
                                        title="Top 10 fournisseurs (impact)"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                st.markdown("### 📋 Détail anomalies")
                                df_results = pd.DataFrame(anomalies)
                                st.dataframe(
                                    df_results.sort_values('Impact_Estimation', ascending=False),
                                    use_container_width=True
                                )
                                
                                st.markdown("---")
                                st.markdown("### 📄 Rapport")
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    fmt = st.selectbox("Format", ["PDF", "Word", "Excel"])
                                
                                with col2:
                                    if st.button("📥 Générer", use_container_width=True):
                                        try:
                                            rapport = report_gen.generate_from_anomalies(
                                                client_name=client_name,
                                                anomalies=anomalies,
                                                format=fmt
                                            )
                                            
                                            ext_map = {"PDF": "pdf", "Word": "docx", "Excel": "xlsx"}
                                            ext = ext_map[fmt]
                                            
                                            st.download_button(
                                                f"⬇️ Télécharger {fmt}",
                                                data=rapport,
                                                file_name=f"Rapport_{client_name}_{datetime.now().strftime('%Y%m%d')}.{ext}",
                                                use_container_width=True
                                            )
                                        except Exception as e:
                                            st.error(f"Erreur: {e}")
                            else:
                                st.success("✅ Aucune anomalie détectée!")
            
            except Exception as e:
                st.error(f"❌ Erreur: {e}")
        
        elif uploaded_file is not None and not client_name:
            st.warning("⚠️ Entrez le nom du client")
    
    # ═══════════════════════════════════════════════════════════════
    #              TAB 2: CHAT IA
    # ═══════════════════════════════════════════════════════════════
    
    with tab2:
        st.markdown("## 💬 Chat IA Assistant")
        
        if not engine.ollama or not engine.ollama.available:
            display_box("""
            <strong>⚠️ IA non disponible</strong><br>
            Ollama n'est pas connecté. Pour activer:<br>
            1. Installer <a href="https://ollama.ai" target="_blank">Ollama</a><br>
            2. Lancer: ollama serve<br>
            3. Télécharger: ollama pull llama3.2
            """, "warning")
        else:
            if f"chat_{username}" not in st.session_state:
                st.session_state[f"chat_{username}"] = []
            
            messages = st.session_state[f"chat_{username}"]
            
            for msg in messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            if prompt := st.chat_input("Posez une question..."):
                messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("🤖 Réflexion..."):
                        response = engine.ollama.query(prompt, use_cache=False)
                        
                        if response:
                            st.markdown(response)
                            messages.append({"role": "assistant", "content": response})
                        else:
                            st.error("Erreur connexion Ollama")
    
    # ═══════════════════════════════════════════════════════════════
    #              TAB 3: PARAMÈTRES
    # ═══════════════════════════════════════════════════════════════
    
    with tab3:
        st.markdown("## ⚙️ Paramètres")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Audits ce mois", user_stats['audits_mois'])
            st.metric("Anomalies trouvées", user_stats['total_anomalies'])
        with col2:
            st.metric("Transactions", user_stats['total_transactions'])
            avg = user_stats['total_anomalies'] / max(user_stats['audits_mois'], 1)
            st.metric("Anom/audit", f"{avg:.1f}")
        with col3:
            st.metric("Impact total", f"${user_stats['impact_total']:,.0f}")
            if user_stats['last_audit']:
                st.metric("Dernier audit", user_stats['last_audit'].strftime('%d-%m-%Y'))
        
        st.markdown("---")
        st.markdown("### ℹ️ À propos")
        st.write("""
        AI_Auditor 2.0, propulsé par Jek_ai neural engine.
        
        Edge-first, LPRPDE compliant, données 100% locales.
        """)

# ═══════════════════════════════════════════════════════════════
#                          FOOTER
# ═══════════════════════════════════════════════════════════════

if check_login():
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
        🚀 AI_Auditor v2.0 | Edge-first, LPRPDE compliant<br>
        ✅ Données 100% locales | 📧 support@ai-auditor.ca
    </div>
    """, unsafe_allow_html=True)
