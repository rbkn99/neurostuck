from bs4 import BeautifulSoup, SoupStrainer
import re
import requests
import pandas as pd
import lxml
import cchardet
from joblib import Parallel, delayed
import multiprocessing

MAX_PAGE = 195

base_url = 'https://ficbook.net'
homestuck_url = base_url + '/fanfiction/comics/homestuck'
requests_session = requests.Session()


def get_content(page_soup):
    story_content = page_soup.find('div', id='content')
    if not story_content:
        return ''
    content = re.sub(r'\t', '\n\n\n\n', story_content.text)
    return content


def get_pairings(page_soup: BeautifulSoup):
    class_ = 'pairing-link'
    first_pairing = page_soup.find('a', class_=class_)
    if not first_pairing:
        return ''
    pairings = first_pairing.parent.findAll('a', class_=class_)
    return ','.join([p.text for p in pairings])


def process_page(page):
    print('Crawling page #{}'.format(page))

    fics_raw_data = []
    fic_list_html = requests_session.get(homestuck_url + '?p=' + str(page)).content
    fic_soup = BeautifulSoup(fic_list_html, 'lxml')
    stories_links = fic_soup.findAll('a', href=re.compile('/readfic/*'))

    story_dict = {}
    for link in stories_links:
        story_dict['Title'] = link.string
        full_link = base_url + link['href']
        print('Traversing link:', full_link)
        story_soup = BeautifulSoup(requests_session.get(full_link).content, 'lxml')
        story_dict['Url'] = full_link
        story_dict['Pairings'] = ''

        for story_part in story_soup.findAll('a', class_='part-link'):
            story_part_link = base_url + story_part['href']
            print('Traversing sub link:', story_part_link)
            content_page_soup = BeautifulSoup(requests_session.get(story_part_link).content, 'lxml')
            content = get_content(content_page_soup)
            if len(content) > 0:
                story_dict['Url'] = story_part_link
                story_dict['Pairings'] = get_pairings(content_page_soup)
                story_dict['Content'] = content
                fics_raw_data.append(story_dict.copy())
        content = get_content(story_soup)
        if len(content) > 0:
            story_dict['Pairings'] = get_pairings(story_soup)
            story_dict['Content'] = content
            fics_raw_data.append(story_dict.copy())

    fic_df = pd.DataFrame(fics_raw_data)
    fic_df.to_csv('data/ficbook_page{}.csv'.format(page), sep='\t')
    print('-------------------------------')


num_cores = multiprocessing.cpu_count()
Parallel(n_jobs=num_cores, prefer="threads")(delayed(process_page)(page) for page in range(1, MAX_PAGE + 1))
