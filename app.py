import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from google.cloud import storage
import uuid

app = Flask(__name__)
CORS(app)

# Configurazione della chiave API di OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configura Google Cloud Storage
GCS_BUCKET_NAME = "crafty-tractor-450216-t8-news-images"
storage_client = storage.Client()
bucket = storage_client.bucket(GCS_BUCKET_NAME)

# Simulazione di un database in memoria (ogni notizia ha un ID univoco)
news_storage = []

# Funzione generica per chiamare le API di OpenAI (ChatGPT)
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

# Funzione per eliminare un'immagine da Google Cloud Storage
def delete_image_from_gcs(image_url):
    if not image_url:
        return
    blob_name = image_url.split(f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/")[-1]
    blob = bucket.blob(blob_name)
    blob.delete()

# Endpoint per sintetizzare le notizie 
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

# Endpoint per correggere le notizie
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

# Endpoint per salvare le notizie
@app.route('/publish_news', methods=['POST'])
def publish_news():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    keywords = request.form.get("keywords", "").strip()

    if not title or not content:
        return jsonify({"error": "Titolo e contenuto sono obbligatori."}), 400

    # Gestione dell'immagine
    image_url = None
    if "image" in request.files:
        image = request.files["image"]
        if image.filename:
            image_url = upload_image_to_gcs(image)

    # Salvataggio della notizia con un ID univoco
    news_item = {
        "id": str(uuid.uuid4()),  # Genera un ID univoco per ogni notizia
        "title": title,
        "content": content,
        "keywords": keywords.split(",") if keywords else [],
        "image_url": image_url
    }
    news_storage.append(news_item)

    return jsonify({"message": "Notizia salvata con successo!", "news": news_item}), 201

# Endpoint per ottenere le notizie salvate
@app.route('/news', methods=['GET'])
def get_news():
    return jsonify({"news": news_storage})

# Endpoint per eliminare una notizia
@app.route('/delete_news/<news_id>', methods=['DELETE'])
def delete_news(news_id):
    global news_storage
    news_item = next((news for news in news_storage if news["id"] == news_id), None)

    if not news_item:
        return jsonify({"error": "Notizia non trovata."}), 404

    # Eliminare l'immagine dallo storage se esiste
    delete_image_from_gcs(news_item["image_url"])

    # Rimuovere la notizia dall'array
    news_storage = [news for news in news_storage if news["id"] != news_id]

    return jsonify({"message": "Notizia eliminata con successo!"}), 200

# Endpoint di test
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"message": "Backend operativo!"})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
