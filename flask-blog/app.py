from flask import Flask
from flask import render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user,  logout_user  ,login_required, current_user
from flask_bootstrap import Bootstrap

from flask_migrate import Migrate
from datetime import datetime
import pytz
import os
import os.path
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename



# create the extension
db = SQLAlchemy()
# create the app
app = Flask(__name__, static_url_path='/static')

#メモ

# configure the SQLite database, relative to the app instance folder
app.config['UPLOAD_FOLDER'] = 'static/thumbnails'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
app.config['SECRET_KEY'] = os.urandom(24)
bootstrap = Bootstrap(app)
# initialize the app with the extension
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager = LoginManager(app)

migrate = Migrate(app, db)



class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(27), nullable=False)
    body= db.Column(db.String(300), nullable=False)
    thumbnail = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False,
                    default=datetime.now(pytz.timezone('Asia/Tokyo')))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(100))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized_callback():
    # ユーザーがログインしていない場合、サインアップ画面にリダイレクト
    return redirect(url_for('signup'))

@app.errorhandler(500)
def internal_server_error(e):
    return "Internal Server Error", 500



@app.route('/', methods=['GET','POST'])
def index():
    if request.method == 'GET':
        posts = Post.query.order_by(Post.created_at.desc()).all()

        return render_template('index.html',posts=posts)

@app.route('/<int:post_id>')
def detail(post_id):
    # post_idに基づいてデータベースから該当する記事を取得する処理
    post = Post.query.get(post_id)
    return render_template('detail.html', post=post)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        # 既に同じメールアドレスのユーザーが存在するか確認
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('このメールアドレスは既に登録されています', 'error')
            return redirect('signup')

        user = User(email=email,  username=username, password=generate_password_hash(password, method='sha256'))

        db.session.add(user)
        db.session.commit()
        return redirect('login')
    else:
        return render_template('signup.html')


# ログインフォームの修正
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')

        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            error_message = "Invalid credentials"
            return render_template('login.html', error_message=error_message)

    return render_template('login.html')




@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect('/login')

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    post = None  # post を初期化

    if request.method == 'POST':
        title = request.form.get('title')
        if len(title) > 27:
            flash('タイトルは27文字以内で入力してください', 'error')
            return redirect('/create')
        body = request.form.get('body')

        # サムネイルの処理
        thumbnail = request.files['thumbnail']
        if thumbnail:
            # 画像がアップロードされた場合、保存する
            thumbnail_path =secure_filename(thumbnail.filename)
            thumbnail.save(os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_path))
        else:
            # 画像がアップロードされなかった場合、thumbnail_path に None を設定
            thumbnail_path = None

        # データベースに新しい記事を追加
        post = Post(title=title, body=body, thumbnail=thumbnail_path)  # thumbnail_path を追加
        db.session.add(post)
        db.session.commit()

        return redirect('/')
    else:
        return render_template('create.html', post=post)




@app.route('/<int:id>/update', methods=['GET', 'POST'])
@login_required
def update(id):
    post = Post.query.get(id)

    if request.method == 'POST':
        title = request.form.get('title')
        body = request.form.get('body')

        # テキストデータの更新
        post.title = title
        post.body = body

        # 画像のアップロード処理
        new_thumbnail = request.files.get('thumbnail')
        if new_thumbnail:
            # 画像ファイル名をセキュアにする
            filename = secure_filename(new_thumbnail.filename)
            # 画像を保存するパスを指定
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # 画像を保存
            new_thumbnail.save(upload_path)
            # データベース内のサムネイルフィールドを更新
            post.thumbnail = filename

        else:
            # サムネイル画像が選択されていない場合、None を代入
            thumbnail_path = None
        db.session.commit()
        return redirect('/')
    else:
        return render_template('update.html', post=post)

@app.route('/<int:id>/delete', methods=['GET'])
@login_required
def delete(id):
    post = Post.query.get(id)

    db.session.delete(post)
    db.session.commit()
    return redirect('/')

@app.route('/search', methods=['POST'])
def search():
    # フォームから検索クエリを取得
    query = request.form.get('query')
    # データベースで検索を実行
    results = Post.query.filter((Post.title.contains(query)) | (Post.body.contains(query))).all()
    # 検索結果をテンプレートに渡して表示
    return render_template('search_results.html', results=results)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)



