"""
Contains evaluator class
"""
import re
from datetime import datetime
from typing import Tuple, List
import yaml
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment
import Levenshtein as lev
from main_tool.core.normalizer import value_normalizer, file_name_normalizer, field_name_normalizer

ID_RE = re.compile(r'\b[A-Za-z]+[0-9]+\b')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
NUMBER_RE = re.compile(r'^[+-]?\d+(\.\d+)?$')
FIELD_EXCEPTIONS = ["contrat délégué", "distributeur délégué", "assureur délégué"]


class Evaluator:
    """
    Main class used to normalize dataframes and match the predictions with their ground truths
    """

    def __init__(self):
        self.value_normalizer = value_normalizer.ValueNormalizer()
        self.field_normalizer = field_name_normalizer.FieldNameNormalizer()
        self.file_normalizer = file_name_normalizer.FileNameNormalizer()
        with open("config.yaml", encoding= 'utf-8') as f:
            self.cfg = yaml.load(f, Loader=yaml.FullLoader)

    def normalize_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize a dataframe file and field names and values
        """
        if "File Name" not in df.columns or "Field Name" not in df.columns or "Value" not in df.columns:
            raise ValueError("DataFrame must contain 'File Name', 'Field Name', 'Value' columns.")

        df["File Name"] = df["File Name"].apply(self.file_normalizer.normalize)
        df["Value"] = df.apply(
            lambda r: self.value_normalizer.normalize(r["Value"], r["Field Name"]), axis=1)
        df = self.field_normalizer.normalize(df)

        return df

    def evaluate_pair(self, df_gt: pd.DataFrame,
                      df_pred: pd.DataFrame) -> Tuple[float, pd.DataFrame]:
        """
        Evaluate predictions vs ground truth (already normalized DataFrames).
        Returns:
            (score, collapsed_detail_dataframe)
        score: match accuracy.
        """

        if df_gt is None or df_pred is None or df_pred.empty:
            return 0.0, pd.DataFrame()

        # Limit GT to predicted files
        pred_files = df_pred["File Name"].unique()
        gt_subset = df_gt[df_gt["File Name"].isin(pred_files)].copy()
        if gt_subset.empty:
            return 0.0, pd.DataFrame()

        # Merge (Cartesian on matching file & field)
        merged = gt_subset.merge(
            df_pred,
            on=["File Name", "Field Name"],
            suffixes=("_gt", "_pred"),
            how="inner"
        )

        if merged.empty:
            return 0.0, pd.DataFrame()

        # Compute distances & matches
        merged = self._compute_distances_and_matches(merged)

        # merged is canonically matched, 
        # so in case of multiple identical field names like in trade project,
        # we need to correctly match each prediction with its value,
        # we do that in collapse by taking for each prediction
        # the best outcome, it could backfire, but it's the simplest solution
        # we also take the correct person gt rows in case of multiple people

        collapsed = self._collapse_rows(merged)

        # accuracy
        score = self._compute_overall_score(collapsed)

        return score, collapsed

    def build_field_summary(self, collapsed: pd.DataFrame) -> pd.DataFrame:
        """
        Returns per-field summary:
          Field Name | gt units | matched units | accuracy
        (Units = value rows or field rows depending on collapse strategy.)
        """

        if collapsed.empty:
            return pd.DataFrame(columns=["Field Name", "total", "matched", "accuracy"])

        grp = collapsed.groupby("Field Name", as_index=False).agg(
            total=("matching", "count"),
            matched=("matching", "sum")
        )

        grp["accuracy"] = grp["matched"] / grp["total"]
        return grp.sort_values("Field Name")


    # ------------- Internal Helpers -------------



    def _compute_distances_and_matches(self, merged: pd.DataFrame) -> pd.DataFrame:
        """
        Adds columns:
          - matching_distance
          - matching (0 to 1)
        """
        v_gt = merged["Value_gt"].astype(str).fillna("")
        v_pr = merged["Value_pred"].astype(str).fillna("")
        field_name = merged["Field Name"].astype(str).fillna("")

        distances : List[float] = []
        matches: List[float] = []

        for field_name, gt_val, pr_val in zip(field_name, v_gt, v_pr):
            # evaluate exceptions
            if not gt_val or gt_val == 'nan':
                if not pr_val or pr_val.lower() == 'none':
                    distances.append(0)
                    matches.append(1)
                else:
                    distances.append(100)
                    matches.append(0)

                continue

            if self._is_field_exception(field_name):
                if (gt_val in pr_val) or (pr_val in gt_val):
                    distances.append(0)
                    matches.append(1)
                    continue

            # # evaluate formule déléguée
            # if field_name.lower() == 'formule déléguée':
            #     if gt_val == pr_val:
            #         distances.append(0)
            #         matches.append(1)
            #     else:
            #         distances.append(100)
            #         matches.append(0)

            #     continue

            # evaluate identifiers
            if "identifiant" in field_name.lower() or self._is_identifier(gt_val):
                matched, dist = self._match_identifiers(gt_val, pr_val)
                matches.append(matched)
                distances.append(dist)
                continue

            # # evaluate dates
            if self._are_dates(gt_val, pr_val):
                matched, dist = self._match_dates(gt_val, pr_val)
                matches.append(matched)
                distances.append(dist)
                continue

            # # evaluate numbers
            if self._are_numbers(gt_val, pr_val):
                matched, dist = self._match_numbers(gt_val, pr_val)
                matches.append(matched)
                distances.append(dist)
                continue

            # evaluate text
            matched, dist = self._match_text(field_name, gt_val, pr_val, len(gt_val))
            matches.append(matched)
            distances.append(dist)

        merged = merged.copy()
        merged["matching_distance"] = distances
        merged["matching"] = matches
        return merged

    def _is_field_exception(self, field_name: str) -> bool:
        return field_name.lower() in FIELD_EXCEPTIONS

    def _are_dates(self, val1: str, val2: str) -> bool:
        return bool(DATE_RE.match(val1) and DATE_RE.match(val2))

    def _match_dates(self, val1: str, val2: str) -> Tuple[float, float]:
        try :
            date1 = datetime.strptime(val1, "%Y-%m-%d").date()
            date2 = datetime.strptime(val2, "%Y-%m-%d").date()
            date_diff = abs((date1 - date2).days)
            matching = 1 if date1 == date2 else 0
            return matching, date_diff
        except ValueError:
            return 0.0, 100

    # def _match_dates(self, val1: str, val2: str) -> Tuple[float, float]:
    #     try :
    #         date1 = datetime.strptime(val1, "%Y-%m-%d").date()
    #         date2 = datetime.strptime(val2, "%Y-%m-%d").date()
    #         date_diff = abs((date1 - date2).days)
    #         return math.exp(-date_diff / self.cfg['evaluator']['dates_scale']), date_diff
    #     except ValueError:
    #         return 0.0, 100

    def _are_numbers(self, val1: str, val2: str) -> bool:
        return bool(NUMBER_RE.match(val1) and NUMBER_RE.match(val2))

    def _match_numbers(self, val1: str, val2: str) -> Tuple[float, float]:
        try:
            num1 = float(val1)
            num2 = float(val2)
            num_diff = abs(num1 - num2)
            matching = 1 if num1 == num2 else 0
            return matching, num_diff
        except ValueError:
            return 0.0, 100

    # def _match_numbers(self, val1: str, val2: str) -> Tuple[float, float]:
    #     try:
    #         num1 = float(val1)
    #         num2 = float(val2)
    #         num_diff = abs(num1 - num2)
    #         return math.exp(-num_diff / self.cfg['evaluator']['numbers_scale']), num_diff
    #     except ValueError:
    #         return 0.0, 100

    def _is_identifier(self, val: str) -> bool:
        return bool(ID_RE.match(val))

    def _match_identifiers(self, val1: str, val2: str) -> Tuple[float, float]:
        try:
            if val1 in val2 or val2 in val1:
                return 1.0, 0.0
            else:
                return 0.0, lev.distance(val1, val2)
        except ValueError:
            return 0.0, 100

    def _match_text(self, field_name: str, val1: str,
                    val2: str, gt_length: int) ->  Tuple[float, float]:
        try:
            if field_name.lower() in self.cfg['evaluator']['thresholds'].keys():
                threshold = self.cfg['evaluator']['thresholds'][field_name.lower()]
            else:
                threshold = 0.5
            lev_distance = lev.distance(val1, val2)
            cer = min(1, lev_distance/gt_length)
            matching = 1 if (1-cer) >= threshold else 0
            return matching, lev_distance

        except ValueError:
            return 0.0, 100

    # def _match_text(self, val1: str, val2: str, gt_length: int,
    #                 scale : int = 0.35) ->  Tuple[float, float]:
    #     try:
    #         lev_distance = lev.distance(val1, val2)
    #         cer = lev_distance/gt_length
    #         return math.exp(-cer/scale), lev_distance

    #     except ValueError:
    #         return 0.0, 100

    def _collapse_rows(self, merged: pd.DataFrame) -> pd.DataFrame:
        """
        Do the hungarian algorithm after constructing a cost matrix
        """
        results = []
        for (file_name, field_name), group in merged.groupby(["File Name", "Field Name"]):
            gt = group["Value_gt"].unique()
            pv = group["Value_pred"].unique()
            # Build cost matrix
            cost = np.zeros((len(gt), len(pv)))
            for i, g in enumerate(gt):
                for j, p in enumerate(pv):
                    # Find match in group
                    subset = group[(group["Value_gt"] == g) & (group["Value_pred"] == p)]
                    if len(subset):
                        cost[i, j] = subset["matching_distance"].iloc[0]
                    else:
                        cost[i, j] = 1e6  # large number to avoid unrelated combinations
            row_ind, col_ind = linear_sum_assignment(cost)
            for i, j in zip(row_ind, col_ind):
                g = gt[i]
                p = pv[j]
                subset = group[(group["Value_gt"] == g) & (group["Value_pred"] == p)]
                best_row = subset.sort_values("matching", ascending=False).iloc[0]
                results.append({
                    "File Name": file_name,
                    "Field Name": field_name,
                    "Value_gt": g,
                    "Value_pred": p,
                    "matching_distance": cost[i, j],
                    "matching": best_row["matching"]
                })

        return pd.DataFrame(results)

        #####

        # # For each original ground truth row, keep the best match
        # # (lowest matching_distance, highest matching flag)
        # grouped = merged.sort_values(
        #     by=['matching', 'matching_distance'],
        #     ascending=[False, True]
        # ).groupby(['File Name', 'Field Name', 'Value_gt'], as_index=False)

        # # Pick the best predicted value for each ground truth row
        # best = grouped.first()

        # # If you want to keep the original number of GT rows for each (File Name,
        # Field Name, Value_gt),
        # # and your canonical merge already has one row per GT, this will work as expected.

        # # You can reindex columns as needed:
        # cols = ['File Name', 'Field Name',
        # 'Value_gt', 'Value_pred', 'matching_distance', 'matching']
        # return best[cols]

        #####
        # Collapse logic with an extra dedup step:
        #     Step 1:
        #     - One row per (File Name, Field Name, Value_gt):
        #         * matching_distance = min distance
        #         * matching = max matching flag in that group
        #         * Value_pred taken from row with min distance
        #     Step 2:
        #     - Further collapse to ONE row per (File Name, Field Name)
        #         ignoring Value_gt by keeping the 'best' candidate:
        #         * Prefer matching == 1 over 0
        #         * Then lower matching_distance
        #         * Then earlier original order (stable)

        # if merged.empty:
        #     return merged.iloc[0:0][[
        #         'File Name', 'Field Name', 'Value_gt',
        #         'Value_pred', 'matching_distance', 'matching'
        #     ]]

        # # -------- Step 1: (File Name, Field Name, Value_gt) collapse --------
        # keys = ["File Name", "Field Name", "Value_gt"]

        # # Index of best (minimum distance) row per key
        # idx_min = merged.groupby(keys)["matching_distance"].idxmin()
        # best_rows = merged.loc[idx_min, keys + ["matching_distance", "Value_pred"]]

        # # Max matching flag per key
        # match_status = (
        #     merged
        #     .groupby(keys, as_index=False)["matching"]
        #     .max()
        # )

        # collapsed = best_rows.merge(match_status, on=keys, how="left")

        # # Preserve original order for stable tie-break in step 2
        # collapsed["_orig_order"] = range(len(collapsed))

        # # -------- Step 2: extra dedup per (File Name, Field Name) --------
        # # Ranking: matching desc, distance asc, original order asc
        # collapsed = collapsed.sort_values(
        #     by=["File Name", "Field Name", "matching", "matching_distance", "_orig_order"],
        #     ascending=[True, True, False, True, True],
        #     kind="stable"
        # )

        # # dedup = (
        # #     collapsed
        # #     .groupby(["File Name", "Field Name"], as_index=False)
        # #     .first()
        # # )

        # # Final column order
        # collapsed = collapsed.reindex(columns=[
        #     "File Name", "Field Name", "Value_gt",
        #     "Value_pred", "matching_distance", "matching"
        # ])

        # # dedup = dedup.reindex(columns=[
        # #     "File Name", "Field Name", "Value_gt",
        # #     "Value_pred", "matching_distance", "matching"
        # # ])

        # # # Add Person Nom Prénom to File Name to differentiate between couples
        # # if set(['Nom assuré', 'Prénom assuré']).issubset(dedup['Field Name'].values):
        # #     field_map = dedup.set_index('Field Name')['Value_gt'].to_dict()
        # #     nom = field_map.get('Nom assuré', '')
        # #     prenom = field_map.get('Prénom assuré', '')
        # #     combi = f'-{nom}-{prenom}'
        # #     dedup['File Name'] = dedup['File Name'] + combi

        # return collapsed

    def _compute_overall_score(self, collapsed: pd.DataFrame) -> float:
        total_matching = collapsed["matching"].sum()
        total_rows = len(collapsed["matching"])
        return float(total_matching / total_rows) if total_rows > 0 else 0.0
