import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# County name to ID mapping (you can find more IDs by inspecting the dropdown)
COUNTY_IDS = {
    'Travis': '2227',
    'Bastrop': '2011'
}

def scrape_tdlr(county_name):
    """Scrape TDLR using the DataTables API"""
    
    if county_name not in COUNTY_IDS:
        print(f"ERROR: Unknown county {county_name}")
        return []
    
    county_id = COUNTY_IDS[county_name]
    url = "https://www.tdlr.texas.gov/TABS/SearchProjects"
    
    # Exact payload structure from the Network tab
    payload = {
        'draw': '2',
        'columns[0][data]': 'ProjectId',
        'columns[0][name]': '',
        'columns[0][searchable]': 'true',
        'columns[0][orderable]': 'true',
        'columns[0][search][value]': '',
        'columns[0][search][regex]': 'false',
        'columns[1][data]': 'ProjectNumber',
        'columns[1][name]': '',
        'columns[1][searchable]': 'true',
        'columns[1][orderable]': 'true',
        'columns[1][search][value]': '',
        'columns[1][search][regex]': 'false',
        'columns[2][data]': 'ProjectName',
        'columns[2][name]': '',
        'columns[2][searchable]': 'true',
        'columns[2][orderable]': 'true',
        'columns[2][search][value]': '',
        'columns[2][search][regex]': 'false',
        'columns[3][data]': 'ProjectCreatedOn',
        'columns[3][name]': '',
        'columns[3][searchable]': 'true',
        'columns[3][orderable]': 'true',
        'columns[3][search][value]': '',
        'columns[3][search][regex]': 'false',
        'columns[4][data]': 'ProjectStatus',
        'columns[4][name]': '',
        'columns[4][searchable]': 'true',
        'columns[4][orderable]': 'true',
        'columns[4][search][value]': '',
        'columns[4][search][regex]': 'false',
        'columns[5][data]': 'FacilityName',
        'columns[5][name]': '',
        'columns[5][searchable]': 'true',
        'columns[5][orderable]': 'true',
        'columns[5][search][value]': '',
        'columns[5][search][regex]': 'false',
        'columns[6][data]': 'City',
        'columns[6][name]': '',
        'columns[6][searchable]': 'true',
        'columns[6][orderable]': 'true',
        'columns[6][search][value]': '',
        'columns[6][search][regex]': 'false',
        'columns[7][data]': 'County',
        'columns[7][name]': '',
        'columns[7][searchable]': 'true',
        'columns[7][orderable]': 'true',
        'columns[7][search][value]': '',
        'columns[7][search][regex]': 'false',
        'columns[8][data]': 'TypeOfWork',
        'columns[8][name]': '',
        'columns[8][searchable]': 'true',
        'columns[8][orderable]': 'true',
        'columns[8][search][value]': '',
        'columns[8][search][regex]': 'false',
        'columns[9][data]': 'EstimatedCost',
        'columns[9][name]': '',
        'columns[9][searchable]': 'true',
        'columns[9][orderable]': 'true',
        'columns[9][search][value]': '',
        'columns[9][search][regex]': 'false',
        'columns[10][data]': 'DataVersionId',
        'columns[10][name]': '',
        'columns[10][searchable]': 'false',
        'columns[10][orderable]': 'true',
        'columns[10][search][value]': '',
        'columns[10][search][regex]': 'false',
        'order[0][column]': '3',
        'order[0][dir]': 'desc',
        'start': '0',
        'length': '100',  # Get up to 100 results
        'search[value]': '',
        'search[regex]': 'false',
        'LocationCounty': county_id  # The key parameter!
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
    }
    
    try:
        print(f"Fetching data for {county_name} County (ID: {county_id})...")
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        # Calculate 7 days ago
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        if 'data' in data:
            print(f"  Received {len(data['data'])} total records")
            
            for item in data['data']:
                # Parse the creation date
                date_text = item.get('ProjectCreatedOn', '')
                if not date_text:
                    continue
                
                try:
                    # Try different date formats
                    date_received = None
                    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%Y %I:%M:%S %p']:
                        try:
                            date_received = datetime.strptime(date_text.split()[0], fmt.split()[0])
                            break
                        except:
                            continue
                    
                    if not date_received:
                        continue
                    
                    # Only include if within 7 days
                    if date_received >= seven_days_ago:
                        results.append({
                            'county': county_name,
                            'projectNumber': item.get('ProjectNumber', ''),
                            'projectName': item.get('ProjectName', ''),
                            'facilityName': item.get('FacilityName', ''),
                            'city': item.get('City', ''),
                            'typeOfWork': item.get('TypeOfWork', ''),
                            'estimatedCost': item.get('EstimatedCost', ''),
                            'projectStatus': item.get('ProjectStatus', ''),
                            'dateCreated': date_text
                        })
                        print(f"    ✓ {item.get('ProjectNumber')} - {date_text}")
                
                except Exception as e:
                    print(f"    ✗ Error parsing date '{date_text}': {e}")
                    continue
        
        print(f"  Found {len(results)} new entries in last 7 days")
        return results
        
    except Exception as e:
        print(f"ERROR scraping {county_name}: {e}")
        return []

def send_email(results, to_emails):
    """Send email notification"""
    
    if not results:
        print("No new entries found - no email sent")
        return
    
    sender = os.environ.get('SENDER_EMAIL')
    password = os.environ.get('SENDER_PASSWORD')
    
    if not sender or not password:
        print("ERROR: Email credentials not set in GitHub Secrets!")
        return
    
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ', '.join(to_emails)
    msg['Subject'] = f'New TDLR Architectural Barriers Projects - {len(results)} entries'
    
    # Build email body
    body = f"New architectural barriers projects filed in the last 7 days:\n\n"
    
    # Group by county
    by_county = {}
    for r in results:
        county = r['county']
        if county not in by_county:
            by_county[county] = []
        by_county[county].append(r)
    
    for county, entries in by_county.items():
        body += f"\n{'='*60}\n"
        body += f"{county.upper()} COUNTY - {len(entries)} new projects\n"
        body += f"{'='*60}\n\n"
        
        for r in entries:
            body += f"Project Number: {r['projectNumber']}\n"
            body += f"Project Name: {r['projectName']}\n"
            body += f"Facility: {r['facilityName']}\n"
            body += f"City: {r['city']}\n"
            body += f"Type of Work: {r['typeOfWork']}\n"
            body += f"Estimated Cost: {r['estimatedCost']}\n"
            body += f"Status: {r['projectStatus']}\n"
            body += f"Date Filed: {r['dateCreated']}\n"
            body += f"\n{'-'*60}\n\n"
    
    body += f"\nView all projects: https://www.tdlr.texas.gov/TABS/Search\n"
    body += f"\n---\nThis is an automated notification from your TDLR project monitor.\n"
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        print(f"✓ Email sent successfully to {len(to_emails)} recipient(s)")
    except Exception as e:
        print(f"✗ Failed to send email: {e}")

if __name__ == '__main__':
    print("="*60)
    print("TDLR Architectural Barriers Project Monitor")
    print("="*60)
    
    # CONFIGURATION - CHANGE THESE VALUES
    counties = ['Travis', 'Bastrop']
    subscribers = ['tammyhliu@gmail.com']  # ← CHANGE THIS TO YOUR EMAIL
    
    all_results = []
    
    for county in counties:
        print(f"\n▶ Scraping {county} County...")
        results = scrape_tdlr(county)
        all_results.extend(results)
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_results)} new entries across all counties")
    print(f"{'='*60}\n")
    
    if all_results:
        send_email(all_results, subscribers)
    else:
        print("No new entries found - no email will be sent")
    
    print("\n✓ Scraper finished successfully")
