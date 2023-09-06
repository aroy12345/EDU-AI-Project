from llama_index import SimpleDirectoryReader, LLMPredictor, ListIndex, ServiceContext, StorageContext, load_index_from_storage
from llama_index.node_parser import SimpleNodeParser
from llama_index.llms import OpenAI
from flask import Flask, render_template, request
import os
import openai
import assemblyai as aai
import os
import shutil
import datetime


from llama_index.node_parser.extractors import (
    MetadataExtractor,
    TitleExtractor,
    QuestionsAnsweredExtractor,
    SummaryExtractor
)

app = Flask(__name__)

# Insert your OpenAI API and Assembly AI key here Not included
os.environ["OPENAI_API_KEY"] = ''
openai.api_key = os.environ["OPENAI_API_KEY"]
aai.settings.api_key = ""
transcriber = aai.Transcriber()

def construct_index(directory_path):
    documents = SimpleDirectoryReader(directory_path).load_data()
    metadata_extractor = MetadataExtractor(
        extractors=[
            TitleExtractor(nodes=5),
            QuestionsAnsweredExtractor(questions=3),
            SummaryExtractor()
            #SummaryExtractor(['self', 'prev', 'next'])
        ],
    )
    parser = SimpleNodeParser.from_defaults(chunk_size=512, chunk_overlap=20, metadata_extractor=metadata_extractor)
    nodes = parser.get_nodes_from_documents(documents)
    llm_predictor = LLMPredictor(llm=OpenAI(temperature=0.7, model_name="gpt-3.5-turbo", max_tokens=51200))
    service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)
    index = ListIndex(nodes, show_progress=True, service_context=service_context)
    index.storage_context.persist(persist_dir="persist")
    return index

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chatbot', methods=['POST'])
def chatbot():
    input_text = request.form['input_text']
    storage_context = StorageContext.from_defaults(persist_dir="persist")
    index = load_index_from_storage(storage_context=storage_context)
    query_engine = index.as_query_engine()
    response = query_engine.query(input_text)
    return response.response

NOTE_SAVE_PATH2 = "saved_flashcards"
@app.route('/flashcards', methods=['POST'])
def generate_flashcards():
    input_text = "Make multiple(at least 5) extremely-detailed college-level flashcards from everything you know, this document, which is a transcript from a video lecture. Supplement each statement with reasoning or evidence. output in html style."
    storage_context = StorageContext.from_defaults(persist_dir="persist")
    index = load_index_from_storage(storage_context=storage_context)
    query_engine = index.as_query_engine(response_mode="tree_summarize")
    response = query_engine.query(input_text)
    
    # Save the response to a file
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"flashcards_{timestamp}.html"
    with open(os.path.join(NOTE_SAVE_PATH2, filename), 'w') as file:
        file.write(response.response)
    
    return response.response

@app.route('/show_flashcards')
def show_flashcards():
    files = os.listdir(NOTE_SAVE_PATH2)
    return render_template('flashcards_list.html', files=files)

NOTE_SAVE_PATH3 = "saved_quizzes"


@app.route('/quizzes', methods=['POST'])
def generate_quizzes():
    input_text = "Make extremely-detailed college-level quizzes with multiple questions (at least 10) from everything you know, this document, which is a transcript from a video lecture. Supplement each statement with reasoning or evidence. output in html style."
    storage_context = StorageContext.from_defaults(persist_dir="persist")
    index = load_index_from_storage(storage_context=storage_context)
    query_engine = index.as_query_engine(response_mode="tree_summarize")
    response = query_engine.query(input_text)
    
    # Save the response to a file
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"quizzes_{timestamp}.html"
    with open(os.path.join(NOTE_SAVE_PATH3, filename), 'w') as file:
        file.write(response.response)
    
    return response.response

@app.route('/show_quizzes')
def show_quizzes():
    files = os.listdir(NOTE_SAVE_PATH3)
    return render_template('quizzes_list.html', files=files)



NOTE_SAVE_PATH = "saved_notes"

@app.route('/notes', methods=['POST'])
def generate_notes():
    input_text = "Make extremely-detailed college-level notes from everything you know, this document, which is a transcript from a video lecture. Supplement each statement with reasoning or evidence. output in html style."
    storage_context = StorageContext.from_defaults(persist_dir="persist")
    index = load_index_from_storage(storage_context=storage_context)
    query_engine = index.as_query_engine(response_mode="tree_summarize")
    response = query_engine.query(input_text)
    
    # Save the response to a file
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"notes_{timestamp}.html"
    with open(os.path.join(NOTE_SAVE_PATH, filename), 'w') as file:
        file.write(response.response)
    
    return response.response

@app.route('/show_notes')
def show_notes():
    files = os.listdir(NOTE_SAVE_PATH)
    return render_template('notes_list.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file is provided in the reques
    empty_folder("docs")
    empty_folder("uploads")
    if 'pdf_file' not in request.files:
        return "No file provided", 400

    pdf_file = request.files['pdf_file']

    # Delete existing PDF file in the 'docs' folder (if any)
    existing_pdf = os.path.join('docs', 'uploaded_pdf.pdf')
    if os.path.exists(existing_pdf):
        os.remove(existing_pdf)

    # Save the uploaded PDF file to the 'docs' folderp
    pdf_path = os.path.join('docs', 'uploaded_pdf.pdf')
    pdf_file.save(pdf_path)

    # Call the index construction function with the updated 'docs' folder
    index = construct_index("docs")
   
    return "File uploaded successfully"

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    empty_folder("docs")
    empty_folder("uploads")
    if 'audio_file' not in request.files:
        return "No audio file provided", 400

    audio_file = request.files['audio_file']

    # Save the uploaded audio file
    audio_path = os.path.join('uploads', audio_file.filename)
    audio_file.save(audio_path)

    # Transcribe the uploaded audio
    transcript = transcriber.transcribe(audio_path)
    f = open('docs/' + audio_file.filename + '.txt', 'w')
    f.write(transcript.text)
    f.close()
    index = construct_index("docs")   

    # Return the transcription
    return "File uploaded successfully"

@app.route('/view_note/<filename>')
def view_note(filename):
    with open(os.path.join(NOTE_SAVE_PATH, filename), 'r') as file:
        content = file.read()
    return content

@app.route('/view_flashcard/<filename>')
def view_flashcard(filename):
    with open(os.path.join(NOTE_SAVE_PATH2, filename), 'r') as file:
        content = file.read()
    return content

@app.route('/view_quiz<filename>')
def view_quiz(filename):
    with open(os.path.join(NOTE_SAVE_PATH3, filename), 'r') as file:
        content = file.read()
    return content

def empty_folder(path):
    """Empty all the contents of a folder but keep the folder itself."""
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

#index = construct_index("docs")
if __name__ == '__main__':
    app.run(debug=True)
