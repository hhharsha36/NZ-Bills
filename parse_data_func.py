from urllib.request import Request, urlopen
from urllib.error import URLError
import pandas as pd
from time import sleep
from os.path import exists
from os import rename
from datetime import datetime


class UpdateData:
    def __init__(self):
        self._req_headers = {'User-Agent': 'Mozilla/5.0'}
        self.page_count: int = 0
        self.df: pd.DataFrame | None = None
        self.file_name = 'parsedData.csv'

    # def __call__(self, *args, **kwargs):
    #     self.update()

    def update(self):
        self.page_count = 0
        self.df = None
        for page_count in range(1, 55):
            req = self.get_data(page_count)
            webpage = urlopen(req).read()
            df_list = pd.read_html(webpage)[-1]

            if self.df is None:
                self.df = df_list
            else:
                self.df = pd.concat([self.df, df_list])
            print(f"\r{page_count}", end='')
        self.save_csv()
        return self.df

    def get_data(self, page_no, attempt=0):
        if attempt >= 10:
            return None
        try:
            return Request(
                f'https://www.parliament.nz/en/pb/bills-and-laws/bills-proposed-laws/all?Criteria.PageNumber={page_no}',
                headers=self._req_headers)
        except URLError:
            attempt += 1
            sleep(12)
            return self.get_data(page_no=page_no, attempt=attempt)

    def save_csv(self):
        if exists(self.file_name):
            rename(src=self.file_name,
                   dst=f"{self.file_name.replace('.csv', '')}_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}_.csv")
        self.df.to_csv(self.file_name)


if __name__ == '__main__':
    func = UpdateData()
    func.update()
