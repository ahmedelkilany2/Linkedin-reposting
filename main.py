import time
import random
import datetime
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import schedule
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import json
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_bot.log"),
        logging.StreamHandler()
    ]
)

class LinkedInBot:
    def __init__(self, email, password, influencer_name):
        """Initialize the LinkedIn bot with credentials and influencer info."""
        self.email = email
        self.password = password
        self.influencer_name = influencer_name
        self.driver = None
        self.posts_today = 0
        self.max_posts_per_day = random.randint(10, 15)
        self.kol_accounts = []
        self.engagement_history = self._load_engagement_history()
        
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            nltk.download('vader_lexicon')
        
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
    def _load_engagement_history(self):
        """Load the engagement history from a JSON file."""
        try:
            if os.path.exists('engagement_history.json'):
                with open('engagement_history.json', 'r') as f:
                    return json.load(f)
            return {"posts": [], "daily_counts": {}}
        except Exception as e:
            logging.error(f"Error loading engagement history: {e}")
            return {"posts": [], "daily_counts": {}}
            
    def _save_engagement_history(self):
        """Save the engagement history to a JSON file."""
        try:
            with open('engagement_history.json', 'w') as f:
                json.dump(self.engagement_history, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving engagement history: {e}")
    
    def setup_browser(self):
        """Set up the browser with appropriate options."""
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)
        
    def login(self):
        """Log into LinkedIn."""
        try:
            logging.info("Logging into LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            username_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            password_field = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
            
            username_field.send_keys(self.email)
            password_field.send_keys(self.password)
            password_field.send_keys(Keys.RETURN)
            
            # Check if login was successful
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, "global-nav")))
                logging.info("Login successful")
                return True
            except TimeoutException:
                logging.error("Login failed - couldn't find navigation")
                return False
                
        except Exception as e:
            logging.error(f"Error during login: {e}")
            return False
            
    def load_kol_accounts(self, file_path):
        """Load KOL LinkedIn accounts from a CSV file."""
        try:
            df = pd.read_csv(file_path)
            self.kol_accounts = df['linkedin_url'].tolist()
            logging.info(f"Loaded {len(self.kol_accounts)} KOL accounts")
        except Exception as e:
            logging.error(f"Error loading KOL accounts: {e}")
            
    def add_kol_account(self, linkedin_url):
        """Add a KOL account to the list."""
        if linkedin_url not in self.kol_accounts:
            self.kol_accounts.append(linkedin_url)
            logging.info(f"Added KOL account: {linkedin_url}")
            
            # Save to CSV
            try:
                df = pd.DataFrame({'linkedin_url': self.kol_accounts})
                df.to_csv('kol_accounts.csv', index=False)
            except Exception as e:
                logging.error(f"Error saving KOL accounts: {e}")
    
    def generate_comment(self, post_text):
        """Generate a relevant comment based on the post content."""
        # Analyze sentiment
        sentiment = self.sentiment_analyzer.polarity_scores(post_text)
        
        # List of domain-specific templates for agriculture tech
        positive_templates = [
            "Great insights on agricultural innovation! This could transform how we approach {topic}.",
            "Really appreciate this perspective on {topic}. Sustainable agriculture is the future!",
            "This is exactly the kind of innovation we need in the agriculture sector. Looking forward to seeing more on {topic}.",
            "Fascinating development in {topic}! How do you see this scaling globally?",
            "This aligns perfectly with the sustainable agriculture goals we should all be working toward. {topic} is crucial."
        ]
        
        neutral_templates = [
            "Interesting points about {topic}. What are your thoughts on implementation challenges?",
            "This raises important questions about {topic} in agricultural technology.",
            "{topic} continues to be a central focus in agtech innovation. Worth following closely.",
            "Thanks for sharing these insights on {topic}. Looking forward to the discussion.",
            "The implications of {topic} for farmers could be significant. Worth considering all perspectives."
        ]
        
        negative_templates = [
            "While challenges exist with {topic}, I believe innovation will help overcome these obstacles.",
            "Important to address these concerns about {topic}. How might we turn these challenges into opportunities?",
            "This highlights some critical issues in {topic}. Collaboration will be key to finding solutions.",
            "These are valid concerns about {topic}. I'd add that looking at successful case studies might provide some answers.",
            "The difficulties with {topic} are real, but I remain optimistic about the potential of agtech solutions."
        ]
        
        # Topics relevant to agricultural technology
        topics = [
            "precision agriculture", 
            "sustainable farming", 
            "vertical farming", 
            "agricultural AI", 
            "farm automation",
            "irrigation technology",
            "crop monitoring systems",
            "agricultural robotics",
            "soil health management",
            "climate-smart agriculture"
        ]
        
        # Select template based on sentiment
        if sentiment['compound'] > 0.05:
            template = random.choice(positive_templates)
        elif sentiment['compound'] < -0.05:
            template = random.choice(negative_templates)
        else:
            template = random.choice(neutral_templates)
            
        # Try to extract relevant topics from the post text, or use random one
        topic = random.choice(topics)
        for t in topics:
            if t.lower() in post_text.lower():
                topic = t
                break
                
        # Format the template with the topic
        comment = template.format(topic=topic)
        
        return comment
        
    def find_and_repost_content(self):
        """Find relevant content from KOLs and repost with comments."""
        if self.posts_today >= self.max_posts_per_day:
            logging.info(f"Reached maximum posts for today ({self.max_posts_per_day})")
            return
            
        if not self.kol_accounts:
            logging.warning("No KOL accounts loaded. Cannot find content.")
            return
            
        # Choose a random KOL account
        kol_url = random.choice(self.kol_accounts)
        
        try:
            logging.info(f"Visiting KOL profile: {kol_url}")
            self.driver.get(kol_url)
            time.sleep(5)  # Wait for page to load
            
            # Scroll down to load more content
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 800)")
                time.sleep(1)
                
            # Find posts
            posts = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'feed-shared-update-v2')]")
            
            if not posts:
                logging.info("No posts found on this profile")
                return
                
            # Find a post we haven't reposted yet
            for post in posts:
                try:
                    # to get post ID or some unique identifier
                    post_id = post.get_attribute("data-urn") or post.get_attribute("id")
                    
                    # Check if we've already reposted this
                    if any(p['post_id'] == post_id for p in self.engagement_history['posts']):
                        continue
                        
                    # Get post text
                    try:
                        post_text = post.find_element(By.XPATH, ".//div[contains(@class, 'feed-shared-update-v2__description')]").text
                    except:
                        post_text = "No text found in this post"
                        
                    # Generate comment
                    comment = self.generate_comment(post_text)
                    
                    # Click share button
                    share_button = post.find_element(By.XPATH, ".//button[contains(@aria-label, 'repost')]")
                    share_button.click()
                    time.sleep(2)
                    
                    # Click "Add a thought" button
                    add_thought = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add a thought')]")))
                    add_thought.click()
                    time.sleep(1)
                    
                    # Enter comment
                    comment_field = self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']")))
                    comment_field.send_keys(comment)
                    time.sleep(1)
                    
                    # Click Post button
                    post_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Post')]")))
                    post_button.click()
                    
                    # Log the activity
                    logging.info(f"Reposted content with comment: {comment}")
                    
                    # Record in history
                    today = datetime.datetime.now().strftime("%Y-%m-%d")
                    self.engagement_history['posts'].append({
                        'post_id': post_id,
                        'kol_url': kol_url,
                        'comment': comment,
                        'date': today,
                        'time': datetime.datetime.now().strftime("%H:%M:%S")
                    })
                    
                    if today not in self.engagement_history['daily_counts']:
                        self.engagement_history['daily_counts'][today] = 0
                    self.engagement_history['daily_counts'][today] += 1
                    
                    self._save_engagement_history()
                    
                    self.posts_today += 1
                    return  # Successfully reposted
                    
                except Exception as e:
                    logging.error(f"Error reposting content: {e}")
                    continue
                    
            logging.info("No suitable posts found for reposting")
            
        except Exception as e:
            logging.error(f"Error in find_and_repost_content: {e}")
            
    def schedule_posts(self):
        """Schedule posts throughout the day."""
        # Reset counter for the day
        self.posts_today = 0
        self.max_posts_per_day = random.randint(10, 15)
        
        logging.info(f"Scheduling {self.max_posts_per_day} posts for today")
        
        # Business hours (9 AM to 6 PM)
        start_hour = 9
        end_hour = 18
        total_minutes = (end_hour - start_hour) * 60
        
        # Calculate posting intervals
        intervals = total_minutes // self.max_posts_per_day
        
        # Schedule posts
        for i in range(self.max_posts_per_day):
            # Calculate post time 
            minutes_offset = i * intervals + random.randint(-5, 5)
            post_time = datetime.time(
                hour=(start_hour + minutes_offset // 60) % 24,
                minute=minutes_offset % 60
            )
            
            # Schedule the post
            schedule.every().day.at(post_time.strftime("%H:%M")).do(self.find_and_repost_content)
            logging.info(f"Post #{i+1} scheduled for {post_time.strftime('%H:%M')}")
            
    def generate_report(self):
        """Generate a report of engagement activity."""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        report = {
            "date": today,
            "influencer_name": self.influencer_name,
            "posts_target": self.max_posts_per_day,
            "posts_completed": self.posts_today,
            "engagement_details": [
                post for post in self.engagement_history['posts'] 
                if post['date'] == today
            ]
        }
        
        # Save report to JSON
        try:
            with open(f"report_{today}.json", 'w') as f:
                json.dump(report, f, indent=4)
            logging.info(f"Report generated for {today}")
        except Exception as e:
            logging.error(f"Error generating report: {e}")
            
        return report
        
    def run(self):
        """Run the bot."""
        try:
            self.setup_browser()
            if not self.login():
                logging.error("Failed to login. Exiting.")
                return
                
            # Schedule posts for the day
            self.schedule_posts()
            
            # Schedule daily report generation
            schedule.every().day.at("19:00").do(self.generate_report)
            
            # Run the scheduler
            logging.info("Bot is now running. Press Ctrl+C to stop.")
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
        except Exception as e:
            logging.error(f"Error in bot execution: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                
    def close(self):
        """Close the browser and clean up."""
        if self.driver:
            self.driver.quit()
            logging.info("Browser closed")

# Example usage
if __name__ == "__main__":
    # Configuration
    influencers = [
        {
            "name": "Lisa Cheuk",
            "email": "lisa@gmail.com",
            "password": "password",
            "linkedin_url": "https://www.linkedin.com/in/"
        },
        {
            "name": "Morgana Lee",
            "email": "morgana@gmail.com",
            "password": "password",
            "linkedin_url": "https://www.linkedin.com/in/"
        }
    ]
    
    # Select which influencer to use
    selected_influencer = influencers[0]  # Change index to switch influencers
    
    # Initialize and run the bot
    bot = LinkedInBot(
        email=selected_influencer["email"],
        password=selected_influencer["password"],
        influencer_name=selected_influencer["name"]
    )
    
    # Load KOL accounts from file or add manually
    # bot.load_kol_accounts("kol_accounts.csv")
    
    # Add some example KOL accounts for agricultural technology
    example_kols = [
        
    ]
    
    for kol in example_kols:
        bot.add_kol_account(kol)
        
    # Run the bot
    bot.run()
