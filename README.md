# visa_rescheduler

**Automated US VISA (ais.usvisa-info.com) Appointment Re-Scheduler**

This script automates checking and rescheduling appointments for US visa applications via `ais.usvisa-info.com`.

---

## Features

- Automatically logs into your visa scheduling account.
- Searches for earlier appointment dates than your current one.
- Attempts to reschedule based on available dates and times.
- Logs all activity for debugging and tracking.
- Handles temporary bans by implementing cooldown periods to avoid detection.

---

## Prerequisites

1. **Existing US VISA Appointment**: Ensure you already have an appointment scheduled.
2. **Google Chrome**: Required for the automation.
3. **Python 3.x**: For running the script.
4. **Chromedriver**: Download the appropriate version for your system [here](https://sites.google.com/a/chromium.org/chromedriver/downloads).

    Update the path to your `chromedriver` in the script:
    ```python
    if LOCAL_USE:
        path_to_chromedriver = './chromedriver-mac-x64/chromedriver'
    ```

---

## Configuration

1. **Edit `config.ini`**  
   Fill out the details in the `config.ini` file:
   - **PERSONAL_INFO Section**:
     - `USERNAME`: Your account email for `ais.usvisa-info.com`.
     - `PASSWORD`: Your account password.
     - `SCHEDULE_ID`: Found in the URL of your appointment rescheduling page.
     - `MY_SCHEDULE_DATE`: Your current scheduled date (format: YYYY-MM-DD).
     - `YOUR_EMBASSY`: Your embassy's identifier from `embassy.py`.

   - **TIME Section**:
     - Customize retry times, work limits, and cooldown periods (values in hours or minutes).

2. **Install Dependencies**  
   Run:
   ```bash
   pip3 install -r requirements.txt
   ```

---

## Running the Script

1. Start the script:
   ```bash
   python3 visa.py
   ```
2. The script will:
   - Log into your account.
   - Check for earlier appointment dates periodically.
   - Reschedule automatically if a suitable date is found.
   - Log all actions in a daily log file (e.g., `log_YYYY-MM-DD.txt`).

---

## Logs

- Logs are saved in the format: `log_YYYY-MM-DD.txt`.
- Each log entry includes the time, request count, available dates, and any exceptions.

---

## Safety Notes

- The script includes safeguards to avoid overloading the visa website:
  - Implements cooldown periods after extended work sessions or temporary bans.
  - Randomizes retry intervals to mimic human behavior.
- Ensure compliance with local regulations and terms of service when using automation tools.

---

Happy scheduling! 😊