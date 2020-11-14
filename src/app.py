import os
import string 
import re 
import nltk 
import math
import requests
from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from bs4 import BeautifulSoup

app = Flask(__name__)
UPLOAD_FOLDER = './static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///documents.db'
db = SQLAlchemy(app)

# Create database model
class Documents(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(200), nullable=True)
    url = db.Column(db.String(2000), nullable=True)
    wordcnt = db.Column(db.Integer, nullable=True)
    first_sentence = db.Column(db.String(200), nullable=True)
    sim = db.Column(db.Float, nullable=True)

# Index route
@app.route('/', methods=['POST','GET'])
def index():
    if request.method == 'POST':
        file = Documents.query.order_by(Documents.sim).all()
        WordInAllDocument = []
        inputQuery = request.form['textquery']
        lowercaseQuery = inputQuery.lower()
            
        # create stemmer
        stemfactory = StemmerFactory()
        stemmer = stemfactory.create_stemmer()

        # Create stopwordsremover
        stopfactory = StopWordRemoverFactory()
        stopword = stopfactory.create_stop_word_remover()

        # Stemming Query with Sastrawi    
        stemmedQuery = stemmer.stem(lowercaseQuery)

        # Remove Stopword from Query with Sastrawi
        removedStopQuery = stopword.remove(stemmedQuery)
        
        queryWordList = re.sub("[^\w]", " ", removedStopQuery).split()			

        # Fill set of unique words from query
        for word in queryWordList:
            if word not in WordInAllDocument:
                WordInAllDocument.append(word)

        for doc in file :
            Similarity = 0
            if doc.url:
                filename = re.sub("[^\w]", "", doc.name) + '.txt'
            else:
                filename = doc.name
            fd = open("./static/"+filename, "r")
            fileContents = fd.read().lower()

            # Stemming File Contents with Sastrawi
            stemmedFileContents = stemmer.stem(fileContents)

            # Remove Stopword from File Contents with Sastrawi
            removedStopFileContents = stopword.remove(stemmedFileContents)    

            fileContentsWordList = re.sub("[^\w]", " ", removedStopFileContents).split()	#Replace punctuation by space and split

            # Fill set of unique words from file
            for word in fileContentsWordList:
                if word not in WordInAllDocument:
                    WordInAllDocument.append(word)

            # Count word frequency in file and query
            queryVector = []
            fileContentsVector = []
            for word in WordInAllDocument:
                queryVector.append(queryWordList.count(word))
                fileContentsVector.append(fileContentsWordList.count(word))

            # Find dot product and magnitude of the vectors
            dotProduct = 0
            queryVectorLength = 0
            fileContentsVectorLength = 0
            for i in range (len(queryVector)):
                dotProduct += queryVector[i]*fileContentsVector[i]
                queryVectorLength += queryVector[i]**2
                fileContentsVectorLength += fileContentsVector[i]**2
            queryVectorLength = math.sqrt(queryVectorLength)                  
            fileContentsVectorLength = math.sqrt(fileContentsVectorLength)
            
            # Calculate similarity
            if queryVectorLength*fileContentsVectorLength != 0:
                Similarity = (float)(dotProduct / (queryVectorLength * fileContentsVectorLength))*100
                doc.sim = Similarity
            else:
                doc.sim = 0

        orderedFiles = Documents.query.order_by(Documents.sim.desc()).all()
        dcount = len(orderedFiles) + 1
        wcount = [[0 for j in range (dcount)] for i in range (len(WordInAllDocument)) ]

        # Fill term table
        for i in range(len(WordInAllDocument)):
            wcount[i][0] = queryWordList.count(WordInAllDocument[i])

        j = 1
        for doc in orderedFiles :
            if doc.url:
                filename = re.sub("[^\w]", "", doc.name) + '.txt'
            else:
                filename = doc.name
            fd = open("./static/" + filename, "r")
            fileContents = fd.read().lower()

            # Stemming File Contents with Sastrawi
            stemmedFileContents = stemmer.stem(fileContents)

            # Remove Stopword from File Contents with Sastrawi
            removedStopFileContents = stopword.remove(stemmedFileContents)    

            fileContentsWordList = re.sub("[^\w]", " ", removedStopFileContents).split()	#Replace punctuation by space and split

            i = 0
            for word in WordInAllDocument:
                # wcount[i][j] = fileContentsWordList.count(word)
                for word2 in fileContentsWordList:
                    if word == word2:
                        wcount[i][j] = wcount[i][j] + 1
                i = i + 1
            j = j + 1
        return render_template('index.html', queryCnt=queryWordList, success='Query success', documents=orderedFiles, arr=WordInAllDocument, arr2=wcount, dcount=dcount, i=0, input=inputQuery)
    else:
        documents = Documents.query.order_by(Documents.date_created).all()
        return render_template('index.html', documents=documents)

# Upload route
@app.route('/upload', methods=['POST','GET'])
def upload():
    files = request.files.getlist("filetxt")
    try:
        for file in files:
            if file:
                # Check file extension
                if not '.' in file.filename or file.filename.rsplit('.', 1)[1].upper() != 'TXT':
                    documents = Documents.query.order_by(Documents.date_created).all()
                    return render_template('index.html', documents=documents , warning ="File format error, please input .txt file")
                    
                file.stream.seek(0) 
                # Save file to local
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                wordlen = 0 
                i = 0
                with open(os.path.join(app.config['UPLOAD_FOLDER'], file.filename)) as f:
                    for line in f:
                        if (i == 0):
                            a_list = nltk.tokenize.sent_tokenize(line)
                            frst_sentence = a_list[0]
                        i = i + 1 
                        # findall re dan metode punctuation ada kekurangan dan kelebihan masing2
                        res = len(re.findall(r'\w+', line)) 
                        # res = sum([i.strip(string.punctuation).isalpha() for i in line.split()])
                        wordlen = wordlen + res

                # Add file to database
                new_document = Documents(name = file.filename, url = '', wordcnt = wordlen, first_sentence = frst_sentence, sim = 0)
                db.session.add(new_document)
                db.session.commit()

        documents = Documents.query.order_by(Documents.date_created).all()
        return render_template('index.html', documents=documents , success ='Document add success')

    except:
        documents = Documents.query.order_by(Documents.date_created).all()
        return render_template('index.html', documents=documents , warning ='There was an issue adding your document')

# Get from webpage
@app.route('/get-from-url', methods=['POST','GET'])
def getUrl():
    try:
        url = request.form['url']
        r = requests.get(url)
    except: 
        documents = Documents.query.order_by(Documents.date_created).all()
        return render_template('index.html', documents=documents , warning ="Unable to get URL. Please make sure it's valid and try again.")

    if r:
        # Get web content with BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.find('title').string.strip().replace('\n','')
        filename = re.sub("[^\w]", "", title) + '.txt'
        rawText = soup.get_text()
        removedSpaces = re.sub(' +', ' ', rawText).strip()
        removedBreaks = re.sub(r'\n\s*\n', '\n\n', removedSpaces)
        try:
            # Save web text to local file
            f = open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'w')
            f.write(removedBreaks)
            f.close()
        except :
            documents = Documents.query.order_by(Documents.date_created).all()
            return render_template('index.html', documents=documents , warning ="We can't process this link right now, please try another link")
        wordlen = 0 
        i = 0
        with open(os.path.join(app.config['UPLOAD_FOLDER'], filename)) as f:
            for line in f:
                if (i == 0):
                    a_list = nltk.tokenize.sent_tokenize(line)
                    frst_sentence = a_list[0]
                i = i + 1 
                # findall re dan metode punctuation ada kekurangan dan kelebihan masing2
                res = len(re.findall(r'\w+', line)) 
                # res = sum([i.strip(string.punctuation).isalpha() for i in line.split()])
                wordlen = wordlen + res

        # Add to database
        new_document = Documents(name = title, url = url, wordcnt = wordlen, first_sentence = frst_sentence, sim = 0)
        db.session.add(new_document)
        db.session.commit()

    documents = Documents.query.order_by(Documents.date_created).all()
    return render_template('index.html', documents=documents , success ='Link add success')
    
# Delete route
@app.route('/delete/<int:id>')
def delete(id):
    document_to_delete = Documents.query.get_or_404(id)

    try: # Delete file from local and database
        if document_to_delete.url:
            filename = re.sub("[^\w]", "", document_to_delete.name) + '.txt'
        else:
            filename = document_to_delete.name
        os.unlink(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.session.delete(document_to_delete)
        db.session.commit()
        
    except: # Delete file database
        db.session.delete(document_to_delete)
        db.session.commit()
    documents = Documents.query.order_by(Documents.date_created).all()
    return render_template('index.html', documents=documents , success ='Delete success')    

# View route
@app.route('/view/<int:id>', methods=['GET'])
def view(id):
    document = Documents.query.get_or_404(id)
    with open(os.path.join(app.config['UPLOAD_FOLDER'], document.name)) as f:
        file_content = f.read().splitlines(True)
        file_content = ''.join(file_content)
        file_content = file_content.replace('\n', '<br>')
    return render_template('viewfile.html', name=document.name, document=file_content)

@app.route('/aboutus')
def about():
    return render_template("aboutus.html")

@app.route('/howtouse')
def howtouse():
    return render_template("howtouse.html")

if __name__ == "__main__":
    app.run(debug=True,threaded=True)
