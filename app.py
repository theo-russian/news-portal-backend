import os
import uuid
import openai
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configurazione API key OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configurazione Google Cloud Storage
GCS_BUCKET_NAME = "crafty-tractor-450216-t8-news-images"
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET_NAME)

# Configurazione Firebase Firestore
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
news_collection = db.collection("news")

# Funzione per chiamare OpenAI API
def chatgpt_request(messages, model="gpt-3.5-turbo"):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return str(e)

# Funzione per caricare immagini su Google Cloud Storage
def upload_image_to_gcs(image):
    blob_name = f"news_images/{uuid.uuid4()}_{image.filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_file(image, content_type=image.content_type)
    blob.make_public()
    return blob.public_url

# Funzione per eliminare immagini da Google Cloud Storage
def delete_image_from_gcs(image_url):
    if not image_url:
        return
    blob_name = image_url.split(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/")[-1]
    blob = bucket.blob(blob_name)
    blob.delete()

# Endpoint per sintetizzare notizie
@app.route('/synthesize', methods=['POST'])
def synthesize():
    data = request.json
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Il testo è obbligatorio."}), 400

    messages = [
        {"role": "system", "content": "Riassumi il seguente testo in un massimo di 1000 caratteri."},
        {"role": "user", "content": text}
    ]
    result = chatgpt_request(messages)
    return jsonify({"summary": result})

# Endpoint per correggere notizie
@app.route('/check_grammar', methods=['POST'])
def check_grammar():
    data = request.get_json()
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Il testo è obbligatorio."}), 400

    messages = [
        {"role": "system", "content": "Correggi eventuali errori grammaticali nel testo fornito."},
        {"role": "user", "content": text}
    ]
    result = chatgpt_request(messages)
    return jsonify({"corrected_text": result})

# Endpoint per generare parole chiave
@app.route('/generate_labels', methods=['POST'])
def generate_labels():
    data = request.json
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Il testo è obbligatorio."}), 400

    messages = [
        {"role": "system", "content": "Genera un massimo di 10 parole chiave per classificare il seguente testo, separate da virgole."},
        {"role": "user", "content": text}
    ]
    result = chatgpt_request(messages)
    labels = [label.strip() for label in result.split(",") if label.strip()]
    return jsonify({"labels": labels})

# Endpoint per pubblicare una notizia
@app.route('/publish_news', methods=['POST'])
def publish_news():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    keywords = request.form.get("keywords", "").strip()

    if not title or not content:
        return jsonify({"error": "Titolo e contenuto sono obbligatori."}), 400

    # Gestione immagine
    image_url = None
    if "image" in request.files:
        image = request.files["image"]
        if image.filename:
            image_url = upload_image_to_gcs(image)

    # Creazione notizia nel database
    news_id = str(uuid.uuid4())
    news_item = {
        "id": news_id,
        "title": title,
        "content": content,
        "keywords": keywords.split(",") if keywords else [],
        "image_url": image_url
    }
    news_collection.document(news_id).set(news_item)

    return jsonify({"message": "Notizia salvata con successo!", "news": news_item}), 201

# Endpoint per ottenere tutte le notizie
@app.route('/news', methods=['GET'])
def get_news():
    news = [doc.to_dict() for doc in news_collection.stream()]
    return jsonify({"news": news})

# Endpoint per eliminare una notizia
@app.route('/delete_news/<news_id>', methods=['DELETE'])
def delete_news(news_id):
    news_doc = news_collection.document(news_id).get()

    if not news_doc.exists:
        return jsonify({"error": "Notizia non trovata."}), 404

    news_item = news_doc.to_dict()
    delete_image_from_gcs(news_item["image_url"])
    news_collection.document(news_id).delete()

    return jsonify({"message": "Notizia eliminata con successo!"}), 200

# Endpoint per test
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"message": "Backend operativo!"})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
