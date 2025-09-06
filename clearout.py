import googlemaps
import csv
from dotenv import load_dotenv
import os
import requests
from urllib.parse import urlparse
load_dotenv()

print("What area would you like data from?")
area = input()
print("What type of business are looking for?")
business = input()

def main():
    # Define your google maps API key here
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    hunter_key = os.getenv("HUNTER_API_KEY")

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

            # Fetch email from Hunter.io if website exists
            if website:
                domain = urlparse(website).netloc
                api_url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={hunter_key}"
                try:
                    response = requests.get(api_url)
                    response.raise_for_status()
                    data = response.json()
                    emails = data.get('data', {}).get('emails', [])
                    if emails:
                        email = emails[0]['value']
                    else:
                        email = 'No email found'
                except:
                    email = 'API error'
            else:
                email = 'No website'

            # Inform if Hunter.io returned an API error (likely out of tokens)
            if email == 'API error':
                print("out of tokens")
                continue

            # Skip businesses where Hunter.io found no emails
            if email == 'No email found':
                continue

            # Extracting the most recent review
            reviews = place_details['result'].get('reviews', [])
            if reviews:  # Check if there are reviews available
                recent_review = reviews[0]  # Assuming the first review is the most recent
                review_text = recent_review.get('text', 'No review text available')
                review_author = recent_review.get('author_name', 'Anonymous')
            else:
                review_text = "No reviews"
                review_author = "N/A"
            
            # Write the business and review information to the CSV
            writer.writerow([name, address, phone_number, website, rating, review_text, email, business, area])
            # Track written name to avoid duplicates within the same run
            existing_names.add(normalized_name)

if __name__ == "__main__":
    main()




