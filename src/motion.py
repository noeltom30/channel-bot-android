import xml.etree.ElementTree as ET
import csv
import hashlib
from pathlib import Path
try:
    from src.ADB import ADB
except ModuleNotFoundError:
    from ADB import ADB
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEADS_CSV_PATH = PROJECT_ROOT / "leads.csv"

def parse_lead(desc):
    # Decode XML newlines and clean up
    clean = desc.replace("&#10;", "\n").strip()
    parts = clean.split("\n")

    if len(parts) < 4:
        return None

    project_raw = parts[2].strip()

    project = project_raw
    bhk = ""

    if "|" in project_raw:
        left, right = project_raw.split("|", 1)
        project = left.strip()
        bhk = right.strip()

    return {
        "name": parts[0].strip(),
        "phone": parts[1].strip(),
        "project": project,
        "bhk": bhk,
        "status": parts[3].strip(),
        "raw": clean
    }


def extract_leads(xml_text):
    root = ET.fromstring(xml_text)
    leads = []

    for node in root.iter("node"):
        if node.attrib.get("class") == "android.view.View" and \
           node.attrib.get("package") == "com.sobha.channelpartner":

            desc = node.attrib.get("content-desc", "")
            if desc and "+" in desc:  # generic phone marker
                lead = parse_lead(desc)
                if lead:
                    leads.append(lead)

    return leads

def lead_key(lead):
    """Create a unique key from lead data including bhk, excluding name and status."""
    return (lead["phone"], lead["project"], lead["bhk"])

def lead_hash(lead):
    key = lead_key(lead)
    key_str = '|'.join(str(x) for x in key)
    return hashlib.sha256(key_str.encode('utf-8')).hexdigest()

FIELDNAMES = ["hash", "name", "phone", "project", "bhk", "status", "logged_at"]

def _needs_header():
    """Check if leads.csv needs a header row written."""
    if not LEADS_CSV_PATH.exists():
        return True
    return LEADS_CSV_PATH.stat().st_size == 0

def load_existing_leads():
    hashes = set()
    if not LEADS_CSV_PATH.exists() or LEADS_CSV_PATH.stat().st_size == 0:
        return hashes
    try:
        with open(LEADS_CSV_PATH, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            f.seek(0)

            if first_line.startswith("hash,"):
                # New format with header
                reader = csv.DictReader(f)
                for row in reader:
                    hashes.add(row["hash"])
            else:
                # Old format without header - assign columns manually
                old_fields = ["name", "phone", "project", "bhk", "status", "logged_at"]
                # Check if first line looks like old header
                if first_line == ",".join(old_fields):
                    reader = csv.DictReader(f)
                else:
                    f.seek(0)
                    reader = csv.DictReader(f, fieldnames=old_fields)
                for row in reader:
                    key = (row["phone"], row["project"], row["bhk"])
                    h = hashlib.sha256('|'.join(str(x) for x in key).encode('utf-8')).hexdigest()
                    hashes.add(h)
    except Exception:
        pass
    return hashes


def newLeadsExist(leads):
    global _logged_leads
    if not leads:
        return False
    for lead in leads:
        if lead_hash(lead) not in _logged_leads:
            return True
    return False

def save_new_leads(leads):
    """Save new leads to CSV and update the logged set."""
    global _logged_leads
    if not leads:
        return
    needs_header = _needs_header()
    with open(LEADS_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if needs_header:
            writer.writeheader()
        for lead in leads:
            h = lead_hash(lead)
            if h not in _logged_leads:
                _logged_leads.add(h)
                logged_at = datetime.now().isoformat()
                writer.writerow({
                    "hash": h,
                    "name": lead["name"],
                    "phone": lead["phone"],
                    "project": lead["project"],
                    "bhk": lead["bhk"],
                    "status": lead["status"],
                    "logged_at": logged_at
                })

# def isOTPPage(xml):
#     root = ET.fromstring(xml)
#     for node in root.iter("node"):
#         if node.attrib.get("class") == "android.view.View" and \
#            node.attrib.get("package") == "com.sobha.channelpartner":
            
#     return test
    
if __name__ == "__main__":
    adb = ADB()

    print(adb.devices())
    pkg = "com.sobha.channelpartner"
    pkg, activity = adb.resolve_activity(pkg)

    adb.start_app(pkg, activity)
    adb.wait(10)

    # xml = adb.ui_dump()
    # if(isOTPPage(xml)):
    #     adb.tap(553, 940)
    #     adb.wait(0.5)
    #     adb.text("")
    #     adb.tap(450, 1057) #submit phone number
    #     test = input("Enter OTP")
    #     adb.tap(435, 835) #select otp field
    #     adb.text(test) 
    #     adb.tap(440, 953) #submit otp

    adb.tap(275, 1550) #click on leads
    adb.wait(1)
    
    global _logged_leads
    _logged_leads = load_existing_leads()
    _pre_existing = set(_logged_leads)  # snapshot of leads before this run

    while True:
        xml = adb.ui_dump()
        leads = extract_leads(xml)

        if not leads:
            break

        # Check if any lead on screen existed BEFORE this run
        found_old = any(lead_hash(lead) in _pre_existing for lead in leads)

        # Save any new leads from this screen
        save_new_leads(leads)

        if found_old:
            print("Previously logged lead encountered. Stopping scroll.")
            break

        adb.scroll()




