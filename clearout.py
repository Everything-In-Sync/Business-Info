import googlemaps
import csv
from dotenv import load_dotenv
import os
import requests
import time
from urllib.parse import urlparse

load_dotenv()

print("What area would you like data from?")
area = input()
print("What type of business are looking for?")
business = input()

def main():
    # API keys
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    clearout_key = os.getenv("CLEAROUT_API_KEY")

    if not api_key:
        print("Missing GOOGLE_PLACES_API_KEY in environment")
        return
    if not clearout_key:
        print("Missing CLEAROUT_API_KEY in environment")
        return

    # Initialize the client with your API key
    gmaps = googlemaps.Client(key=api_key)
    
    # Define the search query
    query = business + " " + area 
    
    # Make a request to the Places API to find businesses based on the query
    places_result = gmaps.places(query)
    
    # Determine master CSV path and load existing names to avoid duplicates
    master_csv = 'business_master.csv'
    existing_names = set()
    file_exists = os.path.exists(master_csv)
    is_empty = (not file_exists) or os.path.getsize(master_csv) == 0

    if file_exists and not is_empty:
        with open(master_csv, mode='r', newline='') as existing_file:
            reader = csv.DictReader(existing_file)
            for row in reader:
                existing_name = row.get('Name')
                if existing_name:
                    existing_names.add(existing_name.strip().lower())

    # Open the master CSV in append mode
    with open(master_csv, mode='a', newline='') as file:
        writer = csv.writer(file)

        # Write the header row if file is new/empty
        if is_empty:
            writer.writerow(['Name', 'Address', 'Phone Number', 'Website', 'Rating', 'Recent Review', 'Email', 'Business', 'Area'])

        # Iterate over the places in the results
        for place in places_result['results']:
            # Get place details
            place_details = gmaps.place(place_id=place['place_id'])
            
            # Extracting the desired business information
            name = place_details['result'].get('name')
            if not name:
                continue
            normalized_name = name.strip().lower()
            # Skip if we've already saved this business name
            if normalized_name in existing_names:
                continue
            address = place_details['result'].get('formatted_address')
            phone_number = place_details['result'].get('formatted_phone_number')
            website = place_details['result'].get('website')
            rating = place_details['result'].get('rating')

            # Skip businesses without websites
            if not website:
                continue

            # Use Clearout Instant Email Finder
            domain = urlparse(website).netloc
            url = "https://api.clearout.io/v2/email_finder/instant"
            payload = {
                "name": name,
                "domain": domain,
                "timeout": 120000
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': clearout_key
            }

            try:
                # Gentle throttle between requests to avoid hitting 429
                throttle_seconds = float(os.getenv("CLEAROUT_THROTTLE_SECONDS", "1.5"))
                if throttle_seconds > 0:
                    time.sleep(throttle_seconds)

                resp = requests.post(url, json=payload, headers=headers, timeout=40)
                if resp.status_code == 401:
                    print("Clearout auth failed (401). Check CLEAROUT_API_KEY is correct and formatted as Clearout expects.")
                    return
                if resp.status_code == 402:
                    # Payment required / out of credits
                    print("out of tokens")
                    return
                if resp.status_code == 429:
                    # Respect Retry-After if sent, otherwise wait ~60s per Clearout docs (code 1030)
                    retry_after = resp.headers.get("Retry-After")
                    wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 65
                    print(f"Clearout rate limit reached (429). Waiting {wait_seconds}s then retrying once...")
                    time.sleep(wait_seconds)
                    resp = requests.post(url, json=payload, headers=headers, timeout=40)
                    if resp.status_code == 429:
                        print("Clearout rate limit still 429 after wait. Stopping run to avoid hammering.")
                        return
                if resp.status_code == 524 or resp.status_code == 408:
                    # Cloudflare timeout or request timeout on Clearout's side
                    print("Clearout timeout (", resp.status_code, "). Consider increasing timeout or trying later.")
                    continue
                if resp.status_code >= 400:
                    print(f"Clearout error {resp.status_code}: {resp.text[:200]}")
                    continue

                data = resp.json()
                emails = ((data or {}).get('data') or {}).get('emails') or []
                if emails:
                    email = emails[0].get('email_address')
                else:
                    # No email found by Clearout; skip
                    continue
            except requests.exceptions.RequestException as e:
                # On API/network error, stop to avoid repeated errors
                print(f"Network/API error contacting Clearout: {e}")
                return

            # Extracting the most recent review
            reviews = place_details['result'].get('reviews', [])
            if reviews:  # Check if there are reviews available
                recent_review = reviews[0]  # Assuming the first review is the most recent
                review_text = recent_review.get('text', 'No review text available')
            else:
                review_text = "No reviews"
            
            # Write the business and review information to the CSV
            # Also print to console for visibility into credits vs results
            try:
                print(f"Found email for {name}: {email}")
            except Exception:
                pass
            writer.writerow([name, address, phone_number, website, rating, review_text, email, business, area])
            # Track written name to avoid duplicates within the same run
            existing_names.add(normalized_name)

if __name__ == "__main__":
    main()


