import streamlit as st
import pandas as pd
from PIL import Image
import google.generativeai as genai
import json
import datetime

st.set_page_config(page_title="CookSnap AI", page_icon="🍳", layout="centered")

# --- CONNEXION API ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # LA CORRECTION EST ICI : On utilise ton nouveau modèle ultra-rapide
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("⚠️ Clé API introuvable ! Pense à l'ajouter dans Settings > Secrets sur Streamlit.")
    st.stop()

# --- BASE DE DONNÉES ---
def load_data():
    try:
        return pd.read_csv("my_recipes.csv")
    except:
        return pd.DataFrame(columns=["date", "nom", "catégorie", "ingrédients", "instructions"])

df = load_data()

# --- INTERFACE ---
st.title("🍳 CookSnap Intelligent")
tabs = st.tabs(["📸 Scanner", "📖 Ma Collection"])

with tabs[0]:
    uploaded_file = st.file_uploader("Prends une photo de la recette", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, use_container_width=True)
        
        if st.button("✨ Analyser la recette"):
            with st.spinner("Lecture par l'IA en cours..."):
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
                    
                    # Nettoyage pour récupérer le JSON
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    data = json.loads(clean_json)
                    
                    # Sauvegarde
                    new_row = {
                        "date": datetime.date.today(),
                        "nom": data['nom'],
                        "catégorie": data['categorie'],
                        "ingrédients": data['ingredients'],
                        "instructions": data['instructions']
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv("my_recipes.csv", index=False)
                    st.success(f"Recette '{data['nom']}' ajoutée !")
                    
                except Exception as e:
                    st.error(f"Erreur d'analyse : {e}")

with tabs[1]:
    search = st.text_input("🔍 Rechercher...")
    if not df.empty:
        mask = df['nom'].str.contains(search, case=False) | df['ingrédients'].str.contains(search, case=False)
        for i, row in df[mask].iloc[::-1].iterrows():
            with st.expander(f"{row['catégorie']} | {row['nom']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Ingrédients :**")
                    st.write(row['ingrédients'])
                with col2:
                    st.markdown("**Instructions :**")
                    st.write(row['instructions'])
                if st.button("Supprimer", key=f"del_{i}"):
                    df.drop(i).to_csv("my_recipes.csv", index=False)
                    st.rerun()
    else:
        st.info("Aucune recette pour le moment.")
