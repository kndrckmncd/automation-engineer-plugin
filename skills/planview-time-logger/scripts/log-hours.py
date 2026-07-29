import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
Planview Time Logger
====================
Logs hours to the Planview timesheet for a given period.

Usage:
    python log-hours.py --config config.json [--dry-run]

Config JSON schema:
{
  "period": "7/4/2026",          // period start date shown on Select Period page
  "resource_code": "128447",     // from Planview URL
  "default_work": {              // used when no specific work is given per day
    "gl_code": "EC10010145",     // Related GL Code from Jira Epic (customfield_25042)
    "assignment": "(CapEx) Analysis"
  },
  "works": [
    {
      "gl_code": "EC10010145",   // matches Planview project name containing this code
      "assignment": "(CapEx) Analysis",
      "hours": {                 // day name -> hours (0 to skip)
        "Mon": 7.5,
        "Tue": 7.5,
        "Wed": 7.5,
        "Thu": 7.5,
        "Fri": 7.5
      }
    }
  ],
  "out_of_office": [],           // e.g. ["Mon", "Fri"] - skips those days entirely
  "sign_and_submit": false       // set true to sign after logging
}

Day numbers in Planview cell IDs:
  Sun=1, Mon=2, Tue=3, Wed=4, Thu=5, Fri=6, Sat=7
"""

import argparse
import json
import sys
import time
import re
from pathlib import Path
from dotenv import load_dotenv

# --- .env loading ---
def _load_env():
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=False)
            break

_load_env()

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Day name -> Planview day number
DAY_NUMBERS = {"Sun": 1, "Mon": 2, "Tue": 3, "Wed": 4, "Thu": 5, "Fri": 6, "Sat": 7}

BASE_URL = "https://mlcdndiv.pvcloud.com/planview"


def make_driver():
    opts = Options()
    opts.add_argument(r"--user-data-dir=C:\Temp\edge_tmp")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--start-maximized")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    return webdriver.Edge(options=opts)


def wait_for_page(driver, expected_title_fragment, timeout=20):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: expected_title_fragment.lower() in d.title.lower()
        )
        return True
    except TimeoutException:
        return False


def navigate_to_period(driver, resource_code, period_date):
    """
    Open the Select Period page and click the link matching period_date (e.g. '7/4/2026').
    Returns the period number from the resulting URL.
    """
    url = f"{BASE_URL}/Track/Time/PickPeriod?resourceCode={resource_code}"
    print(f"Navigating to Select Period: {url}")
    driver.get(url)

    # Wait for SSO if needed
    for _ in range(24):
        time.sleep(5)
        current = driver.current_url
        title = driver.title
        print(f"  [{_*5+5}s] {title[:60]}")
        if "login.microsoftonline" not in current and "Sign in" not in title:
            print("  Logged in.")
            break

    time.sleep(2)

    # Find the period link matching the date
    links = driver.find_elements(By.CSS_SELECTOR, "a")
    target_link = None
    for link in links:
        href = link.get_attribute("href") or ""
        text = link.text.strip()
        if period_date in text or (period_date in href and "periodNumber" in href):
            target_link = link
            break
        # Also match by date in href
        if period_date.replace("/", "%2F") in href or period_date.replace("/", "-") in href:
            target_link = link
            break

    if not target_link:
        # Try partial date match (e.g., "7/4" in link text)
        short_date = "/".join(period_date.split("/")[:2])
        for link in links:
            if short_date in (link.text or ""):
                target_link = link
                break

    if not target_link:
        print(f"ERROR: Could not find period link for '{period_date}'")
        print("Available period links:")
        for link in links:
            href = link.get_attribute("href") or ""
            if "periodNumber" in href:
                print(f"  '{link.text.strip()}' -> {href}")
        return None

    href = target_link.get_attribute("href") or ""
    print(f"Clicking period: '{target_link.text.strip()}'")
    target_link.click()
    time.sleep(3)

    # Extract period number from URL
    match = re.search(r"periodNumber=(\d+)", driver.current_url)
    period_number = match.group(1) if match else None
    print(f"Period number: {period_number}, URL: {driver.current_url}")
    return period_number


def get_existing_rows(driver):
    """
    Return dict mapping assignment lookups to schedule codes.
    Keys: 'assignment_name' (simple) and 'assignment_name|GL_CODE' (disambiguated).
    Uses JavaScript for reliable DOM traversal and ID reading with '###' characters.
    """
    mapping = driver.execute_script("""
        var result = {};
        // Find all total cells with assignment schedule codes
        var totalCells = document.querySelectorAll('td[id$="###total"]');
        totalCells.forEach(function(cell) {
            var cellId = cell.id;
            if (cellId.startsWith('total')) return;  // skip the grand total row
            var sc = cellId.replace('###total', '');

            // Get assignment name from sr-only in the same row
            var row = cell.closest('tr');
            if (!row) return;
            var srOnly = row.querySelector('th .sr-only');
            var name = srOnly ? srOnly.textContent.trim() : '';
            if (!name) return;

            // Walk backwards in the table to find the nearest projRow
            var projName = '';
            var prev = row.previousElementSibling;
            while (prev) {
                if (prev.classList.contains('projRow')) {
                    var projSr = prev.querySelector('th .sr-only, th');
                    projName = projSr ? projSr.textContent.trim() : '';
                    break;
                }
                prev = prev.previousElementSibling;
            }

            // Extract GL code from project name (e.g., 'Ops GB Enhancements • EC10010145')
            var glMatch = projName.match(/[A-Z]{2}\\d+/);
            var glCode = glMatch ? glMatch[0] : projName;

            result[name] = result[name] || sc;  // first occurrence wins for simple key
            result[name + '|' + glCode] = sc;   // always store GL-specific key
        });
        return JSON.stringify(result);
    """)
    return json.loads(mapping) if mapping else {}


def find_and_check_assignment(driver, gl_code, assignment):
    """
    Find and check a single assignment checkbox on the Select Work page.
    For project work, scopes the search to the <li> items belonging to the matching
    GL code project section — prevents accidentally checking the same assignment
    name under a different project. For standard activities (no GL code), searches
    by assignment name only.
    """
    is_standard = not gl_code or gl_code.upper() in ("OOO", "STANDARD", "")

    if is_standard:
        result = driver.execute_script("""
            var asgn = arguments[0];
            var items = document.querySelectorAll('li');
            for (var i = 0; i < items.length; i++) {
                var text = items[i].textContent.trim();
                if (text !== asgn && !text.startsWith(asgn + '\\n')) continue;
                var cb = items[i].querySelector('input[type="checkbox"]');
                if (!cb) continue;
                cb.scrollIntoView({block:'center'});
                if (!cb.checked) { cb.click(); return 'checked'; }
                return 'already';
            }
            return 'not_found';
        """, assignment)
    else:
        # Find the project header <li> whose text contains the GL code, then scan
        # sibling <li> items until the next project header to find the assignment.
        result = driver.execute_script("""
            var glCode   = arguments[0];
            var asgn     = arguments[1];
            var items    = Array.from(document.querySelectorAll('li'));
            var projIdx  = -1;

            // Locate the project header item (contains the GL code)
            for (var i = 0; i < items.length; i++) {
                var t = items[i].textContent.trim();
                if (t.indexOf(glCode) !== -1) {
                    projIdx = i;
                    break;
                }
            }
            if (projIdx < 0) return 'proj_not_found';

            // Walk forward until the next project header (contains a code-like pattern)
            var glPattern = /[A-Z]{2}\\d{7,}/;
            for (var j = projIdx + 1; j < items.length; j++) {
                var itemText = items[j].textContent.trim();
                // Stop when we hit a new project header
                if (j > projIdx + 1 && glPattern.test(itemText) &&
                    items[j].querySelector('input[type="checkbox"]') &&
                    items[j].textContent.indexOf('\\n') !== -1) {
                    break;
                }
                // Match assignment name exactly (item text may be just the label)
                if (itemText === asgn || itemText.startsWith(asgn + '\\n')) {
                    var cb = items[j].querySelector('input[type="checkbox"]');
                    if (!cb) continue;
                    cb.scrollIntoView({block:'center'});
                    if (!cb.checked) { cb.click(); return 'checked'; }
                    return 'already';
                }
            }
            return 'not_found_in_section';
        """, gl_code, assignment)

    if result == 'checked':
        print(f"  [OK] Checked: '{assignment}'")
        return True
    elif result == 'already':
        print(f"  Already checked: '{assignment}'")
        return True
    elif result == 'proj_not_found':
        print(f"  WARNING: Project with GL '{gl_code}' not found on Select Work page")
        return False
    else:
        print(f"  WARNING: '{assignment}' not found in GL '{gl_code}' section (result: {result})")
        return False


def add_work_via_select_work(driver, resource_code, period_number, works_to_add):
    """
    Open Select Work page, check the required assignments, and click Done.
    works_to_add: list of dicts with "gl_code" (or null for standard activities) and "assignment".
    """
    url = f"{BASE_URL}/Track/Time/SelectWork?resourceCode={resource_code}&periodNumber={period_number}"
    print(f"\nOpening Select Work: {url}")
    driver.get(url)
    time.sleep(4)

    if not wait_for_page(driver, "Select Work", timeout=15):
        print("ERROR: Select Work page did not load")
        return False

    # Switch to "All Periods" to see all available assignments
    try:
        all_periods = driver.find_element(By.CSS_SELECTOR, "input[value='allPeriods'], input[id*='allPeriod']")
        if not all_periods.is_selected():
            all_periods.click()
            time.sleep(2)
    except NoSuchElementException:
        pass

    for work in works_to_add:
        gl_code    = work.get("gl_code") or ""
        assignment = work["assignment"]
        print(f"  Looking for '{assignment}' (GL: {gl_code or 'standard activity'})...")
        find_and_check_assignment(driver, gl_code, assignment)

    # Click Done
    try:
        done_btn = driver.find_element(By.LINK_TEXT, "Done")
        done_btn.click()
        print("  Clicked Done.")
        time.sleep(4)
    except NoSuchElementException:
        print("  WARNING: Done button not found")
        return False

    return True


def enter_hours_for_row(driver, schedule_code, day_hours, ooo_days, dry_run=False):
    """
    For each day in day_hours, click the cell and enter the hours value.
    day_hours: {"Mon": 7.5, "Tue": 0, ...}
    ooo_days: list of day names to skip
    """
    for day_name, hours in day_hours.items():
        if day_name in ooo_days:
            print(f"    Skipping {day_name} (OOO)")
            continue
        if hours == 0:
            continue

        day_num = DAY_NUMBERS.get(day_name)
        if day_num is None:
            print(f"    Unknown day: {day_name}")
            continue

        cell_id = f"{schedule_code}###daily#{day_num}"
        print(f"    Entering {hours}h on {day_name} (cell: {cell_id})")

        if dry_run:
            print(f"    [DRY RUN] Would enter {hours}h in {cell_id}")
            continue

        try:
            # Use JS getElementById — avoids CSS/XPath issues with '###' in IDs
            cell = driver.execute_script(f'return document.getElementById("{cell_id}");')
            if not cell:
                print(f"    WARNING: Cell not found via JS: {cell_id}")
                continue

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cell)
            time.sleep(0.3)
            cell.click()
            time.sleep(0.8)

            # Look for input that appeared inside or near the cell
            inp = driver.execute_script(f'return document.querySelector(\'[id="{cell_id}"] input\');')
            if not inp:
                # Sometimes input is a sibling
                inp = driver.execute_script(
                    f'var c = document.getElementById("{cell_id}"); '
                    f'return c ? c.querySelector("input") || c.parentElement.querySelector("input") : null;'
                )
            if inp:
                driver.execute_script("arguments[0].value = '';", inp)
                inp.send_keys(str(hours))
                inp.send_keys("\t")
                time.sleep(0.5)
                print(f"    [OK] Entered {hours}h")
            else:
                print(f"    WARNING: No input found after clicking cell {cell_id}")

        except NoSuchElementException:
            print(f"    WARNING: Cell not found: {cell_id}")
        except Exception as e:
            print(f"    ERROR on {day_name}: {e}")


def sign_and_submit(driver):
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(text(),'Sign and Submit')]")
        btn.click()
        time.sleep(3)
        print("Clicked Sign and Submit.")
        # Confirm dialog if it appears
        try:
            confirm = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Confirm') or contains(text(),'OK') or contains(text(),'Submit')]"))
            )
            confirm.click()
            print("Confirmed submission.")
        except TimeoutException:
            pass
    except NoSuchElementException:
        print("Sign and Submit button not found.")


def run(config_path, dry_run=False):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))

    resource_code = config.get("resource_code", "128447")
    period_date   = config["period"]
    works         = config.get("works", [])
    ooo_days      = config.get("out_of_office", [])
    do_sign       = config.get("sign_and_submit", False)

    if dry_run:
        print("=== DRY RUN MODE — no changes will be made ===\n")

    print(f"Period:    {period_date}")
    print(f"Works:     {len(works)} item(s)")
    print(f"OOO days:  {ooo_days or 'none'}")
    print(f"Sign:      {do_sign}\n")

    driver = make_driver()
    try:
        # 1. Navigate to period
        period_number = navigate_to_period(driver, resource_code, period_date)
        if not period_number:
            print("Could not determine period number. Aborting.")
            return

        time.sleep(3)

        # 2. Get existing rows on the timesheet
        existing = get_existing_rows(driver)
        print(f"\nExisting assignments: {list(existing.keys()) or '(none yet)'}")

        # 3. Determine which works need to be added via Select Work
        missing = [w for w in works if w["assignment"] not in existing]

        if missing:
            if dry_run:
                print("\n[DRY RUN] Would add via Select Work:")
                for w in missing:
                    gl = w.get("gl_code") or "standard activity"
                    print(f"  - '{w['assignment']}' (GL: {gl})")
            else:
                added = add_work_via_select_work(driver, resource_code, period_number, missing)
                if added:
                    time.sleep(2)
                    existing = get_existing_rows(driver)
                    print(f"Updated assignments: {list(existing.keys())}")

        # 4. Enter hours for each work item
        DAY_LABELS = {"Mon": "Jul 6", "Tue": "Jul 7", "Wed": "Jul 8", "Thu": "Jul 9", "Fri": "Jul 10", "Sat": "Jul 11"}
        for work in works:
            assignment = work["assignment"]
            hours      = work.get("hours", {})

            if dry_run:
                print(f"\n[DRY RUN] Would log for '{assignment}':")
                day_total = 0
                for day, h in hours.items():
                    label = DAY_LABELS.get(day, day)
                    print(f"  {day} ({label}): {h}h")
                    day_total += h
                print(f"  Total: {day_total}h")
                continue

            # Prefer GL-specific key first, then fall back to simple name
            gl_code = work.get("gl_code", "")
            if gl_code:
                schedule_code = existing.get(f"{assignment}|{gl_code}") or existing.get(assignment)
            else:
                schedule_code = existing.get(assignment)
            if not schedule_code:
                # Last resort: partial key match
                for key, sc in existing.items():
                    if assignment in key and (not gl_code or gl_code in key):
                        schedule_code = sc
                        break
            if not schedule_code:
                print(f"WARNING: Assignment '{assignment}' not found on timesheet after Select Work")
                continue

            print(f"\nLogging hours for '{assignment}' (SC: {schedule_code}):")
            enter_hours_for_row(driver, schedule_code, hours, ooo_days, dry_run=False)

        # 5. Sign and submit if requested
        if do_sign and not dry_run:
            sign_and_submit(driver)

        print("\n[DONE] Hours logged successfully." if not dry_run else "\n[DRY RUN COMPLETE] Review above and run without --dry-run to apply.")
        if not dry_run:
            time.sleep(3)

    finally:
        driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log hours to Planview timesheet")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()
    run(args.config, dry_run=args.dry_run)


