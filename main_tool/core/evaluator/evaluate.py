"""
Contains evaluator class
"""
import re
from datetime import datetime
from typing import Tuple, List, Dict
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment
import Levenshtein as lev
from main_tool.core.normalizer import value_normalizer, file_name_normalizer, field_name_normalizer

# ID_RE: Matches "IDs", words that contain at least one letter (A-Z, case-insensitive)
# followed directly by at least one digit, and only those (no additional characters).
# The match requires a word boundary (\b) at start and end, so only standalone tokens
# like "AB123", "user42", "X1" are matched, not "abc123def" or embedded IDs.
ID_RE = re.compile(r'\b[A-Za-z]+[0-9]+\b')

# DATE_RE: Matches a date in the ISO format "YYYY-MM-DD".
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# NUMBER_RE: Matches a whole string that represents an integer or decimal number,
# with optional sign.
NUMBER_RE = re.compile(r'^[+-]?\d+(\.\d+)?$')

# We deal with these fields a special way.
FIELD_EXCEPTIONS = ["contrat délégué", "distributeur délégué", "assureur délégué"]


class Evaluator:
    """
    Main class used to normalize dataframes, match the predictions with their ground truths
    and evaluate them.
    """

    def __init__(self, config: Dict):
        self.value_normalizer = value_normalizer.ValueNormalizer()
        self.field_normalizer = field_name_normalizer.FieldNameNormalizer()
        self.file_normalizer = file_name_normalizer.FileNameNormalizer()
        self.cfg = config

    def normalize_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize a dataframe file and field names and values
        """
        if "File Name" not in df.columns \
            or "Field Name" not in df.columns or "Value" not in df.columns:
            raise ValueError("DataFrame must contain 'File Name', 'Field Name', 'Value' columns.")

        # Normalize File names
        df["File Name"] = df["File Name"].apply(self.file_normalizer.normalize)

        # Normalize values
        df["Value"] = df.apply(
            lambda r: self.value_normalizer.normalize(r["Value"], r["Field Name"]), axis=1)

        # Normalize Field names
        df = self.field_normalizer.normalize(df)

        return df

    def evaluate_pair(self, df_gt: pd.DataFrame,
                      df_pred: pd.DataFrame) -> Tuple[float, float, pd.DataFrame]:
        """
        Evaluate predictions vs ground truth (already normalized DataFrames).
        Returns:
            (score, non_nan_score, collapsed_detail_dataframe)
        score: match accuracy.
        non_nanscore: match accuracy without taking into account cases
        where the value to predict is empty.
        (like a field that wasn't existant in the document)
        collapsed_detail_dataframe: 
        """
        # In case the dataframe is empty, we return empty scores and an empty df
        if df_gt is None or df_pred is None or df_pred.empty:
            return 0.0, 0.0, pd.DataFrame()

        # Limit GT to predicted files by using File Name
        pred_files = df_pred["File Name"].unique()
        gt_subset = df_gt[df_gt["File Name"].isin(pred_files)].copy()
        # Return empty if it doesnt exist in ground truth file
        if gt_subset.empty:
            return 0.0, 0.0, pd.DataFrame()

        # Merge (Cartesian on matching file & field)
        # Check pandas documentation on merge for more details.
        # It basically alligns rows from output data and ground truth data
        # using the common fields "File Name" and "Field Name"
        # and in cases where there are multiple matching rows, it does a cartesian match
        # meaning it will create as many rows as possible combinations.
        merged = gt_subset.merge(
            df_pred,
            on=["File Name", "Field Name"],
            suffixes=("_gt", "_pred"),
            how="inner"
        )

        # Return empty if nothing matched
        if merged.empty:
            return 0.0, 0.0, pd.DataFrame()

        # Compute distances & matches
        merged = self._compute_distances_and_matches(merged)

        # As we said before, merged is canonically matched,
        # so in case of multiple identical field names like in trade project,
        # we need to correctly match each prediction with its value,
        # we do that in collapse by taking for each prediction
        # the best outcome, it could backfire, but it's the simplest solution
        # we also take the correct person gt rows in case of multiple people.
        # We do that with the hungarian algorithm.

        collapsed = self._collapse_rows(merged)

        # Accuracy score
        score = self._compute_overall_score(collapsed)

        # Accuracy score excluding empty ocr predictions
        non_nan_score = self._compute_overall_score_nan(collapsed)

        return score, non_nan_score, collapsed

    def build_field_summary(self, collapsed: pd.DataFrame) -> pd.DataFrame:
        """
        Produces a table with these columns for each unique 'Field Name':
        - Field Name: the name of the field as found in the collapsed DataFrame.
        - total: the number of (ground truth, predicted) units (rows) for that field.
        - matched: the sum of the 'matching' column for that field (number of matches).
        - accuracy: matched / total, representing the per-field accuracy rate.
        - Adjusted accuracy: accuracy excluding rows with empty prediction and ground truth.

        It's intended to be used later on the dataframe that concatenates all predictions with their
        ground truth values from all the files.

        Columns: Field Name | total | matched | accuracy | adjusted_accuracy
        """
        # If DataFrame is empty, return summary structure with no rows.
        if collapsed.empty:
            return pd.DataFrame(columns=["Field Name", "total", "matched", "accuracy", "adjusted_accuracy"])

        # Group by 'Field Name': count entries and sum number of correct matches.
        grp = collapsed.groupby("Field Name", as_index=False).agg(
            total=("matching", "count"),
            matched=("matching", "sum")
        )

        # Compute field-level accuracy as proportion of matches.
        grp["accuracy"] = grp["matched"] / grp["total"]

        # Compute adjusted_accuracy per field
        adjusted_metrics = []
        for field, subdf in collapsed.groupby("Field Name"):
            # Exclude rows where Value_pred is empty and Value_gt == "nan"
            filtered = subdf[~((subdf["Value_pred"] == "") & (subdf["Value_gt"] == "nan"))]
            adj_total = len(filtered)
            adj_matched = filtered["matching"].sum()
            adjusted_accuracy = float(adj_matched / adj_total) if adj_total > 0 else 0.0
            adjusted_metrics.append(adjusted_accuracy)
        grp["adjusted_accuracy"] = adjusted_metrics

        # Return summary sorted alphabetically by field name.
        return grp.sort_values("Field Name")


    # ------------- Internal Helpers -------------



    def _compute_distances_and_matches(self, merged: pd.DataFrame) -> pd.DataFrame:
        """
        Adds columns:
          - matching_distance
          - matching (0 to 1)
        The matching distance is the original distance between the two values,
        it could be the difference of days, levenshtein distance... depending on context.
        the matching score is the normalized distance depending on context,
        from 0 which is no match at all, to 1 which is perfect match. 
        """
        v_gt = merged["Value_gt"].astype(str).fillna("")
        v_pr = merged["Value_pred"].astype(str).fillna("")
        field_name = merged["Field Name"].astype(str).fillna("")

        # We append the different scores to these lists
        distances : List[float] = []
        matches: List[float] = []

        # Loop through the rows of merged values computing scores.
        for field_name, gt_val, pr_val in zip(field_name, v_gt, v_pr):

            # evaluate exceptions
            if not gt_val or gt_val == 'nan':
                # In case the ground truth value is none
                # it's only a match if it's the same for the predicted value.
                if not pr_val or pr_val.lower() == 'none':
                    distances.append(0)
                    matches.append(1)
                else:
                    distances.append(100)
                    matches.append(0)

                continue

            if self._is_field_exception(field_name):
                # This is a special matching case, you can in the same fashion add your own rules
                # according to your needs. what this does, is it checks if the field is amongst
                # these special cases, and it checks if the prediction value is in the ground truth
                # or vice versa, and counts that as a match, otherwise we keep going and apply the
                # normal matching functions.
                if (gt_val in pr_val) or (pr_val in gt_val):
                    distances.append(0)
                    matches.append(1)
                    continue

            # evaluate identifiers
            if "identifiant" in field_name.lower() or self._is_identifier(gt_val):
                matched, dist = self._match_identifiers(gt_val, pr_val)
                matches.append(matched)
                distances.append(dist)
                continue

            # evaluate dates
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

            # evaluate text (the last evaluation, thus
            # no need to check for conditions, it acts like an else)
            matched, dist = self._match_text(field_name, gt_val, pr_val, len(gt_val))
            matches.append(matched)
            distances.append(dist)

        # We make a copy to avoid problems modifying the original df as a best practice
        merged = merged.copy()
        # We add the distance and matching columns
        merged["matching_distance"] = distances
        merged["matching"] = matches
        return merged

    def _is_field_exception(self, field_name: str) -> bool:
        # Check field exception using the FIELD_EXCEPTIONS set.
        return field_name.lower() in FIELD_EXCEPTIONS

    def _are_dates(self, val1: str, val2: str) -> bool:
        # Check if both ground trut and prediction values are dates
        return bool(DATE_RE.match(val1) and DATE_RE.match(val2))

    def _match_dates(self, val1: str, val2: str) -> Tuple[float, float]:
        # We chose to do strict matching, meaning it will be a match if date1 == date2
        try :
            date1 = datetime.strptime(val1, "%Y-%m-%d").date()
            date2 = datetime.strptime(val2, "%Y-%m-%d").date()
            # This is the distance we return
            date_diff = abs((date1 - date2).days)
            matching = 1 if date1 == date2 else 0
            return matching, date_diff
        except ValueError:
            return 0.0, 100

    def _are_numbers(self, val1: str, val2: str) -> bool:
        # Check if both ground truth and prediction values are numbers
        return bool(NUMBER_RE.match(val1) and NUMBER_RE.match(val2))

    def _match_numbers(self, val1: str, val2: str) -> Tuple[float, float]:
        # We chose to do strict matching for numbers as well.
        try:
            num1 = float(val1)
            num2 = float(val2)
            # This is the distance we return
            num_diff = abs(num1 - num2)
            matching = 1 if num1 == num2 else 0
            return matching, num_diff
        except ValueError:
            return 0.0, 100

    def _is_identifier(self, val: str) -> bool:
        # Check if the value is meant to be an identifier with the ID_RE regex.
        return bool(ID_RE.match(val))

    def _match_identifiers(self, val1: str, val2: str) -> Tuple[float, float]:
        """
        It's a match if predicted value is in ground truth value or vice versa,
        otherwise it's not.
        The difference from 'field_exceptions' is here we do a matching score of 0
        if it's not matching instead of continuing with other matching functions.
        """
        try:
            if val1 in val2 or val2 in val1:
                return 1.0, 0.0
            else:
                return 0.0, lev.distance(val1, val2)
        except ValueError:
            return 0.0, 100

    def _match_text(self, field_name: str, val1: str,
                    val2: str, gt_length: int) ->  Tuple[float, float]:
        """
        We don't do strict evaluation for text, we use a config dictionnary,
        that's specific to every user.
        The default threshhold for a match is 0.5, otherwise, if another threshhold
        for the specific field name exists in the config, we use it instead.
        """
        try:
            # Check if the field exists in the config
            if field_name.lower() in self.cfg['evaluator']['thresholds'].keys():
                # Get its specified threshhold
                threshold = self.cfg['evaluator']['thresholds'][field_name.lower()]
            else:
                # Use default threshold otherwise
                threshold = 0.5

            # We use the levenshtein distance to compute distance between values
            lev_distance = lev.distance(val1, val2)
            # Then we divide it by the ground truth value length to get the CER
            # CER : Character Error Rate
            # We also cap it by 1.
            cer = min(1, lev_distance/gt_length)
            # We use 1-cer since logically, an error rate of 0 means a perfect match of 1
            matching = 1 if (1-cer) >= threshold else 0
            return matching, lev_distance

        except ValueError:
            return 0.0, 100

    def _collapse_rows(self, merged: pd.DataFrame) -> pd.DataFrame:
        """
        Merges and aligns ground truth (gt) and predicted (pv) values using the Hungarian algorithm.

        This function:
        - Groups the input DataFrame by "File Name" and "Field Name".
        - For each group, creates a cost matrix representing the distance
        (or cost) between each unique ground truth value and each predicted
        value using the "matching_distance" score.
        - Uses the Hungarian algorithm (a.k.a. linear sum assignment) to find
        the optimal pairing of gt and pv values that minimizes the total matching distance.
        - For each pairing, appends the highest matching score row to the results.
        - Returns a new DataFrame with the selected rows and relevant metadata.

        Notes:
            - The Hungarian algorithm ensures a globally optimal assignment.
            - A large default cost (1e6) is used to avoid pairing unrelated
            combinations when no direct match exists.

        Example:
            Given a group with gt = [a, b], pv = [x, y],
            the cost matrix will evaluate all 4 combinations.
        """
        results = []
        # Group by file and field
        for (file_name, field_name), group in merged.groupby(["File Name", "Field Name"]):
            # Get unique values for ground truth and prediction
            gt = group["Value_gt"].unique()
            pv = group["Value_pred"].unique()
            # Build the cost matrix [len(gt) x len(pv)] where each cell is the matching distance
            cost = np.zeros((len(gt), len(pv)))
            for i, g in enumerate(gt):
                for j, p in enumerate(pv):
                    # Find the subset of rows where both values match
                    subset = group[(group["Value_gt"] == g) & (group["Value_pred"] == p)]
                    if len(subset):
                        cost[i, j] = subset["matching_distance"].iloc[0]
                    else:
                        # Large cost to discourage this match if no direct match is present
                        cost[i, j] = 1e6
            # Use the Hungarian algorithm (linear_sum_assignment) to find optimal assignments
            row_ind, col_ind = linear_sum_assignment(cost) # Check scipy.optimize for documentation
            for i, j in zip(row_ind, col_ind):
                g = gt[i]
                p = pv[j]
                subset = group[(group["Value_gt"] == g) & (group["Value_pred"] == p)]
                # Take the row with the best (highest) matching score in case of duplicates
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

    def _compute_overall_score(self, collapsed: pd.DataFrame) -> float:
        # Calculate average score of the file which is simply the mean of the matching score
        total_matching = collapsed["matching"].sum()
        total_rows = len(collapsed["matching"])
        return float(total_matching / total_rows) if total_rows > 0 else 0.0

    def _compute_overall_score_nan(self, collapsed: pd.DataFrame) -> float:
        # Same logic but exclude cases with empty prediction and ground truth values
        total_matching = 0
        total_rows = 0
        for _, row in collapsed.iterrows():
            if (not row["Value_pred"]) and row["Value_gt"] == "nan" :
                continue
            total_rows += 1
            total_matching += row["matching"]

        return float(total_matching / total_rows) if total_rows > 0 else 0.0
