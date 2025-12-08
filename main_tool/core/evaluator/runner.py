"""
Glues everything and runs the tool
"""
import os
from typing import List, Dict, Tuple
import pandas as pd
from main_tool.core.evaluator.evaluate import Evaluator
from main_tool.core.loader import json_loader, csv_loader

class EvaluationRunner:
    """
    Main callable Class that glues everything together
    """
    def __init__(self, config: Dict):
        self.evaluator = Evaluator(config)
        self.json_load = json_loader.JSONDataLoader()
        self.csv_load = csv_loader.CSVDataLoader()

    def run(self, output_files: str, gt_file: str) -> Dict[str, pd.DataFrame]:
        """
        Loads ground trut and outptut files, computing their score and global details.
        output_files : path to outputs folder
        gt_file : path to ground truth file
        """
        # Extract the prediction files from the predictions folder
        predictions_paths = self._get_prediction_file_paths(output_files)

        # Load and normalize GT
        df_gt_raw = self.csv_load.load(gt_file)
        df_gt = self.evaluator.normalize_df(df_gt_raw)
        # We make a set of file names existant in ground truth to use later.
        gt_file_names = set(df_gt["File Name"])

        # We will make a global dataframe that concatenates all rows
        # and a dataframe that summarizes scores per file.
        # That's why we are using these two lists.
        all_collapsed_rows: List[pd.DataFrame] = []
        per_file_scores: List[Tuple[str, float, float]] = []

        # Loop through each prediction file
        for pred_path in predictions_paths:
            # Get the base file name, that we will normalize later
            basename = os.path.basename(pred_path)

            try:
                # Use the output loader to load the prediction data
                df_pred_raw = self.json_load.load(pred_path)

                # Normalize the dataset
                df_pred = self.evaluator.normalize_df(df_pred_raw)

                # Get the file normalized file name to check if it exists
                # in the ground truth dataset
                file_key = df_pred["File Name"][0]

                # We use the gt_file_names set we created earlier
                if file_key not in gt_file_names:
                    print(f"[Evaluator] No GT for file key '{file_key}' (from {basename}).")
                    # If it doesn't exists, continue to the next prediction file
                    continue

                # Compute score, adjusted score and the collapsed dataframe with the evaluator
                score, adjusted_score, collapsed = self.evaluator.evaluate_pair(df_gt, df_pred)

                # Add scores to the per file scores list with the file's base name
                per_file_scores.append((basename, score, adjusted_score))

                # We make sure collapsed isn't empty
                # (in case there was no corresponding ground truth)
                if not collapsed.empty:
                    collapsed = collapsed.copy() # Best practice
                    collapsed["Prediction File"] = basename
                    # Add the entire dataframe to the list so we can concatenate them later
                    all_collapsed_rows.append(collapsed)

                print(f"[Evaluator] {basename}: score={score:.3f}")

            except Exception as e:
                print(f"[Evaluator] Error processing {basename}: {e}")

        # Create dataframe for scores per prediction file and add interesting metrics,
        # you can add other metrics that you deem interesting here
        scores_df = pd.DataFrame(per_file_scores, columns=["Prediction File",
                                                           "Score", "Adjusted Score"])

        # Get the percentage of files with a score of 1
        passing_docs = (scores_df["Score"] == 1).mean() if not scores_df.empty else 0.0

        # Same percentage but using the adjusted score
        adjusted_passing_docs = (scores_df["Adjusted Score"] == 1).mean() \
            if not scores_df.empty else 0.0

        # Overall average score 
        average_score = scores_df["Score"].mean() if not scores_df.empty else 0.0

        # Overall average adjusted score
        adjusted_average_score = scores_df["Adjusted Score"].mean() \
            if not scores_df.empty else 0.0

        # Add average score and adjusted score to file scores
        scores_df.loc[len(scores_df)] = ["Average score",
                                         average_score,
                                         adjusted_average_score]

        # Add Percent of passing docs and adjusted passing docs to file scores
        scores_df.loc[len(scores_df)] = ["Percent of passing docs",
                                         passing_docs,
                                         adjusted_passing_docs]

        print(f"[Evaluator] Average score: {average_score:.3f}")

        # We will return a Dictionnary of the scoring dataframes we constructed
        result : Dict[str, pd.DataFrame] = {"file_scores": scores_df}

        # Concatenate all collapsed dataframes into a single ones, as we said before
        if all_collapsed_rows:
            details_df = pd.concat(all_collapsed_rows, ignore_index=True)
            # Add it to the result dictionnary
            result["details"] = details_df
            # Build a field summary from this dataframe and add it to result
            result["field_summary"] = self.evaluator.build_field_summary(details_df)

        else:
            # Make empty dataframes in case all_collapsed_rows list is empty
            result["details"] = pd.DataFrame(columns=[
                "File Name", "Field Name", "Value_gt",
                "matching_distance", "matching", "Prediction File"
            ])
            result["field_summary"] = pd.DataFrame(columns=["Field Name",
                                                            "total", "matched", "accuracy"])

        return result

    # ------------- Internal Helpers -------------


    def _get_prediction_file_paths(self, folder_path: str) -> List[str]:
        # Returns a list of file paths from outputs folder path
        return {
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith((".txt", ".json"))
        }
