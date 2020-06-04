# InstaScraper

Super basic insta scraper for Lorenzo's dissertation! Given an instagram account loops through followers and 
collects stats including bio, number of posts, etc. Makes use of ChromeDriver and 
[Selenium](https://selenium-python.readthedocs.io/); this repository has win and mac webdrivers for Chrome 80, 
if you need a different webdriver you can download it from 
[here](https://sites.google.com/a/chromium.org/chromedriver/).

## Usage

Add module folder to path and import scraper class. All methods are documented (ish); also see demo notebook. 
For example when running from notebooks folder do: 

```python 
import sys 
sys.path.append("../") 
from insta_scraper import scraper as s
```

