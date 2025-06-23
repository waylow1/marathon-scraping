import os
import requests
from patchright.sync_api import sync_playwright
from bs4 import BeautifulSoup

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
        for i, img_url in enumerate(img_links, start=1):
            try:
                response = requests.get(img_url, stream=True)
                response.raise_for_status()
                filename = os.path.join(self.output_dir, f"{i}.jpg")
                with open(filename, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"Image enregistrée : {filename}")
            except Exception as e:
                print(f"Erreur téléchargement {img_url}: {e}")
                
        return [os.path.join(self.output_dir, f"{i}.jpg") for i in range(1, len(img_links) + 1)]

    def remove_watermark_with_browser(self, images, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        for image in images:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir="userdata", 
                    channel="chrome",
                    headless=False
                )
                page = browser.new_page()

                page.goto("https://www.watermarkremover.io/fr")


                file_input = page.query_selector('input[type="file"]')
                file_input.set_input_files(image_path)

                page.wait_for_timeout(10000) 

                download_link = page.query_selector('a.download-link')  
                if download_link:
                    download_url = download_link.get_attribute('href')
                    print(f"Image sans watermark dispo ici : {download_url}")
                else:
                    print("Lien de téléchargement non trouvé.")

                browser.close()


