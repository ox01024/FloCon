import os
import re
import sys
import urllib.request as request
import logging
from multiprocessing.dummy import Pool as ThreadPool



class Talk:
    def __init__(self, talk_name: str, talk_address: str) -> None:
        self.name = talk_name
        self.address = talk_address

    def _assemble_talk_link(self, talk_relative_address: str) -> list:
        return 'https://insights.sei.cmu.edu{}'.format(talk_relative_address)
    
    @property
    def _raw(self) -> str:
        while True:
            try:
                r = request.urlopen(self.address)
                break
            except Exception as e:
                logging.error(e)
                logging.warning('Retrying  {} talk raw read'.format(self.name))
        return r.read().decode('utf-8')
        
    @property
    def pdf_address(self) -> str:
        try:
            pdf_relative_address = re.findall(r'\"asset_action_0\"\shref=\"(.*?)\"', self._raw)[0]
            return self._assemble_talk_link(pdf_relative_address)
        except IndexError:
            return None
    
    @property
    def overview(self) -> str:
        overview = re.findall(r'\"text-xl font-light\">\s*(.*?)\s*</div>', self._raw)[0]
        return overview


class Flocon:
    def __init__(self, year) -> None:
        self.assets_addres = 'https://insights.sei.cmu.edu/library/flocon-{}-'.format(
            year)

    def _assemble_talk_link(self, talk_relative_address: str) -> list:
        return 'https://insights.sei.cmu.edu{}'.format(talk_relative_address)

    @property
    def talks(self) -> list[Talk]:
        talks_info = []
        extract_talk_relative_address_re = re.compile(
            r'<a href=\"(.*?)\" class=\"link--red block\">\s.*?>(.*?)<\/h4>')
        
        for index,end_tag in enumerate(['assets', 'presentations' , 'collection']):
            try:
                r = request.urlopen(self.assets_addres+end_tag)
                self.assets_addres = r.url
                break
            except Exception as e:
                continue
        talk_index = r.read().decode('utf-8')
        index_talks_info = extract_talk_relative_address_re.findall(talk_index)
        talks_info.extend(index_talks_info)

        pages = [int(pagenumber) for pagenumber in re.findall(
            r'\:bg-gray-200\">\s*(\d)\s*<\/a>', talk_index)]
        for pagenumber in pages:
            r = request.urlopen('{}?page={}'.format(
                self.assets_addres, pagenumber))
            
            talks_info.extend(extract_talk_relative_address_re.findall(r.read().decode('utf-8')))
        return [Talk(name, self._assemble_talk_link(relative_address)) for relative_address, name in talks_info]


def dump_talk(talk: Talk, year: int) -> None:
    directory = './{}/{}'.format(year, talk.name.replace('/', ''))
    if not os.path.exists(directory):
        os.makedirs(directory)
    logging.info('Dumping {} talk'.format(talk.name))

    
    with open('{}/README.md'.format(directory), 'w') as f:
        msg = '''
# {}

{}

[原文｜original]({})
        '''.format(talk.name, talk.overview, talk.address)
        f.write(msg)
    
    file_path = '{}/flocon_{}_{}.pdf'.format(directory, year, talk.name.replace('/', ''))
    if os.path.exists(file_path):
        logging.info('Skipping {} talk'.format(talk.name))
        return
     
    pdf_address = talk.pdf_address
    if not pdf_address:
        logging.warning('No pdf address for {} talk'.format(talk.name))
        return

    
    
    while True:
        try:
            request.urlretrieve(pdf_address, file_path)
            break
        except Exception as e:
            logging.exception(e)
            logging.warning('Retrying to download {} talk'.format(talk.name))

    
    logging.info('Done dumping {} talk'.format(talk.name))
    


def dump_talk_from_flocon(year: int) -> None:
    logging.info('Dumping flocon {} talks'.format(year))
    flocon = Flocon(year)
    directory = '{}'.format(year)
    if not os.path.exists(directory):
        os.makedirs(directory)
    talks = flocon.talks
    logging.info('Dumping {} talks'.format(len(talks)))
    
    # task_args = [(talk, year) for talk in talks]
    # with ThreadPool(8) as pool:
    #     pool.starmap(dump_talk, task_args)
    #     pool.close()
    #     pool.join()
    for talk in talks:
        dump_talk(talk, year)
        
    logging.info('Done dumping flocon {} talks'.format(year))
    
    
    
    flocon_readme_path = './{}/README.md'.format(year)
    with open(flocon_readme_path, 'w') as f:
        msg = '''
# Flocon {} talks

[原文｜original]({})     
'''.format(year, flocon.assets_addres)
        f.write(msg)
    dirs = os.listdir(directory)
    
    with open(flocon_readme_path, 'a+') as f:
        for d in dirs:
            if d == 'README.md' or 'DS_Store' in d:
                continue
            with open('{}/{}/README.md'.format(directory,d), 'r') as ff:
                talk_overview = ff.read().replace('#',"##")
                f.write(talk_overview)
                
        



if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s [%(levelname)s]\t%(message)s')
    logging.getLogger().setLevel(logging.DEBUG)
    
    
    args=sys.argv
    if len(args) > 1:
        dump_talk_from_flocon(int(args[1]))
    else:
        print('Usage: python dumptalk.py [year]')
    