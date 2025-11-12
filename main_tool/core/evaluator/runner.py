"""
Run the tool
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
    def __init__(self, config):
        self.evaluator = Evaluator(config)
        self.json_load = json_loader.JSONDataLoader()
        self.csv_load = csv_loader.CSVDataLoader()

    def run(self, output_files: str, gt_file: str) -> Dict[str, pd.DataFrame]:
        """
        Loads ground trut and outptut files, computing their score and global details.
        """
        predictions_paths = self._get_prediction_file_paths(output_files)

        # Load and normalize GT
        df_gt_raw = self.csv_load.load(gt_file)
        df_gt = self.evaluator.normalize_df(df_gt_raw)
        gt_file_names = set(df_gt["File Name"])

        all_collapsed_rows: List[pd.DataFrame] = []
        per_file_scores: List[Tuple[str, float]] = []

        for pred_path in predictions_paths:
            basename = os.path.basename(pred_path)

            try:
                df_output_list = self.json_load.load(pred_path)

                for df_pred_raw in df_output_list:
                    df_pred = self.evaluator.normalize_df(df_pred_raw)
                    file_key = df_pred["File Name"][0]

                    if file_key not in gt_file_names:
                        print(f"[Evaluator] No GT for file key '{file_key}' (from {basename}).")
                        continue

                    score, collapsed = self.evaluator.evaluate_pair(df_gt, df_pred)
                    per_file_scores.append((basename, score))

                    if not collapsed.empty:
                        collapsed = collapsed.copy()
                        collapsed["Prediction File"] = basename
                        all_collapsed_rows.append(collapsed)

                    print(f"[Evaluator] {basename}: score={score:.3f}")

            except Exception as e:
                print(f"[Evaluator] Error processing {basename}: {e}")

        # Aggregate metrics
        scores_df = pd.DataFrame(per_file_scores, columns=["Prediction File", "Score"])
        passing_docs = (scores_df["Score"] == 1).mean() if not scores_df.empty else 0.0
        average_score = scores_df["Score"].mean() if not scores_df.empty else 0.0
        # Add average score to file scores
        scores_df.loc[len(scores_df)] = ["Average score", average_score]
        scores_df.loc[len(scores_df)] = ["Percent of passing docs", passing_docs]
        print(f"[Evaluator] Average score: {average_score:.3f}")
        result : Dict[str, pd.DataFrame] = {"file_scores": scores_df}

        if all_collapsed_rows:
            details_df = pd.concat(all_collapsed_rows, ignore_index=True)
            result["details"] = details_df
            result["field_summary"] = self.evaluator.build_field_summary(details_df)

        else:
            result["details"] = pd.DataFrame(columns=[
                "File Name", "Field Name", "Value_gt",
                "matching_distance", "matching", "Prediction File"
            ])
            result["field_summary"] = pd.DataFrame(columns=["Field Name",
                                                            "total", "matched", "accuracy"])

        # Add average score to retrieve in API in later use cases
        result["average_score"] = pd.DataFrame([average_score])

        return result

    # ------------- Internal Helpers -------------


    def _get_prediction_file_paths(self, folder_path: str) -> List[str]:
        return {
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith((".txt", ".json"))
        }
