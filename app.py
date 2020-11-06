import os
from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
import string 
import re 
import nltk 
import math

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
    data = db.Column(db.LargeBinary)
    wordcnt = db.Column(db.Integer, nullable=True)
    first_sentence = db.Column(db.String(200), nullable=True)
    sim = db.Column(db.Float, nullable=True)

# Index route
@app.route('/', methods=['POST','GET'])
def index():
    if request.method == 'POST':
        file = Documents.query.order_by(Documents.sim).all()
        universalSetOfUniqueWords = []
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
            if word not in universalSetOfUniqueWords:
                universalSetOfUniqueWords.append(word)

        for doc in file :
            matchPercentage = 0
            fd = open("./static/"+doc.name , "r")
            fileContents = fd.read().lower()

            # Stemming File Contents with Sastrawi
            stemmedFileContents = stemmer.stem(fileContents)

            # Remove Stopword from File Contents with Sastrawi
            removedStopFileContents = stopword.remove(stemmedFileContents)    

            fileContentsWordList = re.sub("[^\w]", " ", removedStopFileContents).split()	#Replace punctuation by space and split

            # Fill set of unique words from file
            for word in fileContentsWordList:
                if word not in universalSetOfUniqueWords:
                    universalSetOfUniqueWords.append(word)

            # Count word frequency in file and query
            queryTF = []
            fileContentsTF = []
            for word in universalSetOfUniqueWords:
                queryTF.append(queryWordList.count(word))
                fileContentsTF.append(fileContentsWordList.count(word))

            # Find dot product and magnitude of the vectors
            dotProduct = 0
            queryVectorMagnitude = 0
            fileContentsVectorMagnitude = 0
            for i in range (len(queryTF)):
                dotProduct += queryTF[i]*fileContentsTF[i]
                queryVectorMagnitude += queryTF[i]**2
                fileContentsVectorMagnitude += fileContentsTF[i]**2
            queryVectorMagnitude = math.sqrt(queryVectorMagnitude)                  
            fileContentsVectorMagnitude = math.sqrt(fileContentsVectorMagnitude)
            
            # Calculate similarity
            if queryVectorMagnitude*fileContentsVectorMagnitude != 0:
                matchPercentage = (float)(dotProduct / (queryVectorMagnitude * fileContentsVectorMagnitude))*100
                doc.sim = matchPercentage
            else:
                doc.sim = 0

        orderedFiles = Documents.query.order_by(Documents.sim.desc()).all()
        dcount = len(orderedFiles) + 1
        wcount = [[0 for j in range (dcount)] for i in range (len(universalSetOfUniqueWords)) ]

        # Fill term table
        for i in range(len(universalSetOfUniqueWords)):
            wcount[i][0] = queryWordList.count(universalSetOfUniqueWords[i])

        j = 1
        for doc in orderedFiles :
            fd = open("./static/" + doc.name, "r")
            fileContents = fd.read().lower()

            # Stemming File Contents with Sastrawi
            stemmedFileContents = stemmer.stem(fileContents)

            # Remove Stopword from File Contents with Sastrawi
            removedStopFileContents = stopword.remove(stemmedFileContents)    

            fileContentsWordList = re.sub("[^\w]", " ", removedStopFileContents).split()	#Replace punctuation by space and split

            i = 0
            for word in universalSetOfUniqueWords:
                for word2 in fileContentsWordList:
                    if word == word2:
                        wcount[i][j] = wcount[i][j] + 1
                i = i + 1
            j = j + 1
        return render_template('index.html', documents=orderedFiles, arr=universalSetOfUniqueWords, arr2=wcount, dcount=dcount, i=0, input=inputQuery)
    else:
        documents = Documents.query.order_by(Documents.date_created).all()
        return render_template('index.html', documents=documents)

# Upload route
@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist("filetxt")
    try:
        for file in files:
            if file:
                data = file.read()
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
                new_document = Documents(name = file.filename, data = data, wordcnt = wordlen, first_sentence = frst_sentence, sim = 0)
                db.session.add(new_document)
                db.session.commit()
    
        return redirect('/')
    except:
        return 'There was an issue adding your document'

# Delete route
@app.route('/delete/<int:id>')
def delete(id):
    document_to_delete = Documents.query.get_or_404(id)

    try: # Delete file from local and database
        os.unlink(os.path.join(app.config['UPLOAD_FOLDER'], document_to_delete.name))
        db.session.delete(document_to_delete)
        db.session.commit()
        return redirect('/')
    except: # Delete file database
        db.session.delete(document_to_delete)
        db.session.commit()
        return redirect('/')

# View route
@app.route('/view/<int:id>', methods=['GET', 'POST'])
def view(id):
    document = Documents.query.get_or_404(id)
    with open(os.path.join(app.config['UPLOAD_FOLDER'], document.name)) as f:
        file_content = f.read().splitlines(True)
        file_content = ''.join(file_content)
        file_content = file_content.replace('\n', '<br>')
    return render_template('update.html', name=document.name, document=file_content)


if __name__ == "__main__":
    app.run(debug=True)
