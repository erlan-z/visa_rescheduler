import time
import json
import random
import requests
import configparser
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from embassy import *

config = configparser.ConfigParser()
config.read('config.ini')

# Personal Info:
# Account and current appointment info from https://ais.usvisa-info.com
USERNAME = config['PERSONAL_INFO']['USERNAME']
PASSWORD = config['PERSONAL_INFO']['PASSWORD']
# Find SCHEDULE_ID in re-schedule page link:
# https://ais.usvisa-info.com/en-am/niv/schedule/{SCHEDULE_ID}/appointment
SCHEDULE_ID = config['PERSONAL_INFO']['SCHEDULE_ID']
# Target Period:
MY_SCHEDULE_DATE = config['PERSONAL_INFO']['MY_SCHEDULE_DATE']
# Embassy Section:
YOUR_EMBASSY = config['PERSONAL_INFO']['YOUR_EMBASSY'] 
EMBASSY = Embassies[YOUR_EMBASSY][0]
FACILITY_ID = Embassies[YOUR_EMBASSY][1]
REGEX_CONTINUE = Embassies[YOUR_EMBASSY][2]

# Time Section:
minute = 60
# Time between steps (interactions with forms)
STEP_TIME = 2

# Time between retries/checks for available dates (seconds)
RETRY_TIME_L_BOUND = timedelta(minutes=config['TIME'].getfloat('RETRY_TIME_L_BOUND'))
RETRY_TIME_U_BOUND = timedelta(minutes=config['TIME'].getfloat('RETRY_TIME_U_BOUND'))

# Cooling down after WORK_LIMIT_TIME hours of work (Avoiding Ban)
WORK_LIMIT_TIME = timedelta(hours=config['TIME'].getfloat('WORK_LIMIT_TIME'))
WORK_COOLDOWN_TIME =timedelta(hours=config['TIME'].getfloat('WORK_COOLDOWN_TIME')) 
EXCEPTION_TIME = timedelta(minutes=30) # wait time when an exception occurs: 30 minutes
BAN_COOLDOWN_TIME = timedelta(hours=config['TIME'].getfloat('BAN_COOLDOWN_TIME'))  # Temporary Banned (empty list): wait COOLDOWN_TIME hours


SIGN_IN_LINK = f"https://ais.usvisa-info.com/{EMBASSY}/niv/users/sign_in"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment"
DATE_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"
SIGN_OUT_LINK = f"https://ais.usvisa-info.com/{EMBASSY}/niv/users/sign_out"

JS_SCRIPT = ("var req = new XMLHttpRequest();"
             f"req.open('GET', '%s', false);"
             "req.setRequestHeader('Accept', 'application/json, text/javascript, */*; q=0.01');"
             "req.setRequestHeader('X-Requested-With', 'XMLHttpRequest');"
             f"req.setRequestHeader('Cookie', '_yatri_session=%s');"
             "req.send(null);"
             "return req.responseText;")


def auto_action(label, find_by, el_type, action, value, sleep_time=0):
    print(f"\t{label}:", end="")
    item = None

    # Refactored to use if-elif statements for broader compatibility
    find_by = find_by.lower()
    if find_by == 'id':
        item = driver.find_element(By.ID, el_type)
    elif find_by == 'name':
        item = driver.find_element(By.NAME, el_type)
    elif find_by == 'class':
        item = driver.find_element(By.CLASS_NAME, el_type)
    elif find_by == 'xpath':
        item = driver.find_element(By.XPATH, el_type)
    else:
        return 0  # Early exit if none of the conditions match

    # Perform the action
    action = action.lower()
    if action == 'send':
        item.send_keys(value)
    elif action == 'click':
        item.click()
    else:
        return 0  # Early exit if action is not recognized

    print("\t\tCheck!")
    if sleep_time:
        time.sleep(sleep_time)



def start_process():
    # Bypass reCAPTCHA
    driver.get(SIGN_IN_LINK)
    time.sleep(STEP_TIME)

    auto_action("Click bounce", "xpath", '//a[@class="down-arrow bounce"]', "click", "", STEP_TIME)
    auto_action("Click smth", "xpath", '//*[@id="header"]/nav/div[1]/div[1]/div[2]/div[1]/ul/li[3]/a', "click", "", STEP_TIME)    
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))
    auto_action("Click bounce", "xpath", '//a[@class="down-arrow bounce"]', "click", "", STEP_TIME)

    print("Login start...")
    auto_action("Email", "id", "user_email", "send", USERNAME, STEP_TIME)
    auto_action("Password", "id", "user_password", "send", PASSWORD, STEP_TIME)
    auto_action("Privacy", "class", "icheckbox", "click", "", STEP_TIME)
    auto_action("Enter Panel", "name", "commit", "click", "", STEP_TIME)

    REGEX_CONTINUE = "//a[contains(text(),'Continue')]"
    Wait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))
    # Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), '" + REGEX_CONTINUE + "')]")))
    print("\n\tlogin successful!\n")

def reschedule(date):
    try:
        time = get_time(date)
        if not time:
            return  ["ERROR", "No time availble :("]
        driver.get(APPOINTMENT_URL)
        
        headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": APPOINTMENT_URL,
            "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
        }
        
        data = {
            # "utf8": driver.find_element(by=By.NAME, value='utf8').get_attribute('value'),
            "authenticity_token": driver.find_element(by=By.NAME, value='authenticity_token').get_attribute('value'),
            "confirmed_limit_message": driver.find_element(by=By.NAME, value='confirmed_limit_message').get_attribute('value'),
            "use_consulate_appointment_capacity": driver.find_element(by=By.NAME, value='use_consulate_appointment_capacity').get_attribute('value'),
            "appointments[consulate_appointment][facility_id]": FACILITY_ID,
            "appointments[consulate_appointment][date]": date,
            "appointments[consulate_appointment][time]": time,
        }
        
        r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
        print(r.status_code)
        if str(r.status_code).startswith("2"):
            title = "SUCCESS"
            msg = f"Rescheduled Successfully! {date} {time}"
        else:
            title = "FAIL"
            msg = f"Reschedule Failed!!! {date} {time}"
    
    except (requests.exceptions.RequestException, 
            exceptions.NoSuchElementException,
            exceptions.WebDriverException) as e:
        title = "ERROR"
        msg = f"An error occurred: {str(e)}"
    
    except Exception as e:
        title = "UNKNOWN ERROR"
        msg = f"An unexpected error occurred: {str(e)}"
    
    return [title, msg]



def get_date():
    # Requesting to get the whole available dates
    try:
        session = driver.get_cookie("_yatri_session")["value"]
        script = JS_SCRIPT % (str(DATE_URL), session)
        content = driver.execute_script(script)
        
        if content:
            return json.loads(content)
    except Exception as e:
        print(f"An error occurred: {e}")
        
    return None

def get_time(date):
    time_url = TIME_URL % date
    session = driver.get_cookie("_yatri_session")["value"]
    script = JS_SCRIPT % (str(time_url), session)
    content = driver.execute_script(script)
    data = json.loads(content)

    time = data.get("available_times")
    if len(time) != 0:
        print(f"Got time successfully! {date} {time[-1]}")
        return time[-1]
    else:
        print(f"No time availables for this {date} : {time}")
        return None


def is_logged_in():
    content = driver.page_source
    if(content.find("error") != -1):
        return False
    return True


def get_available_date(dates):
   
    def is_earlier(date):
        my_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
        new_date = datetime.strptime(date, "%Y-%m-%d")
        result = my_date > new_date
        return result
        

    second_date = None
    print("Checking for an earlier date:")
    for d in dates:
        date = d.get('date')
        if is_earlier(date):
            if second_date:
                return date
            second_date = date
        else:
            print(f'This {second_date} date is returned')
            return second_date

def info_logger(file_path, log):
    # file_path: e.g. "log.txt"
    with open(file_path, "a") as file:
        file.write(str(datetime.now().time()) + ":\n" + log + "\n")


path_to_chromedriver = './chromedriver-mac-x64/chromedriver'  
driver = webdriver.Chrome(service=Service(executable_path=path_to_chromedriver))

if __name__ == "__main__":
    first_loop = True
    while 1:
        LOG_FILE_NAME = "log_" + str(datetime.now().date()) + ".txt"
        if first_loop:
            t0 = time.time()
            total_time = 0
            Req_count = 0
            start_process()
            first_loop = False
        Req_count += 1
        try:
            msg = "-" * 60 + f"\nRequest count: {Req_count}, Log time: {datetime.today()}\n"
            print(msg)
            info_logger(LOG_FILE_NAME, msg)
            dates = get_date()
            if not dates:
                # Ban Situation
                msg = f"List is empty, Probabely banned!\n\tSleep for {BAN_COOLDOWN_TIME.seconds/60/60} hours!\n"
                print(msg)
                info_logger(LOG_FILE_NAME, msg)
                driver.get(SIGN_OUT_LINK)
                time.sleep(BAN_COOLDOWN_TIME.seconds )
                first_loop = True
            else:
               
                date = get_available_date(dates)
                if date:
                    END_MSG_TITLE, msg = reschedule(date)
                    break

                # Print Available dates:
                msg = ""
                for d in dates[:4]:
                    msg = msg + "%s" % (d.get('date')) + ", "
                msg = "Available dates:\n"+ msg
                print(msg)
                info_logger(LOG_FILE_NAME, msg)
            

                print(f"\n\nNo available dates before ({MY_SCHEDULE_DATE})!")
                RETRY_WAIT_TIME = random.randint(RETRY_TIME_L_BOUND.seconds, RETRY_TIME_U_BOUND.seconds)
                t1 = time.time()
                total_time = t1 - t0
                msg = "\nWorking Time:  ~ {:.2f} minutes".format(total_time/minute)
                print(msg)
                info_logger(LOG_FILE_NAME, msg)
                if total_time > WORK_LIMIT_TIME.seconds:
                    # Let program rest a little
                    print("break time")
                    driver.get(SIGN_OUT_LINK)
                    time.sleep(WORK_COOLDOWN_TIME.seconds)
                    first_loop = True
                else:
                    msg = "Retry Wait Time: "+ str(RETRY_WAIT_TIME/60)+ " minutes"
                    print(msg)
                    info_logger(LOG_FILE_NAME, msg)
                    time.sleep(RETRY_WAIT_TIME)
        except:
            # Exception Occured
            msg = f"exception OCCURED!\n"
            Req_count +=1
            time.sleep(EXCEPTION_TIME.seconds)

print(msg)
info_logger(LOG_FILE_NAME, msg)
driver.get(SIGN_OUT_LINK)
driver.stop_client()
driver.quit()