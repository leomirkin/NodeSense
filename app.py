from flask import Flask, request, jsonify, render_template
import spacy
from collections import Counter
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
import re

app = Flask(__name__)

nlp_en = spacy.load("en_core_web_sm")
nlp_es = spacy.load("es_core_news_sm")

G = nx.Graph()
word_frequencies = Counter()

spanish_stop_words = set([
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con", "contra",
    "cual", "cuando", "de", "del", "desde", "donde", "durante", "e", "el", "ella",
    "ellas", "ellos", "en", "entre", "era", "erais", "eran", "eras", "eres", "es",
    "esa", "esas", "ese", "eso", "esos", "esta", "estaba", "estabais", "estaban",
    "estabas", "estad", "estada", "estadas", "estado", "estados", "estamos", "estando",
    "estar", "estaremos", "estará", "estarán", "estarás", "estaré", "estaréis",
    "estaría", "estaríais", "estaríamos", "estarían", "estarías", "estas", "este",
    "estemos", "esto", "estos", "estoy", "estuve", "estuviera", "estuvierais",
    "estuvieran", "estuvieras", "estuvieron", "estuviese", "estuvieseis", "estuviesen",
    "estuvieses", "estuvimos", "estuviste", "estuvisteis", "estuviéramos",
    "estuviésemos", "estuvo", "está", "estábamos", "estáis", "están", "estás", "esté",
    "estéis", "estén", "estés", "fue", "fuera", "fuerais", "fueran", "fueras", "fueron",
    "fuese", "fueseis", "fuesen", "fueses", "fui", "fuimos", "fuiste", "fuisteis",
    "fuéramos", "fuésemos", "ha", "habida", "habidas", "habido", "habidos", "habiendo",
    "habremos", "habrá", "habrán", "habrás", "habré", "habréis", "habría", "habríais",
    "habríamos", "habrían", "habrías", "habéis", "había", "habíais", "habíamos",
    "habían", "habías", "han", "has", "hasta", "hay", "haya", "hayamos", "hayan",
    "hayas", "hayáis", "he", "hemos", "hube", "hubiera", "hubierais", "hubieran",
    "hubieras", "hubieron", "hubiese", "hubieseis", "hubiesen", "hubieses", "hubimos",
    "hubiste", "hubisteis", "hubiéramos", "hubiésemos", "hubo", "la", "las", "le",
    "les", "lo", "los", "me", "mi", "mis", "mucho", "muchos", "muy", "más", "nada", "ni", 
     "nos", "nosotras", "nosotros", "nuestra", "nuestras", "nuestro", "nuestros", "o", "os", 
    "otra", "otras", "otro", "otros", "para", "pero", "poco", "por", "porque", "que", "quien", 
    "quienes", "qué", "se", "sea", "seamos", "sean", "seas", "seremos", "será", "serán", "serás", "seré",
    "seréis", "sería", "seríais", "seríamos", "serían", "serías", "seáis", "sido",
    "siendo", "sin", "sobre", "sois", "somos", "son", "su", "sus", "suya",
    "suyas", "suyo", "suyos", "también", "tanto", "te", "tendremos", "tendrá",
    "tendrán", "tendrás", "tendré", "tendréis", "tendría", "tendríais", "tendríamos",
    "tendrían", "tendrías", "tened", "tenemos", "tenga", "tengamos", "tengan", "tengas",
    "tengo", "tengáis", "tenida", "tenidas", "tenido", "tenidos", "teniendo", "tenéis",
    "tenía", "teníais", "teníamos", "tenían", "tenías", "ti", "tiene", "tienen",
    "tienes", "todo", "todos", "tu", "tus", "tuve", "tuviera", "tuvierais", "tuvieran",
    "tuvieras", "tuvieron", "tuviese", "tuvieseis", "tuviesen", "tuvieses", "tuvimos",
    "tuviste", "tuvisteis", "tuviéramos", "tuviésemos", "tuvo", "tuya", "tuyas", "tuyo",
    "tuyos", "tú", "un", "una", "uno", "unos", "vosotras", "vosotros", "vuestra",
    "vuestras", "vuestro", "vuestros", "y", "ya", "él", "éramos"
])

def detect_language(text):
    es_words = set(spanish_stop_words)
    en_words = set("the an of in".split())
    words = set(text.lower().split())
    es_count = len(words.intersection(es_words))
    en_count = len(words.intersection(en_words))
    return "es" if es_count > en_count else "en"

def is_special_node(token):
    return (token.text.lower() in SELF_REFERENCES or 
            token.text.lower() in RELACIONES_PERSONALES or 
            is_likely_name(token))

def is_relevant_word(token, lang):
    max_length = 20  

    if len(token.text) > max_length:
        return False

    if lang == "es":
        return (token.text.lower() not in spanish_stop_words and 
                (token.is_alpha or is_special_node(token)) and 
                not token.is_stop)
    else:
        return ((not token.is_stop and token.is_alpha) or 
                is_special_node(token))



SPECIAL_COLOR = {"background": "rgba(138, 43, 226, 0.5)", "border": "#FFFFFF"}
RELACIONES_PERSONALES = set(['madre', 'padre', 'hijo', 'hija', 'hermano', 'hermana', 'hermanos', 'hermanas' 'tío', 'tía', 'abuelo', 'abuela', 'primo', 'prima', 'mamá', 'papá', 'mama', 'papa'])
SELF_REFERENCES = set(['yo', 'mi', 'mí', 'mío', 'mia', 'mía', 'conmigo', 'soy'])

def is_likely_name(token):
    return token.is_alpha and token.text[0].isupper() and not token.is_sent_start and not token.is_stop

def extract_keywords(doc, lang, top_n=10000):
    words = []
    ngrams = []
    for i, token in enumerate(doc):
        if is_relevant_word(token, lang) or token.text.lower() in RELACIONES_PERSONALES or is_likely_name(token):
            words.append(token.text)
            # Captura n-gramas para nombres completos
            if i < len(doc) - 1 and is_likely_name(doc[i+1]):
                ngrams.append(f"{token.text} {doc[i+1].text}")
    
    if not words:
        return []
    
    # Añadir n-gramas a las palabras
    words.extend(ngrams)
    
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform([' '.join(words)])
    feature_names = tfidf.get_feature_names_out()
    scores = tfidf_matrix.sum(axis=0).A1
    
    # Ajustar puntuaciones
    for i, word in enumerate(feature_names):
        if word.lower() in RELACIONES_PERSONALES:
            scores[i] *= 2  # Duplicar puntuación para relaciones personales
        elif re.match(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)?', word):  # Patrón para nombres propios
            scores[i] *= 2  # Duplicar puntuación para posibles nombres propios
    
    top_words = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)[:top_n]
    return [word for word, score in top_words]


def update_concept_hierarchy(keywords, doc, lang):
    global G, word_frequencies
    
    for token in doc:
        if is_relevant_word(token, lang) or is_special_node(token):
            word = token.text
            word_frequencies[word] = word_frequencies.get(word, 0) + 1
            if word not in G.nodes():
                is_special = is_special_node(token)
                mass = 2 if is_special else 1
                node_data = {
                    "sentiment": "neutral", 
                    "mass": mass,
                    "is_special": is_special
                }
                if is_special:
                    node_data["color"] = SPECIAL_COLOR
                G.add_node(word, **node_data)
    
    window_size = 5
    
    for i, token1 in enumerate(doc):
        if not is_relevant_word(token1, lang) and not is_special_node(token1):
            continue
        for j in range(i+1, min(i+window_size+1, len(doc))):
            token2 = doc[j]
            if not is_relevant_word(token2, lang) and not is_special_node(token2):
                continue
            if token1.text != token2.text:
                similarity = token1.similarity(token2)
                co_occurrence = 1 / (j - i)
                weight = (similarity + co_occurrence) / 2
                if G.has_edge(token1.text, token2.text):
                    G[token1.text][token2.text]['weight'] += weight
                else:
                    G.add_edge(token1.text, token2.text, weight=weight)

    if G.edges():
        max_weight = max([d['weight'] for (u, v, d) in G.edges(data=True)])
        for u, v, d in G.edges(data=True):
            G[u][v]['weight'] = d['weight'] / max_weight
    else:
        print("No se crearon aristas en el grafo.")

@app.route('/analyze', methods=['POST'])
def analyze_text():
    global G, word_frequencies
    text = request.json['text']
    
    lang = detect_language(text)
    nlp = nlp_es if lang == "es" else nlp_en
    
    doc = nlp(text)
    
    keywords = extract_keywords(doc, lang)
    update_concept_hierarchy(keywords, doc, lang)

    if not G.nodes():
        return jsonify({"error": "No se pudieron generar nodos. Intenta con un texto más largo o variado."})

    max_frequency = max(word_frequencies.values()) if word_frequencies else 1
    nodes = []
    for node in G.nodes():
        node_data = {
            "id": node, 
            "label": node, 
            "value": word_frequencies[node] / max_frequency * 20 + 10, 
            "sentiment": G.nodes[node]['sentiment'], 
            "mass": G.nodes[node]['mass']
        }
        if 'color' in G.nodes[node]:
            node_data["color"] = G.nodes[node]['color']
        nodes.append(node_data)

    edges = [{"from": u, "to": v, "value": data['weight']} for (u, v, data) in G.edges(data=True)]
    
    return jsonify({"nodes": nodes, "edges": edges})

@app.route('/remove_node', methods=['POST'])
def remove_node():
    node_id = request.json['node_id']
    G.remove_node(node_id)
    word_frequencies.pop(node_id, None)
    return jsonify({"status": "success"})

@app.route('/update_sentiment', methods=['POST'])
def update_sentiment():
    node_id = request.json['node_id']
    sentiment = request.json['sentiment']
    if node_id in G.nodes():
        G.nodes[node_id]['sentiment'] = sentiment
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Node not found"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clear', methods=['POST'])
def clear_all():
    global G, word_frequencies
    G.clear()
    word_frequencies.clear()
    return jsonify({"status": "cleared"})

@app.route('/create_edge', methods=['POST'])
def create_edge():
    from_node = request.json['from']
    to_node = request.json['to']
    if from_node in G.nodes() and to_node in G.nodes():
        G.add_edge(from_node, to_node, weight=1)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "One or both nodes not found"})

@app.route('/toggle_special_node', methods=['POST'])
def toggle_special_node():
    node_id = request.json['node_id']
    if node_id in G.nodes():
        is_special = not G.nodes[node_id].get('is_special', False)
        G.nodes[node_id]['is_special'] = is_special
        G.nodes[node_id]['mass'] = 2 if is_special else 1
        if is_special:
            G.nodes[node_id]['color'] = SPECIAL_COLOR
        else:
            G.nodes[node_id].pop('color', None)
        return jsonify({"status": "success", "is_special": is_special})
    return jsonify({"status": "error", "message": "Node not found"})

if __name__ == '__main__':
    app.run(debug=True)