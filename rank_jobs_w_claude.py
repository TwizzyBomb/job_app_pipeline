#!/usr/bin/env python3
"""
Job Listing Ranker Script
Automatically ranks job listings from 1-10 based on resume match using Claude API
"""

# Import standard library modules for file operations, JSON handling, and time delays
import os
import json
import time

# Ensure the Anthropic API key is set in environment variables
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from a .env file if present

# Import typing hints for better code documentation and IDE support
from typing import List, Dict, Tuple

# Import dataclass decorator for creating structured data objects
from dataclasses import dataclass

# Import the official Anthropic API client library
import anthropic

# Import URL parsing utilities for extracting company names from job URLs
from urllib.parse import urlparse

# Import requests for making HTTP calls to Google Search API
import requests

# Create a data structure to hold job information using Python's dataclass decorator
@dataclass
class JobListing:
    title: str           # Job title (e.g. "Senior Software Engineer")
    company: str         # Company name (e.g. "Google")
    url: str            # Link to the job posting
    description: str = ""    # Full job description text (optional, defaults to empty)
    match_score: int = 0     # Ranking score from 1-10 (filled in by analysis)
    analysis: str = ""       # Detailed explanation of the match (filled in by analysis)

# Main class that handles all job ranking functionality
class JobRanker:
    def __init__(self, api_key: str = None):
        """Initialize the JobRanker with Anthropic API key"""
        resume_path = os.getenv("RESUME_PATH", "resume.txt")
        
        # Try to get API key from parameter first, then environment variable
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        
        # Raise an error if no API key is found - the script can't work without it
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set or pass api_key parameter")
        
        # Create the Anthropic client object that will make API calls
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Load the default resume text into memory
        self.resume = self.load_resume_from_file(resume_path)
        print(f"✅ first 100 of resume text: {self.resume[:100]}...")  # Print first 100 chars of resume
    
    def set_resume(self, resume_text: str):
        """Update the resume text - allows using a different resume"""
        # Replace the current resume with new text provided by user
        self.resume = resume_text
    
    def load_resume_from_file(self, file_path: str):
        """Load resume from a text file on disk"""
        try:
            # Open the file and read all its contents into memory
            with open(file_path, 'r', encoding='utf-8') as f:
                resume_content = f.read()
                return resume_content  # Return the full text of the resume
            # Print success message to user
            print(f"✅ Resume loaded from {file_path}")
        except FileNotFoundError:
            # If file doesn't exist, print error and re-raise exception
            print(f"❌ Resume file not found: {file_path}")
            raise
    
    def analyze_job_listing(self, job: JobListing) -> Tuple[int, str]:
        """Analyze a single job listing and return match score (1-10) and analysis"""
        
        # Create the prompt that will be sent to Claude
        # This prompt contains both the resume and job details for comparison
        prompt = f"""You are an expert career advisor and technical recruiter. Analyze how well this job listing matches the candidate's resume and experience.

CANDIDATE'S RESUME:
{self.resume}

JOB LISTING:
Company: {job.company}
Title: {job.title}
URL: {job.url}
Description: {job.description[:4000]}  # Truncate to avoid token limits

Please provide:
1. A match score from 1-10 (where 10 is a perfect match)
2. A detailed analysis explaining:
   - Key strengths/alignments
   - Potential gaps or concerns
   - Overall fit assessment

Format your response as JSON:
{{
    "match_score": <integer 1-10>,
    "analysis": "<detailed analysis text>"
}}

Focus on technical skills, experience level, industry alignment, and role responsibilities."""

        try:
            # Make the API call to Claude using the Anthropic client
            response = self.client.messages.create(
                model="claude-3-haiku-20240307", # Use the most capable model for analysis
                max_tokens=1000,                     # Limit response length to control costs
                messages=[{
                    "role": "user",           # We are the user asking the question
                    "content": prompt         # Send our complete prompt with resume + job info
                }]
            )
            
            # Try to parse Claude's response as JSON
            result = json.loads(response.content[0].text)
            # Extract the score and analysis from the parsed JSON
            return result["match_score"], result["analysis"]
            
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract information manually
            # This is a fallback in case Claude doesn't format the response perfectly
            content = response.content[0].text
            
            # Try to extract score from the response text
            score = 5  # Default score if we can't parse it
            if "match_score" in content:
                try:
                    # Look for pattern like "match_score": 7 and extract the number
                    score = int(content.split("match_score")[1].split(":")[1].split(",")[0].strip().strip('"'))
                except:
                    # If extraction fails, keep the default score
                    pass
            # Return the score and raw content as analysis
            return score, content
            
        except Exception as e:
            # If any other error occurs, print it and return error values
            print(f"❌ Error analyzing {job.title}: {str(e)}")
            return 0, f"Analysis failed: {str(e)}"
    
    def rank_jobs(self, jobs: List[JobListing], delay_seconds: float = 1.0) -> List[JobListing]:
        """Rank multiple job listings, adding delays to respect rate limits"""
        
        # Print status message showing how many jobs we're about to analyze
        print(f"🔍 Analyzing {len(jobs)} job listings...")
        
        # Loop through each job and analyze it one by one
        for i, job in enumerate(jobs, 1):  # enumerate starts counting at 1
            # Show progress to user - which job we're currently analyzing
            print(f"   Analyzing {i}/{len(jobs)}: {job.company} - {job.title}")
            
            # Call our analysis function to get score and detailed analysis
            score, analysis = self.analyze_job_listing(job)
            
            # Store the results back into the job object
            job.match_score = score    # Save the numerical score (1-10)
            job.analysis = analysis    # Save the detailed text analysis
            
            # Add a delay between API calls to avoid hitting rate limits
            if i < len(jobs):  # Don't delay after the last job (no more calls coming)
                time.sleep(delay_seconds)  # Pause execution for specified seconds
        
        # Sort all jobs by their match scores, highest scores first
        # This creates our final ranking from best match to worst match
        ranked_jobs = sorted(jobs, key=lambda x: x.match_score, reverse=True)
        return ranked_jobs
    
    def print_rankings(self, ranked_jobs: List[JobListing]):
        """Print formatted rankings to the console in a nice, readable format"""
        
        # Print a header with decorative lines to separate output sections
        print("\n" + "="*80)           # Print 80 equal signs for visual separation
        print("🏆 JOB RANKINGS (Best to Worst Match)")
        print("="*80)
        
        # Loop through each job and print its details with ranking number
        for i, job in enumerate(ranked_jobs, 1):  # Start counting at 1 for user display
            print(f"\n#{i} - MATCH SCORE: {job.match_score}/10")  # Show rank and score
            print(f"Company: {job.company}")                      # Company name
            print(f"Title: {job.title}")                          # Job title
            print(f"URL: {job.url}")                             # Link to job posting
            print(f"Analysis: {job.analysis}")                    # Detailed analysis text
            print("-" * 60)  # Print separator line between jobs
    
    def save_results(self, ranked_jobs: List[JobListing], filename: str = "job_rankings.json"):
        """Save results to JSON file for later reference or further processing"""
        
        # Create a list to hold all job results in a structured format
        results = []
        
        # Convert each job object into a dictionary for JSON serialization
        for i, job in enumerate(ranked_jobs, 1):  # Start rank counting at 1
            results.append({
                "rank": i,                    # Position in ranking (1, 2, 3, etc.)
                "match_score": job.match_score,  # Numerical score from analysis
                "company": job.company,       # Company name
                "title": job.title,          # Job title
                "url": job.url,              # Link to job posting
                "analysis": job.analysis     # Full text analysis
            })
        
        # Write the results to a JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)  # Pretty format with indentation
        
        # Confirm to user that file was saved
        print(f"📁 Results saved to {filename}")
    
    def load_jobs_from_urls(self, urls: List[str]) -> List[JobListing]:
        """Load job listings from URLs using Claude's web fetching capabilities"""
        # This function creates JobListing objects from a list of URLs
        # Note: The actual job descriptions would need to be fetched separately
        
        jobs = []  # Initialize empty list to store job objects
        
        # Process each URL provided
        for url in urls:
            try:
                # Extract company name from the URL domain
                domain = urlparse(url).netloc  # Get domain part (e.g., "greenhouse.io")
                
                # Try to extract company name from domain
                # For "job-boards.greenhouse.io" this gets "greenhouse"
                company = domain.split('.')[1] if '.' in domain else domain
                
                # Create a JobListing object with basic info from URL
                jobs.append(JobListing(
                    title="Position from URL",        # Generic title since we don't have details yet
                    company=company.title(),          # Capitalize company name
                    url=url,                         # Store the original URL
                    description="[Job description will be fetched via Claude API]"  # Placeholder
                ))
            except:
                # If URL parsing fails, show warning and continue with other URLs
                print(f"⚠️  Could not parse URL: {url}")
                
        return jobs  # Return list of JobListing objects

    def parse_google_search_json(self, search_results: dict) -> List[JobListing]:
        """Parse Google Custom Search API JSON results into JobListing objects"""
        
        jobs = []  # Initialize empty list to store job objects
        
        # Check if the search results contain any items
        if 'items' not in search_results or not search_results['items']:
            print("⚠️  No search results found in Google API response")
            return jobs
        
        # Print status message showing how many results we found
        print(f"📋 Found {len(search_results['items'])} job listings from Google Search")
        
        # Loop through each search result item
        for i, item in enumerate(search_results['items'], 1):
            try:
                # Extract basic information from the search result
                title = item.get('title', 'Unknown Position')  # Job title from search result title
                url = item.get('link', '')                      # Direct link to job posting
                snippet = item.get('snippet', '')              # Short description from search results
                
                # Extract company name from the URL domain or title
                company = self._extract_company_name(url, title)
                
                # Create a JobListing object with the extracted information
                job = JobListing(
                    title=title,                    # Use the search result title as job title
                    company=company,                # Company name extracted from URL/title
                    url=url,                       # Direct link to the job posting
                    description=snippet            # Use the search snippet as initial description
                )
                
                jobs.append(job)  # Add the job to our list
                
                # Print progress message for each job parsed
                print(f"   ✅ Parsed job {i}: {company} - {title[:50]}...")
                
            except Exception as e:
                # If parsing fails for any item, log the error and continue
                print(f"⚠️  Error parsing search result {i}: {str(e)}")
                continue
        
        return jobs  # Return list of JobListing objects created from search results
    
    def _extract_company_name(self, url: str, title: str) -> str:
        """Helper method to extract company name from URL or title"""
        
        try:
            # First, try to extract company from the job title
            # Many job titles follow format: "Company Name hiring Position Title"
            if " hiring " in title:
                company = title.split(" hiring ")[0].strip()
                # Clean up common prefixes that Google adds
                if company.startswith("Jobs at "):
                    company = company.replace("Jobs at ", "")
                return company
            
            # If title parsing fails, try to extract from URL domain
            domain = urlparse(url).netloc.lower()  # Get domain part (e.g., "glassdoor.com")
            
            # Handle known job board domains - extract the actual company when possible
            if 'linkedin.com' in domain:
                return "LinkedIn Job"  # LinkedIn jobs need special handling
            elif 'glassdoor.com' in domain:
                return "Glassdoor Job"  # Glassdoor jobs need special handling
            elif 'indeed.com' in domain:
                return "Indeed Job"  # Indeed jobs need special handling
            elif 'greenhouse.io' in domain:
                return "Greenhouse Job"  # Greenhouse jobs usually have company info in URL
            else:
                # For direct company websites, extract main domain
                domain_parts = domain.split('.')
                if len(domain_parts) >= 2:
                    # Get the main domain name (e.g., "microsoft" from "careers.microsoft.com")
                    company = domain_parts[-2].capitalize()
                    return company
                else:
                    return domain.capitalize()
                    
        except Exception:
            # If all extraction methods fail, return a default value
            return "Unknown Company"
    
    def load_jobs_from_google_search(self, search_results: dict, fetch_full_descriptions: bool = False) -> List[JobListing]:
        """
        Load job listings from Google Custom Search API results
        
        Args:
            search_results: Dictionary containing Google Custom Search API JSON response
            fetch_full_descriptions: If True, attempts to fetch full job descriptions from URLs
        
        Returns:
            List of JobListing objects
        """
        
        # Parse the Google search results into JobListing objects
        jobs = self.parse_google_search_json(search_results)
        
        # If requested, try to fetch full job descriptions (this will use more API calls)
        if fetch_full_descriptions and jobs:
            print(f"🔍 Attempting to fetch full descriptions for {len(jobs)} jobs...")
            print("⚠️  Note: This feature would require additional web scraping capabilities")
            # TODO: Implement web scraping to get full job descriptions
            # This would require additional libraries like BeautifulSoup or Selenium
        
        return jobs
    
    def load_jobs_from_google_search_file(self, json_file_path: str) -> List[JobListing]:
        """
        Load job listings from a saved Google Custom Search API JSON file
        
        Args:
            json_file_path: Path to JSON file containing Google search results
            
        Returns:
            List of JobListing objects
        """
        
        try:
            # Read the JSON file from disk
            with open(json_file_path, 'r', encoding='utf-8') as f:
                search_results = json.load(f)
            
            print(f"📁 Loaded Google search results from {json_file_path}")
            
            # Parse the loaded JSON data
            return self.parse_google_search_json(search_results)
            
        except FileNotFoundError:
            print(f"❌ Google search results file not found: {json_file_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in file {json_file_path}: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Error loading Google search results: {str(e)}")
            raise

def main():
    """Example usage of the JobRanker - this runs when you execute the script"""
    
    # Initialize ranker - this creates the JobRanker object and loads API key
    try:
        ranker = JobRanker()  # Try to create ranker with API key from environment
    except ValueError as e:
        # If API key is missing, show error and exit
        print(f"❌ {e}")
        print("Please set your ANTHROPIC_API_KEY environment variable or pass it directly")
        return  # Exit the function early
    
    # Parse Google search results into JobListing objects
    # print("🔍 Using Google Search API results...")
    # jobs_from_google = ranker.load_jobs_from_google_search(sample_google_results)
    
    # Load from a saved Google search JSON file
    print("📁 Loading from saved Google search results file...")
    job_search_list_path = os.getenv("JOB_SEARCH_LIST_PATH", "job_search_results.json")
    jobs_from_google = ranker.load_jobs_from_google_search_file(job_search_list_path)
    jobs_to_analyze = jobs_from_google # could have other sources too
    
    # Check if we have any jobs to analyze
    if not jobs_to_analyze:
        print("❌ No jobs found to analyze. Please check your Google search results or add manual jobs.")
        return
    
    print(f"\n📊 Total jobs to analyze: {len(jobs_to_analyze)}")
    
    # Rank the jobs using our ranker with 2-second delays between API calls
    ranked_jobs = ranker.rank_jobs(jobs_to_analyze, delay_seconds=2.0)
    
    # Display results in formatted output to console
    ranker.print_rankings(ranked_jobs)
    
    # Save results to JSON file for later reference
    ranker.save_results(ranked_jobs)
    
    # Print completion message
    print("\n✅ Job ranking complete!")

# This is Python's standard way to run code only when the script is executed directly
# (not when it's imported as a module by another script)
if __name__ == "__main__":
    main()  # Call the main function to start the program