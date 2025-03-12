import os
import json
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import PyPDF2
import uuid

def setup_driver():
    """Set up and return a configured Chrome webdriver."""
    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver, download_dir

def download_pdf(driver, url, download_dir):
    """Download PDF from the URL using Selenium."""
    driver.get(url)
    
    # Generate a unique filename based on URL
    filename = f"{uuid.uuid4().hex}.pdf"
    filepath = os.path.join(download_dir, filename)
    
    # Wait for download to complete
    time.sleep(5)  # Simple wait
    
    # If Selenium download doesn't work, try direct download
    if not any(file.endswith('.pdf') for file in os.listdir(download_dir)):
        print(f"Selenium download failed for {url}, trying direct download")
        response = requests.get(url)
        with open(filepath, 'wb') as f:
            f.write(response.content)
    else:
        # Rename the downloaded file
        for file in os.listdir(download_dir):
            if file.endswith('.pdf'):
                os.rename(os.path.join(download_dir, file), filepath)
                break
    
    return filepath

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file with page separation."""
    pages = []
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page_text = reader.pages[page_num].extract_text()
                pages.append(page_text)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
    
    return pages

def parse_pdf_structure(pages):
    """Parse PDF pages into a structured format with sections and content."""
    # Initialize the structure
    structure = []
    
    # Regular expressions for section identification
    section_pattern = re.compile(r'^Section\s+(\d+(?:\.\d+)?)\s*[-–:]\s*(.+?)$', re.MULTILINE)
    subsection_pattern = re.compile(r'^(\d+(?:\.\d+)?)\s+(.+?)$', re.MULTILINE)
    
    current_section = None
    section_content = []
    
    # Process each page
    for page_idx, page_text in enumerate(pages):
        lines = page_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check if this is a new section
            section_match = section_pattern.match(line)
            if section_match:
                # If we were building a section, add it to the structure
                if current_section:
                    structure.append({
                        "id": f"section_{current_section['number'].replace('.', '_')}",
                        "type": "section",
                        "number": current_section['number'],
                        "title": current_section['title'],
                        "citation_path": f"s. {current_section['number']}",
                        "content": section_content
                    })
                    section_content = []
                
                # Start a new section
                section_num = section_match.group(1)
                section_title = section_match.group(2).strip()
                current_section = {
                    "number": section_num,
                    "title": section_title
                }
                
                # Add a headnote for the section title
                section_content.append({
                    "id": f"section_{section_num.replace('.', '_')}_text_0",
                    "type": "headnote",
                    "text": section_title,
                    "citation_path": f"s. {section_num}"
                })
            
            # Process content of the current section
            elif current_section:
                # Check if this is a subsection
                subsection_match = subsection_pattern.match(line)
                if subsection_match and len(line) < 100:  # Avoid matching paragraph text
                    subsection_num = subsection_match.group(1)
                    subsection_text = subsection_match.group(2).strip()
                    
                    # Add this as a paragraph element
                    section_content.append({
                        "id": f"section_{current_section['number'].replace('.', '_')}_text_{len(section_content)}",
                        "type": "paragraph",
                        "text": f"{subsection_num} {subsection_text}",
                        "citation_path": f"s. {current_section['number']}"
                    })
                elif line:
                    # Regular content
                    section_content.append({
                        "id": f"section_{current_section['number'].replace('.', '_')}_text_{len(section_content)}",
                        "type": "section",
                        "text": line,
                        "citation_path": f"s. {current_section['number']}"
                    })
            else:
                # Before any section is identified, store content as metadata
                pass
            
            i += 1
    
    # Add the last section if there is one
    if current_section:
        structure.append({
            "id": f"section_{current_section['number'].replace('.', '_')}",
            "type": "section",
            "number": current_section['number'],
            "title": current_section['title'],
            "citation_path": f"s. {current_section['number']}",
            "content": section_content
        })
    
    return structure

def extract_metadata(pages):
    """Extract metadata from the PDF pages with improved title detection."""
    # Try to extract a title from the first page
    title = ""
    if pages and len(pages) > 0:
        first_page = pages[0]
        lines = first_page.split('\n')
        
        # Check for common navigation or header patterns to avoid
        navigation_patterns = [
            r'you are here',
            r'home\s+>',
            r'print',
            r'www\.fsra\.ca',
            r'page\s+\d+\s+of',
            r'^\d+$',  # Just page numbers
            r'menu',
            r'navigation',
            r'header',
            r'footer'
        ]
        
        # First attempt: Look for patterns that could indicate an actual document title
        title_patterns = [
            # Look for formal document titles with specific keywords
            r'(?:^|\n)([^<>\d]{10,150}(?:Policy|Guideline|Form|Manual|Bulletin|Act|Regulation)s?)(?:\n|$)',
            r'(?:^|\n)((?:Ontario|Automobile|Insurance|Auto)(?:\s+[^<>\d]{3,50}){1,3})(?:\n|$)',
            r'(?:^|\n)((?:FSRA|FSRAO)\s+[^<>\d]{5,100})(?:\n|$)',
            # Standard document title formats - often all caps or title case
            r'(?:^|\n)([A-Z][a-z]+(?: [A-Z][a-z]+){2,7})(?:\n|$)',
            r'(?:^|\n)([A-Z]{2,}(?: [A-Z]{2,}){1,5})(?:\n|$)'
        ]
        
        # Try to extract title using specific patterns
        for pattern in title_patterns:
            matches = re.finditer(pattern, first_page, re.IGNORECASE)
            for match in matches:
                candidate = match.group(1).strip()
                # Check if the candidate contains any navigation patterns
                if len(candidate) > 10 and len(candidate) < 200:
                    is_navigation = False
                    for nav_pattern in navigation_patterns:
                        if re.search(nav_pattern, candidate, re.IGNORECASE):
                            is_navigation = True
                            break
                    if not is_navigation:
                        title = candidate
                        break
            if title:
                break
        
        # If no title found, try to use content from first section if available
        if not title and len(pages) > 1:
            # Look for section title patterns in first few pages
            section_title_pattern = re.compile(r'^(?:Section|Chapter|Part)\s+\d+[.:]\s*(.*?)$', re.IGNORECASE | re.MULTILINE)
            for page in pages[:2]:  # Check first 2 pages
                section_matches = section_title_pattern.findall(page)
                if section_matches:
                    potential_title = section_matches[0].strip()
                    if len(potential_title) > 5 and len(potential_title) < 150:
                        title = potential_title
                        break
        
        # If still no title, look for centered text or bold text (common for titles)
        # This is a basic heuristic since we can't detect formatting
        if not title:
            line_lengths = [len(line.strip()) for line in lines[:20] if line.strip()]
            if line_lengths:
                avg_length = sum(line_lengths) / len(line_lengths)
                for i, line in enumerate(lines[:20]):
                    line = line.strip()
                    # Skip very short lines, likely not titles
                    if line and len(line) > 10 and len(line) < 100:
                        # Check if it's potentially centered (shorter than average)
                        if len(line) < avg_length * 0.8:
                            # Validate it's not navigation
                            is_navigation = False
                            for nav_pattern in navigation_patterns:
                                if re.search(nav_pattern, line, re.IGNORECASE):
                                    is_navigation = True
                                    break
                            if not is_navigation:
                                title = line
                                break
        
        # Fallback: Use the first substantial non-navigational text
        if not title:
            for line in lines[:30]:  # Look deeper in the document
                line = line.strip()
                if line and len(line) > 15 and len(line) < 150:
                    # Check if it contains navigation patterns
                    is_navigation = False
                    for nav_pattern in navigation_patterns:
                        if re.search(nav_pattern, line, re.IGNORECASE):
                            is_navigation = True
                            break
                    if not is_navigation and not line.isdigit():
                        title = line
                        break
        
        # Last resort: Use the first few non-empty lines
        if not title:
            title_lines = []
            for line in lines[:15]:
                line = line.strip()
                if line and len(line) > 5:
                    # Skip navigation patterns
                    is_navigation = False
                    for nav_pattern in navigation_patterns:
                        if re.search(nav_pattern, line, re.IGNORECASE):
                            is_navigation = True
                            break
                    if not is_navigation:
                        title_lines.append(line)
                        if len(title_lines) >= 2:
                            break
            
            if title_lines:
                title = " - ".join(title_lines)
    
    # Clean up the title - remove multiple spaces, newlines, etc.
    if title:
        title = re.sub(r'\s+', ' ', title).strip()
        # Remove common prefixes that might have been included
        title = re.sub(r'^(Print|PDF|Download|View|Document):\s*', '', title, flags=re.IGNORECASE)
    
    return {
        "title": title[:250] if title else "Untitled Document",  # Truncate if too long
        "citation": title[:250] if title else "Untitled Document",
        "jurisdiction": "Ontario",
        "last_updated": time.strftime("%Y-%m-%d"),
        "source_url": ""  # To be filled later
    }

def process_pdf_to_structured_json(pdf_path, url):
    """Process PDF into a structured JSON format similar to Ontario law documents."""
    pages = extract_text_from_pdf(pdf_path)
    
    # First pass to identify sections and structure
    structure = parse_pdf_structure(pages)
    
    # If no sections were found or structure is too small, try a simpler approach
    if not structure or len(structure) <= 1:
        # Create a single section containing all content
        combined_text = "\n".join(pages)
        
        # Try to find a title or use first few words
        title_match = re.search(r'^(.*?)$', combined_text, re.MULTILINE)
        title = title_match.group(1) if title_match else "Document Content"
        
        # Split into paragraphs
        paragraphs = [p for p in combined_text.split('\n') if p.strip()]
        
        content = []
        for i, para in enumerate(paragraphs):
            content.append({
                "id": f"section_1_text_{i}",
                "type": "paragraph" if len(para) < 300 else "section",
                "text": para,
                "citation_path": "s. 1"
            })
        
        structure = [{
            "id": "section_1",
            "type": "section",
            "number": "1",
            "title": title[:100],  # Truncate if too long
            "citation_path": "s. 1",
            "content": content
        }]
    
    # Extract metadata
    metadata = extract_metadata(pages)
    metadata["source_url"] = url
    
    # Final structured data
    data = {
        "metadata": metadata,
        "structure": structure
    }
    
    return data

def save_json_for_url(data, url):
    """Save data to a JSON file in the FSRAO_docs subfolder using the document title."""
    # Get the document title from metadata
    title = data["metadata"]["title"]
    
    # Create a safe filename from the title
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
    safe_title = re.sub(r'[-\s]+', '_', safe_title)
    
    # Limit filename length and ensure it's not empty
    if len(safe_title) > 50:
        safe_title = safe_title[:50]
    if not safe_title:
        # Fallback to URL ID if title produces empty filename
        safe_title = url.split('/')[-2]
    
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create FSRAO_docs subfolder
    output_dir = os.path.join(script_dir, "FSRAO_docs")
    os.makedirs(output_dir, exist_ok=True)
    
    # Also include URL ID to ensure uniqueness
    url_id = url.split('/')[-2]
    
    # Create full path for the output file
    filename = os.path.join(output_dir, f"{safe_title}_{url_id}.json")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    return filename

def main():
    urls = [
        "https://www.fsrao.ca/media/7726/download",
        "https://www.fsrao.ca/media/14931/download",
        "https://www.fsrao.ca/media/7351/download",
        "https://www.fsrao.ca/media/7371/download",
        "https://www.fsrao.ca/media/6941/download",
        "https://www.fsrao.ca/media/7081/download",
        "https://www.fsrao.ca/media/7091/download",
        "https://www.fsrao.ca/media/7211/download",
        "https://www.fsrao.ca/media/7681/download",
        "https://www.fsrao.ca/media/7686/download",
        "https://www.fsrao.ca/media/7716/download",
        "https://www.fsrao.ca/media/7721/download",
        "https://www.fsrao.ca/media/7726/download",
        "https://www.fsrao.ca/media/7731/download",
        "https://www.fsrao.ca/media/1606/download",
        "https://www.fsrao.ca/media/15261/download",
        "https://www.fsrao.ca/media/26021/download",
        "https://www.fsrao.ca/media/2551/download",
        "https://www.fsrao.ca/media/26096/download",
        "https://www.fsrao.ca/media/23566/download",
        "https://www.fsrao.ca/media/24721/download",
    ]
    
    driver, download_dir = setup_driver()
    
    try:
        for url in urls:
            print(f"Processing {url}")
            pdf_path = download_pdf(driver, url, download_dir)
            
            # Process PDF into structured JSON
            data = process_pdf_to_structured_json(pdf_path, url)
            
            # Save data to a JSON file specific to this URL
            output_file = save_json_for_url(data, url)
            print(f"Data for {url} saved to {output_file}")
            
            # Delete the PDF after processing
            os.remove(pdf_path)
            print(f"Processed and deleted {pdf_path}")
    
    finally:
        # Clean up
        driver.quit()
        print("Processing complete. Results saved to individual JSON files.")

if __name__ == "__main__":
    main() 