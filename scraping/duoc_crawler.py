import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import sys
from dataclasses import dataclass, asdict
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv

# Configuration
@dataclass
class CrawlerConfig:
    """Configuration class for the web crawler"""
    max_depth: int = 2
    delay_min: float = 1.0  # Minimum delay between requests (seconds)
    delay_max: float = 3.0  # Maximum delay between requests (seconds)
    timeout: int = 10
    max_retries: int = 3
    retry_delay: float = 2.0
    max_workers: int = 3  # For concurrent requests
    output_format: str = "json"  # json or csv
    log_level: str = "INFO"
    user_agents: List[str] = None
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]

@dataclass
class ScrapedItem:
    """Data structure for scraped items"""
    url: str
    title: str
    text: str
    section: str
    depth: int
    timestamp: str
    status_code: int
    content_type: str = ""
    meta: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.meta is None:
            self.meta = {}

class ProgressTracker:
    """Class to track and display crawling progress"""
    
    def __init__(self, total_sections: int):
        self.total_sections = total_sections
        self.current_section = 0
        self.total_urls = 0
        self.processed_urls = 0
        self.successful_urls = 0
        self.failed_urls = 0
        self.start_time = time.time()
        self.section_start_time = None
        
    def start_section(self, section_name: str, total_urls: int):
        self.current_section += 1
        self.section_start_time = time.time()
        self.total_urls = total_urls
        
        print(f"\n{'='*80}")
        print(f"🚀 INICIANDO SECCIÓN {self.current_section}/{self.total_sections}: {section_name.upper()}")
        print(f"📊 URLs a procesar: {total_urls}")
        print(f"⏰ Hora de inicio: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}")
        
    def update_progress(self, url: str, success: bool, error: str = None):
        self.processed_urls += 1
        if success:
            self.successful_urls += 1
            status = "✅"
        else:
            self.failed_urls += 1
            status = "❌"
            
        progress = (self.processed_urls / self.total_urls) * 100
        elapsed = time.time() - self.section_start_time
        rate = self.processed_urls / elapsed if elapsed > 0 else 0
        
        # Calculate ETA
        if rate > 0:
            remaining = self.total_urls - self.processed_urls
            eta_seconds = remaining / rate
            eta = f"{int(eta_seconds//60)}:{int(eta_seconds%60):02d}"
        else:
            eta = "∞"
            
        print(f"\r{status} [{progress:5.1f}%] {self.processed_urls}/{self.total_urls} | "
              f"Velocidad: {rate:.1f} URLs/s | ETA: {eta} | {url[:60]}...", end="")
        
        if error:
            print(f"\n   ⚠️  Error: {error}")
            
    def finish_section(self, section_name: str, items_saved: int):
        elapsed = time.time() - self.section_start_time
        print(f"\n\n✅ SECCIÓN COMPLETADA: {section_name}")
        print(f"📈 Estadísticas:")
        print(f"   • URLs procesadas: {self.processed_urls}")
        print(f"   • Exitosas: {self.successful_urls}")
        print(f"   • Fallidas: {self.failed_urls}")
        print(f"   • Items guardados: {items_saved}")
        print(f"   • Tiempo total: {elapsed:.1f} segundos")
        print(f"   • Velocidad promedio: {self.processed_urls/elapsed:.1f} URLs/s")
        
    def finish_all(self):
        total_elapsed = time.time() - self.start_time
        print(f"\n{'='*80}")
        print(f"🎉 CRAWLING COMPLETADO")
        print(f"📊 RESUMEN FINAL:")
        print(f"   • Secciones procesadas: {self.current_section}")
        print(f"   • URLs totales procesadas: {self.processed_urls}")
        print(f"   • Exitosas: {self.successful_urls}")
        print(f"   • Fallidas: {self.failed_urls}")
        print(f"   • Tiempo total: {total_elapsed:.1f} segundos")
        print(f"   • Tasa de éxito: {(self.successful_urls/self.processed_urls*100):.1f}%")
        print(f"{'='*80}")

class DuocCrawler:
    """Improved web crawler with progress tracking and best practices"""
    
    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.session = requests.Session()
        self.visited = set()
        self.items = []
        
        # Setup logging
        self.setup_logging()
        
        # Setup base directories
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.OUTPUT_DIR = os.path.join(self.BASE_DIR, "datasets")
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        
        # Setup URL logging
        self.setup_url_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(os.path.dirname(__file__), 'crawler.log')),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_url_logging(self):
        """Setup separate logging for URLs"""
        # Create URL loggers
        self.url_discovery_logger = logging.getLogger('url_discovery')
        self.url_processing_logger = logging.getLogger('url_processing')
        self.url_statistics_logger = logging.getLogger('url_statistics')
        
        # Setup file handlers for URL logs
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # URL discovery log
        discovery_handler = logging.FileHandler(os.path.join(log_dir, 'urls_discovered.log'))
        discovery_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.url_discovery_logger.addHandler(discovery_handler)
        self.url_discovery_logger.setLevel(logging.INFO)
        
        # URL processing log
        processing_handler = logging.FileHandler(os.path.join(log_dir, 'urls_processed.log'))
        processing_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.url_processing_logger.addHandler(processing_handler)
        self.url_processing_logger.setLevel(logging.INFO)
        
        # URL statistics log
        stats_handler = logging.FileHandler(os.path.join(log_dir, 'urls_statistics.log'))
        stats_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.url_statistics_logger.addHandler(stats_handler)
        self.url_statistics_logger.setLevel(logging.INFO)
        
    def log_url_discovery(self, url: str, source_url: str = "", depth: int = 0):
        """Log URL discovery"""
        log_entry = f"DISCOVERED | {url} | Source: {source_url} | Depth: {depth}"
        self.url_discovery_logger.info(log_entry)
        
    def log_url_processing(self, url: str, status: str, response_time: float = 0,
                         content_length: int = 0, error: str = ""):
        """Log URL processing with detailed information"""
        log_entry = (f"PROCESSED | {url} | Status: {status} | "
                    f"Response_Time: {response_time:.3f}s | "
                    f"Content_Length: {content_length} bytes")
        if error:
            log_entry += f" | Error: {error}"
        self.url_processing_logger.info(log_entry)
        
    def log_url_statistics(self, section: str, total_discovered: int, total_processed: int,
                        successful: int, failed: int, total_time: float):
        """Log detailed statistics for a section"""
        log_entry = (f"STATISTICS | Section: {section} | "
                    f"Discovered: {total_discovered} | "
                    f"Processed: {total_processed} | "
                    f"Successful: {successful} | "
                    f"Failed: {failed} | "
                    f"Success_Rate: {(successful/total_processed*100):.1f}% | "
                    f"Total_Time: {total_time:.1f}s | "
                    f"Avg_Time_Per_URL: {total_time/total_processed:.3f}s")
        self.url_statistics_logger.info(log_entry)
        
    def get_random_user_agent(self) -> str:
        """Get a random user agent from the configured list"""
        return random.choice(self.config.user_agents)
        
    def make_request(self, url: str, retry_count: int = 0) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and rate limiting"""
        try:
            # Rate limiting
            delay = random.uniform(self.config.delay_min, self.config.delay_max)
            time.sleep(delay)
            
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(
                url, 
                timeout=self.config.timeout,
                headers=headers
            )
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            if retry_count < self.config.max_retries:
                self.logger.warning(f"Retry {retry_count + 1}/{self.config.max_retries} for {url}: {str(e)}")
                time.sleep(self.config.retry_delay * (retry_count + 1))
                return self.make_request(url, retry_count + 1)
            else:
                self.logger.error(f"Failed to fetch {url} after {self.config.max_retries} retries: {str(e)}")
                return None
                
    def get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc
        
    def is_internal_link(self, base_url: str, link: str) -> bool:
        """Check if link is internal to the base domain"""
        return self.get_domain(base_url) == self.get_domain(link)
        
    def extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML"""
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove unwanted tags
        for tag in soup(["script", "style", "noscript", "iframe", "nav", "footer"]):
            tag.extract()
            
        # Extract structured information
        title = soup.title.string if soup.title else ""
        
        # Extract main content (try to find main content areas)
        main_content = ""
        for selector in ['main', 'article', '.content', '#content', '.main-content']:
            main_elem = soup.select_one(selector)
            if main_elem:
                main_content = " ".join(main_elem.stripped_strings)
                break
                
        # If no main content found, use body
        if not main_content:
            main_content = " ".join(soup.stripped_strings)
            
        # Clean up text
        lines = [line.strip() for line in main_content.split('\n') if line.strip()]
        return '\n'.join(lines)
        
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract internal links from page"""
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            
            # Clean URL (remove fragments, etc.)
            parsed = urlparse(full_url)
            clean_url = parsed._replace(fragment="", query="").geturl()
            
            if self.is_internal_link(base_url, clean_url) and clean_url not in self.visited:
                links.append(clean_url)
                
        return list(set(links))  # Remove duplicates
        
    def scrape_url(self, url: str, section: str, depth: int) -> Optional[ScrapedItem]:
        """Scrape a single URL and return structured data"""
        try:
            response = self.make_request(url)
            if not response:
                return None
                
            soup = BeautifulSoup(response.text, "html.parser")
            text = self.extract_text_from_html(response.text)
            
            # Extract metadata
            meta = {
                'content_length': len(response.content),
                'response_time': response.elapsed.total_seconds() if response.elapsed else 0,
                'charset': response.encoding or 'unknown',
            }
            
            # Extract structured data if available
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    meta['structured_data'] = json.loads(script.string)
                except:
                    pass
                    
            return ScrapedItem(
                url=url,
                title=soup.title.string if soup.title else "",
                text=text,
                section=section,
                depth=depth,
                timestamp=datetime.now().isoformat(),
                status_code=response.status_code,
                content_type=response.headers.get('content-type', ''),
                meta=meta
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")
            return None
            
    def scrape_section(self, base_url: str, section_name: str, progress_tracker: ProgressTracker) -> List[ScrapedItem]:
        """Scrape a complete section with progress tracking"""
        items = []
        to_visit = [(base_url, 0)]  # (url, depth)
        section_urls = set()
        
        # First pass: collect all URLs
        print(f"\n🔍 Descubriendo URLs en sección: {section_name}")
        discovery_start = time.time()
        
        # Log initial URL discovery
        self.log_url_discovery(base_url, "START", 0)
        
        while to_visit:
            next_level = []
            for url, depth in to_visit:
                if url in section_urls or depth >= self.config.max_depth:
                    continue
                    
                section_urls.add(url)
                self.log_url_discovery(url, to_visit[0][0] if to_visit else base_url, depth)
                
                try:
                    response = self.make_request(url)
                    if response and response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")
                        links = self.extract_links(soup, base_url)
                        
                        for link in links:
                            if link not in section_urls:
                                next_level.append((link, depth + 1))
                                self.log_url_discovery(link, url, depth + 1)
                                
                except Exception as e:
                    self.logger.warning(f"Error discovering links from {url}: {str(e)}")
                    
            to_visit = next_level
            
        discovery_time = time.time() - discovery_start
        print(f"🔍 Descubrimiento completado: {len(section_urls)} URLs en {discovery_time:.1f}s")
        print(f"📝 URLs descubiertas registradas en logs/urls_discovered.log")
        
        # Start progress tracking
        progress_tracker.start_section(section_name, len(section_urls))
        
        # Second pass: scrape all URLs
        section_start_time = time.time()
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_url = {
                executor.submit(self.scrape_url, url, section_name, 0): url
                for url in section_urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    item = future.result()
                    if item:
                        items.append(item)
                        progress_tracker.update_progress(url, True)
                        # Log successful processing
                        response_time = item.meta.get('response_time', 0)
                        content_length = item.meta.get('content_length', 0)
                        self.log_url_processing(url, "SUCCESS", response_time, content_length)
                    else:
                        progress_tracker.update_progress(url, False, "Failed to scrape")
                        self.log_url_processing(url, "FAILED", 0, 0, "Failed to scrape")
                except Exception as e:
                    progress_tracker.update_progress(url, False, str(e))
                    self.log_url_processing(url, "ERROR", 0, 0, str(e))
                    
        # Save results
        self.save_items(items, section_name)
        
        # Log section statistics
        section_time = time.time() - section_start_time
        self.log_url_statistics(
            section_name,
            len(section_urls),
            len(section_urls),
            len(items),
            len(section_urls) - len(items),
            section_time
        )
        
        progress_tracker.finish_section(section_name, len(items))
        
        return items
        
    def save_items(self, items: List[ScrapedItem], section_name: str):
        """Save scraped items to file"""
        if not items:
            return
            
        if self.config.output_format.lower() == 'json':
            output_path = os.path.join(self.OUTPUT_DIR, f"{section_name}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump([asdict(item) for item in items], f, ensure_ascii=False, indent=2)
                
        elif self.config.output_format.lower() == 'csv':
            import csv
            output_path = os.path.join(self.OUTPUT_DIR, f"{section_name}.csv")
            
            if items:
                with open(output_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=asdict(items[0]).keys())
                    writer.writeheader()
                    for item in items:
                        writer.writerow(asdict(item))
                        
        self.logger.info(f"Saved {len(items)} items to {output_path}")
        
    def run(self, urls_base: List[str]):
        """Run the crawler on multiple base URLs"""
        progress_tracker = ProgressTracker(len(urls_base))
        all_items = []
        
        try:
            for url in urls_base:
                section_name = urlparse(url).path.strip("/").split("/")[0] or "root"
                items = self.scrape_section(url, section_name, progress_tracker)
                all_items.extend(items)
                
            progress_tracker.finish_all()
            
            # Save combined dataset
            if all_items:
                self.save_items(all_items, "combined_dataset")
                
            return all_items
            
        except KeyboardInterrupt:
            print("\n⚠️  Crawling interrupted by user")
            return all_items
        except Exception as e:
            self.logger.error(f"Fatal error during crawling: {str(e)}")
            return all_items

def main():
    """Main function to run the crawler"""
    # Configuration
    config = CrawlerConfig(
        max_depth=2,
        delay_min=1.0,
        delay_max=3.0,
        max_workers=3,
        output_format="json",
        log_level="INFO"
    )
    
    # URLs to crawl
    URLS_BASE = [
        "https://www.duoc.cl/admision/",
        "https://www.duoc.cl/carreras",
        "https://www.duoc.cl/oferta-academica",
    ]
    
    # Create and run crawler
    crawler = DuocCrawler(config)
    items = crawler.run(URLS_BASE)
    
    print(f"\n🎉 Crawling completed! Total items scraped: {len(items)}")

if __name__ == "__main__":
    main()