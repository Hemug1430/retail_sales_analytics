import os
import pandas as pd

# ============================================================
# TRACKER 03.11 - PROFILE INCOMING DATASET
# ============================================================

INPUT_FOLDER = "incoming"
OUTPUT_FOLDER = "data/outputs"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def profile_dataset(file_path):
    print("\n" + "=" * 80)
    print(f"FILE: {os.path.basename(file_path)}")
    print("=" * 80)

    try:
        df = pd.read_csv(file_path)

        # ----------------------------------------------------
        # 1. ROWS AND COLUMNS
        # ----------------------------------------------------
        rows, columns = df.shape

        print(f"\nRows    : {rows}")
        print(f"Columns : {columns}")

        # ----------------------------------------------------
        # 2. NULL COUNTS AND NULL %
        # ----------------------------------------------------
        null_count = df.isnull().sum()
        null_pct = (null_count / rows * 100).round(2) if rows > 0 else null_count

        null_profile = pd.DataFrame({
            "null_count": null_count,
            "null_pct": null_pct
        })

        print("\n--- NULL PROFILE ---")
        print(null_profile[null_profile["null_count"] > 0])

        # ----------------------------------------------------
        # 3. UNIQUE COUNTS
        # ----------------------------------------------------
        print("\n--- UNIQUE COUNTS ---")

        unique_profile = pd.DataFrame({
            "column": df.columns,
            "unique_count": [df[col].nunique(dropna=True) for col in df.columns]
        })

        print(unique_profile.to_string(index=False))

        # ----------------------------------------------------
        # 4. NUMERIC PROFILE
        # ----------------------------------------------------
        numeric_columns = df.select_dtypes(include="number").columns

        if len(numeric_columns) > 0:
            numeric_profile = pd.DataFrame({
                "min": df[numeric_columns].min(),
                "max": df[numeric_columns].max(),
                "mean": df[numeric_columns].mean().round(2),
                "median": df[numeric_columns].median().round(2)
            })

            print("\n--- NUMERIC PROFILE ---")
            print(numeric_profile)

        # ----------------------------------------------------
        # 5. DATE PROFILE
        # ----------------------------------------------------
        date_columns = []

        for col in df.columns:
            col_lower = col.lower()

            if "date" in col_lower:
                date_columns.append(col)

        if date_columns:
            print("\n--- DATE PROFILE ---")

            for col in date_columns:
                parsed_dates = pd.to_datetime(
                    df[col],
                    errors="coerce"
                )

                print(f"\nColumn: {col}")
                print(f"Parse failures : {parsed_dates.isna().sum()}")

                valid_dates = parsed_dates.dropna()

                if len(valid_dates) > 0:
                    print(f"Minimum date   : {valid_dates.min().date()}")
                    print(f"Maximum date   : {valid_dates.max().date()}")
                else:
                    print("Minimum date   : N/A")
                    print("Maximum date   : N/A")

        # ----------------------------------------------------
        # 6. DUPLICATES
        # ----------------------------------------------------
        duplicate_rows = df.duplicated().sum()

        print("\n--- DUPLICATE PROFILE ---")
        print(f"Duplicate rows : {duplicate_rows}")

        # ----------------------------------------------------
        # 7. CATEGORY FREQUENCIES
        # ----------------------------------------------------
        print("\n--- CATEGORY FREQUENCIES ---")

        categorical_columns = df.select_dtypes(
            include=["object", "category"]
        ).columns

        for col in categorical_columns:
            print(f"\nColumn: {col}")

            frequencies = (
                df[col]
                .fillna("<NULL>")
                .value_counts()
                .head(20)
            )

            print(frequencies.to_string())

        # ----------------------------------------------------
        # 8. SAVE PROFILE REPORT
        # ----------------------------------------------------
        report_file = os.path.join(
            OUTPUT_FOLDER,
            f"{os.path.splitext(os.path.basename(file_path))[0]}_profile.txt"
        )

        # Re-run key information into report file
        with open(report_file, "w", encoding="utf-8") as report:

            report.write(f"FILE: {os.path.basename(file_path)}\n")
            report.write("=" * 80 + "\n\n")

            report.write(f"Rows    : {rows}\n")
            report.write(f"Columns : {columns}\n\n")

            report.write("--- NULL PROFILE ---\n")
            report.write(
                null_profile.to_string()
            )
            report.write("\n\n")

            report.write("--- UNIQUE COUNTS ---\n")
            report.write(
                unique_profile.to_string(index=False)
            )
            report.write("\n\n")

            if len(numeric_columns) > 0:
                report.write("--- NUMERIC PROFILE ---\n")
                report.write(
                    numeric_profile.to_string()
                )
                report.write("\n\n")

            if date_columns:
                report.write("--- DATE PROFILE ---\n")

                for col in date_columns:
                    parsed_dates = pd.to_datetime(
                        df[col],
                        errors="coerce"
                    )

                    valid_dates = parsed_dates.dropna()

                    report.write(f"\nColumn: {col}\n")
                    report.write(
                        f"Parse failures : {parsed_dates.isna().sum()}\n"
                    )

                    if len(valid_dates) > 0:
                        report.write(
                            f"Minimum date   : {valid_dates.min().date()}\n"
                        )
                        report.write(
                            f"Maximum date   : {valid_dates.max().date()}\n"
                        )

                report.write("\n")

            report.write("--- DUPLICATE PROFILE ---\n")
            report.write(
                f"Duplicate rows : {duplicate_rows}\n\n"
            )

            report.write("--- CATEGORY FREQUENCIES ---\n")

            for col in categorical_columns:
                report.write(f"\nColumn: {col}\n")

                frequencies = (
                    df[col]
                    .fillna("<NULL>")
                    .value_counts()
                    .head(20)
                )

                report.write(
                    frequencies.to_string()
                )
                report.write("\n")

        print(f"\nProfile report saved to: {report_file}")

    except Exception as e:
        print(f"\nERROR profiling {file_path}: {e}")


def main():
    if not os.path.exists(INPUT_FOLDER):
        print(f"ERROR: Incoming folder not found: {INPUT_FOLDER}")
        return

    csv_files = [
        file for file in os.listdir(INPUT_FOLDER)
        if file.lower().endswith(".csv")
    ]

    if not csv_files:
        print(f"No CSV files found in: {INPUT_FOLDER}")
        return

    print(f"Found {len(csv_files)} CSV file(s) in '{INPUT_FOLDER}'.")

    for file in sorted(csv_files):
        file_path = os.path.join(INPUT_FOLDER, file)
        profile_dataset(file_path)

    print("\n" + "=" * 80)
    print("Tracker 03.11 dataset profiling completed.")
    print("=" * 80)


if __name__ == "__main__":
    main()