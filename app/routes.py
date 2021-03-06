from app import app, db
from flask import render_template, flash, redirect, url_for, request, g
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, SearchForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Post
from werkzeug.urls import url_parse
from datetime import datetime
from guess_language import guess_language
from app.translate import translate

@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language=="UNKNOWN" or len(language) > 5:
            language = ""
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash("Your post in now live!")
        return redirect(url_for('index'))
    page_num = request.args.get('page',1,type=int)
    posts = current_user.followed_posts().paginate(page_num,app.config['POSTS_PER_PAGE'],False)
    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None
    page = render_template('index.html', title='Home', form=form, posts=posts.items, next_url=next_url, prev_url=prev_url)
    return page

@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    page = render_template("login.html", title="Sign In", form=form)
    return page

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        if app.config['STORE_EMAIL']:
            user = User(username = form.username.data, email=form.email.data)
        else:
            user = User(username = form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/user/<username>")
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page_num = request.args.get('page',1,type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(page_num,app.config['POSTS_PER_PAGE'],False)
    next_url = url_for('user', username=user.username, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) if posts.has_prev else None
    page = render_template('user.html', user=user, posts=posts.items, next_url=next_url, prev_url=prev_url)
    return page

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()

@app.route("/edit_profile", methods=["GET","POST"])
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)

@app.route("/follow/<username>")
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("User {} not found".format(username))
        return redirect(url_for("index"))
    if user == current_user:
        flash("You can't follow yourself!")
        return redirect(url_for('user',username=username))
    current_user.follow(user)
    db.session.commit()
    flash("You are following {}".format(username))
    return redirect(url_for('user',username=username))

@app.route("/unfollow/<username>")
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("User {} not found".format(username))
        return redirect(url_for("index"))
    if user == current_user:
        flash("You can't unfollow yourself!")
        return redirect(url_for('user',username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash("You are no longer following {}".format(username))
    return redirect(url_for('user',username=username))

@app.route("/explore")
@login_required
def explore():
    page_num = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page_num,app.config['POSTS_PER_PAGE'],False)
    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None
    page = render_template('index.html', title='Explore', posts=posts.items, next_url=next_url, prev_url=prev_url)
    return page

@app.route("/translate", methods=['POST'])
@login_required
def translate_text():
    return {'text': translate(request.form['text'], request.form['source_language'], request.form['dest_language'])}

@app.route("/search")
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for("explore"))
    page = request.args.get('page',1,type=int)
    posts, total = Post.search(g.search_form.q.data, page, app.config['POSTS_PER_PAGE'])
    next_url = url_for('/search',q=g.search_form.q.data,page=page+1) if total > page*app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('/search',q=g.search_form.q.data,page=page-1) if page > 1 else None
    return render_template('search.html', title='Search', posts=posts, next_url=next_url, prev_url=prev_url)