import os
import time
import base64
import tempfile
import requests
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
import re

class WatermarkRemover:
    def __init__(self):
        self.API_KEY = os.getenv('API_KEY')
        self.site_key = None
        self.website_url = None

    def accept_cookies(self, page):
        try:
            page.wait_for_selector('button.fc-button.fc-cta-consent.fc-primary-button', timeout=5000)
            page.click('button.fc-button.fc-cta-consent.fc-primary-button')
            print("[✓] Cookies accepted.")
        except Exception:
            print("[!] No cookie consent button found or already accepted.")

    def listen_for_recaptcha(self, page):
        page.on("request", self.extract_sitekey_from_request)


    def log_requests(self, page):
        def on_request(request):
            url = request.url
            if "google.com/recaptcha/api2/" in url:
                print(f"[REQUEST] {url}")
        page.on("request", on_request)

    def extract_sitekey_from_html(self, html):
        match = re.search(r'data-sitekey=["\']([a-zA-Z0-9_-]{30,})["\']', html)
        if match:
            return match.group(1)
        match2 = re.search(r'sitekey=["\']([a-zA-Z0-9_-]{30,})["\']', html)
        if match2:
            return match2.group(1)
        return None


    def extract_sitekey_from_request(self, request):
        if "https://www.google.com/recaptcha/api2/" in request.url:
            if "anchor" in request.url and "k=" in request.url:
                params = parse_qs(urlparse(request.url).query)
                if "k" in params:
                    self.site_key = params["k"][0]
                    print(f"[✓] Sitekey found: {self.site_key}")

    def create_captcha_task(self):
        payload = {
            'clientKey': self.API_KEY,
            'task': {
                'type': 'ReCaptchaV2TaskProxyLess',
                'websiteURL': self.website_url,
                'websiteKey': self.site_key
            }
        }
        print("[*] Creating CAPTCHA task...")
        response = requests.post('https://api.capsolver.com/createTask', json=payload)
        data = response.json()

        if 'taskId' not in data:
            raise Exception(f"[!] Failed to create CAPTCHA task: {data}")

        return data['taskId']

    def wait_for_captcha_solution(self, task_id, max_attempts=30, delay=2):
        payload = {
            'clientKey': self.API_KEY,
            'taskId': task_id
        }

        print(f"[*] Polling CAPTCHA solution for task: {task_id}")
        for attempt in range(max_attempts):
            time.sleep(delay)
            response = requests.post('https://api.capsolver.com/getTaskResult', json=payload)
            data = response.json()

            if data.get('status') == 'ready':
                token = data['solution']['gRecaptchaResponse']
                print(f"[✓] CAPTCHA solved.")
                return token

        raise Exception("[!] CAPTCHA solving timed out.")

    def inject_captcha_token(self, page, token):
        print(token)
        print("[*] Injecting CAPTCHA token...")
        
        # Injecter le token dans la textarea dans la page principale
        page.evaluate(f"""
            () => {{
                const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                if (textarea) {{
                    textarea.style.display = 'block';
                    textarea.value = "{token}";
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            }}
        """)
        
        # Attendre un peu que la page prenne en compte le token
        page.wait_for_timeout(500)
        
        # Trouver l'iframe contenant le bouton reCAPTCHA (ajuste le sélecteur si nécessaire)
        iframe = None
        for frame in page.frames:
            if "recaptcha" in frame.url:
                iframe = frame
                break
        
        if iframe is None:
            print("[!] reCAPTCHA iframe not found!")
            return
        
        # Cliquer sur le bouton de validation reCAPTCHA dans l'iframe
        try:
            iframe.click('#recaptcha-verify-button')
            print("[✓] Clicked on recaptcha-verify-button inside iframe.")
        except Exception as e:
            print(f"[!] Failed to click recaptcha-verify-button in iframe: {e}")
        
        # Capture écran après injection
        screenshot_path = "after_captcha_injection.png"
        page.screenshot(path=screenshot_path)
        print(f"[*] Screenshot taken: {screenshot_path}")
        
        # Collecte logs console
        console_messages = []
        def on_console(msg):
            console_messages.append(f"[console.{msg.type}] {msg.text}")
        page.on("console", on_console)
        
        # Collecte requêtes réseau pendant 5 secondes après injection
        requests_log = []
        def on_request(request):
            requests_log.append(f"[REQUEST] {request.method} {request.url}")
        def on_response(response):
            requests_log.append(f"[RESPONSE] {response.status} {response.url}")
        page.on("request", on_request)
        page.on("response", on_response)
        
        print("[*] Listening to network and console events for 5 seconds...")
        page.wait_for_timeout(5000)
        
        # Affichage logs console
        print("\n[Console logs after CAPTCHA injection]:")
        for msg in console_messages:
            print(msg)
        
        # Affichage logs réseau
        print("\n[Network requests after CAPTCHA injection]:")
        for req in requests_log:
            print(req)


    def solve_captcha(self, page):
        self.website_url = page.url
        self.listen_for_recaptcha(page)
        print("[*] Waiting for CAPTCHA to load...")
        page.wait_for_timeout(5000)  # attendre que la requête recaptcha soit visible

        if not self.site_key:
            print("[!] Sitekey not found in network traffic. Trying to extract from HTML...")
            html = page.content()
            self.site_key = self.extract_sitekey_from_html(html)
            if self.site_key:
                print(f"[✓] Sitekey extracted from HTML: {self.site_key}")
            else:
                raise Exception("[!] Sitekey not found anywhere!")
            
        task_id = self.create_captcha_task()
        token = self.wait_for_captcha_solution(task_id)
        self.inject_captcha_token(page, token)

    def check_for_captcha(self, page) -> bool:
        html = page.content()
        if re.search(r'<iframe[^>]+src=["\'][^"\']*recaptcha[^"\']*["\']', html, re.IGNORECASE):
            print("[CAPTCHA DETECTÉ] iframe reCAPTCHA trouvée dans le HTML.")
            return True

        if re.search(r'<textarea[^>]+name=["\']g-recaptcha-response["\']', html, re.IGNORECASE):
            print("[CAPTCHA DETECTÉ] textarea g-recaptcha-response trouvé dans le HTML.")
            return True
        
        print("[PAS DE CAPTCHA] reCAPTCHA non détecté dans le HTML.")
        return False


    def upload_image(self, page, image_path):
        try:
            with page.expect_file_chooser() as fc_info:
                page.click('#UploadImage__HomePage')
            file_chooser = fc_info.value
            file_chooser.set_files(image_path)
            print(f"[✓] Image uploaded: {image_path}")
        except Exception as e:
            print(f"[!] Error uploading image: {e}")

    def download_processed_image(self, page, output_dir, original_image_path):
        try:
            page.wait_for_selector('img[data-testid="pixelbin-image"]', timeout=15000)
            img_elems = page.query_selector_all('img[data-testid="pixelbin-image"]')
        except Exception as e:
            raise Exception("[!] Processed image not found or timeout.") from e

        if not img_elems:
            raise Exception("[!] No processed image found.")

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
            img_bytes = base64.b64decode(img_base64)
            output_filename = os.path.join(output_dir, os.path.basename(original_image_path))
            with open(output_filename, "wb") as f:
                f.write(img_bytes)
            print(f"[✓] Download complete: {output_filename}")
        else:
            print("[!] Unable to extract image data.")

    def remove_watermark_with_browser(self, image, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        url = "https://www.watermarkremover.io/fr"

        with tempfile.TemporaryDirectory() as tmp_user_data_dir:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=tmp_user_data_dir,
                    channel="chrome",
                    headless=False
                )
                page = browser.new_page()

                try:
                    
                    page.on("request", self.extract_sitekey_from_request)
                    
                    page.goto(url)
                    self.website_url = page.url
                    self.accept_cookies(page)

                    self.upload_image(page, image)

                    page.wait_for_timeout(10000)  # Attendre que l'image soit traitée après l'upload

                    if self.check_for_captcha(page):
                        print("[!] CAPTCHA detected, solving...")
                        self.solve_captcha(page)
                    page.wait_for_timeout(600000)  
                    self.download_processed_image(page, output_dir, image)
                except Exception as e:
                    print(f"[!] Failed to remove watermark: {e}")
                    raise
                finally:
                    browser.close()

