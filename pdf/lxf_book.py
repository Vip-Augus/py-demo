# coding=utf-8
from __future__ import unicode_literals

import requests
from bs4 import BeautifulSoup
import logging
import os
import re
import time
from urllib.parse import urlparse
import pdfkit

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
</head>
<body>
{content}
</body>
</html>
"""


class Crawler(object):
    """
    爬虫类
    """
    name = None

    def __init__(self, name, start_url):
        """
        初始化
        :param name: 将要保存为PDF的名字 
        :param start_url:  爬虫入口的url
        """
        self.name = name
        self.start_url = start_url
        self.domain = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(self.start_url))

    @staticmethod
    def request(url, **kwargs):
        """
        网络请求,返回response对象
        :param url: 
        :param kwargs: 
        :return: 
        """
        response = requests.get(url, **kwargs)
        return response

    def parse_menu(self, response):
        """
        从response解析出所有目录的URL链接
        :param response: 
        :return: 
        """
        raise NotImplementedError

    def parse_body(self, response):
        """
        解析正文,由子类实现
        :param response: 
        :return: 
        """
        raise NotImplementedError

    def run(self):
        start = time.time()
        options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
            'custom-header': [
                ('Accept-Encoding', 'gzip')
            ],
            'cookie': [
                ('cookie-name1', 'cookie-value1'),
                ('cookie-name2', 'cookie-value2')
            ],
            'outline-depth': 10,
        }
        htmls = []
        for index, url in enumerate(self.parse_menu(self.request(self.start_url))):
            html = self.parse_body(self.request(url))
            f_name = str(index) + ".html"
            with open(f_name, 'wb') as f:
                f.write(html)
            htmls.append(f_name)

        config = pdfkit.configuration(wkhtmltopdf=r"F:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
        pdfkit.from_file(htmls, self.name + '.pdf', options=options, configuration=config)
        for html in htmls:
            os.remove(html)
        total_time = time.time() - start
        print(u"总共耗时: %f秒" % total_time)


class JingQPythonCrawler(Crawler):
    """
    廖雪峰Python3教程
    """

    def parse_menu(self, response):
        """
        解析目录结构,获取所有URL目录列表
        :param response: 爬虫返回的response对象
        :return: url生成器 
        """
        soup = BeautifulSoup(response.content, "html.parser")
        menu_tag = soup.find_all(class_="uk-nav uk-nav-side")[1]
        for li in menu_tag.find_all("li"):
            url = li.a.get("href")
            if not url.startswith("http"):
                #补全为全路径
                url = self.domain + url
            yield url

    def parse_body(self, response):
        """
        解析正文
        :param response: 爬虫返回的response对象 
        :return: 返回处理后的html文本
        """
        try:
            soup = BeautifulSoup(response.content, "html.parser")
            body = soup.find_all(class_="x-wiki-content x-main-content")[0]

            # 加入标题,居中显示
            title = soup.find('h4').get_text()
            center_title = soup.new_tag("center")
            title_tag = soup.new_tag('h1')
            title_tag.string = title
            center_title.insert(1, title_tag)
            body.insert(1, center_title)

            html = str(body)
            # body中的img标签的src相对路径改成绝对路径
            pattern = "(<img .*?src=\")(.*?)(\")"

            def func(m):
                if not m.group(2).startswith("http"):
                    rtn = "".join([m.group(1), self.domain, m.group(2), m.group(3)])
                    return rtn
                else:
                    return "".join([m.group(1), m.group(2), m.group(3)])

            html = re.compile(pattern).sub(func, html)
            html = html_template.format(content=html)
            html = html.encode("utf-8")
            return html
        except Exception as e:
            logging.error("解析错误", exc_info=True)


if __name__ == '__main__':
    start_url = "https://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000"
    crawler = JingQPythonCrawler("廖雪峰Python", start_url)
    crawler.run()