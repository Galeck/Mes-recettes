import streamlit as st
import pandas as pd
from PIL import Image
import google.generativeai as genai
import json
import datetime

# --- CONFIGURATION API ---
# Sur Streamlit Cloud, on utilise les "Secrets" pour cacher la clé
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("Clé API manquante ! Ajoute-la dans les Secrets de Streamlit.")

model = genai.GenerativeModel('gemini-1.5-flash')

# --- FONCTION MAGIQUE ---
def analyser_recette(image_pil):
    prompt = """
    Analyse cette image de recette. 
    Retourne uniquement un objet JSON avec exactement ces clés :
    {
      "nom": "Le titre de la recette",
      "categorie": "Plat, Dessert, Entrée ou Boisson",
      "ingredients": "liste des ingrédients",
      "instructions": "étapes de préparation"
    }
    Si tu ne trouves pas de recette, réponds avec une erreur.
    """
    response = model.generate_content([prompt, image_pil])
    # Nettoyage de la réponse pour extraire le JSON
    text = response.text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

# --- INTERFACE ---
st.set_page_config(page_title="CookSnap AI", page_icon="🧠")
st.title("🧠 CookSnap Intelligent")

if "df" not in st.session_state:
    try:
        st.session_state.df = pd.read_csv("my_recipes.csv")
    except:
        st.session_state.df = pd.DataFrame(columns=["date", "nom", "catégorie", "ingrédients", "instructions"])

tabs = st.tabs(["📸 Scanner", "📖 Ma Collection"])

with tabs[0]:
    file = st.file_uploader("Prends ta recette en photo", type=["jpg", "jpeg", "png"])
    if file:
        img = Image.open(file)
        st.image(img, width=300)
        
        if st.button("🚀 Analyser avec l'IA"):
            with st.spinner("L'IA lit et organise ta recette..."):
                try:
                    data = analyser_recette(img)
                    
                    # Enregistrement
                    new_recette = {
                        "date": datetime.date.today(),
                        "nom": data['nom'],
                        "catégorie": data['categorie'],
                        "ingrédients": data['ingredients'],
                        "instructions": data['instructions']
                    }
                    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_recette])], ignore_index=True)
                    st.session_state.df.to_csv("my_recipes.csv", index=False)
                    st.success(f"Enregistré : {data['nom']} !")
                except Exception as e:
                    st.error(f"Erreur d'analyse : {e}")

with tabs[1]:
    search = st.text_input("🔍 Rechercher...")
    # Affichage propre avec colonnes
    for i, row in st.session_state.df.iloc[::-1].iterrows():
        if search.lower() in row['nom'].lower() or search.lower() in str(row['ingrédients']).lower():
            with st.expander(f"{row['nom']} ({row['catégorie']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🛒 Ingrédients")
                    st.write(row['ingrédients'])
                with col2:
                    st.subheader("👨‍🍳 Préparation")
                    st.write(row['instructions'])
