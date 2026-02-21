import streamlit as st
import pandas as pd
from PIL import Image
import google.generativeai as genai
import json
import datetime
import gspread

st.set_page_config(page_title="CookSnap Cloud", page_icon="🍳", layout="centered")

# --- CONNEXIONS SÉCURISÉES ---
if "GOOGLE_API_KEY" not in st.secrets or "GOOGLE_CREDENTIALS" not in st.secrets:
    st.error("⚠️ Clés manquantes ! Vérifie tes Secrets sur Streamlit.")
    st.stop()

# 1. On réveille l'IA
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. On connecte ton Google Sheets
try:
    # On lit ta clé secrète
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    gc = gspread.service_account_from_dict(creds_dict)
    
    # On ouvre TON fichier (le nom doit être exact)
    sh = gc.open("Mes Recettes CookSnap")
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"Erreur de connexion à Google Sheets : {e}")
    st.stop()

# --- CHARGEMENT DES DONNÉES DEPUIS LE DRIVE ---
def load_data():
    data = worksheet.get_all_values()
    if not data:
        # Si le fichier est vide, le robot crée les en-têtes
        en_tetes = ["date", "nom", "catégorie", "ingrédients", "instructions"]
        worksheet.append_row(en_tetes)
        return pd.DataFrame(columns=en_tetes)
    elif len(data) == 1:
        return pd.DataFrame(columns=data[0])
    else:
        return pd.DataFrame(data[1:], columns=data[0])

df = load_data()

# --- INTERFACE ---
st.title("🍳 CookSnap Cloud")
st.caption("Tes recettes sont synchronisées et sauvées à vie sur Google Drive ☁️")

tabs = st.tabs(["📸 Scanner", "📖 Ma Collection"])

with tabs[0]:
    uploaded_file = st.file_uploader("Prends une photo de la recette", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, use_container_width=True)
        
        if st.button("✨ Analyser et Sauvegarder"):
            with st.spinner("L'IA lit et envoie au Google Sheets..."):
                try:
                    prompt = """Analyse cette image de recette. 
                    Retourne UNIQUEMENT un objet JSON valide avec ces clés exactes :
                    {
                      "nom": "Titre",
                      "categorie": "Plat, Dessert, Entrée ou Boisson",
                      "ingredients": "liste des ingrédients",
                      "instructions": "étapes de préparation"
                    }"""
                    response = model.generate_content([prompt, img])
                    
                    # Nettoyage
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    data = json.loads(clean_json)
                    
                    # 🚀 L'ACTION MAGIQUE : Écriture directe dans Google Sheets
                    aujourdhui = str(datetime.date.today())
                    nouvelle_ligne = [aujourdhui, data['nom'], data['categorie'], data['ingredients'], data['instructions']]
                    worksheet.append_row(nouvelle_ligne)
                    
                    st.success(f"Magique ! '{data['nom']}' a été ajoutée à ton tableur.")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Erreur lors de l'analyse : {e}")

with tabs[1]:
    search = st.text_input("🔍 Rechercher...")
    if not df.empty:
        # Recherche
        mask = df['nom'].str.contains(search, case=False, na=False) | df['ingrédients'].str.contains(search, case=False, na=False)
        df_affiche = df[mask]
        
        # Affichage (de la plus récente à la plus ancienne)
        for i, row in df_affiche.iloc[::-1].iterrows():
            with st.expander(f"{row.get('catégorie', '')} | {row.get('nom', '')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🛒 Ingrédients :**")
                    st.write(row.get('ingrédients', ''))
                with col2:
                    st.markdown("**👨‍🍳 Instructions :**")
                    st.write(row.get('instructions', ''))
                
                # Le bouton de suppression a été remplacé par un conseil pratique
                st.info("💡 Pour modifier un mot ou supprimer cette recette, ouvre simplement ton fichier 'Mes Recettes CookSnap' sur Google Drive !")
    else:
        st.info("Ton grimoire est vide. Va vite scanner une recette !")
