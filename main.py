import time
import json
import random
import logging
import schedule
import requests
import datetime
import getpass
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta

class LinkedInBot:
    def __init__(self, email, password, topics=None):
        """
        Initialize the LinkedIn automation bot
        """
        self.email = email
        self.password = password
        self.topics = topics if topics else ["agriculture technology innovation"]
        self.driver = None
        self.cookies = None
        self.daily_log = []
        self.log_file = f"linkedin_activity_{datetime.now().strftime('%Y%m%d')}.json"
        self.posts_done_today = 0
        self.max_daily_posts = 15
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for the bot"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("linkedin_bot.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("LinkedInBot")

    def setup_browser(self):
        """Set up the Chrome browser for automation"""
        try:
            self.logger.info("Setting up Chrome browser")
            chrome_options = Options()
            
            # Add options to make browser less detectable
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            # Uncomment to run headless if needed
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Override the navigator properties to prevent detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return True
        except Exception as e:
            self.logger.error(f"Browser setup failed: {str(e)}")
            return False

    def login(self):
        """Log into LinkedIn using Selenium to handle security challenges"""
        try:
            if not self.driver and not self.setup_browser():
                return False
                
            self.logger.info("Attempting to login to LinkedIn via browser")
            self.driver.get("https://www.linkedin.com/login")
            
            # Wait for the page to load
            time.sleep(3)
            
            # Enter email
            email_field = self.driver.find_element(By.ID, "username")
            email_field.clear()
            email_field.send_keys(self.email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # To solve a verification challenge
            if "checkpoint" in self.driver.current_url or "challenge" in self.driver.current_url:
                self.logger.warning("LinkedIn security challenge detected")
                print("\nLinkedIn security challenge detected. Please complete the verification in the browser window.")
                print("The program will continue once you've completed the verification.")
                
                # Wait for user to solve the challenge
                input("Press Enter once you've completed the verification in the browser...")
            
            # Check if login was successful
            if "feed" in self.driver.current_url:
                self.logger.info("Successfully logged in to LinkedIn")
                
                # Save cookies for future use
                self.cookies = self.driver.get_cookies()
                with open("linkedin_cookies.json", "w") as f:
                    json.dump(self.cookies, f)
                
                return True
            else:
                self.logger.error("Failed to log in to LinkedIn")
                return False
                
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False

    def search_posts(self, topic, count=20):
        """Search for relevant LinkedIn posts on a specific topic"""
        try:
            self.logger.info(f"Searching for posts about: {topic}")
            
            # Navigate to LinkedIn search page
            search_url = f"https://www.linkedin.com/search/results/content/?keywords={topic.replace(' ', '%20')}&origin=GLOBAL_SEARCH_HEADER&sortBy=relevance"
            self.driver.get(search_url)
            
            # Wait for search results to load
            time.sleep(5)
            
            # Find post containers
            posts = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'feed-shared-update-v2')]")
            
            if not posts:
                self.logger.warning(f"No posts found for topic: {topic}")
                return []
                
            self.logger.info(f"Found {len(posts)} posts for topic: {topic}")
            
            # Extract posts data
            posts_data = []
            for post in posts[:min(count, len(posts))]:
                try:
                    # Extract post ID
                    post_id = post.get_attribute("data-urn")
                    
                    # Extract post text
                    post_text_element = post.find_elements(By.XPATH, ".//div[contains(@class, 'feed-shared-update-v2__description-wrapper')]//span")
                    post_text = " ".join([elem.text for elem in post_text_element]) if post_text_element else ""
                    
                    # Extract engagement stats
                    likes_element = post.find_elements(By.XPATH, ".//span[contains(@class, 'social-details-social-counts__reactions-count')]")
                    likes = int(likes_element[0].text.replace(',', '')) if likes_element else 0
                    
                    comments_element = post.find_elements(By.XPATH, ".//li[contains(@class, 'social-details-social-counts__comments')]//span")
                    comments = int(comments_element[0].text.replace(',', '')) if comments_element else 0
                    
                    # Extract author info
                    author_element = post.find_elements(By.XPATH, ".//span[contains(@class, 'feed-shared-actor__name')]")
                    author = author_element[0].text if author_element else "Unknown"
                    
                    # Extract post URL
                    post_url_element = post.find_elements(By.XPATH, ".//a[contains(@class, 'app-aware-link') and contains(@href, '/posts/')]")
                    post_url = post_url_element[0].get_attribute("href") if post_url_element else None
                    
                    # Add to posts data if it has good engagement
                    if likes > 10 or comments > 5:
                        posts_data.append({
                            "id": post_id,
                            "text": post_text,
                            "author": author,
                            "likes": likes,
                            "comments": comments,
                            "url": post_url
                        })
                        
                except Exception as e:
                    self.logger.error(f"Error extracting post data: {str(e)}")
                    continue
            
            self.logger.info(f"Extracted data for {len(posts_data)} relevant posts")
            return posts_data
            
        except Exception as e:
            self.logger.error(f"Error searching posts: {str(e)}")
            return []

    def generate_comment(self, post_content):
        """Generate a relevant comment based on the post content"""
        # Simple comment templates
        templates = [
            "Great insights on {topic}! This is definitely going to shape the future of the industry.",
            "I found this perspective on {topic} quite interesting. What are your thoughts?",
            "The innovations in {topic} mentioned here are truly game-changing for businesses.",
            "This is exactly the kind of advancement in {topic} that we need to be focusing on.",
            "Sharing this because it highlights important trends in {topic} that we should all be aware of.",
            "Fascinating development in {topic}. I'm curious to see how this evolves further.",
            "Important information for anyone working with {topic}.",
            "This approach to {topic} could revolutionize how we think about solutions in this space."
        ]
        
        # Extract topic from post or use default
        if not post_content or len(post_content) < 10:
            topic = random.choice(self.topics)
        else:
            # Use the first topic that appears in the content, or default
            topic = next((t for t in self.topics if t.lower() in post_content.lower()), random.choice(self.topics))
            
        comment = random.choice(templates).format(topic=topic)
        return comment

    def repost(self, post):
        """Repost a LinkedIn post with a comment"""
        try:
            post_url = post.get("url")
            if not post_url:
                self.logger.warning("Missing post URL, cannot repost")
                return False
                
            # Generate comment
            comment = self.generate_comment(post.get("text", ""))
            self.logger.info(f"Reposting content with comment: {comment[:50]}...")
            
            # Navigate to the post
            self.driver.get(post_url)
            time.sleep(5)
            
            # Click on share button
            share_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'share-button')]"))
            )
            share_button.click()
            time.sleep(2)
            
            # Click on "Repost" option
            repost_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'feed-shared-control-menu__item') and contains(., 'Repost')]"))
            )
            repost_button.click()
            time.sleep(2)
            
            # Add comment
            comment_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'editor-content')]"))
            )
            comment_field.send_keys(comment)
            time.sleep(2)
            
            # Click post button
            post_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'share-actions__primary-action')]"))
            )
            post_button.click()
            time.sleep(5)
            
            # Log the activity
            activity = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "repost",
                "post_url": post_url,
                "comment": comment,
                "success": True
            }
            
            self.daily_log.append(activity)
            self.posts_done_today += 1
            self.save_log()
            
            self.logger.info("Repost successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error reposting: {str(e)}")
            
            # Log the failed attempt
            activity = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "repost",
                "post_url": post.get("url", "unknown"),
                "error": str(e),
                "success": False
            }
            self.daily_log.append(activity)
            self.save_log()
            
            return False

    def save_log(self):
        """Save the daily activity log to a file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "posts_completed": self.posts_done_today,
                    "max_daily_posts": self.max_daily_posts,
                    "activities": self.daily_log
                }, f, indent=2)
            self.logger.info(f"Log saved to {self.log_file}")
        except Exception as e:
            self.logger.error(f"Error saving log: {str(e)}")

    def distribute_posting_times(self, start_hour=8, end_hour=20):
        """Create a schedule of posting times throughout the day"""
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        # Adjust for current time
        if current_hour < start_hour:
            start_hour = current_hour
        if current_hour > end_hour:
            # Too late in the day, schedule for tomorrow
            return []
            
        # Determine how many hours are left in the posting window
        hours_left = end_hour - max(current_hour, start_hour) + 1
        if hours_left <= 0:
            return []
            
        # Calculate posts per hour, minimum 1
        posts_left = min(self.max_daily_posts - self.posts_done_today, 15)
        if posts_left <= 0:
            return []
            
        posts_per_hour = max(1, min(posts_left // hours_left, 3))  # Cap at 3 posts per hour
        
        # Create schedule
        schedule = []
        for hour in range(max(current_hour, start_hour), end_hour + 1):
            # Skip current hour if we're more than 45 minutes into it
            if hour == current_hour and current_minute > 45:
                continue
                
            # Distribute evenly within the hour
            for i in range(min(posts_per_hour, posts_left)):
                if hour == current_hour:
                    # For current hour, schedule after current time
                    minute = random.randint(current_minute + 5, 59)
                else:
                    minute = random.randint(0, 59)
                
                schedule_time = now.replace(hour=hour, minute=minute, second=random.randint(0, 59))
                schedule.append(schedule_time)
                posts_left -= 1
                
                if posts_left <= 0:
                    break
            
            if posts_left <= 0:
                break
                
        # Sort by time
        schedule.sort()
        return schedule

    def run_daily_routine(self):
        """Execute the daily posting routine"""
        self.logger.info("Starting daily routine")
        
        # Reset daily counter if it's a new day
        current_date = datetime.now().strftime('%Y%m%d')
        if self.log_file != f"linkedin_activity_{current_date}.json":
            self.log_file = f"linkedin_activity_{current_date}.json"
            self.posts_done_today = 0
            self.daily_log = []
        
        # Login if not already
        if not self.driver:
            if not self.login():
                self.logger.error("Daily routine cancelled: Could not login")
                return

        # Schedule posts throughout the day
        posting_schedule = self.distribute_posting_times()
        self.logger.info(f"Created schedule for {len(posting_schedule)} posts today")
        
        for scheduled_time in posting_schedule:
            # Select a random topic
            topic = random.choice(self.topics)
            
            # Collect posts about this topic
            posts = self.search_posts(topic)
            
            if not posts:
                self.logger.warning(f"No posts found for topic: {topic}")
                continue
                
            # Select a post with good engagement
            selected_post = random.choice(posts[:min(5, len(posts))])
            
            # Schedule the repost
            delay_seconds = (scheduled_time - datetime.now()).total_seconds()
            if delay_seconds > 0:
                self.logger.info(f"Scheduled post for {scheduled_time.strftime('%H:%M:%S')} (in {delay_seconds/60:.1f} minutes)")
                time.sleep(delay_seconds)
            
            # Repost
            success = self.repost(selected_post)
            
            if success:
                self.logger.info(f"Posted {self.posts_done_today}/{self.max_daily_posts} for today")
            
            # If we've reached the daily limit, stop
            if self.posts_done_today >= self.max_daily_posts:
                self.logger.info(f"Reached daily posting limit of {self.max_daily_posts}")
                break
                
            # Small sleep to avoid rate limiting
            time.sleep(random.uniform(30, 60))

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

def main():
    # Initialize the bot with your credentials
    bot = LinkedInBot(
        email="ahmedelkilany.rouge@gmail.com",
        password="AGHK3684269",
        topics=[
            "agriculture technology innovation", 
            "agritech", 
            "sustainable agriculture", 
            "farming technology",
            "precision agriculture",
            "agricultural AI",
            "smart farming"
        ]
    )
    
    try:
        # Log in immediately
        if not bot.login():
            print("Failed to login. Please check the browser window to complete any security challenges.")
            return
        
        # Run once immediately
        bot.run_daily_routine()
        
        # Schedule to run every day at 8:00 AM
        schedule.every().day.at("08:00").do(bot.run_daily_routine)
        
        print("Bot is running. Press Ctrl+C to stop.")
        
        # Keep the script running
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    finally:
        bot.cleanup()

if __name__ == "__main__":
    main()
