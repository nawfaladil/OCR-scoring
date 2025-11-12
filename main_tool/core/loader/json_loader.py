"""
Load json output files
"""
import json
import os
from typing import Optional, Any, List, Dict, Tuple
import pandas as pd
from main_tool.core.loader.ab_class import DataLoader

class JSONDataLoader(DataLoader):
    """
    Convert a structured prediction JSON file into a long-form DataFrame:

        File Name | Field Name | Value

    Recognized patterns:
      1. Primitive: "Field": <primitive or null>
      2. List: "Field": [a, b, ...]  -> one row per element
      3. Structured: "Field": {"value": <primitive>, "alternative_names": [...], "type": ...}
      4. Simplified boolean dict: {"type": true} (when treat_simplified_boolean_dict=True)
      5. Generic dict: flattened (shallow or recursive depending on config)

    Behavior is controlled by JSONLoaderConfig.
    """

    # ---------------- Public API ---------------- #

    def load(self, path: str) -> List[pd.DataFrame]:
        """
        Main loading function
        """
        data = self._read_json(path)
        if isinstance(data, list):
            data = data[0]

        if not isinstance(data, dict):
            raise ValueError(f"Top-level JSON must be an object (dict) : {path}")

        file_name = os.path.basename(path)
        rows: List[Dict[str, Any]] = []

        print(f"[JSONDataLoader] Loading {path}")

        # Recursively get all field_name : value for file into our rows
        for field_name, entry in data.items():
            self._dispatch_top_level(field_name, entry, file_name, rows)

        # Build pandas dataframe from our rows
        df = pd.DataFrame(rows, columns=["File Name", "Field Name", "Value"])

        # Transform to strings and strip extra white spaces
        df["File Name"] = df["File Name"].astype(str).str.strip()
        df["Field Name"] = df["Field Name"].astype(str).str.strip()
        df["Value"] = df["Value"].astype(str).str.strip()

        # if len(df["Field Name"].unique()) != len(df.index) and \
        #         "Nom de l'assuré" in df["Field Name"].values:

        #     return self._split_people_dataframes(df)
        df.drop(df[df["Field Name"].isin(["Nom de l'assuré", "Prénom de l'assuré"])].index, inplace=True)

        return [df]

    # ---------------- Internal Helpers ---------------- #

    def _read_json(self, json_path: str) -> Dict:
        with open(json_path, 'r', encoding="UTF-8") as f:
            return json.load(f)

    def _dispatch_top_level(self, field_name: str, entry: Any,
                            file_name: str, rows: List[Dict[str, Any]]) -> None:
        """
        Determine which handler to use for a top-level entry.
        """
        if self._is_primitive(entry):
            self._handle_primitive(field_name, entry, file_name, rows)
            return

        self._flatten_recursive(field_name, entry, file_name, rows)
        return

    @staticmethod
    def _is_primitive(v: Any) -> bool:
        return isinstance(v, (str, int, float, bool)) or v is None


    def _handle_primitive(self, field_name: str, value: Any, file_name: str,
                          rows: List[Dict[str, Any]]) -> None:
        rows.append({
            "File Name": file_name,
            "Field Name": field_name,
            "Value": value
        })


    def _flatten_recursive(self, field_name: str, entry: Optional[Dict[str, Any] | List],
                           file_name: str, rows: List[Dict[str, Any]]) -> None:
        if isinstance(entry, List):
            for val in entry:
                if self._is_primitive(val):
                    self._handle_primitive(field_name, val, file_name, rows)
                    continue
                else:
                    self._flatten_recursive(field_name, val, file_name, rows)
                    continue

        elif isinstance(entry, Dict):
            structured_dict = self._dict_is_structured(field_name, entry)
            if structured_dict:
                names, value = structured_dict
                for name_variant in names:
                    self._handle_primitive(name_variant, value, file_name, rows)
                return
            for key, value in entry.items():
                if self._is_primitive(value):
                    self._handle_primitive(key, value, file_name, rows)
                    continue
                self._flatten_recursive(key, value, file_name, rows)

        return



    def _dict_is_structured(self, field_name: str,
                            entry: Dict[str, Any]) -> Optional[Tuple[List[str], Any]]:
        """
        Return (names_list, value) if entry is a recognized structured pattern, else None.
        Patterns:
          A) {"value": <primitive>, "alternative_names": [...], "type": <meta>}
          B) {"type": <bool>} (simplified boolean) when treat_simplified_boolean_dict = True
        """
        if "value" in entry:
            value = entry.get("value")
            alt = entry.get("alternative_names") or []
            names = [field_name] + [a for a in alt if isinstance(a, str)]

        elif "type" in entry and isinstance(entry["type"], bool):
            value = entry["type"]
            alt = entry.get("alternative_names") or []
            names = [field_name] + [a for a in alt if isinstance(a, str)]

        else:
            return None

        return names, value

    def _split_people_dataframes(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        first_person_df = df.drop_duplicates("Field Name", keep = "first")
        second_person_df = df.drop_duplicates("Field Name", keep="last")

        return [first_person_df, second_person_df]



# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    json_loader = JSONDataLoader()
    # df_json = json_loader.load("data/trade/Air+waybill (4).PDF.txt")
    # df_json = json_loader.load("data/macif_layout/MACIF DEVIS 5869224 2.json")
    df_json = json_loader.load("data/vision/APRIL 213314G 8.json")
    # json_loader._read_json("data/vision/APRIL 213314G 8.json")
    for df_ in df_json:
        print(df_)
