import os
from PIL import Image
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_ckeditor import CKEditor
from flask import send_from_directory


app = Flask(__name__)
app.config['SECRET_KEY'] = 'sjnc>Vdf23few>#2423rferfwe$>3343we'


ckeditor = CKEditor(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flaskdb.db'
db = SQLAlchemy(app)

class UserInfo(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    instagram = db.Column(db.String(255))  # URL социальных сетей (может быть JSON или текстовым полем)
    x = db.Column(db.String(255))
    facebook = db.Column(db.String(255))
    github = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=False)  # Поле "активный"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Поле "дата создания"
    last_active_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Поле "последнее время активности"

    articles = db.relationship('Article', backref='author', lazy=True)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user_info.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Article('{self.title}', '{self.created_at}')"
    
    def __str__(self):
        return self.title
    

# Инициализация Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return UserInfo.query.get(int(user_id))



@app.route('/')
@app.route('/home')
def home():
    posts = Article.query.order_by(Article.created_at.desc()).limit(100).all()
    posts_data = []
    
    for post in posts:
        # Получаем информацию об авторе
        author = UserInfo.query.get(post.user_id)
        
        # Добавляем данные в список
        post_data = {
            'id': post.id,
            'title': post.title,
            'user_id': post.user_id,
            'content': post.content,
            'author': author.username,
            'created_at': post.created_at
        }
        posts_data.append(post_data)
    return render_template('home.html', posts = posts_data)


@app.route('/about')
def about():
    # Получение количества пользователей
    users_count = UserInfo.query.count()
    
    # Получение количества статей
    posts_count = Article.query.count()
    return render_template('about.html', posts_count=posts_count, users_count=users_count)


@app.route('/add_post', methods = ['GET', 'POST'])
def add_post():
    title, content = "", ""
    if request.method == 'POST':
        form = request.form
        title = form['title']
        content = form['content']
        if not title or not content:
            flash('Заполните все поля', category='warning')
        else:
            # Создание новой статьи и сохранение в базе данных
            new_article = Article(
                title=title,
                content=content,
                user_id=current_user.id,  # Замените на соответствующий user_id
            )
            db.session.add(new_article)
            db.session.commit()

            flash('Пост успешно добавлен', category='success')
            return redirect(url_for('my_posts', id=current_user.id))
    return render_template('add_post.html', title = title, content = content)


@app.route('/edit_post/<int:id>', methods=['get', 'post'])
@login_required
def edit_post(id):
    post = Article.query.get(id)
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if title == "" or content == "":
            flash('Заполните все поля', category="danger")
        post.title = title
        post.content = content
        db.session.commit()
        return redirect(url_for('my_posts'))
    return render_template('edit_post.html', post_id = id, post = post)


@app.route('/register', methods=['get', 'post'])
def register():
    first_name, last_name, username, email, password, password2 = "", "", "", "", "", ""
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        if first_name == "" or last_name == "" or username == "" or email == "" or password == "" or password2 == "":
            flash('Заполните все поля!', category='warning')
        elif not is_username_unique(username):
            flash(f'{username} такой никнейм уже существует!', category='danger')
        elif not is_email_unique(email):
            flash(f'{email} такой email адресс уже существует!', category='danger')
        elif len(password) < 8:
            flash('Длина парола должен больше 8!', category="danger")
        elif password != password2:
            flash('Пароли должны совпадать!', category='danger')
        else:
            new_user = UserInfo(
                first_name = first_name, 
                last_name = last_name, 
                username = username,
                email=email, 
                password=generate_password_hash(password)
            )

            db.session.add(new_user)
            db.session.commit()

            flash('Регистрация успешно прошла!', category='success')
            return redirect('login')
    return render_template('register.html', first_name=first_name, last_name=last_name, email = email, username=username, password=password, password2 = password2)

# Проверка уникальности username
def is_username_unique(username):
    return UserInfo.query.filter_by(username=username).first() is None

# Проверка уникальности email
def is_email_unique(email):
    return UserInfo.query.filter_by(email=email).first() is None


# Роут для логина
@app.route('/login', methods=['GET', 'POST'])
def login():
    username, password = "", ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = UserInfo.query.filter_by(username=username).first()

        if username == "" or password == "":
            flash("Заполните все поля", category="warning")
        elif user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('profile', id = user.id))
        else:
            flash('Неправильные имя пользователя или пароль', category='danger')

    return render_template('login.html', username = username, password = password)


# Защищенный роут - требует аутентификации
@app.route('/profile/<int:id>')
@login_required
def profile(id):
    user = UserInfo.query.get(id)
    posts_count = Article.query.filter_by(user_id=id).count()
    return render_template('profile.html', p = posts_count, user=user)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        form = request.form

        if form['first_name'] == "" or form['last_name'] == "" or form['username'] == "" or form['email'] == "":
            flash("Не должно быть пустых полей Имя, Фамилия, Никнейм и Email", category="warning")
        else:
            # Обновление данных пользователя
            current_user.first_name = form['first_name']
            current_user.last_name = form['last_name']
            current_user.username = form['username']
            current_user.email = form['email']
            current_user.instagram = form['instagram']
            current_user.x = form['x']
            current_user.facebook = form['facebook']
            current_user.github = form['github']

            db.session.commit()  # Сохранение изменений в базе данных

    return render_template('edit_profile.html')



@app.route('/my_posts')
@login_required
def my_posts():
    """Страница просмотра записей пользователя"""
    my = Article.query.filter_by(user_id=current_user.id).all()
    return render_template('my_posts.html', posts = my)


@app.route('/posts/<int:id>')
def posts(id):
    my = Article.query.filter_by(user_id=id).all()
    user = UserInfo.query.get(id)
    if id == current_user.id:
        return redirect(url_for('my_posts'))
    return render_template('posts.html', posts = my, user = user)


# Роут для выхода
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Выход выполнен успешно!', category='success')
    return redirect(url_for('login'))


@app.route('/delete_post/<int:id>', methods=['POST'])
@login_required
def delete_post(id):
    post = Article.query.get(id)
    
    # Проверка, принадлежит ли пост текущему пользователю
    if post and post.user_id == current_user.id:
        db.session.delete(post)
        db.session.commit()
        flash('Пост успешно удален', category='success')
    else:
        flash('Невозможно удалить пост', category='danger')
    
    return redirect(url_for('my_posts', id=current_user.id))


@app.route('/read_post/<int:id>')
def read_post(id):
    post = Article.query.get(id)
    return render_template('read_post.html', id = id, post = post)


@app.errorhandler(404)
def error(e):
    return render_template('error.html', e=e)

if __name__ == "__main__":
    app.run(debug=True)