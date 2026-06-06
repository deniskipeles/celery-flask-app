from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ScraperConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    pagination_selector = db.Column(db.String(200))
    max_pages = db.Column(db.Integer, default=1)
    follow_links = db.Column(db.Boolean, default=False)
    link_selector = db.Column(db.String(200))
    schedule_interval = db.Column(db.Integer)  # in minutes
    last_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    fields = db.relationship('ScraperField', backref='config', cascade="all, delete-orphan")
    results = db.relationship('ScrapedData', backref='config', cascade="all, delete-orphan")

class ScraperField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('scraper_config.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    selector = db.Column(db.String(200), nullable=False)
    field_type = db.Column(db.String(20), default='text')  # text, attr
    attr_name = db.Column(db.String(100))

class ScrapedData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('scraper_config.id'), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    page_url = db.Column(db.String(500))
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
