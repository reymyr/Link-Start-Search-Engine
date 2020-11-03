import os
from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import string 
import re 
import nltk 

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
