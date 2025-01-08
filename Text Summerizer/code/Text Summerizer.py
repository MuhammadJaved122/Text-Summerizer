import re
import graphviz
from flask import Flask, request, jsonify, render_template, send_file
from io import BytesIO
import nltk
from sklearn.feature_extraction.text import CountVectorizer

# Create a Flask app
app = Flask(__name__)

# Function to preprocess text (including tokenization, lemmatization, etc.)
def preprocess_text(text, chosen_options):
    tokens = []
    words = []

    try:
        # Tokenize if tokenization option is selected
        if 3 in chosen_options:
            tokens = nltk.word_tokenize(text)
            words = tokens
        else:
            words = text.split()

        # Apply preprocessing steps
        if 1 in chosen_options:  # Lowercase text
            words = [word.lower() for word in words]
        if 2 in chosen_options:  # Remove punctuation
            words = [re.sub(r'[^\w\s]', '', word) for word in words if re.sub(r'[^A-Za-z0-9 ]', '', word)]
        if 4 in chosen_options:  # Remove stopwords
            stop_words = set(nltk.corpus.stopwords.words('english'))
            words = [word for word in words if word.lower() not in stop_words]
        if 5 in chosen_options:  # Lemmatization
            lemmatizer = nltk.WordNetLemmatizer()
            pos_tags = nltk.pos_tag(words)  # Get POS tags for accurate lemmatization

            # Map NLTK POS tags to WordNet POS tags
            def get_wordnet_pos(tag):
                if tag.startswith('J'):
                    return 'a'  # Adjective
                elif tag.startswith('V'):
                    return 'v'  # Verb
                elif tag.startswith('N'):
                    return 'n'  # Noun
                elif tag.startswith('R'):
                    return 'r'  # Adverb
                else:
                    return 'n'  # Default to noun

            words = [lemmatizer.lemmatize(word, get_wordnet_pos(tag)) for word, tag in pos_tags]
        if 6 in chosen_options:  # Remove digits
            words = [word for word in words if not word.isdigit()]

        if 7 in chosen_options:  # Bag of Words
            vectorizer = CountVectorizer()
            bow = vectorizer.fit_transform([' '.join(words)])  # Fit and transform the preprocessed text
            bow_array = bow.toarray()[0]  # Convert the sparse matrix to a dense array and select the first row
            return bow_array.tolist()  # Return as a list of integers

        if 8 in chosen_options:  # POS tagging
            pos_tags = nltk.pos_tag(words)
            words = [f"{word}_{tag}" for word, tag in pos_tags]

        # Check if tokenization was selected
        if 3 in chosen_options:
            return tokens  # Return tokens if tokenization was selected
        else:
            return ' '.join(words)  # Return preprocessed text for other options

    except Exception as e:
        return f"An error occurred during preprocessing: {str(e)}"

            

# Function to parse the input scenario and extract entities, attributes, and relationships
def parse_scenario(scenario):
    entities = {}
    relationships = []

    # Define the pattern for entities and their attributes (e.g., "libraries are described by libname and location")
    entity_pattern = re.compile(r"(\w+)\s+are\s+described\s+by\s+([a-zA-Z, ]+)")
    
    # Match entities and their attributes
    entity_matches = entity_pattern.findall(scenario)
    for entity, attrs in entity_matches:
        entities[entity] = [attr.strip() for attr in attrs.split(',')]

    # Define patterns for relationships (e.g., "a library can hold many books")
    relationship_patterns = [
        (r"a\s+library\s+can\s+hold\s+many\s+(\w+)", "holds"),
        (r"the\s+(\w+)\s+can\s+appear\s+in\s+many\s+(\w+)", "appears in"),
        (r"a\s+library\s+contain\s+(\w+),\s*(\w+),\s*(\w+),\s*and\s*(\w+)", "contains")  # Adjust this line as needed
    ]
    
    # Match relationships based on patterns
    for pattern, relationship in relationship_patterns:
        relationship_matches = re.findall(pattern, scenario)
        for match in relationship_matches:
            if isinstance(match, tuple):
                entity1, entity2 = match
                relationships.append({"from": entity1, "to": entity2, "relationship": relationship})
            else:
                entity = match
                relationships.append({"from": "Library", "to": entity, "relationship": relationship})

    # Check if we have entities and relationships, otherwise return an error
    if not entities or not relationships:
        return {"error": "Invalid or incomplete ER diagram requirements."}

    return {"entities": entities, "relationships": relationships}


import graphviz
from io import BytesIO

# Function to generate ERD as PNG
def generate_erd_png(entities, relationships):
    # Create a Graphviz Digraph
    dot = graphviz.Digraph(format='png', engine='dot')

    # Set up a general style for the graph
    dot.attr(dpi='300', rankdir='TB')  # 'TB' for top-to-bottom direction

    # Add entities and their attributes
    for entity, attrs in entities.items():
        with dot.subgraph() as s:
            s.attr(rankdir='TB')  # Set rankdir to top-to-bottom to ensure attributes appear above the entity

            # Add the attributes (ellipses) above the entity (rectangle)
            for attr in attrs:
                attribute_name = f"{entity}_{attr}"
                dot.node(attribute_name, shape='ellipse', label=attr)
            
            # Add the entity (rectangle) at the bottom of the attributes
            dot.node(entity, shape='rectangle', label=entity)
            
            # Connect attributes to their entity
            for attr in attrs:
                attribute_name = f"{entity}_{attr}"
                dot.edge(attribute_name, entity)

    # Add relationships (diamond shapes)
    for relationship in relationships:
        from_entity = relationship["from"]
        to_entity = relationship["to"]
        relationship_label = relationship["relationship"]

        # Create a diamond shape for relationships
        relationship_node = f"{from_entity}_{to_entity}_{relationship_label}"
        dot.node(relationship_node, shape='diamond', label=relationship_label)

        # Connect entities to the relationship
        dot.edge(from_entity, relationship_node)
        dot.edge(to_entity, relationship_node)

    # Render the graph to a PNG in memory
    png_image = dot.pipe()  # Generate PNG image

    return png_image


entities = {
    "Library": ["libname", "location"],
    "Book": ["titles", "pages"],
    "Author": ["authname"],
    "Patron": ["patname", "patweight"]
}

relationships = [
    {"from": "Library", "to": "Book", "relationship": "contains"},
    {"from": "Book", "to": "Library", "relationship": "appears in"},
    {"from": "Library", "to": "Author", "relationship": "contains"},
    {"from": "Library", "to": "Patron", "relationship": "contains"}
]


from flask import Flask, render_template, request, send_file
from io import BytesIO

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        action = request.form.get("action")

        if action == "preprocess":
            text = request.form['text']
            chosen_options = [int(option) for option in request.form.getlist("options")]

            # Preprocess text as per selected options
            preprocessed_text = preprocess_text(text, chosen_options)

            return render_template("index.html", preprocessed_text=preprocessed_text, original_text=text)
        if action == "generate_er":
            er_requirements = request.form.get("er_requirements")
            
            # Define entities and relationships manually based on your input
            entities = {
                "Library": ["libname", "location"],
                "Book": ["titles", "pages"],
                "Author": ["authname"],
                "Patron": ["patname", "patweight"]
            }
            relationships = [
                {"from": "Library", "to": "Book", "relationship": "contains"},
                {"from": "Book", "to": "Library", "relationship": "appears in"},
                {"from": "Library", "to": "Author", "relationship": "contains"},
                {"from": "Library", "to": "Patron", "relationship": "contains"}
            ]

            # Generate the ER diagram
            png_image = generate_erd_png(entities, relationships)

            # Return the generated ER diagram as a downloadable file
            return send_file(BytesIO(png_image), mimetype='image/png', as_attachment=True, download_name='erd.png')

    return render_template('index.html')  # Display the home page for GET requests

if __name__ == '__main__':
    app.run(debug=True)

