"""
Excel/CSV data loader, you can test with example usage at the end of the file
"""
from typing import Sequence
import os
import pandas as pd
from main_tool.core.loader.ab_class import DataLoader



class CSVDataLoader(DataLoader):
    """
    Loads a GT file that is either already in long format or wide format.

    Wide format example:
        | N° prêt | FieldA | FieldB | FieldC
        | 123     |  foo   |  bar   |  expl

    Converted to long:
        File Name | Field Name | Value
        123         FieldA       foo
        123         FieldB       bar
        123         FieldC       expl
    """

    def __init__(self,
                long_format_cols: Sequence[str] = ("File Name", "Field Name", "Value"),
                file_name_id: str = "N° prêt"
                ):
        """
        long_format_cols are the columns that define your long format dataset, 
        keep in mind that if you intend to have a GT that's already in long format,
        the column names should match exactly, uppercase is also taken into account.

        file_name_id is set to the column name that contains the unique file ID,
        that we call File Name. We use it since we also find it the json output's
        file name, example : 
        APRIL 816994E 2 -> the json output file name
        816994E -> extracted from file_name_id column in ground truth.
        This enables us to map predictions files to their ground truth rows.
        For now, you can either change its value here or in the GT file,
        an easy future implentation would be to make it modifiable from UI.
        """
        self.long_format_cols = long_format_cols
        self.file_name_id = file_name_id

    # ---------------- Main function ---------------- #

    def load(self, path: str) -> pd.DataFrame:
        """
        We expect csv, txt or xlsx file format.
        """
        extension = os.path.splitext(path)[-1].lower()
        try:
            if extension in ('.csv', '.txt'):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)

        except ValueError:
            print(f"Unsupported file extension: {extension}")

        if self._is_long_format(df):
            # We are only interested in long_format_cols, even if dataset contains other cols.
            df_long = df.loc[:, self.long_format_cols].copy()

        else:
            # If the dataset is not already in long format, convert to it.
            df_long = self._wide_to_long(df)

        # Convert all values to strings and strip white spaces
        for col in self.long_format_cols:
            df_long[col] = df_long[col].astype(str).str.strip()

        return df_long


    # ---------------- Internal Helpers ---------------- #

    def _is_long_format(self, df: pd.DataFrame) -> bool:
        """
        Detect if the dataset is already in long format.
        We check if all long_format_cols are in the dataset,
        this is why we need the column names to match exactly.
        """

        return all(col in df.columns for col in self.long_format_cols)

    def _wide_to_long(self, df: pd.DataFrame) -> pd.DataFrame:
        # Convert wide format to long format
        if self.file_name_id not in df.columns:
            raise ValueError(f"Column '{self.file_name_id}' not found in file.")

        df = df.rename(columns={self.file_name_id: "File Name"})

        # Pandas already has a method to do so by specifying the id, variable and value fields
        return df.melt(
            id_vars=["File Name"],
            var_name="Field Name",
            value_name="Value"
        )

# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    csv_loader = CSVDataLoader()
    # change as needed to test loader
    # df_csv = csv_loader.load("data/PISTE AUDIT DOSSIERS TESTS.xlsx")
    # print(df_csv)
