"""
Json output data loader, you can test with example usage at the end of the file
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

    Since our goal is to have a generic solution, and OCR output formats vary from json to another,
    we take multiple patterns into account, if you don't understand a pattern,
    seeing the json output will help. Here are two examples of different output formats :
    (I switched the real values with "data")

---------------------------------------------------------------------------------
    example 1 :

    {
        "Entities": [
            data,
            data,
            data
        ],
        "Banks": [
            ""
        ],
        "Ports and Airports": [
            data,
            data
        ],
        "Countries": [
            data,
            data
        ],
        "Cargos and IMO": [
            data
        ],
        "Containers": [
            data,
            data,
            data,
            data
        ],
        "Merchandises": [
            data,
            data,
            data,
            data
        ]
    }

    - - - - - - - - 

    example 2 :

    {
        "contract_info": {
            "information": {
                "Mandataire": data,
                "email mandataire": data,
                "Le prêt est-il déjà signé ?": data,
                "Date de prise d'effet du contrat externe": data,
                "Etat d'avancement de l'assurance externe : Contrat signé": data,
                "Montant couvert par le contrat externe": data,
                "Durée couverte par le contrat externe": data,
                "Quotité": data,
                "Clause bénéficiaire valide": data,
                "Assureur délégué": data,
                "Distributeur délégué": data,
                "Contrat délégué": data,
                "Identifiant du contrat délégué": data,
                "Formule déléguée": dat
            }
        },
        "insured": [
            {
                "information": {
                    "Nom de l'assuré": data,
                    "Prénom de l'assuré": data,
                    "Coût Assurance Externe": data,
                    "Coût assurance à 8 ans": data
                }
            },
            {
                "information": {
                    "Nom de l'assuré": data,
                    "Prénom de l'assuré": data,
                    "Coût Assurance Externe": data,
                    "Coût assurance à 8 ans": data
                }
            }
        ]
    }
 ---------------------------------------------------------------------------------

    Recognized patterns: (keep in mind, the naming of the patterns is just made up)
      1. Primitive: "Field": <primitive or null> (exple "name": "nawfal" or "age": 23)
      2. List: "Field": [a, b, ...]  or Dict: "Field": {a, b, ...} -> one row per element
      3. Structured:
      {
        "field":
            "value": <primitive>
            "alternative_names": [...] # as in other possible field names for the field
            "type": ... # str or int etc
      }
      4. Simplified boolean dict: {"type": true} # in Structured pattern,
      We could have an empty value field, with a boolean in the type field,
      meaning the value is meant to be True / False

    """

    # ---------------- Main function ---------------- #

    def load(self, path: str) -> pd.DataFrame:
        """
        Main loading function
        """
        # We load our json data
        data = self._read_json(path)

        # Normally the top level of json is always a dictionnary,
        # but there are instances where that dictionnary is inside a List,
        # this takes care of those cases to avoid throwing an error.
        if isinstance(data, list):
            data = data[0]

        if not isinstance(data, dict):
            raise ValueError(f"[Loader][load] Top-level JSON must be an dict : {path}")

        file_name = os.path.basename(path)

        # The way we convert json data to long format data,
        # is by recursively looping through the data and appending it
        # to this list of rows, that we convert at the end into a pandas df.
        rows: List[Dict[str, Any]] = []

        print(f"[JSONDataLoader] Loading {path}")

        # Recursively get all field_name : value from file into our rows
        for field_name, entry in data.items():
            self._dispatch_top_level(field_name, entry, file_name, rows)

        # Build pandas dataframe from our rows
        df = pd.DataFrame(rows, columns=["File Name", "Field Name", "Value"])

        # Transform to strings and strip extra white spaces
        # The simplest way is to just deal with everything as a string.
        df["File Name"] = df["File Name"].astype(str).str.strip()
        df["Field Name"] = df["Field Name"].astype(str).str.strip()
        df["Value"] = df["Value"].astype(str).str.strip()

        # I was instructed to not include names into the evaluation,
        # You can just comment it out if you want to include them.
        df.drop(df[df["Field Name"].isin(["Nom de l'assuré",
                                          "Prénom de l'assuré"])].index, inplace=True)

        return df

    # ---------------- Internal Helpers ---------------- #

    def _read_json(self, json_path: str) -> Dict:
        with open(json_path, 'r', encoding="UTF-8") as f:
            return json.load(f)

    def _dispatch_top_level(self, field_name: str, entry: Any,
                            file_name: str, rows: List[Dict[str, Any]]) -> None:
        """
        Top level elements are the initial keys of the json dictionnary.
        For example, the keys 1 and 2 are top elements here:

        {
            1: data,
                3:  data,
                    data
                data,
            2: data    
        }

        We check if it's a simple element, or it's a dictionnary/list and handle accordingly.
        """
        if self._is_primitive(entry):
            self._handle_primitive(field_name, entry, file_name, rows)
            return

        self._flatten_recursive(field_name, entry, file_name, rows)
        return

    def _is_primitive(self, v: Any) -> bool:
        # Checking if it's not a dictionnary/list
        return isinstance(v, (str, int, float, bool)) or v is None


    def _handle_primitive(self, field_name: str, value: Any, file_name: str,
                          rows: List[Dict[str, Any]]) -> None:
        # We directly add the primitives to rows.
        rows.append({
            "File Name": file_name,
            "Field Name": field_name,
            "Value": value
        })


    def _flatten_recursive(self, field_name: str, entry: Optional[Dict[str, Any] | List],
                           file_name: str, rows: List[Dict[str, Any]]) -> None:
        """
        We recursively flatten the current json entry, it's either a list or dictionnary,
        in case of a List, we handle primitives with our primitive handling function, and
        we do a recursion by calling this same function when the element is not a primitive.
        In case of a dictionnary, we do the same, except we detect if the it's a structured pattern,
        and handle it by adding all possible name variants to the database, so that later on,
        this row can be matched against the correct field name from the ground truth.
        """
        if isinstance(entry, List):
            for val in entry:
                if self._is_primitive(val):
                    self._handle_primitive(field_name, val, file_name, rows)
                    continue
                self._flatten_recursive(field_name, val, file_name, rows)

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
          B) {"type": <bool>}
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

# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    json_loader = JSONDataLoader()
    # change as needed to test loader
    # df_json = json_loader.load("data/vision/APRIL 213314G 8.json")
    # for df_ in df_json:
    #     print(df_)
