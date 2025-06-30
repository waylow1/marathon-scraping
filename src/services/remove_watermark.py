import os
import tempfile
from playwright.sync_api import sync_playwright

class WatermarkRemover:
    def accept_cookies(self, page):
        try:
            page.wait_for_selector('button.fc-button.fc-cta-consent.fc-primary-button', timeout=5000)
            page.click('button.fc-button.fc-cta-consent.fc-primary-button')
            print("Consent accepted.")
        except Exception:
            print("No consent button found or already accepted.")


    def check_for_captcha(self, page):
        try:
            if page.query_selector('iframe[src*="captcha"]') or page.query_selector('div:has-text("captcha")'):
                raise Exception("Captcha detected. Cannot proceed automatically.")
        except Exception as e:
            raise Exception("Captcha detected or error during captcha check.") from e

    def upload_image(self, page, image_path):
        try:
            with page.expect_file_chooser() as fc_info:
                page.click('#UploadImage__HomePage')
            file_chooser = fc_info.value
            file_chooser.set_files(image_path)
            print(f"Image uploaded: {image_path}")
        except Exception as e:
            print(f"Error during image upload: {e}")

    def download_processed_image(self, page, output_dir, original_image_path):
        try:
            page.wait_for_selector('img[data-testid="pixelbin-image"]', timeout=15000)
            img_elems = page.query_selector_all('img[data-testid="pixelbin-image"]')
        except Exception as e:
            raise Exception("Image not found or timeout occurred.") from e

        if not img_elems:
            raise Exception("No processed image found on the page.")

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
            print(f"Download complete: {output_filename}")
        else:
            print("Unable to extract image.")

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
                    page.goto(url)
                    self.accept_cookies(page)
                    self.upload_image(page, image)
                    self.check_for_captcha(page)
                    page.wait_for_timeout(10000)
                    self.download_processed_image(page, output_dir, image)
                except Exception as e:
                    print(f"Failed to remove watermark: {e}")
                    raise 
                finally:
                    browser.close()
