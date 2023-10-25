import io
from pathlib import Path
from typing import Optional, List

import pandas
import pandas as pd
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


class CellarNUTSProcessor(object):
    NUTS_CODE_COLUMN_NAME = 'code'
    NUTS_LABEL_COLUMN_NAME = 'label'
    NUTS_PARENT_COLUMN_NAME = 'parent'
    def __init__(self, nuts_csv: io.StringIO):
        self.dataframe: DataFrame = pd.read_csv(
            nuts_csv,
            dtype={
                self.NUTS_CODE_COLUMN_NAME: str,
                self.NUTS_LABEL_COLUMN_NAME: str,
                self.NUTS_PARENT_COLUMN_NAME: str
            }
        )
        self.dataframe[self.NUTS_PARENT_COLUMN_NAME] = self.dataframe[self.NUTS_PARENT_COLUMN_NAME].str.split("/").str[-1]
        self.dataframe[self.NUTS_LABEL_COLUMN_NAME] = self.dataframe[self.NUTS_LABEL_COLUMN_NAME].str.partition(" ")[2]

    def nuts_exists(self, nuts_code: str) -> bool:
        """
        Check if a NUTS code exists in the NUTS table.
        :param nuts_code: NUTS code to check.
        :return: True if the CPV code exists, False otherwise.
        """
        return nuts_code in self.dataframe[self.NUTS_CODE_COLUMN_NAME].values

    def get_nuts_label_by_code(self, nuts_code: str) -> Optional[str]:
        """
        Get the label of a NUTS code.
        :param nuts_code: NUTS code to check.
        :return: The label of the NUTS code if it exists, None otherwise.
        """
        if not self.nuts_exists(nuts_code=nuts_code):
            return None
        return self.dataframe[self.dataframe[self.NUTS_CODE_COLUMN_NAME] == nuts_code][self.NUTS_LABEL_COLUMN_NAME].values[0]

    def get_nuts_level_by_code(self, nuts_code: str) -> Optional[int]:
        """
        Get the level of a NUTS code.
        :param nuts_code: NUTS code to check.
        :return: The level of the NUTS code if it exists, None otherwise.
        """
        if not self.nuts_exists(nuts_code=nuts_code):
            return None
        nuts_lvl = 0
        nuts_parent = self.dataframe.loc[self.dataframe[self.NUTS_CODE_COLUMN_NAME] == nuts_code, self.NUTS_PARENT_COLUMN_NAME].iloc[0]
        while not pd.isnull(nuts_parent):
            nuts_lvl += 1
            previous_nuts_code = nuts_parent
            nuts_parent = self.dataframe.loc[self.dataframe[self.NUTS_CODE_COLUMN_NAME] == previous_nuts_code, self.NUTS_PARENT_COLUMN_NAME]
            if nuts_parent.empty:
                return nuts_lvl
            nuts_parent = nuts_parent.iloc[0]
        return nuts_lvl

    def get_nuts_parent_code_by_level(self, nuts_code: str, nuts_level: int) -> Optional[str]:
        """
        Given a nuts code and a nuts level returns the nuts code for that level
        :param nuts_code: Nuts code
        :param nuts_level: Nuts level
        :return: Nuts code for the given level
        """
        if not self.nuts_exists(nuts_code=nuts_code):
            return None
        current_nuts_level = self.get_nuts_level_by_code(nuts_code)
        if current_nuts_level < nuts_level:
            return None
        if current_nuts_level == nuts_level:
            return nuts_code

        while current_nuts_level > nuts_level:
            nuts_code = self.dataframe[self.dataframe[self.NUTS_CODE_COLUMN_NAME] == nuts_code][self.NUTS_PARENT_COLUMN_NAME].values[0]
            current_nuts_level -= 1
        return nuts_code