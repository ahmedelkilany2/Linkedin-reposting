import time
import datetime
import logging
import json
import os
import requests
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
    def __init__(self, email, password, access_token, person_id, search_query="agricultural technology"):
        self.email = email
        self.password = password
        self.access_token = access_token
        self.person_id = person_id  # LinkedIn person URN ID
        self.search_query = search_query
        self.driver = None
        self.wait = None
        self.history_file = 'engagement_history.json'
        self.engagement_history = self._load_history()

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

    def extract_images_from_post(self, post):
        """Extract image URLs from a LinkedIn post"""
        image_urls = []
        try:
            # Look for images in the post
            image_elements = post.find_elements(By.CSS_SELECTOR, "div.feed-shared-image__container img")
            if not image_elements:
                # Try alternative selectors for carousel images
                image_elements = post.find_elements(By.CSS_SELECTOR, "li.feed-shared-image-carousel__item img")
            
            for img in image_elements:
                src = img.get_attribute('src')
                if src:
                    image_urls.append(src)
                    logging.info(f"Found image: {src[:50]}...")
        except Exception as e:
            logging.error(f"Error extracting images: {e}")
        
        return image_urls

    def upload_image_to_linkedin_api(self, image_url):
        """Upload an image directly from URL to LinkedIn API without downloading it first"""
        try:
            # First, register the image upload
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'X-Restli-Protocol-Version': '2.0.0',
                'Content-Type': 'application/json'
            }
            
            register_upload_response = requests.post(
                'https://api.linkedin.com/v2/assets?action=registerUpload',
                headers=headers,
                json={
                    "registerUploadRequest": {
                        "recipes": [
                            "urn:li:digitalmediaRecipe:feedshare-image"
                        ],
                        "owner": f"urn:li:person:{self.person_id}",
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent"
                            }
                        ]
                    }
                }
            )
            
            if register_upload_response.status_code != 200:
                logging.error(f"Failed to register image upload: {register_upload_response.status_code} - {register_upload_response.text}")
                return None
            
            upload_data = register_upload_response.json()
            asset_id = upload_data.get('value', {}).get('asset')
            upload_url = upload_data.get('value', {}).get('uploadMechanism', {}).get('com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest', {}).get('uploadUrl')
            
            if not upload_url or not asset_id:
                logging.error("Failed to get upload URL or asset ID")
                return None
                
            # Now stream the image from original URL directly to LinkedIn
            # First get the image data
            image_response = requests.get(image_url)
            if image_response.status_code != 200:
                logging.error(f"Failed to get image from URL: {image_url}")
                return None
                
            # Then upload it to LinkedIn
            upload_response = requests.post(
                upload_url,
                data=image_response.content,
                headers={
                    'Authorization': f'Bearer {self.access_token}'
                }
            )
            
            if upload_response.status_code < 200 or upload_response.status_code >= 300:
                logging.error(f"Failed to upload image: {upload_response.status_code} - {upload_response.text}")
                return None
                
            logging.info(f"Successfully uploaded image, asset ID: {asset_id}")
            return asset_id
            
        except Exception as e:
            logging.error(f"Error in image upload: {e}")
            return None

    def create_post_api(self, text, image_assets=None):
        """Create a post via LinkedIn API with optional images"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        # Prepare the post content
        post_request = {
            "author": f"urn:li:person:{self.person_id}",
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
        
        # Add images if available
        if image_assets and len(image_assets) > 0:
            media_list = []
            for asset_id in image_assets:
                media_list.append({
                    "status": "READY",
                    "description": {
                        "text": "Image from reposted content"
                    },
                    "media": asset_id,
                    "title": {
                        "text": "Reposted image"
                    }
                })
            
            if media_list:
                post_request["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
                post_request["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_list
        
        logging.info(f"Creating post with request: {json.dumps(post_request)}")
        resp = requests.post('https://api.linkedin.com/v2/ugcPosts', headers=headers, json=post_request)
        
        if resp.status_code == 201:
            post_id = resp.headers.get('X-RestLi-Id')
            logging.info(f"API post created successfully with ID: {post_id}")
            return True
        logging.error(f"API post failed: {resp.status_code} - {resp.text}")
        return False

    def repost_once(self):
        post = self.find_top_post()
        if not post:
            logging.info("No post found to repost")
            return
            
        pid = post.get_attribute('data-urn') or post.get_attribute('id')
        
        # author
        try:
            actor = post.find_element(By.CSS_SELECTOR,
                "div.update-components-actor__meta span.update-components-actor__title span").text
        except Exception:
            actor = "Unknown"
            
        # expand text
        try:
            btn = post.find_element(By.CSS_SELECTOR, ".feed-shared-inline-show-more-text__see-more-less-toggle")
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.5)
        except NoSuchElementException:
            pass
            
        # text
        try:
            body = post.find_element(By.CSS_SELECTOR,
                "div.feed-shared-update-v2__description span.break-words").text
        except Exception:
            body = ""
            
        content = f"Repost from {actor}:\n\n{body}"
        content = ''.join(ch for ch in content if ord(ch) <= 0xFFFF)
        
        # Extract images
        image_urls = self.extract_images_from_post(post)
        image_assets = []
        
        # Directly upload images to LinkedIn without downloading
        for url in image_urls:
            asset_id = self.upload_image_to_linkedin_api(url)
            if asset_id:
                image_assets.append(asset_id)

        # Use API to post with images
        if self.create_post_api(content, image_assets):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.engagement_history['posts'].append({
                'post_id': pid, 
                'author': actor, 
                'timestamp': now, 
                'had_images': len(image_assets) > 0,
                'image_count': len(image_assets)
            })
            self._save_history()
            
    def close(self):
        if self.driver:
            self.driver.quit()

if __name__ == '__main__':
    # LinkedIn API credentials
    EMAIL = 'your_email@example.com'
    PASSWORD = 'your_password'
    ACCESS_TOKEN = 'your_linkedin_access_token'  # OAuth 2.0 access token with w_member_social scope
    PERSON_ID = 'your_linkedin_person_id'  # This is the numeric ID in your LinkedIn profile URL
    
    bot = LinkedInBot(EMAIL, PASSWORD, ACCESS_TOKEN, PERSON_ID)
    try:
        bot.setup_browser()
        if bot.login():
            bot.repost_once()
    finally:
        bot.close()
