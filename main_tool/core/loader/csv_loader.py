from typing import Sequence
import os
import pandas as pd
from main_tool.core.loader.ab_class import DataLoader



class CSVDataLoader(DataLoader):
    """
    Loads a GT (or similar) file that is either already in long format or wide format.

    Wide format example:
        | N° prêt | FieldA | FieldB |
        | 123     |  foo   |  bar   |

    Converted to long:
        File Name | Field Name | Value
        123         FieldA       foo
        123         FieldB       bar
    """

    def __init__(self, long_format_cols: Sequence[str] = ("File Name", "Field Name", "Value"),
                file_name_id: str = "N° prêt"):
        self.long_format_cols = long_format_cols
        self.file_name_id = file_name_id

    # ---------------- Public API ---------------- #

    def load(self, path: str):
        extension = os.path.splitext(path)[-1].lower()
        try:
            if extension in ('.csv', '.txt'):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)

        except ValueError:
            print(f"Unsupported file extension: {extension}")

        if self._is_long_format(df):
            df_long = df.loc[:, self.long_format_cols].copy()

        else:
            df_long = self._wide_to_long(df)

        # convert all values to strings and strip white spaces
        for col in self.long_format_cols:
            df_long[col] = df_long[col].astype(str).str.strip() 

        return df_long


    # ---------------- Internal Helpers ---------------- #

    def _is_long_format(self, df: pd.DataFrame) -> bool:
        return all(col in df.columns for col in self.long_format_cols)

    def _wide_to_long(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.file_name_id not in df.columns:
            raise ValueError(f"Column '{self.file_name_id}' not found in file.")

        df = df.rename(columns={self.file_name_id: "File Name"})

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
    # df_csv = csv_loader.load("data/PISTE AUDIT DOSSIERS TESTS.xlsx")
    df_csv = csv_loader.load("data/makram/GT APC - contracts 06102025.xlsx")
    print(df_csv)
