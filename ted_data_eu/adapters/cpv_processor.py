from pathlib import Path
from typing import Optional, List

import pandas
from pandas import DataFrame

from ted_data_eu import PROJECT_RESOURCES_PATH

CPV_TABLE_DEFAULT_PATH = PROJECT_RESOURCES_PATH / 'cpv_list.xlsx'

CPV_SHEET_NAME = 'CPV codes'
CPV_FULL_CODE_COLUMN_NAME = 'FULL CODE'
CPV_CODE_COLUMN_NAME = 'CODE'
CPV_LABEL_COLUMN_NAME = 'EN'

CPV_MIN_RANK = 0
CPV_MAX_RANK = CPV_MIN_RANK + 4
CPV_STR_LENGTH = 8


class CPVProcessor(object):
    """
    CPVProcessor is a class that provides methods to process CPV codes.
    It is used to check if a CPV code is valid and to get the rank of a CPV code.
    It is also used to get the parent CPV code of a given CPV code at a given rank.
    """

    def __init__(self, cpv_table_path: Path = CPV_TABLE_DEFAULT_PATH):
        """
        CPVProcessor constructor.
        """
        self.dataframe: DataFrame = pandas.read_excel(
            cpv_table_path,
            sheet_name=CPV_SHEET_NAME,
            header=0,
            dtype={
                CPV_FULL_CODE_COLUMN_NAME: str,
                CPV_CODE_COLUMN_NAME: str,
                CPV_LABEL_COLUMN_NAME: str
            }
        )
        self.dataframe.fillna(0)

    def cpv_exists(self, cpv_code: str) -> bool:
        """
        Check if a CPV code exists in the CPV table.
        :param cpv_code: CPV code to check.
        :return: True if the CPV code exists, False otherwise.
        """
        return cpv_code in self.dataframe[CPV_CODE_COLUMN_NAME].values

    def get_cpv_rank(self, cpv_code: str) -> Optional[int]:
        """
        Get the rank of a CPV code.
        :param cpv_code: CPV code to check.
        :return: The rank of the CPV code if it exists, None otherwise.
        """
        if not self.cpv_exists(cpv_code=cpv_code):
            return None
        if cpv_code.endswith('000000'):
            return CPV_MIN_RANK
        elif cpv_code.endswith('00000'):
            return CPV_MIN_RANK + 1
        elif cpv_code.endswith('0000'):
            return CPV_MIN_RANK + 2
        elif cpv_code.endswith('000'):
            return CPV_MIN_RANK + 3
        return CPV_MAX_RANK

    def _get_cpv_parent(self, cpv_code: str) -> Optional[str]:
        """
        Get the parent CPV code of a given CPV code.
        :param cpv_code: CPV code to check.
        :return: The parent CPV parent code if it exists, None otherwise.
        """
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

    def get_cpv_parent_code_by_rank(self, cpv_code: str, rank: int) -> Optional[str]:
        """
        Get the parent CPV code of a given CPV code at a given rank.
        :param cpv_code: CPV code to check.
        :param rank: Rank of the parent CPV code.
        :return: The parent CPV parent code if it exists, None otherwise.
        """
        if (rank < CPV_MIN_RANK) or (rank > CPV_MAX_RANK):
            return None

        cpv_code_rank = self.get_cpv_rank(cpv_code=cpv_code)
        if (cpv_code_rank is None) or (cpv_code_rank < rank) or (cpv_code_rank == CPV_MIN_RANK):
            return None

        if cpv_code_rank == rank:
            return cpv_code

        cpv_parent_rank = self._get_cpv_parent(cpv_code)
        while self.get_cpv_rank(cpv_parent_rank) > rank:
            if cpv_parent_rank is None:
                return None
            cpv_parent_rank = self._get_cpv_parent(cpv_parent_rank)
        return cpv_parent_rank

    def get_unique_cpvs_parent_codes_by_rank(self, cpv_codes: List[str], rank: int) -> Optional[List]:
        """
        Get the parent CPV codes of a given list of CPV codes at a given rank.
        :param cpv_codes: List of CPV codes to check.
        :param rank: Rank of the parent CPV codes.
        :return: The unique parent CPV codes if they exist, None otherwise.
        """
        if cpv_codes is None:
            return None
        cpv_parent_codes = []
        for cpv_code in cpv_codes:
            cpv_parent_code = self.get_cpv_parent_code_by_rank(cpv_code, rank)
            if cpv_parent_code is not None:
                cpv_parent_codes.append(cpv_parent_code)

        return list(set(cpv_parent_codes)) if cpv_parent_codes else None

    def get_cpvs_ranks(self, cpv_codes: List[str]) -> Optional[List]:
        """
        Get the ranks of a given list of CPV codes.
        :param cpv_codes: List of CPV codes to check.
        :return: The ranks of the CPV codes if they exist, None otherwise.
        """
        if cpv_codes is None:
            return None
        cpv_ranks = []
        for cpv_code in cpv_codes:
            cpv_ranks.append(self.get_cpv_rank(cpv_code))

        return cpv_ranks if cpv_ranks else None

    def get_unique_cpvs_parent_codes(self, cpv_codes: List[str]) -> Optional[List]:
        """
        Get the parent CPV codes of a given list of CPV codes.
        :param cpv_codes: List of CPV codes to check.
        :return: The unique parent CPV codes if they exist, None otherwise.
        """
        if cpv_codes is None:
            return None
        cpv_parents = []
        for cpv_code in cpv_codes:
            cpv_rank = self.get_cpv_rank(cpv_code)
            if cpv_rank is not None:
                cpv_parent = self.get_cpv_parent_code_by_rank(cpv_code, cpv_rank - 1)
                if cpv_parent is not None:
                    cpv_parents.append(cpv_parent)

        return list(set(cpv_parents)) if cpv_parents else None


    def get_cpv_label_by_code(self, cpv_code: str) -> Optional[str]:
        """
        Get the label of a CPV code.
        :param cpv_code: CPV code to check.
        :return: The label of the CPV code if it exists, None otherwise.
        """
        if not self.cpv_exists(cpv_code=cpv_code):
            return None
        return self.dataframe.loc[self.dataframe[CPV_CODE_COLUMN_NAME] == cpv_code, CPV_LABEL_COLUMN_NAME].iloc[0]


    def get_all_cpvs_name_as_list(self) -> list:
        """
        Returns list of CPVs
        :return: CPV list
        """
        return self.dataframe[CPV_CODE_COLUMN_NAME].to_list()

    def get_all_cpvs_label_as_list(self) -> list:
        """
            Returns list of CPV labels
            :return: Label list
        """
        return self.dataframe[CPV_LABEL_COLUMN_NAME].to_list()

