import time
import random
import datetime
import logging
import pandas as pd
import requests
import json
import os
import schedule
from urllib.parse import urlencode

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("linkedin_bot.log"),
        logging.StreamHandler()
    ]
)

class LinkedInAPIBot:
    def __init__(self, email, password, influencer_name):
        """Initialize the LinkedIn API bot with credentials and influencer info."""
        self.email = email
        self.password = password
        self.influencer_name = influencer_name
        self.posts_today = 0
        self.max_posts_per_day = 15  # 15 posts per day
        self.post_interval_minutes = 90  # Post every 90 minutes
        self.post_history = self._load_post_history()
        
        # LinkedIn API credentials (these need to be obtained from LinkedIn Developer Portal)
        self.client_id = "779reg5m69yf04"
        self.client_secret = "WPL_AP1.4aVvexvHlSYM3GlM.QR/ro"
        self.redirect_uri = "REDIRECT_URI"
        self.access_token = self._load_access_token()
        
        # AI Prompt Content for Posts
        self.ai_prompts = [
            {
                "title": "Write Code",
                "content": """Claude Sonnet 3.7 is the most powerful AI coding assistant.

<role>You are a seasoned programmer.</role>
<context>Write efficient and well-structured code in [PROGRAMMING LANGUAGE] to [PERFORM ACTION].</context>
<steps> 
1. Implement the necessary logic and algorithms.
2. Optimize for performance and readability.
3. Document the code for future reference and maintenance.</steps>"""
            },
            {
                "title": "Debug Code",
                "content": """Debug your code more efficiently with Claude 3.7 Sonnet!

Use this prompt to identify and fix bugs quickly:

<role>You are a debugging expert with over 20 years of experience.</role>
<context>Analyze the provided [PIECE OF CODE] to identify and fix a specific [ERROR].</context>
<steps> 
1. Step through the code to diagnose the issue.
2. Propose a solution to fix the error.
3. Suggest optimizations for performance and readability.</steps>"""
            },
            {
                "title": "Code Review",
                "content": """Get expert code reviews with Claude 3.7 Sonnet using this prompt:

<role>You are a senior software engineer with expertise in code reviews.</role>
<context>Review the following [CODE] for best practices, potential bugs, and improvements.</context>
<steps>
1. Analyze the code structure and organization.
2. Identify potential bugs, edge cases, or performance issues.
3. Suggest improvements following industry best practices.
4. Provide examples of refactored code where applicable.</steps>"""
            },
            {
                "title": "Generate Test Cases",
                "content": """Create comprehensive test cases with Claude 3.7 Sonnet:

<role>You are a QA engineer specializing in test case design.</role>
<context>Create test cases for [FUNCTION/APPLICATION] to ensure it works correctly.</context>
<steps>
1. Identify the key functionality to test.
2. Design test cases covering normal usage, edge cases, and error conditions.
3. Include expected outputs for each test case.
4. Suggest testing frameworks and methodologies appropriate for the task.</steps>"""
            },
            {
                "title": "System Design",
                "content": """Design robust systems with Claude 3.7 Sonnet:

<role>You are a system architect with extensive experience in designing scalable systems.</role>
<context>Design a system architecture for [PROJECT/APPLICATION] that needs to handle [REQUIREMENTS].</context>
<steps>
1. Outline the high-level components and their interactions.
2. Specify technologies and frameworks for each component.
3. Address scalability, reliability, and security considerations.
4. Discuss potential bottlenecks and mitigation strategies.</steps>"""
            },
            {
                "title": "Algorithm Design",
                "content": """Create efficient algorithms with Claude 3.7 Sonnet:

<role>You are an algorithm specialist with deep knowledge of data structures and algorithms.</role>
<context>Design an efficient algorithm to solve [PROBLEM] with [CONSTRAINTS].</context>
<steps>
1. Analyze the problem requirements and constraints.
2. Develop a step-by-step algorithm with pseudocode.
3. Analyze time and space complexity.
4. Discuss tradeoffs and alternative approaches.</steps>"""
            },
            {
                "title": "Code Documentation",
                "content": """Generate comprehensive documentation with Claude 3.7 Sonnet:

<role>You are a technical writer specializing in code documentation.</role>
<context>Create clear and comprehensive documentation for [CODE/PROJECT].</context>
<steps>
1. Explain the purpose and functionality of the code.
2. Document functions, classes, and important variables.
3. Include usage examples and edge cases.
4. Format the documentation according to industry standards.</steps>"""
            },
            {
                "title": "API Integration",
                "content": """Master API integrations with Claude 3.7 Sonnet:

<role>You are an integration specialist with expertise in API implementations.</role>
<context>Provide guidance on integrating [API NAME] into [APPLICATION/SERVICE].</context>
<steps>
1. Outline the authentication and authorization process.
2. Detail the key endpoints and their parameters.
3. Provide code examples for common operations.
4. Discuss error handling and rate limiting considerations.</steps>"""
            },
            {
                "title": "Database Optimization",
                "content": """Optimize your database with Claude 3.7 Sonnet:

<role>You are a database administrator with extensive performance tuning experience.</role>
<context>Optimize [DATABASE TYPE] for [SPECIFIC WORKLOAD/APPLICATION].</context>
<steps>
1. Analyze current database structure and queries.
2. Identify bottlenecks and performance issues.
3. Suggest indexing strategies and query optimizations.
4. Recommend scaling and partitioning approaches.</steps>"""
            },
            {
                "title": "DevOps Automation",
                "content": """Automate your DevOps workflow with Claude 3.7 Sonnet:

<role>You are a DevOps engineer specializing in automation.</role>
<context>Create a CI/CD pipeline for [PROJECT TYPE] using [TOOLS/SERVICES].</context>
<steps>
1. Design the pipeline stages from commit to deployment.
2. Configure automated testing and quality checks.
3. Implement deployment strategies (blue/green, canary, etc.).
4. Set up monitoring and alerting.</steps>"""
            },
            {
                "title": "Security Assessment",
                "content": """Enhance your application security with Claude 3.7 Sonnet:

<role>You are a cybersecurity expert specializing in application security.</role>
<context>Perform a security assessment for [APPLICATION TYPE] to identify vulnerabilities.</context>
<steps>
1. Identify potential attack vectors and security risks.
2. Evaluate authentication and authorization mechanisms.
3. Assess data protection and encryption practices.
4. Recommend security improvements and mitigations.</steps>"""
            },
            {
                "title": "UI/UX Design",
                "content": """Create better user experiences with Claude 3.7 Sonnet:

<role>You are a UX designer with expertise in creating intuitive interfaces.</role>
<context>Design a user interface for [FEATURE/APPLICATION] that meets [USER NEEDS].</context>
<steps>
1. Define user personas and journey maps.
2. Create wireframes and interaction flows.
3. Apply design principles and accessibility guidelines.
4. Prepare for usability testing and iteration.</steps>"""
            },
            {
                "title": "Performance Optimization",
                "content": """Optimize application performance with Claude 3.7 Sonnet:

<role>You are a performance engineer with expertise in optimizing applications.</role>
<context>Improve the performance of [APPLICATION] that is experiencing [ISSUE].</context>
<steps>
1. Profile and identify performance bottlenecks.
2. Implement code-level optimizations.
3. Enhance resource utilization and caching strategies.
4. Measure improvements and establish performance baselines.</steps>"""
            },
            {
                "title": "Machine Learning Integration",
                "content": """Integrate ML models with Claude 3.7 Sonnet:

<role>You are a machine learning engineer specializing in model deployment.</role>
<context>Integrate a [MODEL TYPE] model into [APPLICATION/SERVICE].</context>
<steps>
1. Prepare the model for production deployment.
2. Design the integration architecture and API.
3. Implement inference and prediction workflows.
4. Set up monitoring and retraining processes.</steps>"""
            },
            {
                "title": "Code Migration",
                "content": """Migrate your codebase with Claude 3.7 Sonnet:

<role>You are a software architect specializing in code migration projects.</role>
<context>Migrate [EXISTING SYSTEM] from [OLD TECHNOLOGY] to [NEW TECHNOLOGY].</context>
<steps>
1. Assess the current codebase and dependencies.
2. Design the target architecture and migration strategy.
3. Implement incremental migration steps.
4. Verify functionality and performance in the new environment.</steps>"""
            }
        ]
        
    def _load_post_history(self):
        """Load the post history from a JSON file."""
        try:
            if os.path.exists('post_history.json'):
                with open('post_history.json', 'r') as f:
                    return json.load(f)
            return {"posts": [], "daily_counts": {}}
        except Exception as e:
            logging.error(f"Error loading post history: {e}")
            return {"posts": [], "daily_counts": {}}
            
    def _save_post_history(self):
        """Save the post history to a JSON file."""
        try:
            with open('post_history.json', 'w') as f:
                json.dump(self.post_history, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving post history: {e}")
            
    def _load_access_token(self):
        """Load the access token from a file or get a new one."""
        try:
            if os.path.exists('linkedin_token.json'):
                with open('linkedin_token.json', 'r') as f:
                    token_data = json.load(f)
                    if 'expires_at' in token_data and token_data['expires_at'] > datetime.datetime.now().timestamp():
                        return token_data['access_token']
        except Exception as e:
            logging.error(f"Error loading access token: {e}")
        
        # If we get here, we need a new token
        return self._get_new_access_token()
        
    def _get_new_access_token(self):
        """Get a new access token from LinkedIn's OAuth flow."""
        # NOTE: This is a simplified version. In a real application, We would need to:
        # 1. Redirect the user to LinkedIn's authorization page
        # 2. Get the authorization code from the callback
        # 3. Exchange the authorization code for an access token
        
        logging.warning("This function requires manual steps to get an access token from LinkedIn")
        logging.warning("Please visit: https://www.linkedin.com/developers/apps and follow the OAuth flow")
        
        # In a production environment, We would implement the full OAuth flow
        # For now, we'll just prompt for manual entry
        token = input("Please enter your LinkedIn API access token: ")
        
        # Save the token with an expiration time (usually 60 days for LinkedIn)
        expires_at = datetime.datetime.now().timestamp() + (60 * 24 * 60 * 60)  # 60 days in seconds
        token_data = {
            "access_token": token,
            "expires_at": expires_at
        }
        
        with open('linkedin_token.json', 'w') as f:
            json.dump(token_data, f, indent=4)
            
        return token
        
    def create_post(self, text):
        """Create a post on LinkedIn using the API."""
        try:
            url = "https://api.linkedin.com/v2/ugcPosts"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Get the person URN (requires a profile API call)
            person_url = "https://api.linkedin.com/v2/me"
            person_response = requests.get(person_url, headers=headers)
            
            if person_response.status_code != 200:
                logging.error(f"Failed to get profile data: {person_response.text}")
                return False
                
            person_data = person_response.json()
            person_urn = f"urn:li:person:{person_data['id']}"
            
            # Prepare the post data
            post_data = {
                "author": person_urn,
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
            
            response = requests.post(url, headers=headers, json=post_data)
            
            if response.status_code == 201:
                logging.info("Post created successfully!")
                return True
            else:
                logging.error(f"Failed to create post: {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Error creating post: {e}")
            return False
            
    def post_ai_prompt(self):
        """Post one of the AI prompting techniques."""
        if self.posts_today >= self.max_posts_per_day:
            logging.info(f"Reached maximum posts for today ({self.max_posts_per_day})")
            return
            
        # Choose a random AI prompt that hasn't been posted today
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        posted_today = [post['title'] for post in self.post_history['posts'] if post['date'] == today]
        
        available_prompts = [prompt for prompt in self.ai_prompts if prompt['title'] not in posted_today]
        
        if not available_prompts:
            # If all prompts have been used today, allow reusing prompts
            logging.info("All prompts have been posted today, selecting from all available prompts")
            available_prompts = self.ai_prompts
            
        selected_prompt = random.choice(available_prompts)
        
        # Create the post
        success = self.create_post(selected_prompt['content'])
        
        if success:
            # Record in history
            self.post_history['posts'].append({
                'title': selected_prompt['title'],
                'date': today,
                'time': datetime.datetime.now().strftime("%H:%M:%S")
            })
            
            if today not in self.post_history['daily_counts']:
                self.post_history['daily_counts'][today] = 0
            self.post_history['daily_counts'][today] += 1
            
            self._save_post_history()
            
            self.posts_today += 1
            logging.info(f"Posted content about: {selected_prompt['title']} ({self.posts_today}/{self.max_posts_per_day})")
        else:
            logging.error(f"Failed to post content about: {selected_prompt['title']}")
            
    def schedule_posts(self):
        """Schedule posts throughout the day at 90-minute intervals."""
        # Reset counter for the day
        self.posts_today = 0
        
        logging.info(f"Scheduling {self.max_posts_per_day} posts for today, every {self.post_interval_minutes} minutes")
        
        # Business hours (8 AM to 10 PM to accommodate 15 posts with 90-min intervals)
        start_hour = 8
        start_minute = 0
        
        # Schedule each post at fixed 90-minute intervals
        for i in range(self.max_posts_per_day):
            # Calculate post time 
            total_minutes = start_minute + (i * self.post_interval_minutes)
            hour_offset = total_minutes // 60
            minute_offset = total_minutes % 60
            
            post_time = datetime.time(
                hour=(start_hour + hour_offset) % 24,
                minute=minute_offset
            )
            
            # Schedule the post
            schedule.every().day.at(post_time.strftime("%H:%M")).do(self.post_ai_prompt)
            logging.info(f"Post #{i+1} scheduled for {post_time.strftime('%H:%M')}")
            
    def generate_report(self):
        """Generate a report of posting activity."""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        report = {
            "date": today,
            "influencer_name": self.influencer_name,
            "posts_target": self.max_posts_per_day,
            "posts_completed": self.posts_today,
            "post_details": [
                post for post in self.post_history['posts'] 
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
            logging.info("Starting LinkedIn API Bot")
            
            # Verify we have a valid access token
            if not self.access_token:
                logging.error("No valid access token available. Please authenticate first.")
                return
                
            # Schedule posts for the day
            self.schedule_posts()
            
            # Schedule daily report generation
            schedule.every().day.at("22:30").do(self.generate_report)
            
            # Run the scheduler
            logging.info("Bot is now running. Press Ctrl+C to stop.")
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
        except Exception as e:
            logging.error(f"Error in bot execution: {e}")

# Example usage
if __name__ == "__main__":
    # Configuration
    influencers = [
        {
            "name": "Ahmed Tamer",
            "email": "ahmedelkilany.rouge@gmail.com",
            "password": "AGHK3684269",
            "linkedin_url": "https://www.linkedin.com/in/ahmed-tamer-509353360"
        }
    ]
    
    # Select which influencer to use
    selected_influencer = influencers[0]
    
    # Initialize and run the bot
    bot = LinkedInAPIBot(
        email=selected_influencer["email"],
        password=selected_influencer["password"],
        influencer_name=selected_influencer["name"]
    )
    
    # Run the bot
    bot.run()
