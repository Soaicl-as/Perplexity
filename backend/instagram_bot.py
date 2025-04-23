import time
import random
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class InstagramBot:
    def __init__(self, headless=True):
        self.logger = logging.getLogger('instagram_bot')
        self.driver = None
        self.headless = headless
        self.is_logged_in = False
        self.setup_driver()
        
    def setup_driver(self):
        """Initialize the Selenium webdriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)
        self.logger.info("Webdriver initialized")
        
    def login(self, username, password):
        """Login to Instagram"""
        self.logger.info(f"Attempting to log in as {username}")
        try:
            self.driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(3)  # Wait for the page to load
            
            # Accept cookies if prompted
            try:
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow')]"))
                )
                cookie_button.click()
                time.sleep(2)
            except:
                self.logger.info("No cookie consent prompt found or already accepted")
            
            # Enter username
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
            )
            username_field.clear()
            username_field.send_keys(username)
            
            # Enter password
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[name='password']")
            password_field.clear()
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Check for security verification
            time.sleep(5)
            if "suspicious_login" in self.driver.current_url or "challenge" in self.driver.current_url:
                self.logger.warning("Security verification required")
                return {"status": "verification_required"}
            
            # Check if login was successful
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: "login" not in driver.current_url
                )
                self.is_logged_in = True
                self.logger.info("Successfully logged in")
                return {"status": "success"}
            except TimeoutException:
                # Check for error messages
                try:
                    error_message = self.driver.find_element(By.ID, "slfErrorAlert").text
                    self.logger.error(f"Login failed: {error_message}")
                    return {"status": "error", "message": error_message}
                except:
                    self.logger.error("Login failed: Unknown error")
                    return {"status": "error", "message": "Unknown login error"}
                
        except Exception as e:
            self.logger.error(f"Exception during login: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_user_followers(self, username, max_count=100):
        """Extract followers of a given username"""
        if not self.is_logged_in:
            self.logger.error("Not logged in. Cannot get followers.")
            return {"status": "error", "message": "Not logged in"}
        
        try:
            # Navigate to user's profile
            self.driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(3)
            
            # Click on followers link
            followers_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/followers')]")
            followers_count = followers_link.text.replace("followers", "").strip()
            followers_link.click()
            
            self.logger.info(f"Extracting up to {max_count} followers from {username} (total: {followers_count})")
            
            # Wait for the followers modal to appear
            followers_modal = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
            )
            
            # Extract usernames through scrolling
            followers = self._extract_users_from_modal(followers_modal, max_count)
            
            self.logger.info(f"Extracted {len(followers)} followers")
            return {"status": "success", "followers": followers}
        
        except Exception as e:
            self.logger.error(f"Error getting followers: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_user_following(self, username, max_count=100):
        """Extract following of a given username"""
        if not self.is_logged_in:
            self.logger.error("Not logged in. Cannot get following.")
            return {"status": "error", "message": "Not logged in"}
        
        try:
            # Navigate to user's profile
            self.driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(3)
            
            # Click on following link
            following_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/following')]")
            following_count = following_link.text.replace("following", "").strip()
            following_link.click()
            
            self.logger.info(f"Extracting up to {max_count} following from {username} (total: {following_count})")
            
            # Wait for the following modal to appear
            following_modal = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
            )
            
            # Extract usernames through scrolling
            following = self._extract_users_from_modal(following_modal, max_count)
            
            self.logger.info(f"Extracted {len(following)} following")
            return {"status": "success", "following": following}
        
        except Exception as e:
            self.logger.error(f"Error getting following: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    def _extract_users_from_modal(self, modal, max_count):
        """Helper method to extract usernames from a modal through scrolling"""
        user_elements = []
        previous_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 30
        
        while len(user_elements) < max_count and scroll_attempts < max_scroll_attempts:
            # Find all username elements
            user_elements = modal.find_elements(By.XPATH, ".//a[contains(@href, '/')]")
            
            # If no new users were loaded after scrolling, break
            if len(user_elements) == previous_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
            
            previous_count = len(user_elements)
            
            # Scroll down in the modal
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", 
                modal
            )
            time.sleep(2)
        
        # Extract usernames
        usernames = []
        for element in user_elements[:max_count]:
            try:
                username = element.get_attribute("href").split("/")[-2]
                if username and username != "":
                    usernames.append(username)
            except:
                continue
                
        return usernames
    
    def send_dm(self, username, message):
        """Send a direct message to a specific user"""
        if not self.is_logged_in:
            self.logger.error("Not logged in. Cannot send DM.")
            return {"status": "error", "message": "Not logged in"}
        
        try:
            # Go to the user's profile
            self.driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(3)
            
            # Check if the user exists
            if "Page Not Found" in self.driver.title or "Sorry, this page isn't available" in self.driver.page_source:
                self.logger.warning(f"User {username} not found")
                return {"status": "error", "message": f"User {username} not found"}
            
            # Click on message button
            try:
                message_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Message') or contains(text(), 'Send Message')]"))
                )
                message_button.click()
                time.sleep(3)
            except TimeoutException:
                self.logger.warning(f"Could not find message button for {username}")
                return {"status": "error", "message": f"Could not find message button for {username}"}
            
            # Find message input field and send message
            try:
                message_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']"))
                )
                message_input.click()
                time.sleep(1)
                message_input.send_keys(message)
                time.sleep(2)
                
                # Click send button
                send_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Send')]")
                send_button.click()
                time.sleep(2)
                
                self.logger.info(f"Message sent to {username}")
                return {"status": "success", "message": f"Message sent to {username}"}
            except Exception as e:
                self.logger.error(f"Error sending message to {username}: {str(e)}")
                return {"status": "error", "message": f"Error sending message: {str(e)}"}
                
        except Exception as e:
            self.logger.error(f"Error sending DM to {username}: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def mass_dm(self, usernames, message, delay_range=(30, 60), progress_callback=None):
        """Send DMs to multiple users with random delays"""
        if not self.is_logged_in:
            self.logger.error("Not logged in. Cannot send mass DMs.")
            return {"status": "error", "message": "Not logged in"}
        
        results = {"successful": [], "failed": []}
        
        for i, username in enumerate(usernames):
            # Send progress update
            if progress_callback:
                progress_callback({
                    "current": i + 1, 
                    "total": len(usernames),
                    "username": username,
                    "status": "sending"
                })
            
            # Send the DM
            result = self.send_dm(username, message)
            
            if result["status"] == "success":
                results["successful"].append(username)
                if progress_callback:
                    progress_callback({
                        "current": i + 1, 
                        "total": len(usernames),
                        "username": username,
                        "status": "success"
                    })
            else:
                results["failed"].append({"username": username, "reason": result["message"]})
                if progress_callback:
                    progress_callback({
                        "current": i + 1, 
                        "total": len(usernames),
                        "username": username,
                        "status": "failed",
                        "reason": result["message"]
                    })
            
            # Add random delay between messages
            if i < len(usernames) - 1:  # No need to wait after the last message
                delay = random.uniform(delay_range[0], delay_range[1])
                self.logger.info(f"Waiting {delay:.2f} seconds before sending next message")
                if progress_callback:
                    progress_callback({
                        "current": i + 1, 
                        "total": len(usernames),
                        "status": "waiting",
                        "delay": delay
                    })
                time.sleep(delay)
        
        return {
            "status": "complete",
            "summary": {
                "total": len(usernames),
                "successful": len(results["successful"]),
                "failed": len(results["failed"])
            },
            "details": results
        }
    
    def close(self):
        """Close the webdriver"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Webdriver closed")
            self.driver = None
            self.is_logged_in = False
