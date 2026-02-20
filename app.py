import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="CookSnap",
    page_icon="🍳",
    initial_sidebar_state="collapsed"
)

# Style CSS personnalisé pour faire "App Mobile"
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #FF4B4B; color: white; }
    .recipe-card { 
        background-color: white; 
        padding: 15px; 
        border-radius: 15px; 
        border-left: 5px solid #FF4B4B;
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE DE DONNÉES ---
def load_data():
    try:
        return pd.read_csv("my_recipes.csv")
    except:
        return pd.DataFrame(columns=["date", "nom", "catégorie", "contenu"])

df = load_data()

# --- INTERFACE ---
st.title("🍳 CookSnap")
st.caption("Capturez vos recettes en un clin d'œil.")

tabs = st.tabs(["➕ Ajouter", "📚 Ma Bibliothèque"])

# --- ONGLET 1 : AJOUT ---
with tabs[0]:
    col1, col2 = st.columns(2)
    nom = col1.text_input("Nom du plat", placeholder="Ex: Lasagnes")
    cat = col2.selectbox("Type", ["🍽 Plat", "🍰 Dessert", "🥗 Entrée", "🍹 Boisson"])
    
    uploaded_file = st.file_uploader("Prendre une photo ou choisir un screen", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, use_container_width=True)
        
        if st.button("✨ Scanner & Enregistrer"):
            with st.spinner("Lecture magique en cours..."):
                # OCR
                raw_text = pytesseract.image_to_string(img, lang='fra')
                
                # Sauvegarde
                new_row = {
                    "date": datetime.date.today(),
                    "nom": nom if nom else "Recette sans nom",
                    "catégorie": cat,
                    "contenu": raw_text
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv("my_recipes.csv", index=False)
                st.success("Enregistré dans ton grimoire !")

# --- ONGLET 2 : BIBLIOTHÈQUE ---
with tabs[1]:
    search = st.text_input("🔍 Rechercher une recette ou un ingrédient...")
    
    if not df.empty:
        # Filtre de recherche
        mask = df['nom'].str.contains(search, case=False) | df['contenu'].str.contains(search, case=False)
        display_df = df[mask].sort_index(ascending=False)

        for i, row in display_df.iterrows():
            with st.expander(f"{row['catégorie']} | {row['nom']}"):
                st.markdown(f"**Ajouté le :** {row['date']}")
                st.markdown("---")
                # On affiche le texte proprement
                st.write(row['contenu'])
                if st.button("🗑 Supprimer", key=f"del_{i}"):
                    df = df.drop(i)
                    df.to_csv("my_recipes.csv", index=False)
                    st.rerun()
    else:
        st.info("Ta bibliothèque est vide. Commence par scanner une recette !")