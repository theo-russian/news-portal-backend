import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai

app = Flask(__name__)
CORS(app)

# Configurazione della chiave API di OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Cartella uploads/ in cui salvare le immagini delle notizie caricate
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Simulazione di un database in memoria
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
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
            image.save(image_path)
            image_url = f"/{image_path}"  # Percorso dell'immagine

    # Salvataggio della notizia in memoria
    news_item = {
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

# Endpoint di test
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"message": "Backend operativo!"})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
