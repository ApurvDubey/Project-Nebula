import socket
import ipaddress
import urllib.parse
import httpx
from bs4 import BeautifulSoup
import markdownify

MAX_BYTES = 5 * 1024 * 1024  # 5 MB limit

async def fetch_url_to_markdown(url: str) -> tuple[str, str]:
    """
    Fetches the HTML from a URL, extracts the main content using BeautifulSoup,
    and converts it to Markdown.
    
    Returns:
        tuple[str, str]: (Page Title, Markdown Content)
    """
    # Parse URL to get hostname
    parsed = urllib.parse.urlparse(str(url))
    host = parsed.hostname
    
    # 1. DNS Resolution and IP Validation (SSRF Protection)
    # Note on DNS Rebinding: We resolve the hostname here, check the IP, and then pass
    # the hostname to httpx which will re-resolve it. A sophisticated DNS rebinding
    # attacker could theoretically change the IP between these two resolutions. Since
    # this is a self-hosted tool and we also disable redirects, this is an accepted residual risk.
    try:
        ip_info = socket.getaddrinfo(host, None)
        ip_str = ip_info[0][4][0]
        ip_obj = ipaddress.ip_address(ip_str)
        # Note: is_private in Python covers link-local (169.254.x.x) AWS metadata IPs.
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
            raise ValueError(f"Blocked private/reserved IP: {ip_str}")
    except Exception as e:
        raise ValueError(f"Invalid target host: {e}")

    # 2. Fetch with size limit and no redirects
    html_content = b""
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        async with client.stream("GET", str(url)) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                raise ValueError("Redirects are blocked for security")
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                html_content += chunk
                if len(html_content) > MAX_BYTES:
                    raise ValueError("Response exceeds maximum size limit (5MB)")
                    
    html_content_str = html_content.decode('utf-8', errors='replace')
        
    soup = BeautifulSoup(html_content_str, 'html.parser')
    
    # Extract and sanitize title
    raw_title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled Webpage"
    title = "".join(c for c in raw_title if c.isalnum() or c in " -_").strip()[:100]
    if not title:
        title = "Untitled Webpage"
    
    # Clean up unnecessary tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
        
    # Extract main content (try common content wrappers first, fallback to body)
    main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
    
    if not main_content:
        # Fallback if the page is weirdly structured
        main_content = soup
        
    # Convert to markdown
    md_content = markdownify.markdownify(str(main_content), heading_style="ATX").strip()
    
    return title, md_content
