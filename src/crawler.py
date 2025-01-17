import asyncio
import psutil
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import requests
from xml.etree import ElementTree
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# Set Playwright browser path
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.expanduser("~/Library/Caches/ms-playwright")

@dataclass
class CrawlProgress:
    status: str
    memory_usage: float
    pages_crawled: int = 0
    total_pages: int = 0
    time_elapsed: float = 0
    is_complete: bool = False
    error: Optional[str] = None

class WebCrawler:
    def __init__(self, progress_callback: Callable[[CrawlProgress], None]):
        print("Initializing WebCrawler...")
        self.progress_callback = progress_callback
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=True
        )
        self.start_time = None
        self.process = psutil.Process(os.getpid())
        self.crawled_content = {}  # Store crawled content

    async def crawl_single_page(self, url: str) -> str:
        """Crawl a single page with better error handling and retries"""
        print(f"Starting single page crawl for: {url}")
        self.start_time = datetime.now()
        max_retries = 3
        retry_count = 0

        progress = CrawlProgress(
            status="Initializing crawler...",
            memory_usage=self.get_memory_usage(),
            pages_crawled=0,
            total_pages=1
        )
        self.progress_callback(progress)

        while retry_count < max_retries:
            crawler = None
            try:
                crawler = AsyncWebCrawler(config=self.browser_config)
                await crawler.start()

                progress.status = f"Crawling page... (Attempt {retry_count + 1}/{max_retries})"
                self.progress_callback(progress)

                result = await asyncio.wait_for(
                    crawler.arun(
                        url=url,
                        config=CrawlerRunConfig(
                            cache_mode=CacheMode.BYPASS
                        )
                    ),
                    timeout=60
                )

                if result and result.markdown:
                    progress.status = "Crawling completed successfully!"
                    progress.pages_crawled = 1
                    progress.is_complete = True
                    self.crawled_content = {"result": result.markdown}  # Store content
                    self.progress_callback(progress)
                    return result.markdown

                progress.error = "Failed to retrieve content"
                self.progress_callback(progress)
                retry_count += 1

            except Exception as e:
                print(f"Error during crawl (attempt {retry_count + 1}): {e}")
                retry_count += 1
                progress.error = f"Error: {str(e)}"
                self.progress_callback(progress)

            finally:
                if crawler:
                    try:
                        await crawler.close()
                    except:
                        pass

            if retry_count < max_retries:
                await asyncio.sleep(2)

        progress.status = "Crawling failed after all attempts"
        progress.is_complete = True
        self.progress_callback(progress)
        return ""

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            return self.process.memory_info().rss / (1024 * 1024)
        except Exception as e:
            print(f"Error getting memory usage: {e}")
            return 0.0

    async def crawl_sitemap(self, sitemap_url: str, max_concurrent: int = 3) -> Dict[str, str]:
        """Crawl sitemap with improved stability and error handling"""
        print(f"Starting sitemap crawl for: {sitemap_url}")
        self.start_time = datetime.now()
        
        # First, try common sitemap locations if the provided URL fails
        sitemap_urls_to_try = [
            sitemap_url,
            sitemap_url.replace('sitemap.xml', 'sitemap_index.xml'),
            sitemap_url.replace('sitemap.xml', 'sitemap_news.xml'),
            sitemap_url.replace('/sitemap.xml', '/sitemap/sitemap.xml')
        ]
        
        urls = []
        sitemap_found = False
        results = {}  # Initialize results dictionary
        
        for try_url in sitemap_urls_to_try:
            try:
                print(f"Trying sitemap at: {try_url}")
                response = requests.get(try_url, timeout=30)
                
                if response.status_code == 200:
                    try:
                        root = ElementTree.fromstring(response.content)
                        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                        found_urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
                        
                        if found_urls:
                            urls = found_urls
                            sitemap_found = True
                            print(f"Found valid sitemap at {try_url} with {len(urls)} URLs")
                            break
                    except ElementTree.ParseError:
                        continue
                        
            except requests.exceptions.RequestException:
                continue

        if not sitemap_found:
            # If no sitemap found, try to crawl just the base URL
            base_url = sitemap_url.replace('/sitemap.xml', '')
            if base_url.endswith('/'):
                base_url = base_url[:-1]
                
            progress = CrawlProgress(
                status="No sitemap found. Treating as single page...",
                memory_usage=self.get_memory_usage(),
                pages_crawled=0,
                total_pages=1
            )
            self.progress_callback(progress)
            
            try:
                crawler = AsyncWebCrawler(config=self.browser_config)
                await crawler.start()
                
                result = await crawler.arun(
                    url=base_url,
                    config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                )
                
                if result.success and result.markdown:
                    progress.status = "Successfully crawled as single page"
                    progress.pages_crawled = 1
                    progress.is_complete = True
                    self.progress_callback(progress)
                    return {base_url: result.markdown}
                else:
                    progress.status = "Failed to crawl page"
                    progress.error = "Could not retrieve content from the page"
                    self.progress_callback(progress)
                    return {}
                    
            except Exception as e:
                progress.status = "Error crawling page"
                progress.error = str(e)
                self.progress_callback(progress)
                return {}
            finally:
                if crawler:
                    try:
                        await crawler.close()
                    except:
                        pass

        # Continue with multi-page crawling if sitemap was found
        progress = CrawlProgress(
            status=f"Found {len(urls)} URLs in sitemap",
            memory_usage=self.get_memory_usage(),
            pages_crawled=0,
            total_pages=len(urls)
        )
        self.progress_callback(progress)

        crawler = None
        try:
            crawler = AsyncWebCrawler(config=self.browser_config)
            await crawler.start()

            async def process_url(url: str):
                try:
                    print(f"Crawling: {url}")
                    result = await crawler.arun(
                        url=url,
                        config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                    )
                    if result.success and result.markdown:
                        print(f"Successfully crawled: {url}")
                        return url, result.markdown
                    print(f"No content retrieved from: {url}")
                    return url, ""
                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                    return url, ""

            # Process in smaller batches
            batch_size = min(max_concurrent, 10)
            for i in range(0, len(urls), batch_size):
                print(f"\n=== Processing Batch {i//batch_size + 1} ===")
                batch = urls[i:i + batch_size]
                tasks = []
                
                for url in batch:
                    task = asyncio.create_task(process_url(url))
                    tasks.append(task)

                print(f"Awaiting batch results...")
                batch_results = await asyncio.gather(*tasks)
                
                # Update progress
                successful_in_batch = 0
                for url, content in batch_results:
                    if content:
                        results[url] = content
                        successful_in_batch += 1
                
                progress.pages_crawled += successful_in_batch
                print(f"Batch complete: {successful_in_batch} pages successful")
                print(f"Total progress: {progress.pages_crawled}/{progress.total_pages}")
                
                progress.status = f"Crawling pages... ({progress.pages_crawled}/{progress.total_pages})"
                self.progress_callback(progress)
                
                print(f"Completed batch {i//batch_size + 1}, Total: {len(results)}/{len(urls)} pages")
                await asyncio.sleep(0.5)  # Small delay between batches
            if not results:
                progress.status = "No content could be retrieved"
                progress.error = "Failed to retrieve content from any URLs"
            else:
                progress.status = f"Successfully crawled {len(results)} pages"
                
            progress.is_complete = True
            self.progress_callback(progress)

        except Exception as e:
            print(f"Error during sitemap crawl: {e}")
            progress.error = str(e)
            self.progress_callback(progress)
        finally:
            if crawler:
                try:
                    await crawler.close()
                except:
                    pass

        return results

    def get_sitemap_urls(self, sitemap_url: str) -> List[str]:
        """Fetch URLs from sitemap with better error handling"""
        print(f"Fetching sitemap from: {sitemap_url}")
        try:
            response = requests.get(sitemap_url, timeout=30)
            response.raise_for_status()
            
            root = ElementTree.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
            
            if not urls:
                print("No URLs found in sitemap")
                raise Exception("Sitemap is empty or has invalid format")
                
            print(f"Found {len(urls)} URLs in sitemap")
            return urls
        except requests.exceptions.Timeout:
            print("Sitemap request timed out")
            raise Exception("Sitemap request timed out")
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch sitemap: {e}")
            raise
        except ElementTree.ParseError:
            print("Invalid sitemap format")
            raise Exception("Invalid sitemap format - Not a valid XML file")
        except Exception as e:
            print(f"Error fetching sitemap: {e}")
            raise

    def clean_content_for_rag(self, content: str) -> str:
        """Clean crawled content for RAG usage"""
        import re
        
        # Remove image markdown
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        
        # Clean up malformed URLs while keeping link text
        content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)
        
        # Remove multiple newlines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Clean up special characters
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        
        # Remove any remaining markdown artifacts
        content = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', content)
        
        return content.strip()

    def export_to_txt(self, content: str, filepath: str, clean_for_rag: bool = True):
        """Export crawled content to a text file"""
        try:
            if clean_for_rag:
                content = self.clean_content_for_rag(content)
                
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error exporting to file: {e}")
            return False