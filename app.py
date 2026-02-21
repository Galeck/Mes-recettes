import streamlit as st
import pandas as pd
from PIL import Image
import google.generativeai as genai
import json
import datetime
import gspread
import os # Pour vérifier si la bannière existe

st.set_page_config(page_title="CookSnap Cloud", page_icon="🍳", layout="centered")

# --- 1. BANNIÈRE DÉCORATIVE ---
# On vérifie si le fichier existe pour éviter une erreur si tu oublies de le mettre
if os.path.exists("banner.jpg"):
    st.image("banner.jpg", use_container_width=True)
elif os.path.exists("banner.png"):
    st.image("banner.png", use_container_width=True)
else:
    # Un petit message discret si pas de bannière
    st.caption("💡 Ajoute une image 'banner.jpg' sur GitHub pour décorer ici !")

st.title("🍳 CookSnap Cloud")
st.caption("Ton assistant culinaire personnel, propulsé par l'IA.")

# --- CONNEXIONS SÉCURISÉES ---
if "GOOGLE_API_KEY" not in st.secrets or "GOOGLE_CREDENTIALS" not in st.secrets:
    st.error("⚠️ Clés manquantes ! Vérifie tes Secrets sur Streamlit.")
    st.stop()

# Connexion IA et GSheets
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

try:
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open("Mes Recettes CookSnap")
    worksheet = sh.sheet1
except Exception as e:
    st.error(f"Erreur de connexion à Google Sheets : {e}")
    st.stop()

# --- CHARGEMENT DES DONNÉES ---
def load_data():
    data = worksheet.get_all_values()
    if not data:
        en_tetes = ["date", "nom", "catégorie", "ingrédients", "instructions"]
        worksheet.append_row(en_tetes)
        return pd.DataFrame(columns=en_tetes)
    elif len(data) == 1:
        return pd.DataFrame(columns=data[0])
    else:
        # On s'assure que les noms de colonnes sont bien en minuscules pour le code
        df = pd.DataFrame(data[1:], columns=data[0])
        df.columns = df.columns.str.lower()
        return df

# On utilise session_state pour que les données ne se rechargent pas à chaque clic
if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- INTERFACE PRINCIPALE ---
tabs = st.tabs(["📸 Scanner (Multi-pages)", "📖 Ma Collection & Assistant"])

# --- ONGLET 1 : SCAN MULTIPLE ---
with tabs[0]:
    st.write("Charge une ou plusieurs photos d'une même recette (ex: pages d'un livre, screenshots Instagram...)")
    # MODIFICATION ICI : accept_multiple_files=True
    uploaded_files = st.file_uploader("Choisis tes images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if uploaded_files:
        # On prépare la liste des images pour l'IA
        image_parts = []
        cols = st.columns(len(uploaded_files)) # Petit affichage sympa en colonnes
        for i, file in enumerate(uploaded_files):
            img = Image.open(file)
            image_parts.append(img)
            cols[i].image(img, use_container_width=True, caption=f"Page {i+1}")
        
        if st.button(f"✨ Analyser ces {len(uploaded_files)} images"):
            with st.spinner("L'IA compile les informations de toutes les images..."):
                try:
                    # Le prompt est adapté pour le pluriel
                    prompt = """Analyse ces images qui constituent une seule et même recette.
                    Synthétise les informations (titre, tous les ingrédients, toutes les étapes dans l'ordre).
                    Retourne UNIQUEMENT un objet JSON valide avec ces clés exactes :
                    {
                      "nom": "Titre de la recette",
                      "categorie": "Plat, Dessert, Entrée ou Boisson",
                      "ingredients": ["ingrédient 1", "ingrédient 2"],
                      "instructions": ["étape 1", "étape 2"]
                    }"""
                    
                    # On envoie le prompt + TOUTES les images d'un coup
                    response = model.generate_content([prompt, *image_parts])
                    
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    data = json.loads(clean_json)
                    
                    # Formatage pour Google Sheets
                    ingredients_texte = "\n- ".join(data['ingredients']) if isinstance(data['ingredients'], list) else str(data['ingredients'])
                    instructions_texte = "\n- ".join(data['instructions']) if isinstance(data['instructions'], list) else str(data['instructions'])
                    
                    aujourdhui = str(datetime.date.today())
                    nouvelle_ligne = [aujourdhui, str(data['nom']), str(data['categorie']), ingredients_texte, instructions_texte]
                    worksheet.append_row(nouvelle_ligne)
                    
                    # On recharge les données locales pour voir l'ajout tout de suite
                    st.session_state.df = load_data()
                    st.success(f"Magique ! '{data['nom']}' (basée sur {len(uploaded_files)} images) est sauvegardée.")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Erreur lors de l'analyse : {e}. Essaie avec des images plus claires.")

# --- ONGLET 2 : COLLECTION & ASSISTANT ---
with tabs[1]:
    search = st.text_input("🔍 Rechercher une recette...")
    df_filtered = st.session_state.df.copy()
    if search:
        mask = df_filtered['nom'].str.contains(search, case=False, na=False) | df_filtered['ingrédients'].str.contains(search, case=False, na=False)
        df_filtered = df_filtered[mask]

    if not df_filtered.empty:
        # Affichage inversé (plus récent en haut)
        for i, row in df_filtered.iloc[::-1].iterrows():
            # On utilise l'index réel du DataFrame comme clé unique
            real_index = df_filtered.index[df_filtered['nom'] == row['nom']][0]
            
            with st.expander(f"👩‍🍳 {row.get('nom', 'Sans nom')} ({row.get('catégorie', 'Plat')})"):
                
                # --- PARTIE RECETTE ---
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 🛒 Ingrédients")
                    ing_text = str(row.get('ingrédients', ''))
                    for j, line in enumerate(ing_text.split('\n')):
                        clean_line = line.strip().lstrip('-').strip()
                        if clean_line:
                            st.checkbox(clean_line, key=f"chk_{real_index}_{j}")
                with col2:
                    st.markdown("#### 🔪 Instructions")
                    st.write(row.get('instructions', ''))
                
                st.divider() # Un petit trait de séparation

                # --- PARTIE ASSISTANT IA ---
                st.markdown("#### 💬 Assistant culinaire pour cette recette")
                st.caption("Pose une question sur les étapes, un doute sur une cuisson...")

                # Clé unique pour l'historique de chat DE CETTE recette précise
                chat_key = f"chat_history_{real_index}"
                if chat_key not in st.session_state:
                    st.session_state[chat_key] = []

                # Afficher l'historique de la conversation
                for message in st.session_state[chat_key]:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

                # Zone de saisie de la question
                if question := st.chat_input(f"Une question sur '{row.get('nom')}' ?", key=f"input_{real_index}"):
                    # 1. Afficher la question de l'utilisateur
                    st.session_state[chat_key].append({"role": "user", "content": question})
                    with st.chat_message("user"):
                        st.markdown(question)

                    # 2. Préparer le contexte pour l'IA
                    contexte_recette = f"""
                    Tu es un chef assistant. L'utilisateur est en train de cuisiner la recette suivante :
                    TITRE : {row.get('nom')}
                    INGRÉDIENTS : {row.get('ingrédients')}
                    INSTRUCTIONS : {row.get('instructions')}

                    L'utilisateur te pose cette question : "{question}"
                    Réponds-lui brièvement et précisément pour l'aider dans sa cuisine, en te basant UNIQUEMENT sur le contexte de cette recette si possible. Si la recette ne le dit pas, utilise tes connaissances de chef pour conseiller au mieux.
                    """

                    # 3. Demander à l'IA
                    with st.chat_message("assistant"):
                        with st.spinner("Le chef réfléchit..."):
                            response_chat = model.generate_content(contexte_recette)
                            reply = response_chat.text
                            st.markdown(reply)
                            # 4. Sauvegarder la réponse
                            st.session_state[chat_key].append({"role": "assistant", "content": reply})

    else:
        st.info("Aucune recette trouvée. Commence par en scanner une !")
