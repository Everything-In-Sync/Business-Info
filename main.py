import googlemaps
import csv

print("What area would you like data from?")
area = input()
print("What type of business are looking for?")
business = input()

def main():
    # Define your google maps API key here
    api_key = ""
    
    # Initialize the client with your API key
    gmaps = googlemaps.Client(key=api_key)
    
    # Define the search query
    query = business + " " + area 
    
    # Make a request to the Places API to find businesses based on the query
    places_result = gmaps.places(query)
    
    # Open a file to write to
    with open(business + "_" + area + '.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # Write the header row
        writer.writerow(['Name', 'Address', 'Phone Number', 'Website', 'Rating', 'Recent Review'])
        
        # Iterate over the places in the results
        for place in places_result['results']:
            # Get place details
            place_details = gmaps.place(place_id=place['place_id'])
            
            # Extracting the desired business information
            name = place_details['result'].get('name')
            address = place_details['result'].get('formatted_address')
            phone_number = place_details['result'].get('formatted_phone_number')
            website = place_details['result'].get('website')
            rating = place_details['result'].get('rating')
            
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
            writer.writerow([name, address, phone_number, website, rating, review_text])

if __name__ == "__main__":
    main()




