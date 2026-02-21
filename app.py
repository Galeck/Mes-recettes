import streamlit as st
import pandas as pd
from PIL import Image
import google.generativeai as genai
import json
import datetime
import gspread
import os

st.set_page_config(page_title="CookSnap Cloud", page_icon="🍳", layout="centered")

# --- BANNIÈRE DÉCORATIVE ---
if os.path.exists("banner.jpg"):
    st.image("banner.jpg", use_container_width=True)
elif os.path.exists("banner.png"):
    st.image("banner.png", use_container_width=True)

st.title("🍳 CookSnap Cloud")
st.caption("Ton assistant culinaire personnel, propulsé par l'IA.")

# --- CONNEXIONS SÉCURISÉES ---
if "GOOGLE_API_KEY" not in st.secrets or "GOOGLE_CREDENTIALS" not in st.secrets:
    st.error("⚠️ Clés manquantes ! Vérifie tes Secrets sur Streamlit.")
    st.stop()

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
        en_tetes = ["date", "nom", "catégorie", "ingrédients", "instructions", "portions"]
        worksheet.append_row(en_tetes)
        return pd.DataFrame(columns=en_tetes)
    elif len(data) == 1:
        return pd.DataFrame(columns=data[0])
    else:
        df = pd.DataFrame(data[1:], columns=data[0])
        df.columns = df.columns.str.lower()
        # Si d'anciennes recettes n'ont pas de portions, on met 4 par défaut
        if 'portions' not in df.columns:
            df['portions'] = '4'
        return df

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- INTERFACE PRINCIPALE ---
tabs = st.tabs(["📸 Scanner", "📖 Ma Collection"])

# --- ONGLET 1 : SCAN ---
with tabs[0]:
    st.write("Charge une ou plusieurs photos d'une même recette.")
    uploaded_files = st.file_uploader("Choisis tes images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if uploaded_files:
        image_parts = []
        cols = st.columns(len(uploaded_files))
        for i, file in enumerate(uploaded_files):
            img = Image.open(file)
            image_parts.append(img)
            cols[i].image(img, use_container_width=True, caption=f"Page {i+1}")
        
        if st.button(f"✨ Analyser ces {len(uploaded_files)} images"):
            with st.spinner("L'IA compile les informations..."):
                try:
                    prompt = """Analyse ces images qui constituent une recette.
                    Synthétise les informations.
                    Retourne UNIQUEMENT un objet JSON valide avec ces clés exactes :
                    {
                      "nom": "Titre",
                      "categorie": "Apéro, Entrée, Plat, Dessert ou Boisson",
                      "ingredients": ["ingrédient 1", "ingrédient 2"],
                      "instructions": ["étape 1", "étape 2"],
                      "portions": "Un nombre entier représentant le nombre de personnes (mets 4 si non précisé)"
                    }"""
                    
                    response = model.generate_content([prompt, *image_parts])
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    data = json.loads(clean_json)
                    
                    ingredients_texte = "\n- ".join(data['ingredients']) if isinstance(data['ingredients'], list) else str(data['ingredients'])
                    instructions_texte = "\n- ".join(data['instructions']) if isinstance(data['instructions'], list) else str(data['instructions'])
                    
                    aujourdhui = str(datetime.date.today())
                    nouvelle_ligne = [aujourdhui, str(data['nom']), str(data['categorie']), ingredients_texte, instructions_texte, str(data.get('portions', '4'))]
                    worksheet.append_row(nouvelle_ligne)
                    
                    st.session_state.df = load_data()
                    st.success(f"Magique ! '{data['nom']}' sauvegardée pour {data.get('portions', 4)} personnes.")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Erreur lors de l'analyse : {e}")

# --- ONGLET 2 : COLLECTION ---
with tabs[1]:
    search = st.text_input("🔍 Rechercher une recette...")
    df_filtered = st.session_state.df.copy()
    
    if search:
        mask = df_filtered['nom'].str.contains(search, case=False, na=False) | df_filtered['ingrédients'].str.contains(search, case=False, na=False)
        df_filtered = df_filtered[mask]

    categories = ["Toutes", "Apéro", "Entrée", "Plat", "Dessert", "Boisson"]
    onglets_cat = st.tabs(categories)

    for i, onglet in enumerate(onglets_cat):
        cat_actuelle = categories[i]
        
        with onglet:
            if cat_actuelle == "Toutes":
                df_affiche = df_filtered
            else:
                df_affiche = df_filtered[df_filtered['catégorie'].str.contains(cat_actuelle, case=False, na=False)]
            
            if not df_affiche.empty:
                for real_index, row in df_affiche.iloc[::-1].iterrows():
                    
                    with st.expander(f"👩‍🍳 {row.get('nom', 'Sans nom')} ({row.get('catégorie', 'Plat')})"):
                        
                        # --- BOUTON D'ÉDITION DE BASE ---
                        with st.popover("✏️ Modifier"):
                            with st.form(key=f"form_edit_{real_index}_{cat_actuelle}"):
                                nouveau_nom = st.text_input("Nom", value=row.get('nom', ''))
                                cat_actuelle_form = row.get('catégorie', 'Plat')
                                list_cat = ["Apéro", "Entrée", "Plat", "Dessert", "Boisson", "Autre"]
                                index_cat = list_cat.index(cat_actuelle_form) if cat_actuelle_form in list_cat else 2
                                nouvelle_cat = st.selectbox("Catégorie", list_cat, index=index_cat)
                                
                                if st.form_submit_button("💾 Enregistrer"):
                                    sheet_row = real_index + 2 
                                    with st.spinner("Mise à jour du Google Sheets..."):
                                        worksheet.update_cell(sheet_row, 2, nouveau_nom)
                                        worksheet.update_cell(sheet_row, 3, nouvelle_cat)
                                        st.session_state.df.at[real_index, 'nom'] = nouveau_nom
                                        st.session_state.df.at[real_index, 'catégorie'] = nouvelle_cat
                                        st.rerun()
                        
                        st.divider()

                        # --- MODULE D'AJUSTEMENT INTELLIGENT DES PORTIONS ---
                        port_orig_str = row.get('portions', '4')
                        port_orig = int(port_orig_str) if str(port_orig_str).isdigit() else 4
                        
                        # Mémoire locale pour ne pas perdre la liste si on clique sur une case
                        ing_key = f"ing_display_{real_index}_{cat_actuelle}"
                        if ing_key not in st.session_state:
                            st.session_state[ing_key] = str(row.get('ingrédients', ''))
                            st.session_state[f"current_port_{real_index}"] = port_orig

                        col_p1, col_p2 = st.columns([1, 1])
                        with col_p1:
                            new_portions = st.number_input("Nombre de personnes", min_value=1, max_value=50, value=st.session_state[f"current_port_{real_index}"], key=f"port_{real_index}_{cat_actuelle}")
                        
                        with col_p2:
                            # Le bouton n'apparaît que si on a changé le nombre
                            if new_portions != st.session_state[f"current_port_{real_index}"]:
                                if st.button("⚖️ Recalculer intelligemment", key=f"btn_ajust_{real_index}_{cat_actuelle}"):
                                    with st.spinner("Le chef recalcule avec bon sens..."):
                                        prompt_scale = f"""
                                        Adapte ces ingrédients initialement prévus pour {port_orig} personnes, pour {new_portions} personnes. 
                                        Règle absolue : Garde du bon sens culinaire. Ne propose pas "0.6 saucisse" ou "1.3 oignon", arrondis à l'unité la plus logique. Ajuste les épices et les liquides proportionnellement.
                                        Renvoie UNIQUEMENT la nouvelle liste d'ingrédients, avec un ingrédient par ligne commençant par un tiret (-). Ne fais pas de phrase d'introduction.
                                        
                                        Ingrédients originaux :
                                        {row.get('ingrédients', '')}
                                        """
                                        rep = model.generate_content(prompt_scale)
                                        st.session_state[ing_key] = rep.text.replace('```', '').strip()
                                        st.session_state[f"current_port_{real_index}"] = new_portions
                                        st.rerun()

                        st.divider()

                        # --- PARTIE RECETTE ---
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("#### 🛒 Ingrédients")
                            # On affiche la liste (originale ou recalculée par l'IA)
                            for j, line in enumerate(st.session_state[ing_key].split('\n')):
                                clean_line = line.strip().lstrip('-').strip()
                                if clean_line:
                                    st.checkbox(clean_line, key=f"chk_ing_{real_index}_{j}_{cat_actuelle}")
                        with col2:
                            st.markdown("#### 🔪 Instructions")
                            st.write(row.get('instructions', ''))
                        
                        st.divider()

                        # --- PARTIE ASSISTANT IA ---
                        st.markdown("#### 💬 L'Assistant du Chef")
                        chat_key = f"chat_history_{real_index}"
                        if chat_key not in st.session_state:
                            st.session_state[chat_key] = []

                        for message in st.session_state[chat_key]:
                            with st.chat_message(message["role"]):
                                st.markdown(message["content"])

                        if question := st.chat_input(f"Une question sur '{row.get('nom')}' ?", key=f"input_{real_index}_{cat_actuelle}"):
                            st.session_state[chat_key].append({"role": "user", "content": question})
                            with st.chat_message("user"):
                                st.markdown(question)

                            contexte_recette = f"""
                            Tu es un chef assistant. L'utilisateur cuisine ceci :
                            TITRE : {row.get('nom')}
                            INGRÉDIENTS : {st.session_state[ing_key]}
                            INSTRUCTIONS : {row.get('instructions')}

                            Question : "{question}"
                            Réponds brièvement pour l'aider, en te basant sur cette recette.
                            """

                            with st.chat_message("assistant"):
                                with st.spinner("Le chef réfléchit..."):
                                    response_chat = model.generate_content(contexte_recette)
                                    reply = response_chat.text
                                    st.markdown(reply)
                                    st.session_state[chat_key].append({"role": "assistant", "content": reply})
            else:
                st.info(f"Aucune recette dans la catégorie '{cat_actuelle}'.")
