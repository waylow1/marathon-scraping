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

    def accept_cookies(self, page):
        try:
            page.wait_for_selector('button.fc-button.fc-cta-consent.fc-primary-button', timeout=5000)
            page.click('button.fc-button.fc-cta-consent.fc-primary-button')
            print("Consentement accepté.")
        except Exception:
            print("Pas de bouton de consentement trouvé ou déjà accepté.")

    def upload_image(self, page, image_path):
        try:
            with page.expect_file_chooser() as fc_info:
                page.click('#UploadImage__HomePage') 
            file_chooser = fc_info.value
            file_chooser.set_files(image_path)
            print(f"Image uploadée : {image_path}")
        except Exception as e:
            print(f"Erreur lors de l'upload de l'image : {e}")
     
    def download_processed_image(self, page, output_dir, original_image_path):
        try:
            page.wait_for_selector('img[data-testid="pixelbin-image"]', timeout=15000)
            img_elems = page.query_selector_all('img[data-testid="pixelbin-image"]')
        except Exception as e:
            print(f"Erreur lors de la récupération de l'image traitée : {e}")
            return

        img_elem = img_elems[-1]
    
        img_base64 = page.evaluate("""
            async (img) => {
                const response = await fetch(img.src);
                const blob = await response.blob();
                return await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result.split(',')[1]);
                    reader.readAsDataURL(blob);
                });
            }
        """, img_elem)

        if img_base64:
            import base64
            img_bytes = base64.b64decode(img_base64)
            output_filename = os.path.join(output_dir, os.path.basename(original_image_path))
            with open(output_filename, "wb") as f:
                f.write(img_bytes)
            print(f"Téléchargement terminé : {output_filename}")
        else:
            print("Impossible d'extraire l'image.")
 
    
    def remove_watermark_with_browser(self, images, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        url = "https://www.watermarkremover.io/fr"

        def batched(iterable, n):
            it = iter(iterable)
            while True:
                batch = list(islice(it, n))
                if not batch:
                    break
                yield batch

        for batch in batched(images, 2): 
            with tempfile.TemporaryDirectory() as tmp_user_data_dir:
                with sync_playwright() as p:
                    browser = p.chromium.launch_persistent_context(
                        user_data_dir=tmp_user_data_dir,
                        channel="chrome",
                        headless=False
                    )
                    page = browser.new_page()
                    page.goto(url)
                    self.accept_cookies(page)

                    for image in batch:
                        self.upload_image(page, image)
                        page.wait_for_timeout(10000)  
                        self.download_processed_image(page, output_dir, image)

                    browser.close()
