import os
from datetime import datetime
import dotenv
from flask import Flask, request, jsonify, render_template, redirect, abort
from flask_sqlalchemy import SQLAlchemy
from flask_basicauth import BasicAuth
from short_url import UrlEncoder
import validators

dotenv.load_dotenv(dotenv_path=dotenv.find_dotenv())

base_url = os.environ['APP_BASE_URL']

db = SQLAlchemy()
app = Flask(__name__)
codec = UrlEncoder(alphabet=os.environ['APP_ALPHABET'])

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
db.init_app(app)


class LinkEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String, nullable=False)
    visit_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LinkEntry #{self.id}>'


app.config['BASIC_AUTH_USERNAME'] = os.environ['APP_USERNAME']
app.config['BASIC_AUTH_PASSWORD'] = os.environ['APP_PASSWORD']
basic_auth = BasicAuth(app)


@app.route('/create', methods=['GET', 'POST'])
@basic_auth.required
def create_link():
    if request.method == 'GET':
        return render_template('create.html')

    url = request.json.get('url')
    if url is None or not validators.url(url):
        return jsonify({'detail': 'Invalid URL'}), 400

    link_entry = LinkEntry(url=url)
    db.session.add(link_entry)
    db.session.commit()
    link_slug = codec.encode_url(link_entry.id)
    return jsonify({'short_link': f'{base_url}/{link_slug}'}), 201


@app.route('/<string:slug>', methods=['GET'])
def open_link(slug):
    if not validators.slug(slug):
        abort(404)

    link_id = codec.decode_url(slug)
    link_entry = db.get_or_404(LinkEntry, link_id)
    link_entry.visit_count += 1
    db.session.commit()
    return redirect(link_entry.url)


@app.route('/<string:slug>/info', methods=['GET'])
def get_info(slug):
    if not validators.slug(slug):
        abort(404)

    link_id = codec.decode_url(slug)
    link_entry = db.get_or_404(LinkEntry, link_id)
    return jsonify({
        'url': link_entry.url,
        'visit_count': link_entry.visit_count,
        'created_at': link_entry.created_at,
    }), 200


@app.cli.command("setup-db")
def create_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()
