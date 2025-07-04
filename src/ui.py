import tkinter as tk
from tkinter import messagebox
from src.services.scraper import PhotoScraper
from src.services.rq_service import RQService

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Téléchargeur de photos - PhotoRunning")
        self.rq_service = RQService()
        self.rq_service.set_queue("remove-watermark")

        tk.Label(root, text="Event ID:").grid(row=0, column=0, padx=10, pady=5, sticky='e')
        self.event_id_entry = tk.Entry(root)
        self.event_id_entry.insert(0, "2393")
        self.event_id_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(root, text="Numéro de dossard:").grid(row=1, column=0, padx=10, pady=5, sticky='e')
        self.tag_entry = tk.Entry(root)
        self.tag_entry.grid(row=1, column=1, padx=10, pady=5)

        start_button = tk.Button(root, text="Télécharger les photos", command=self.start_scraping)
        start_button.grid(row=2, column=0, columnspan=2, pady=15)

    def start_scraping(self):
        event_id = self.event_id_entry.get()
        tag = self.tag_entry.get()

        if not event_id or not tag:
            messagebox.showerror("Erreur", "Veuillez entrer l'Event ID et le numéro de dossard.")
            return

        scraper = PhotoScraper(event_id, tag)
        img_links = scraper.scrape_images()

        if not img_links:
            messagebox.showinfo("Aucun résultat", "Aucune image trouvée.")
            return

        images = scraper.download_images(img_links)

        self.rq_service.set_queue(tag)
        
        for img in images:
            self.rq_service.enqueue_jobs(img, tag)

        print(f"Enqueued {len(images)} jobs for processing.")