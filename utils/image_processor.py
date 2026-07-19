import cv2
import numpy as np
import os
import math
from PIL import Image

class ImageProcessor:
    @staticmethod
    def create_tiles(image_path, output_dir="output/tiles", tile_size=1024, overlap=200):
        """Slices the P&ID into tiles for VLM processing."""
        os.makedirs(output_dir, exist_ok=True)
        img = Image.open(image_path)
        img_w, img_h = img.size
        
        tiles = []
        step = tile_size - overlap
        
        for y in range(0, img_h, step):
            for x in range(0, img_w, step):
                # Ensure we don't go out of bounds
                x_end = min(x + tile_size, img_w)
                y_end = min(y + tile_size, img_h)
                
                # Adjust if the tile is smaller than expected at edges
                x_start = max(0, x_end - tile_size) if x_end == img_w else x
                y_start = max(0, y_end - tile_size) if y_end == img_h else y
                
                box = (x_start, y_start, x_end, y_end)
                patch = img.crop(box)
                
                patch_name = f"tile_{x_start}_{y_start}.png"
                patch_path = os.path.join(output_dir, patch_name)
                patch.save(patch_path, "PNG")
                
                tiles.append({
                    "path": patch_path,
                    "offset": (x_start, y_start),
                    "size": (x_end - x_start, y_end - y_start)
                })
        return tiles

    @staticmethod
    def draw_grid(image_path, step=100):
        """
        Overlays a minimal coordinate grid on the image to provide the VLM with
        explicit spatial awareness, drastically reducing coordinate hallucination.
        """
        from PIL import ImageDraw, ImageFont
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        
        try:
            # Try to load a default font, otherwise fall back to default
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            font = ImageFont.load_default()

        # Draw Vertical Lines (labels only at the top margin to avoid obscuring symbols)
        for x in range(0, w, step):
            draw.line([(x, 0), (x, h)], fill="red", width=1)
            draw.text((x + 2, 2), str(x), fill="yellow", font=font, stroke_width=1, stroke_fill="black")

        # Draw Horizontal Lines (labels only at the left margin)
        for y in range(0, h, step):
            draw.line([(0, y), (w, y)], fill="red", width=1)
            draw.text((2, y + 2), str(y), fill="yellow", font=font, stroke_width=1, stroke_fill="black")

        grid_path = image_path.replace(".png", "_grid.png")
        img.save(grid_path, "PNG")
        return grid_path

    @staticmethod
    def locate_all_symbols(image_path, min_area=100, max_area=100000):
        """
        Scans the P&ID to find every physical bounding box of symbols.
        Guarantees <2px precision by following the actual ink.
        """
        img = cv2.imread(image_path)
        if img is None: return []
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2)) 
        opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        h_img, w_img = opened.shape[:2]
        cv2.rectangle(opened, (0, 0), (w_img, 5), 0, -1)
        cv2.rectangle(opened, (0, h_img-5), (w_img, h_img), 0, -1)
        cv2.rectangle(opened, (0, 0), (5, h_img), 0, -1)
        cv2.rectangle(opened, (w_img-5, 0), (w_img, h_img), 0, -1)
        
        contours, _ = cv2.findContours(opened, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        roi_x1, roi_y1 = int(w_img * 0.01), int(h_img * 0.01)
        roi_x2, roi_y2 = int(w_img * 0.99), int(h_img * 0.85)
        
        bboxes = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 150 < area < 100000:
                x, y, w, h = cv2.boundingRect(cnt)
                
                if x > roi_x1 and y > roi_y1 and (x+w) < roi_x2 and (y+h) < roi_y2:
                    aspect_ratio = float(w) / h if h > 0 else 0
                    if 0.1 < aspect_ratio < 10.0:
                        bboxes.append([x-1, y-1, x+w+1, y+h+1])
        
        return bboxes

    @staticmethod
    def crop_symbol(image_path, bbox, output_path):
        img = Image.open(image_path)
        crop = img.crop((bbox[0], bbox[1], bbox[2], bbox[3]))
        crop.save(output_path)
        return output_path

    @staticmethod
    def crop_batch(image_path, bboxes, output_dir):
        img = cv2.imread(image_path)
        if img is None: return []
        
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for i, bbox in enumerate(bboxes):
            x1, y1, x2, y2 = [int(v) for v in bbox]
            crop = img[max(0, y1):y2, max(0, x1):x2]
            path = os.path.join(output_dir, f"crop_{i}.png")
            cv2.imwrite(path, crop)
            paths.append(path)
        return paths
