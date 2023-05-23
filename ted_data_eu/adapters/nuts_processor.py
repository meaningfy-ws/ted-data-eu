from pathlib import Path
from typing import Optional, List

import pandas
from pandas import DataFrame

from ted_data_eu import PROJECT_RESOURCES_PATH

NUTS_TABLE_DEFAULT_PATH = PROJECT_RESOURCES_PATH / 'nuts_list.xlsx'
NUTS_SHEET_NAME = 'NUTS'

NUTS_CODE_COLUMN_NAME = 'Code'
NUTS_LABEL_COLUMN_NAME = 'NUTS Name'
NUTS_ORIGINAL_LABEL_COLUMN_NAME = 'NUTS Original Name'
NUTS_LEVEL_COLUMN_NAME = 'NUTS level'

NUTS_MIN_RANK = 0
NUTS_MAX_RANK = 3
class NUTSProcessor(object):
    """
    NUTSProcessor is a class that processes NUTS codes.
    """

    def __init__(self, nuts_table_path: Path = NUTS_TABLE_DEFAULT_PATH):
        """
        CPVProcessor constructor.
        """
        self.dataframe: DataFrame = pandas.read_excel(
            nuts_table_path,
            sheet_name=NUTS_SHEET_NAME,
            header=0,
            dtype={
                NUTS_CODE_COLUMN_NAME: str,
                NUTS_LABEL_COLUMN_NAME: str,
                NUTS_ORIGINAL_LABEL_COLUMN_NAME: str,
                NUTS_LEVEL_COLUMN_NAME: str
            }
        )
        self.dataframe.fillna(0)

    def nuts_exists(self, nuts_code: str) -> bool:
        """
        Check if a NUTS code exists in the NUTS table.
        :param nuts_code: NUTS code to check.
        :return: True if the CPV code exists, False otherwise.
        """
        return nuts_code in self.dataframe[NUTS_CODE_COLUMN_NAME].values

    def get_nuts_level_by_code(self, nuts_code: str) -> Optional[int]:
        """
        Get the level of a NUTS code.
        :param nuts_code: NUTS code to check.
        :return: The level of the NUTS code if it exists, None otherwise.
        """
        if not self.nuts_exists(nuts_code=nuts_code):
            return None
        return int(self.dataframe[self.dataframe[NUTS_CODE_COLUMN_NAME] == nuts_code][NUTS_LEVEL_COLUMN_NAME].values[0])

    def get_nuts_label_by_code(self, nuts_code: str) -> Optional[str]:
        """
        Get the label of a NUTS code.
        :param nuts_code: NUTS code to check.
        :return: The label of the NUTS code if it exists, None otherwise.
        """
        if not self.nuts_exists(nuts_code=nuts_code):
            return None
        return self.dataframe[self.dataframe[NUTS_CODE_COLUMN_NAME] == nuts_code][NUTS_LABEL_COLUMN_NAME].values[0]

    def get_nuts_original_label_by_code(self, nuts_code: str) -> Optional[str]:
        """
        Get the original label of a NUTS code.
        :param nuts_code: NUTS code to check.
        :return: The original label of the NUTS code if it exists, None otherwise.
        """
        if not self.nuts_exists(nuts_code=nuts_code):
            return None
        return \
        self.dataframe[self.dataframe[NUTS_CODE_COLUMN_NAME] == nuts_code][NUTS_ORIGINAL_LABEL_COLUMN_NAME].values[0]

    def get_nuts_code_by_level(self, nuts_code: str, nuts_level: int) -> Optional[str]:
        """
            Given a nuts code and a nuts level returns the nuts code for that level
        :param nuts_code: Nuts code
        :param nuts_level: Nuts level
        :return: Nuts code for the given level
        """
        if (nuts_code is None) or (self.nuts_exists(nuts_code=nuts_code) is None):
            return None

        nuts_level += 2
        nuts_code_length = len(nuts_code)
        if nuts_code_length < nuts_level:
            return None

        generated_nuts_code = nuts_code[:nuts_level]
        if not self.nuts_exists(nuts_code=generated_nuts_code):
            return None
        return generated_nuts_code