import pandas as pd
from openai import OpenAI 
import json
import re
from sqlalchemy import create_engine, MetaData, Table, text



client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="dummy-key"
)

EXCEL_FILE_PATH="DDL_File.xlsx"
DATABASE_URL = "postgresql+psycopg2://postgres:password@localhost:5432/exampleDatabase"

engine = create_engine(DATABASE_URL)


def map_data_type(data_type):
    """Map Excel data types to SQL (modify per target DB dialect)."""
    if "VARCHAR2" in data_type:
        length = data_type[data_type.find("(")+1:data_type.find(")")]
        return f"VARCHAR({length})"
    elif "NUMERIC" in data_type:
        if "(" in data_type:
            return data_type.replace("NUMERIC", "NUMERIC")
        return "NUMERIC"
    elif "DATE" in data_type:
        return "DATE"
    elif "TIMESTAMP" in data_type:
        return "TIMESTAMP"
    else:
        return data_type

def sanitize_column_name(name):
    return re.sub(r'__+', '_', name.strip().replace("-", "_").replace(" ", "_"))



def create_ddl(excel_data_frame):
    ddl_parts = []
    for _, row in excel_data_frame.iterrows():
        col_name = sanitize_column_name(row['COLUMN_NAME'])
        data_type = map_data_type(row['DATA_TYPE'])
        nullable = "NULL" if row['NULLABLE'].strip().lower() == "yes" else "NOT NULL"
        ddl_parts.append(f'    "{col_name}" {data_type} {nullable}')

    ddl_statement = f"CREATE TABLE {NAME_OF_TABLE} (\n" + ",\n".join(ddl_parts) + "\n);"
    with engine.connect() as conn:
        conn.execute(text(ddl_statement))
        conn.commit() 
    return ddl_statement

def generate_data_with_gemma(prompt):
    response = client.chat.completions.create(
        model="gemma3:latest",
        messages=[{"role":"user","content":prompt}],
        max_tokens=2048,
        n=1,
        stop=None,
        temperature=0.1
    )
    raw_response = response.choices[0].message.content
    modified_response = re.sub(r"^```\s*json\s*|\s*```\s*$","",raw_response)
    return json.loads(modified_response)



def insert_record(record):
    metadata = MetaData()
    table = Table(NAME_OF_TABLE.lower(), metadata, autoload_with=engine)

    valid_columns = {col.name for col in table.columns}
    filtered_record = {sanitize_column_name(k): v for k, v in record.items() if sanitize_column_name(k) in valid_columns}


    # Fallback for missing or NULL values in NOT NULL columns
    for col in table.columns:
        needs_fallback = (
            col.name not in filtered_record or 
            filtered_record[col.name] is None
        )
        if needs_fallback and not col.nullable and col.default is None and not col.autoincrement:
            col_type_str = str(col.type).lower()

            if any(x in col_type_str for x in ['varchar', 'text', 'char']):
                length = getattr(col.type, 'length', None)
                if length is None:
                    length = 255
                fallback = 'U' if length == 1 else 'UNKNOWN'
                filtered_record[col.name] = fallback[:length]

            elif any(x in col_type_str for x in ['date', 'timestamp']):
                filtered_record[col.name] = '1500-01-01'

            elif any(x in col_type_str for x in ['int', 'numeric', 'decimal', 'float']):
                filtered_record[col.name] = 0

            else:
                filtered_record[col.name] = 'UNKNOWN'

    # Truncate any string values to their column max length
    for col in table.columns:
        if col.name in filtered_record and isinstance(filtered_record[col.name], str):
            length = getattr(col.type, 'length', None)
            if length and len(filtered_record[col.name]) > length:
                filtered_record[col.name] = filtered_record[col.name][:length]

    if not filtered_record:
        print(f"No valid columns found in record: {record}")
        return

    columns = ', '.join([f'"{col}"' for col in filtered_record.keys()])
    placeholders = ', '.join([f':{col}' for col in filtered_record.keys()])
    insert_sql = f'INSERT INTO {NAME_OF_TABLE} ({columns}) VALUES ({placeholders})'

    with engine.connect() as conn:
        conn.execute(text(insert_sql), filtered_record)
        conn.commit()



def main():

    xlsx = pd.ExcelFile(EXCEL_FILE_PATH)

    sheet_name_list = xlsx.sheet_names

    for sheet_name in sheet_name_list:

        excel_dataframe = pd.read_excel(EXCEL_FILE_PATH,sheet_name=sheet_name)

        global NAME_OF_TABLE 
        NAME_OF_TABLE = f"STAGING_{sheet_name.upper().replace(' ','_')}"

        ddl_statement = create_ddl(excel_dataframe)

        prompt = """You are a data generator specializing in Life and Annuity insurance data for source staging database of a PAS(Policy Admin System). 
                       Generate ONLY a valid json object for life insurances policy. Do not include any explanation or markdown code blocks. Include all relevant fields as per the the ddl statement for the table:
                       """ + ddl_statement + """ Ensure all the data fields including age is within the specified range and health status is realistic for the given age and gender.  Ensure that all data is present
                    for each column as shown in the ddl statement. Now, generate a single JSON object.""" 

        record = generate_data_with_gemma(prompt)
        print(record)
        insert_record(record)
        


if __name__=="__main__":
    main()



