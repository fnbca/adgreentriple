import streamlit as st
import os
import base64
import requests

# Configuration API Fidealis
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
ACCOUNT_KEY = os.getenv("ACCOUNT_KEY")

# Configuration API Google Maps
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Fonction pour obtenir les coordonnées GPS à partir d'une adresse
def get_coordinates(address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
    return None, None

# Fonction pour se connecter à l'API Fidealis
def api_login():
    login_response = requests.get(
        f"{API_URL}?key={API_KEY}&call=loginUserFromAccountKey&accountKey={ACCOUNT_KEY}"
    )
    login_data = login_response.json()
    if "PHPSESSID" in login_data:
        return login_data["PHPSESSID"]
    return None

# Fonction pour appeler l'API Fidealis (batch de 12 fichiers max)
def api_upload_files(description, files, session_id):
    for i in range(0, len(files), 12):
        batch_files = files[i:i + 12]

        data = {
            "key": API_KEY,
            "PHPSESSID": session_id,
            "call": "setDeposit",
            "description": description,
            "type": "deposit",
            "hidden": "0",
            "sendmail": "1",
        }

        for idx, file_path in enumerate(batch_files, start=1):
            with open(file_path, "rb") as f:
                encoded_file = base64.b64encode(f.read()).decode("utf-8")
            data[f"filename{idx}"] = os.path.basename(file_path)
            data[f"file{idx}"] = encoded_file

        requests.post(API_URL, data=data)

# Function to get the quantity of product 4 (deposit package)
def get_quantity_for_product_4(credit_data):
    if isinstance(credit_data, dict) and "4" in credit_data:
        return credit_data["4"].get("quantity")
    return "Product 4 not found."

# Function to get the remaining credit for the client
def get_credit(session_id):
    credit_url = f"{API_URL}?key={API_KEY}&PHPSESSID={session_id}&call=getCredits&product_ID="
    response = requests.get(credit_url)
    if response.status_code == 200:
        return response.json()
    return None

# Interface utilisateur Streamlit
st.title("Formulaire de dépôt FIDEALIS pour adgreen inserer triple")

session_id = api_login()
if session_id:
    credit_data = get_credit(session_id)

    if isinstance(credit_data, dict):
        product_4_quantity = get_quantity_for_product_4(credit_data)
        st.write("Crédit restant pour la clé de compte :")
        st.write(f"La quantité de credit : {product_4_quantity}")
    else:
        st.error("Échec de la récupération des données de crédit.")
else:
    st.error("Échec de la connexion.")

client_name = st.text_input("Nom du client")
address = st.text_input("Adresse complète (ex: 123 rue Exemple, Paris, France)")

# Initialisation des champs Latitude et Longitude
latitude = st.session_state.get("latitude", "")
longitude = st.session_state.get("longitude", "")

# Bouton pour générer automatiquement les coordonnées GPS
if st.button("Générer les coordonnées GPS"):
    if address:
        lat, lng = get_coordinates(address)
        if lat is not None and lng is not None:
            st.session_state["latitude"] = str(lat)
            st.session_state["longitude"] = str(lng)
            latitude = str(lat)
            longitude = str(lng)
        else:
            st.error("Impossible de générer les coordonnées GPS pour l'adresse fournie.")

# Champs Latitude et Longitude pré-remplis
latitude = st.text_input("Latitude", value=latitude)
longitude = st.text_input("Longitude", value=longitude)

uploaded_files = st.file_uploader(
    "Téléchargez les photos (JPEG/PNG)",
    accept_multiple_files=True,
    type=["jpg", "png"]
)

if st.button("Soumettre"):
    if not client_name or not address or not latitude or not longitude or not uploaded_files:
        st.error("Veuillez remplir tous les champs et télécharger au moins une photo.")
    else:
        st.info("Préparation de l'envoi...")

        if session_id:
            # Sauvegarder les fichiers localement (sans collage)
            saved_files = []
            for idx, file in enumerate(uploaded_files, start=1):
                ext = os.path.splitext(file.name)[1].lower()
                if ext not in [".jpg", ".jpeg", ".png"]:
                    ext = ".jpg"

                save_path = f"{client_name}_{idx}{ext}"
                with open(save_path, "wb") as f:
                    f.write(file.read())
                saved_files.append(save_path)

            # Description avec coordonnées GPS
            description = (
                f"SCELLÉ NUMERIQUE Bénéficiaire: Nom: {client_name}, Adresse: {address}, "
                f"Coordonnées GPS: Latitude {latitude}, Longitude {longitude}"
            )

            st.info("Envoi des données (12 photos max par appel)...")
            api_upload_files(description, saved_files, session_id)
            st.success("Données envoyées avec succès !")
