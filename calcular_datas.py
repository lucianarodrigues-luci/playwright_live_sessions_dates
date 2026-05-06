import pandas as pd
from datetime import datetime, timedelta

INPUT_CSV = "orig.csv"
OUTPUT_CSV = "orig_teste.csv"

DATE_COLUMNS = [
    "section1_date_and_time",
    "section2_date_and_time",
    "section3_date_and_time",
    "section4_date_and_time",
]

DEFAULT_YEAR = 2026
WEEKS_TO_ADD = 1
USE_BREAKS = False

BREAKS = [
    ("2026-04-06", "2026-04-26"),
]


def parse_breaks(breaks):
    parsed = []
    for start_str, end_str in breaks:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        parsed.append((start_date, end_date))
    return parsed


PARSED_BREAKS = parse_breaks(BREAKS)


def is_in_break(date_obj) -> bool:
    for start_date, end_date in PARSED_BREAKS:
        if start_date <= date_obj <= end_date:
            return True
    return False


def is_blank(value) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def split_date_text(text: str):
    text = text.strip()
    first_comma_index = text.find(",")

    if first_comma_index == -1:
        raise ValueError(f"Formato invalido: {text}")

    date_part = text[:first_comma_index].strip()
    suffix = text[first_comma_index:]
    return date_part, suffix


def parse_date_part(date_part: str, year: int):
    return datetime.strptime(f"{date_part} {year}", "%B %d %Y").date()


def format_date_part(date_obj):
    return date_obj.strftime("%B %d")


def next_valid_date(date_obj, weeks_to_add=1):
    new_date = date_obj + timedelta(weeks=weeks_to_add)

    if USE_BREAKS:
        while is_in_break(new_date):
            new_date += timedelta(weeks=1)

    return new_date


def build_shifted_session_dates(
    session_texts, year: int = DEFAULT_YEAR, weeks_to_add: int = WEEKS_TO_ADD
):
    last_filled_index = None

    for idx, text in enumerate(session_texts):
        if not is_blank(text):
            last_filled_index = idx

    if last_filled_index is None:
        return session_texts

    base_text = str(session_texts[last_filled_index]).strip()
    base_date_part, base_suffix = split_date_text(base_text)
    current_date = parse_date_part(base_date_part, year)

    updated_texts = list(session_texts)

    for idx in range(len(session_texts)):
        if is_blank(session_texts[idx]):
            continue

        current_date = next_valid_date(current_date, weeks_to_add=weeks_to_add)
        updated_texts[idx] = f"{format_date_part(current_date)}{base_suffix}"

    return updated_texts


def main():
    print(f"Lendo arquivo: {INPUT_CSV}")
    print(f"USE_BREAKS = {USE_BREAKS}")

    df = pd.read_csv(INPUT_CSV)

    missing_columns = [col for col in DATE_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Colunas faltando: {missing_columns}")

    for row_index in df.index:
        trainer_label = (
            df.at[row_index, "trainer_label"]
            if "trainer_label" in df.columns
            else f"linha {row_index + 1}"
        )
        current_texts = [df.at[row_index, col] for col in DATE_COLUMNS]

        try:
            new_texts = build_shifted_session_dates(current_texts)

            for col, current_value, new_text in zip(
                DATE_COLUMNS, current_texts, new_texts
            ):
                if is_blank(current_value):
                    continue

                current_text = str(current_value).strip()
                df.at[row_index, col] = new_text

                print(f"[OK] {trainer_label} | {col}")
                print(f"     antes: {current_text}")
                print(f"     depois: {new_text}")

        except Exception as e:
            print(f"[ERRO] {trainer_label} | {e}")

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nArquivo salvo em: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
