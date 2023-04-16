from pathlib import Path
from typing import Optional, List

import pandas
from pandas import DataFrame

CPV_SHEET_NAME = 'CPV codes'
CPV_FULL_CODE_SHEET_NAME = 'FULL CODE'
CPV_CODE_SHEET_NAME = 'CODE'
CPV_NAME_SHEET_NAME = 'EN'

CPV_MIN_RANK = 0
CPV_MAX_RANK = CPV_MIN_RANK + 4
CPV_STR_LENGTH = 8


class CPVAlgorithms(object):
    def __init__(self, cpv_table_path: Path):
        self.dataframe: DataFrame = pandas.read_excel(
            cpv_table_path,
            sheet_name=CPV_SHEET_NAME,
            header=0,
            dtype={
                CPV_FULL_CODE_SHEET_NAME: str,
                CPV_CODE_SHEET_NAME: str,
                CPV_NAME_SHEET_NAME: str
            }
        )

    def cpv_exists(self, cpv_code: str) -> bool:
        return cpv_code in self.dataframe[CPV_CODE_SHEET_NAME].values

    def get_cpv_rank(self, cpv_code: str) -> Optional[int]:
        if not self.cpv_exists(cpv_code=cpv_code):
            return None
        cpv_code = cpv_code[::-1]
        if cpv_code.startswith('000000'):
            return CPV_MIN_RANK
        elif cpv_code.startswith('00000'):
            return CPV_MIN_RANK + 1
        elif cpv_code.startswith('0000'):
            return CPV_MIN_RANK + 2
        elif cpv_code.startswith('000'):
            return CPV_MIN_RANK + 3
        return CPV_MAX_RANK

    def _get_cpv_parent(self, cpv_code: str) -> Optional[str]:
        cpv_code_list = list(cpv_code)
        i = CPV_STR_LENGTH

        while cpv_code_list[i - 1] == '0':
            i -= 1
        if i < 2:
            return None
        if i > CPV_STR_LENGTH - 3:
            cpv_parent = cpv_code[:CPV_STR_LENGTH - 3]
            cpv_parent += '000'
        else:
            cpv_code_list[i - 1] = '0'
            cpv_parent = ''.join(cpv_code_list)

        if self.cpv_exists(cpv_parent):
            return cpv_parent
        return self._get_cpv_parent(cpv_code=cpv_parent)

    def get_cpv_rank_code(self, cpv_code: str, rank: int) -> Optional[str]:
        if (rank < CPV_MIN_RANK) or (rank > CPV_MAX_RANK):
            return None

        cpv_code_rank = self.get_cpv_rank(cpv_code=cpv_code)
        if cpv_code_rank is None or cpv_code_rank < rank or cpv_code_rank == CPV_MIN_RANK:
            return None

        if cpv_code_rank == rank:
            return cpv_code

        cpv_parent_rank = self._get_cpv_parent(cpv_code)
        while self.get_cpv_rank(cpv_parent_rank) > rank:
            if cpv_parent_rank is None:
                return None
            cpv_parent_rank = self._get_cpv_parent(cpv_parent_rank)
        return cpv_parent_rank

    def get_cpv_rank_code_list(self, cpv_codes: List[str], rank: int) -> Optional[List]:
        cpv_parent_ranks = []
        for cpv_code in cpv_codes:
            cpv_parent_rank = self.get_cpv_rank_code(cpv_code, rank)
            if cpv_parent_rank is not None:
                cpv_parent_ranks.append(cpv_parent_rank)

        return list(dict.fromkeys(cpv_parent_ranks)) if cpv_parent_ranks else None

    def get_cpv_rank_list(self, cpv_codes: List[str]) -> Optional[List]:
        cpv_ranks = []
        for cpv_code in cpv_codes:
            cpv_ranks.append(self.get_cpv_rank(cpv_code))

        return cpv_ranks if cpv_ranks else None


if __name__ == "__main__":
    cpvalg = CPVAlgorithms(Path('C:\\Users\\user\\Desktop\\ted-data-eu\\ted_data_eu\\resources\\cpv_list.xlsx'))
    cpvs = ['60112000', '60140000', '99999', '63712321', '63712311']
    # print(cpvalg.dataframe.head())
    print("alo")
    print(cpvs)
    print(
        cpvalg.get_cpv_rank_list(cpvs)
    )
    print(
        cpvalg.get_cpv_rank_code_list(cpv_codes=cpvs, rank=4)
    )

    print("salut")
