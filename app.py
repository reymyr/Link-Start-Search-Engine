import os
from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = './static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(200), nullable=True)
    data = db.Column(db.LargeBinary)



@app.route('/', methods=['POST','GET'])
def index():
    if request.method == 'POST':
        # task_content = request.form['content']
        file = request.files['filetxt']
        new_task = Todo(name = file.filename, data = file.read())

        try:
            db.session.add(new_task)
            db.session.commit()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
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
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return 'There was a problem deleting that task'

@app.route('/view/<int:id>', methods=['GET', 'POST'])
def update(id):
    task = Todo.query.get_or_404(id)
    return render_template('update.html', task=task)


if __name__ == "__main__":
    app.run(debug=True)
