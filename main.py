import time
import datetime
import logging
import json
import os
import requests
import uuid
import base64
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

# Logging setup
logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_bot.log"),
        logging.StreamHandler()
    ]
)

class LinkedInBot:
    def __init__(self, email, password, access_token, search_query="agricultural technology"):
        self.email = email
        self.password = password
        self.access_token = access_token
        self.search_query = search_query
        self.driver = None
        self.wait = None
        self.history_file = 'engagement_history.json'
        self.engagement_history = self._load_history()
        self.image_dir = 'downloaded_images'
        
        # Create images directory if it doesn't exist
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed loading history: {e}")
        return {"posts": []}

    def _save_history(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.engagement_history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed saving history: {e}")

    def setup_browser(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)

    def login(self):
        logging.info("Logging into LinkedIn via Selenium...")
        self.driver.get("https://www.linkedin.com/login")
        user = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        pwd = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
        user.send_keys(self.email)
        pwd.send_keys(self.password)
        pwd.send_keys(Keys.RETURN)
        time.sleep(50)  # Wait for login to complete
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "global-nav")))
            logging.info("Selenium login successful")
            return True
        except TimeoutException:
            logging.error("Selenium login failed")
            return False

    def find_top_post(self):
        encoded = quote_plus(self.search_query)
        url = f"https://www.linkedin.com/search/results/content/?keywords={encoded}"
        logging.info(f"Searching for: {self.search_query}")
        self.driver.get(url)
        time.sleep(5)
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 800)")
            time.sleep(1)
        posts = self.driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")
        best, best_score = None, -1
        for p in posts:
            try:
                pid = p.get_attribute('data-urn') or p.get_attribute('id')
                if pid in (x['post_id'] for x in self.engagement_history['posts']):
                    continue
                # reactions
                try:
                    r = p.find_element(By.XPATH, ".//button[contains(@aria-label,'reactions')]/span").text
                    rc = int(''.join(filter(str.isdigit, r)))
                except Exception:
                    rc = 0
                # comments
                try:
                    c = p.find_element(By.XPATH, ".//button[contains(@aria-label,'comment')]/span").text
                    cc = int(''.join(filter(str.isdigit, c)))
                except Exception:
                    cc = 0
                score = rc + cc
                if score > best_score:
                    best, best_score = p, score
            except Exception:
                continue
        return best

    def download_images(self, post):
        """Extract and download images from the post"""
        image_paths = []
        try:
            # Find all images in the post
            images = post.find_elements(By.CSS_SELECTOR, "div.feed-shared-image__container img, li.artdeco-carousel__slide img")
            
            if not images:
                logging.info("No images found in the post")
                return []
            
            logging.info(f"Found {len(images)} images in the post")
            
            # Download each image
            for i, img in enumerate(images):
                try:
                    img_url = img.get_attribute('src')
                    # Skip LinkedIn default icons/avatars
                    if not img_url or 'data:image' in img_url or 'ghost-person' in img_url:
                        continue
                    
                    # Generate a unique filename
                    img_filename = f"{self.image_dir}/{uuid.uuid4()}.jpg"
                    
                    # Download the image
                    response = requests.get(img_url, stream=True)
                    if response.status_code == 200:
                        with open(img_filename, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        image_paths.append(img_filename)
                        logging.info(f"Downloaded image: {img_filename}")
                    else:
                        logging.error(f"Failed to download image: {response.status_code}")
                except Exception as e:
                    logging.error(f"Error downloading image: {e}")
            
            return image_paths
        except Exception as e:
            logging.error(f"Error extracting images: {e}")
            return []

    def upload_image_to_linkedin(self, image_path):
        """Upload an image to LinkedIn and get the asset ID"""
        try:
            # Register the upload
            register_headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'X-Restli-Protocol-Version': '2.0.0'
            }
            
            register_data = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": "urn:li:person:uuser_id",  # Replace with your LinkedIn user ID
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
            
            register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
            register_resp = requests.post(register_url, headers=register_headers, json=register_data)
            
            if register_resp.status_code != 200:
                logging.error(f"Failed to register image upload: {register_resp.status_code} {register_resp.text}")
                return None
            
            # Extract upload URL and asset ID
            upload_data = register_resp.json()
            upload_url = upload_data.get('value', {}).get('uploadMechanism', {}).get('com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest', {}).get('uploadUrl')
            asset_id = upload_data.get('value', {}).get('asset')
            
            if not upload_url or not asset_id:
                logging.error("Failed to get upload URL or asset ID")
                return None
            
            # Upload the image binary
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                
            upload_resp = requests.put(
                upload_url,
                data=image_data,
                headers={
                    'Authorization': f'Bearer {self.access_token}'
                }
            )
            
            if upload_resp.status_code not in (200, 201):
                logging.error(f"Failed to upload image: {upload_resp.status_code} {upload_resp.text}")
                return None
                
            logging.info(f"Successfully uploaded image, asset ID: {asset_id}")
            return asset_id
            
        except Exception as e:
            logging.error(f"Error uploading image: {e}")
            return None

    def create_post_with_images_api(self, text, image_paths):
        """Create a LinkedIn post with text and images using the API"""
        # First upload all images and collect their asset IDs
        image_assets = []
        for img_path in image_paths:
            asset_id = self.upload_image_to_linkedin(img_path)
            if asset_id:
                image_assets.append(asset_id)
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        # Construct the post body based on whether we have images
        if image_assets:
            # Post with images
            media_items = []
            for i, asset in enumerate(image_assets):
                media_items.append({
                    "status": "READY",
                    "description": {
                        "text": f"Image {i+1}"
                    },
                    "media": asset,
                    "title": {
                        "text": f"Image {i+1}"
                    }
                })
            
            body = {
                "author": "urn:li:person:uuser_id",  # Replace with your LinkedIn user ID
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "IMAGE",
                        "media": media_items
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        else:
            # Text-only post
            body = {
                "author": "urn:li:person:uuser_id",  # Replace with your LinkedIn user ID
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        
        resp = requests.post('https://api.linkedin.com/v2/ugcPosts', headers=headers, json=body)
        if resp.status_code == 201:
            logging.info("API post created successfully with images")
            # Clean up downloaded images after posting
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                    logging.info(f"Deleted temporary image: {img_path}")
                except:
                    pass
            return True
        
        logging.error(f"API post failed: {resp.status_code} {resp.text}")
        return False

    def get_author_details(self, post):
        """Get more complete author details from the post"""
        try:
            # Get author name
            author_name = post.find_element(By.CSS_SELECTOR, 
                "div.update-components-actor__meta span.update-components-actor__title span").text
            
            # Get author headline/title if available
            try:
                author_title = post.find_element(By.CSS_SELECTOR, 
                    "div.update-components-actor__meta span.update-components-actor__description").text
            except:
                author_title = ""
                
            # Get author profile URL if available
            try:
                author_link = post.find_element(By.CSS_SELECTOR, 
                    "div.update-components-actor__meta a.app-aware-link").get_attribute("href")
                # Extract just the profile name
                if '/in/' in author_link:
                    profile_name = author_link.split('/in/')[1].split('/')[0]
                    author_link = f"linkedin.com/in/{profile_name}"
            except:
                author_link = ""
                
            author_detail = f"{author_name}"
            if author_title:
                author_detail += f", {author_title}"
            if author_link:
                author_detail += f" (linkedin.com/in/{profile_name})"
                
            return author_detail
            
        except Exception as e:
            logging.error(f"Error getting author details: {e}")
            return "Unknown LinkedIn User"

    def repost_once(self):
        post = self.find_top_post()
        if not post:
            logging.info("No post found to repost")
            return
        
        pid = post.get_attribute('data-urn') or post.get_attribute('id')
        
        # Get detailed author information
        author_info = self.get_author_details(post)
        
        # Expand text if needed
        try:
            btn = post.find_element(By.CSS_SELECTOR, ".feed-shared-inline-show-more-text__see-more-less-toggle")
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
        except NoSuchElementException:
            pass
            
        # Get post text
        try:
            body = post.find_element(By.CSS_SELECTOR,
                "div.feed-shared-update-v2__description span.break-words").text
        except Exception:
            body = ""
            
        # Format content with clear author attribution
        content = f"Repost from {author_info}:\n\n{body}"
        content = ''.join(ch for ch in content if ord(ch) <= 0xFFFF)
        
        # Get images from the post
        image_paths = self.download_images(post)
        
        # Create post with images
        if self.create_post_with_images_api(content, image_paths):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.engagement_history['posts'].append({
                'post_id': pid, 
                'author': author_info, 
                'timestamp': now,
                'has_images': len(image_paths) > 0
            })
            self._save_history()
            logging.info(f"Successfully reposted content from {author_info} with {len(image_paths)} images")
        else:
            logging.error("Failed to repost content")

    def close(self):
        if self.driver:
            self.driver.quit()

if __name__ == '__main__':
    EMAIL = 'email'
    PASSWORD = 'password'
    TOKEN = 'access_token'  # Replace with your LinkedIn API access token
    bot = LinkedInBot(EMAIL, PASSWORD, TOKEN)
    try:
        bot.setup_browser()
        if bot.login():
            bot.repost_once()
    finally:
        bot.close()
