from datetime import datetime, timedelta
import scrapy
# https://monkeylearn.com/blog/filtering-startup-news-machine-learning/#scraping-from-tech-news-sites
# https://doc.scrapy.org/en/latest/intro/tutorial.html
# to run this use commands:
# 1. scrapy crawl techcrunch -o output.json -a date=2019-06-01
# 2. scrapy crawl techcrunch -o output.json -a start=2019-06-01 -a end=2019-06-07

class TechCrunchSpider(scrapy.Spider):
    name = "techcrunch"

    def __init__(self, date='', start='', end='', **kwargs):
        if len(date) > 0:
            self.start_date = datetime.strptime(date, '%Y-%m-%d')
            self.end_date = self.start_date
        elif (len(start) > 0 and len(end) > 0):
            self.start_date = datetime.strptime(start, '%Y-%m-%d')
            self.end_date = datetime.strptime(end, '%Y-%m-%d')
        else:
            self.start_date = datetime.today().strftime('%Y-%m-%d')
            self.end_date = self.start_date
        super().__init__(**kwargs)

    def start_requests(self):        
        curr_date = self.start_date
        
        while curr_date <= self.end_date:
            new_request = scrapy.Request(self.generate_url(curr_date))
            new_request.meta["date"] = curr_date
            new_request.meta["page_number"] = 1
            yield new_request
            curr_date += timedelta(days=1)


    def generate_url(self, date, page_number=None):
        url = 'https://techcrunch.com/' + date.strftime("%Y/%m/%d") + "/"
        if page_number:
            url  += "page/" + str(page_number) + "/"
        return url


    def parse(self, response):
        date = response.meta['date']
        page_number = response.meta['page_number']

        # when I access a page number that doesn't exist I get 404
        # I could use the pagination buttons, but this is less work
        if response.status == 200:
            articles = response.xpath('//h2[@class="post-block__title"]/a/@href').extract()
            for url in articles:
                request = scrapy.Request(url,
                                callback=self.parse_article)
                request.meta['date'] = date
                yield request

            url = self.generate_url(date, page_number+1)
            request = scrapy.Request(url,
                            callback=self.parse)
            request.meta['date'] = date
            request.meta['page_number'] = page_number
            yield request



    def parse_article(self, response):

        yield {
            'title': "".join(response.xpath('//h1/text()').extract()),
            'text': "".join(response.xpath('//div[starts-with(@class,"article-content")]/p//text()').extract()),
            'date': response.meta['date'].strftime("%Y/%m/%d"),
            'url' : response.url
        }