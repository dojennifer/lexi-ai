import time
import re
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_ontario_laws(url):
    """
    Scrape text content from Ontario Laws website using Selenium with headless Chrome
    and BeautifulSoup for more robust parsing.
    
    Args:
        url (str): URL to scrape
        
    Returns:
        str: All text content from the webpage
    """
    print(f"Starting to scrape: {url}")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    try:
        # Navigate to the URL
        driver.get(url)
        
        # Wait for the page to load (adjust timeout as needed)
        wait = WebDriverWait(driver, 20)
        
        # Wait for content to be loaded
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.act-content")))
        
        # Give more time for JavaScript to render
        time.sleep(5)
        
        # Get the page source after JavaScript has loaded
        page_source = driver.page_source
        
        # Get the title and other metadata before we close the driver
        try:
            title_element = driver.find_element(By.CSS_SELECTOR, "div.act-content > h1")
            title = title_element.text
            print(f"Found title: {title}")
            
            # Try to extract citation information (R.S.O., etc.)
            citation = ""
            citation_element = driver.find_elements(By.CSS_SELECTOR, "div.act-name")
            if citation_element:
                citation = citation_element[0].text
            else:
                # Extract citation from title if possible
                citation_match = re.search(r'([RS]\.[SO]\.[O]\.\s+\d{4},\s+c\.\s+\w+(\.\d+)?)', title)
                if citation_match:
                    citation = citation_match.group(1)
                else:
                    citation = title
        except:
            title = f"Ontario Law {url.split('/')[-1]}"
            citation = title
            print("Could not find title element")
        
        # Create BeautifulSoup object from the source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Dictionary to map class names to element types
        element_type_map = {
            # Standard elements
            "paragraph": "paragraph",
            "definition": "definition", 
            "headnote": "headnote",
            "section": "section",
            "subsection": "subsection",
            "title": "title",
            "chapter": "chapter",
            "part": "part",
            "schedule": "schedule",
            "form": "form",
            # Elements with "-e" suffix (regulations)
            "paragraph-e": "paragraph",
            "definition-e": "definition",
            "headnote-e": "headnote",
            "section-e": "section",
            "subsection-e": "subsection",
            "title-e": "title",
            "chapter-e": "chapter", 
            "part-e": "part",
            "schedule-e": "schedule",
            "form-e": "form",
            # Add more specific classes used in the Ontario Laws site
            "sectionNum": "section_number",
            "sectionTitle": "section_title",
            "subsectionNum": "subsection_number",
            "subsectionTitle": "subsection_title",
            "partNum": "part_number",
            "partTitle": "part_title",
            "chapterNum": "chapter_number",
            "chapterTitle": "chapter_title",
            "scheduleNum": "schedule_number",
            "scheduleTitle": "schedule_title"
        }
        
        # Find all relevant elements within act-content
        act_content = soup.select_one("div.act-content")
        
        # Raw ordered list of all elements (will be processed into hierarchical structure later)
        raw_elements = []
        
        if act_content:
            # Print the HTML structure of a sample of elements to debug
            debug_sample = act_content.find_all('p', limit=5)
            for idx, elem in enumerate(debug_sample):
                print(f"Debug - Element {idx}:")
                print(f"  Tag: {elem.name}")
                print(f"  Classes: {elem.get('class', [])}")
                print(f"  Text: {elem.get_text(strip=True)}")
            
            # Find all paragraph elements
            all_p_elements = act_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            # Use patterns to identify different types of elements
            section_number_pattern = re.compile(r'^(\d+\.(\d+)?)$')
            definition_pattern = re.compile(r'^"([^"]+)"\s+means\s+')
            paragraph_pattern = re.compile(r'^[(]([a-z])[)]\s+')
            roman_numeral_pattern = re.compile(r'^[(]([ivxlcdm]+)[)]\s+', re.IGNORECASE)
            part_pattern = re.compile(r'^PART\s+([IVXLCDM]+)', re.IGNORECASE)
            
            current_section = None
            current_part = None
            
            for i, p_element in enumerate(all_p_elements):
                # Get the class attribute
                class_attr = p_element.get('class', [])
                text = p_element.get_text(strip=True)
                
                # Skip empty elements
                if not text:
                    continue
                
                # Determine element type
                elm_type = "unknown"
                
                # Try to identify by class
                if class_attr:
                    class_str = ' '.join(class_attr)
                    for class_name, type_name in element_type_map.items():
                        if class_name in class_str:
                            elm_type = type_name
                            break
                
                # If still unknown, try to identify by content pattern
                if elm_type == "unknown":
                    # Check for section numbers (e.g., "115.", "116.")
                    if section_number_pattern.match(text):
                        elm_type = "section_number"
                    # Check for Part headings
                    elif part_pattern.match(text) or (text.startswith("PART ") and any(numeral in text for numeral in ["I", "V", "X"])):
                        elm_type = "part"
                    # Check for ALL CAPS text which often indicates part or section titles
                    elif text.isupper() and len(text) > 3:
                        elm_type = "part_title" if "PART" in text else "section_title"
                    # Element right after a section number is usually a section title
                    elif len(raw_elements) > 0 and raw_elements[-1]["elm_type"] == "section_number":
                        elm_type = "section_title"
                    # Check for definitions
                    elif text.startswith('"') and '"' in text[1:] and "means" in text:
                        elm_type = "definition"
                    # Check for paragraphs (a), (b), etc.
                    elif paragraph_pattern.match(text):
                        elm_type = "paragraph"
                    # Check for roman numerals (i), (ii), etc.
                    elif roman_numeral_pattern.match(text):
                        elm_type = "subparagraph"
                
                # Extract additional information based on element type
                element_data = {
                    "elm_type": elm_type,
                    "text": text,
                    "position": i  # Store position to help with parent-child relationships later
                }
                
                # Extract numbers/identifiers for certain element types
                if elm_type == "section_number":
                    section_match = section_number_pattern.match(text)
                    if section_match:
                        element_data["number"] = section_match.group(1).rstrip('.')
                        current_section = element_data["number"]
                
                elif elm_type == "part":
                    part_match = part_pattern.match(text)
                    if part_match:
                        element_data["number"] = part_match.group(1)
                        current_part = element_data["number"]
                    else:
                        # Try to extract Roman numeral from the text
                        roman_match = re.search(r'PART\s+([IVXLCDM]+)', text, re.IGNORECASE)
                        if roman_match:
                            element_data["number"] = roman_match.group(1)
                            current_part = element_data["number"]
                
                elif elm_type == "paragraph":
                    para_match = paragraph_pattern.match(text)
                    if para_match:
                        element_data["letter"] = para_match.group(1)
                
                elif elm_type == "definition":
                    def_match = definition_pattern.match(text)
                    if def_match:
                        element_data["term"] = def_match.group(1)
                
                # Add parent section or part if we know it
                if current_section and elm_type not in ["section_number", "part"]:
                    element_data["parent_section"] = current_section
                
                if current_part:
                    element_data["parent_part"] = current_part
                
                # Add to raw elements list
                raw_elements.append(element_data)
                
                # If this is the first time we've seen an "unknown" type, print details to help debug
                if elm_type == "unknown" and not hasattr(scrape_ontario_laws, 'reported_unknown'):
                    print(f"First unknown element:")
                    print(f"  Text: {text}")
                    print(f"  Classes: {class_attr}")
                    scrape_ontario_laws.reported_unknown = True
        
        # Fallback: If we didn't find elements with our target patterns,
        # get all paragraphs and headings to preserve some structure
        if not raw_elements:
            print("Using fallback content extraction method")
            for i, element in enumerate(act_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])):
                text = element.get_text(strip=True)
                if text:
                    # Determine a generic type based on the tag
                    if element.name.startswith('h'):
                        elm_type = "heading"
                    else:
                        elm_type = "paragraph"
                    
                    raw_elements.append({
                        "elm_type": elm_type,
                        "text": text,
                        "position": i
                    })
        
        # Process raw elements into structured hierarchy
        structured_data = process_to_structured_format(raw_elements, title, citation, url)
        
        # Ensure data directory exists
        data_dir = "data/Ontario_docs/"
        os.makedirs(data_dir, exist_ok=True)
        
        # Create filename from title
        json_filename = f"{title.replace(' ', '_').replace('/', '_').replace(',', '').replace(':', '')}.json"
        json_file_path = os.path.join(data_dir, json_filename)
        
        # Save the structured data as JSON
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False)
            
        print(f"Structured data saved to {json_file_path}")
        
        # Create a text summary
        content_parts = []
        for item in raw_elements:
            content_parts.append(f"{item['elm_type'].upper()}: {item['text']}")
        
        # Join all content with line breaks
        content = "\n\n".join(content_parts)
        
        return content
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Close the browser
        driver.quit()

def process_to_structured_format(raw_elements, title, citation, url):
    """
    Process the raw elements into a structured hierarchical format.
    
    Args:
        raw_elements (list): List of raw elements extracted from the page
        title (str): Title of the law
        citation (str): Citation of the law
        url (str): Source URL
        
    Returns:
        dict: Structured data in the improved format
    """
    # Create the metadata section
    structured_data = {
        "metadata": {
            "title": title,
            "citation": citation,
            "jurisdiction": "Ontario",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "source_url": url
        },
        "structure": []
    }
    
    # Initialize tracking variables
    current_part = None
    current_section = None
    current_subsection = None
    current_definition = None
    
    # Process elements to create the hierarchical structure
    i = 0
    while i < len(raw_elements):
        element = raw_elements[i]
        element_type = element["elm_type"]
        
        # Process PART elements
        if element_type == "part":
            part_number = element.get("number", "")
            part_title = element["text"]
            
            # If the next element is a part title, use that instead
            if i+1 < len(raw_elements) and raw_elements[i+1]["elm_type"] == "part_title":
                part_title = raw_elements[i+1]["text"]
                i += 1  # Skip the next element since we've used it
            
            part_id = f"part_{part_number}"
            
            part_obj = {
                "id": part_id,
                "type": "part",
                "number": part_number,
                "title": part_title,
                "citation_path": f"Part {part_number}",
                "content": []
            }
            
            structured_data["structure"].append(part_obj)
            current_part = part_obj
        
        # Process SECTION elements
        elif element_type == "section_number":
            section_number = element.get("number", "")
            section_title = ""
            
            # If the next element is a section title, use that
            if i+1 < len(raw_elements) and raw_elements[i+1]["elm_type"] == "section_title":
                section_title = raw_elements[i+1]["text"]
                i += 1  # Skip the next element since we've used it
            
            section_id = f"section_{section_number.replace('.', '_')}"
            
            section_obj = {
                "id": section_id,
                "type": "section",
                "number": section_number,
                "title": section_title,
                "citation_path": f"s. {section_number}",
                "content": []
            }
            
            # Add section to appropriate parent or to the main structure
            if current_part:
                current_part["content"].append(section_obj)
            else:
                structured_data["structure"].append(section_obj)
            
            current_section = section_obj
            current_subsection = None
        
        # Process section text (not a title or number)
        elif current_section and element_type not in ["section_number", "section_title", "part", "part_title"]:
            if element_type == "definition" and "term" in element:
                # Process definition elements
                term = element["term"]
                definition_id = f"{current_section['id']}_def_{term.replace(' ', '_')}"
                
                definition_obj = {
                    "id": definition_id,
                    "type": "definition",
                    "term": term,
                    "text": element["text"],
                    "citation_path": f"{current_section['citation_path']}, \"{term}\""
                }
                
                current_section["content"].append(definition_obj)
                current_definition = definition_obj
            
            elif element_type == "paragraph" and "letter" in element:
                # Process paragraph elements
                letter = element["letter"]
                paragraph_id = f"{current_section['id']}_para_{letter}"
                
                paragraph_obj = {
                    "id": paragraph_id,
                    "type": "paragraph",
                    "letter": letter,
                    "text": element["text"],
                    "citation_path": f"{current_section['citation_path']}, para. ({letter})"
                }
                
                # Add paragraph to appropriate parent
                if current_definition:
                    if "paragraphs" not in current_definition:
                        current_definition["paragraphs"] = []
                    current_definition["paragraphs"].append(paragraph_obj)
                elif current_subsection:
                    if "content" not in current_subsection:
                        current_subsection["content"] = []
                    current_subsection["content"].append(paragraph_obj)
                else:
                    current_section["content"].append(paragraph_obj)
            
            else:
                # Process other section content elements
                content_id = f"{current_section['id']}_text_{len(current_section['content'])}"
                
                content_obj = {
                    "id": content_id,
                    "type": element_type,
                    "text": element["text"],
                    "citation_path": current_section["citation_path"]
                }
                
                current_section["content"].append(content_obj)
        
        i += 1
    
    return structured_data

if __name__ == "__main__":
    # URL of the Ontario law to scrape
    ontario_urls = [
        "https://www.ontario.ca/laws/statute/90i08",
        "https://www.ontario.ca/laws/statute/90m41",
        "https://www.ontario.ca/laws/statute/16f37",
        "https://www.ontario.ca/laws/statute/03a09",
        "https://www.ontario.ca/laws/regulation/900664",
        "https://www.ontario.ca/laws/statute/90c25",
        "https://www.ontario.ca/laws/regulation/r24383",
        "https://www.ontario.ca/laws/regulation/930777",
        "https://www.ontario.ca/laws/statute/90h08"
    ]
    
    # Scrape the content
    for url in ontario_urls:
        text_content = scrape_ontario_laws(url)
    
    