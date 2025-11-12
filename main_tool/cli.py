"""
The tool's main interaction
"""
import os
import argparse
import pandas as pd
from gooey import Gooey, GooeyParser
from main_tool.core.evaluator.runner import EvaluationRunner


def build_arg_parser() -> argparse.ArgumentParser:
    """
    make the user interface CLI
    """
    p = GooeyParser(description="Evaluate prediction JSON files against GT.")
    p.add_argument("--output_files", type=str, required=True,
                    help="Folder containing prediction files",
                    widget= "DirChooser")
    p.add_argument("--gt_file", type=str, required=True, help="Ground truth file (CSV/XLSX)",
                   widget= "FileChooser")

    # p = argparse.ArgumentParser(description="Evaluate prediction JSON files against GT.")
    # p.add_argument("--output_files", type=str, required=True,
    #                 help="Folder containing prediction files")
    # p.add_argument("--gt_file", type=str, required=True, help="Ground truth file (CSV/XLSX)")
    return p

@Gooey
def main():
    """
    execute runner with parameters from CLI
    """
    parser = build_arg_parser()
    args = parser.parse_args()
    runner = EvaluationRunner()
    result = runner.run(args.output_files, args.gt_file)

    print(result["details"].to_string())

    # Simple console output summary
    print("\nPer-file scores:")
    print(result["file_scores"].to_string(index=False))
    print("\nField summary:")
    print(result["field_summary"].to_string(index=False))

    # Comment or uncomment to choose to persist details:
    df_list = [result["details"], result["field_summary"], result["file_scores"]]
    sheet_names = ["details", "field_summary", "file_scores"]
    i = 0
    while os.path.exists("data/outputs/evaluation_details_%s.xlsx" %i):
        i += 1

    with pd.ExcelWriter("data/outputs/evaluation_details_%s.xlsx" %i,
                        engine='xlsxwriter') as writer:
        for df, sheet in zip(df_list, sheet_names):
            df.to_excel(writer, sheet_name= sheet, index=False)
            worksheet = writer.sheets[sheet]
            # Set column widths
            for col_num in range(0, 2):
                worksheet.set_column(col_num, col_num, 50)

            for col_num in range(2,4):
                worksheet.set_column(col_num, col_num, 40)

            for col_num in range(4,6):
                worksheet.set_column(col_num, col_num, 20)

            worksheet.set_column(6, 6, 40)

    # result["details"].to_excel("data/outputs/evaluation_details_%s.xlsx" %i, index=False)

if __name__ == "__main__":
    main()
