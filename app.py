import os
from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import string 
import re 
import nltk 
import math 

app = Flask(__name__)
UPLOAD_FOLDER = './static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test2.db'
db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(200), nullable=True)
    data = db.Column(db.LargeBinary)
    wordcnt = db.Column(db.Integer, nullable=True)
    first_sentence = db.Column(db.String(200), nullable=True)
    sim = db.Column(db.Float, nullable=True)



@app.route('/', methods=['POST','GET'])
def index():
    if request.method == 'POST':
        if 'InputFile' in request.form:
            files = request.files.getlist("filetxt")
            try:
                for file in files:
                    if file:
                        data = file.read()
                        file.stream.seek(0) 
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
                        new_task = Todo(name = file.filename, data = data, wordcnt = wordlen, first_sentence = frst_sentence, sim = 0)
                        db.session.add(new_task)
                        db.session.commit()
            
                return redirect('/')
            except:
                return 'There was an issue adding your task'
        else  :
            file = Todo.query.order_by(Todo.sim).all()
            universalSetOfUniqueWords = []
            inputQuery = request.form['textquery']
            lowercaseQuery = inputQuery.lower()

            queryWordList = re.sub("[^\w]", " ",lowercaseQuery).split()			

            for word in queryWordList:
                if word not in universalSetOfUniqueWords:
                    universalSetOfUniqueWords.append(word)
            for doc in file :
                matchPercentage = 0
                fd = open("./static/"+doc.name , "r")
                database1 = fd.read().lower()

                databaseWordList = re.sub("[^\w]", " ",database1).split()	#Replace punctuation by space and split

                for word in databaseWordList:
                    if word not in universalSetOfUniqueWords:
                        universalSetOfUniqueWords.append(word)
    
                queryTF = []
                databaseTF = []
                for word in universalSetOfUniqueWords:
                    queryTfCounter = 0
                    databaseTfCounter = 0

                    for word2 in queryWordList:
                        if word == word2:
                            queryTfCounter += 1
                    queryTF.append(queryTfCounter)

                    for word2 in databaseWordList:
                        if word == word2:
                            databaseTfCounter += 1
                    databaseTF.append(databaseTfCounter)

                dotProduct = 0
                for i in range (len(queryTF)):
                    dotProduct += queryTF[i]*databaseTF[i]

                queryVectorMagnitude = 0
                for i in range (len(queryTF)):
                    queryVectorMagnitude += queryTF[i]**2
                queryVectorMagnitude = math.sqrt(queryVectorMagnitude)

                databaseVectorMagnitude = 0
                for i in range (len(databaseTF)):
                    databaseVectorMagnitude += databaseTF[i]**2
                databaseVectorMagnitude = math.sqrt(databaseVectorMagnitude)

                matchPercentage = (float)(dotProduct / (queryVectorMagnitude * databaseVectorMagnitude))*100
                doc.sim = matchPercentage
            file2 = Todo.query.order_by(Todo.sim.desc()).all()
            dcount = len(file2) + 1
            wcount = [[0 for j in range (dcount)] for i in range (len(universalSetOfUniqueWords)) ]
            i = 0
            j = 0
            for word in universalSetOfUniqueWords:
                for word2 in queryWordList:
                    if word == word2:
                        wcount[i][j] = wcount[i][j] + 1
                i = i + 1
            j = 1
            for doc in file2 :
                fd = open("./static/"+doc.name , "r")
                database1 = fd.read().lower()
                databaseWordList = re.sub("[^\w]", " ",database1).split()	#Replace punctuation by space and split
                i = 0
                for word in universalSetOfUniqueWords:
                    for word2 in databaseWordList:
                        if word == word2:
                            wcount[i][j] = wcount[i][j] + 1
                    i = i + 1
                j = j + 1
            return render_template('index.html', tasks=file2, Ikkeh="success", arr=universalSetOfUniqueWords, arr2 = wcount, dcount = dcount, i = 0)

            # return request.form['textQuery']
    else:
        tasks = Todo.query.order_by(Todo.date_created).all()
        return render_template('index.html', tasks=tasks)


@app.route('/delete/<int:id>')
def delete(id):
    task_to_delete = Todo.query.get_or_404(id)

    try:
        os.unlink(os.path.join(app.config['UPLOAD_FOLDER'], task_to_delete.name))
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/')

@app.route('/view/<int:id>', methods=['GET', 'POST'])
def view(id):
    task = Todo.query.get_or_404(id)
    with open(os.path.join(app.config['UPLOAD_FOLDER'], task.name)) as f:
        file_content = f.read().splitlines(True)
        file_content = ''.join(file_content)
        file_content = file_content.replace('\n', '<br>')
    return render_template('update.html', task=file_content)


if __name__ == "__main__":
    app.run(debug=True)
