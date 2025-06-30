from src.services.remove_watermark import WatermarkRemover

def run(file_path, tag):
    client = WatermarkRemover()
    
    client.remove_watermark_with_browser(file_path, f"./output_no_watermark_{tag}")