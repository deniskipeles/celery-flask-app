import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, ScraperConfig, ScraperField, ScrapedData
from tasks import run_scraper

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', "super-secret-scraper-key")

database_url = os.getenv('DATABASE_URL', 'sqlite:///scraper.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    configs = ScraperConfig.query.all()
    return render_template('index.html', configs=configs)

@app.route('/scraper/new', methods=['GET', 'POST'])
def create_scraper():
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        pagination_selector = request.form.get('pagination_selector')
        max_pages = int(request.form.get('max_pages') or 1)
        follow_links = 'follow_links' in request.form
        link_selector = request.form.get('link_selector')
        schedule_interval = request.form.get('schedule_interval')

        config = ScraperConfig(
            name=name,
            url=url,
            pagination_selector=pagination_selector,
            max_pages=max_pages,
            follow_links=follow_links,
            link_selector=link_selector,
            schedule_interval=int(schedule_interval) if schedule_interval else None
        )
        db.session.add(config)
        db.session.flush()

        field_names = request.form.getlist('field_name[]')
        field_selectors = request.form.getlist('field_selector[]')
        field_types = request.form.getlist('field_type[]')
        field_attrs = request.form.getlist('field_attr[]')

        for i in range(len(field_names)):
            if field_names[i] and field_selectors[i]:
                field = ScraperField(
                    config_id=config.id,
                    name=field_names[i],
                    selector=field_selectors[i],
                    field_type=field_types[i],
                    attr_name=field_attrs[i] if field_types[i] == 'attr' else None
                )
                db.session.add(field)

        db.session.commit()
        flash(f"Scraper '{name}' created successfully!")
        return redirect(url_for('index'))

    return render_template('scraper_form.html')

@app.route('/scraper/<int:config_id>/edit', methods=['GET', 'POST'])
def edit_scraper(config_id):
    config = ScraperConfig.query.get_or_404(config_id)
    if request.method == 'POST':
        config.name = request.form.get('name')
        config.url = request.form.get('url')
        config.pagination_selector = request.form.get('pagination_selector')
        config.max_pages = int(request.form.get('max_pages') or 1)
        config.follow_links = 'follow_links' in request.form
        config.link_selector = request.form.get('link_selector')
        schedule_interval = request.form.get('schedule_interval')
        config.schedule_interval = int(schedule_interval) if schedule_interval else None

        ScraperField.query.filter_by(config_id=config.id).delete()

        field_names = request.form.getlist('field_name[]')
        field_selectors = request.form.getlist('field_selector[]')
        field_types = request.form.getlist('field_type[]')
        field_attrs = request.form.getlist('field_attr[]')

        for i in range(len(field_names)):
            if field_names[i] and field_selectors[i]:
                field = ScraperField(
                    config_id=config.id,
                    name=field_names[i],
                    selector=field_selectors[i],
                    field_type=field_types[i],
                    attr_name=field_attrs[i] if field_types[i] == 'attr' else None
                )
                db.session.add(field)

        db.session.commit()
        flash(f"Scraper '{config.name}' updated successfully!")
        return redirect(url_for('index'))

    return render_template('scraper_form.html', config=config)

@app.route('/scraper/<int:config_id>/run', methods=['POST'])
def run_scraper_manually(config_id):
    run_scraper.delay(config_id)
    flash("Scraping task started in background.")
    return redirect(url_for('index'))

@app.route('/scraper/<int:config_id>/results')
def view_results(config_id):
    config = ScraperConfig.query.get_or_404(config_id)
    results = ScrapedData.query.filter_by(config_id=config_id).order_by(ScrapedData.scraped_at.desc()).all()
    return render_template('results.html', config=config, results=results)

@app.route('/scraper/<int:config_id>/delete', methods=['POST'])
def delete_scraper(config_id):
    config = ScraperConfig.query.get_or_404(config_id)
    db.session.delete(config)
    db.session.commit()
    flash("Scraper deleted.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
