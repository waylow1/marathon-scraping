import os
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup
from itertools import islice
import tempfile

class PhotoScraper:
    def __init__(self, event_id, tag, output_dir="./output"):
        self.event_id = event_id
        self.tag = tag
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def build_url(self):
        return f"https://photorunning.com/events/{self.event_id}/tags/{self.tag}"

    def scrape_images(self):
        url = self.build_url()

        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir="userdata",
                channel="chrome",
                headless=False,
                no_viewport=True
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto(url)
            page.wait_for_timeout(3000)
            html_content = page.content()
            browser.close()

        soup = BeautifulSoup(html_content, "lxml")
        masonry_container = soup.find("ngx-masonry")

        if not masonry_container:
            return []

        img_tags = masonry_container.find_all("img", class_="image-area")
        img_links = [img["src"] for img in img_tags if img.get("src")]
        return img_links

    def download_images(self, img_links):
        saved_paths = []
        for i, img_url in enumerate(img_links, start=1):
            try:
                response = requests.get(img_url, stream=True)
                response.raise_for_status()
                filename = os.path.join(self.output_dir, f"{i}.jpg")
                with open(filename, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"Image enregistrée : {filename}")
                saved_paths.append(filename)
            except Exception as e:
                print(f"Erreur téléchargement {img_url}: {e}")
        return saved_paths

   
