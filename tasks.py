import os
from bs4 import BeautifulSoup
from celery import Celery
from celery.utils.log import get_task_logger
from models import db, ScraperConfig, ScraperField, ScrapedData
from flask import Flask
from urllib.parse import urljoin, urlparse
from camoufox.sync_api import Camoufox

def create_app():
    app = Flask(__name__)
    database_url = os.getenv('DATABASE_URL', 'sqlite:///scraper.db')
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

flask_app = create_app()

celery_app = Celery('tasks', broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
logger = get_task_logger(__name__)

def scrape_page(browser, url, fields):
    try:
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')

        extracted_data = {}
        for field in fields:
            elements = soup.select(field.selector)
            if field.field_type == 'text':
                extracted_data[field.name] = [el.get_text(strip=True) for el in elements]
            elif field.field_type == 'attr' and field.attr_name:
                extracted_data[field.name] = [el.get(field.attr_name) for el in elements if el.has_attr(field.attr_name)]

        page.close()

        if not extracted_data:
            return [], soup

        max_len = max(len(v) for v in extracted_data.values())
        final_results = []
        for i in range(max_len):
            item = {}
            for name, values in extracted_data.items():
                if i < len(values):
                    item[name] = values[i]
                else:
                    item[name] = None
            final_results.append(item)

        return final_results, soup
    except Exception as e:
        logger.error(f"Error scraping {url} with Camoufox: {e}")
        return [], None

@celery_app.task
def run_scraper(config_id):
    with flask_app.app_context():
        config = ScraperConfig.query.get(config_id)
        if not config:
            return "Config not found"

        logger.info(f"Starting scraper: {config.name} on {config.url}")

        visited_urls = set()
        urls_to_visit = [config.url]
        pages_scraped = 0

        base_domain = urlparse(config.url).netloc

        with Camoufox(headless=True) as browser:
            while urls_to_visit and pages_scraped < config.max_pages:
                current_url = urls_to_visit.pop(0)
                if current_url in visited_urls:
                    continue

                logger.info(f"Scraping page: {current_url}")
                results, soup = scrape_page(browser, current_url, config.fields)

                if results:
                    for item in results:
                        data_entry = ScrapedData(config_id=config.id, data=item, page_url=current_url)
                        db.session.add(data_entry)
                    db.session.commit()

                visited_urls.add(current_url)
                pages_scraped += 1

                if soup:
                    if config.pagination_selector:
                        next_page_el = soup.select_one(config.pagination_selector)
                        if next_page_el:
                            next_page_url = next_page_el.get('href')
                            if next_page_url:
                                full_url = urljoin(current_url, next_page_url)
                                if full_url not in visited_urls:
                                    urls_to_visit.append(full_url)

                    if config.follow_links and config.link_selector:
                        link_elements = soup.select(config.link_selector)
                        for el in link_elements:
                            link_url = el.get('href')
                            if link_url:
                                full_url = urljoin(current_url, link_url)
                                if urlparse(full_url).netloc == base_domain and full_url not in visited_urls:
                                    urls_to_visit.append(full_url)

        from datetime import datetime
        config.last_run = datetime.utcnow()
        db.session.commit()
        return f"Finished scraping {pages_scraped} pages"

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    with flask_app.app_context():
        configs = ScraperConfig.query.filter(ScraperConfig.schedule_interval.isnot(None)).all()
        for config in configs:
            sender.add_periodic_task(
                config.schedule_interval * 60.0,
                run_scraper.s(config.id),
                name=f'Run scraper {config.name} every {config.schedule_interval} min'
            )
