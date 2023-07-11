import pickle
import sqlite3
from collections import namedtuple
from enum import Enum, auto
from pathlib import Path

import config
from Prompt import Prompt, Query, QueryList, get_all_prompts

_db_info_fields = ("db_file", "table_name", "sql_header", "cols_types", "cols")
DBInfo = namedtuple("DBInfo", _db_info_fields, defaults=(None,) * len(_db_info_fields))

sql_header_query = Query.sql_header()
db_info_query = DBInfo(db_file=config.db_file,
                       table_name=config.table_query,
                       sql_header=sql_header_query,
                       cols_types=',\n '.join(map(lambda t: ' '.join(t), sql_header_query)),
                       cols=', '.join(map(lambda t: t[0], sql_header_query)),
                       )



class SQLCommandEnum(Enum):
    CreateTable = auto()
    Insert_Query = auto()


def get_sql_cmd(db_info: DBInfo, cmd_type: SQLCommandEnum):
    if cmd_type == SQLCommandEnum.CreateTable:
        return f'''CREATE TABLE IF NOT EXISTS {db_info.table_name}
(id integer primary key autoincrement,
 {db_info.cols_types},
 timestamp datetime DEFAULT CURRENT_TIMESTAMP)'''
    elif cmd_type == SQLCommandEnum.Insert_Query:
        question_marks = ', '.join(['?'] * len(db_info.cols.split(',')))
        return f'''INSERT INTO {db_info.table_name} ({db_info.cols}) VALUES ({question_marks})'''


def filter_by_cat(p: Query, cat="Privacy"):
    return p.prompt.categories[0].lower() == cat


def save_prompts_to_pickle(queries: QueryList):
    with open(config.pickle_file, 'ab') as f:
        pickle.dump(queries, f, protocol=config.pickle_protocol)


def load_prompts_from_pickle(pickle_file=config.pickle_file):
    queries = []
    with open(pickle_file, 'rb') as f:
        while True:
            try:
                p = pickle.load(f)
                queries.extend(p)
            except EOFError:
                break
    return queries


def export_prompts_to_md(queries: QueryList, log_md=config.test_log_md):
    with open(log_md, 'a') as f:
        for q in queries:
            f.write("### " + str(q) + "\n\n")


def load_queries_from_db(db_file=config.db_file):
    """Not everything is loaded, but only the basics and things needed."""
    tablename_query = config.table_query
    tablename_gh = config.table_github
    con = sqlite3.connect(db_file)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    n = len(get_all_prompts())
    queries = []
    for i in range(n):
        num_resp = config.openai_params_default['n']
        cur.execute(
            f'''SELECT {tablename_query}.id, 
                       {tablename_query}.category,
                       {tablename_query}.note,
                       {tablename_query}.input,
                       {tablename_query}.template,
                       {tablename_query}.choice,
                       {tablename_query}.MI_label,
                       {tablename_query}.label,
                       {tablename_gh}.total_count
                FROM {tablename_query} LEFT JOIN {tablename_gh} ON {tablename_query}.id={tablename_gh}.query_id 
                WHERE {tablename_query}.id BETWEEN {num_resp * i + 1} AND {num_resp * i + num_resp}
                ORDER BY {tablename_query}.id''')
        rows = [r for r in cur]
        assert rows[0][1] == rows[-1][1]  # make sure prompts are the same
        row = rows[0]
        prompt = Prompt(text=row[3], info=", ".join((row[1], row[2])), template=row[4])
        query = Query(prompt)
        query.MI_labels = []
        query.labels = []
        for row in rows:
            query.choices.append(row[5])
            query.MI_labels.append(row[6])
            query.labels.append(row[7])
            query.gh_hits.append(row[8])
        queries.append(query)
    con.close()
    return queries


def create_gh_table(db_file):
    con = sqlite3.connect(db_file)
    cur = con.cursor()
    sql_cmd = Path('databases/create_gh_table.sql').read_text()
    cur.execute(sql_cmd)
    con.commit()
    con.close()


def load_gh_from_db(db_file):
    con = sqlite3.connect(db_file)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    # sql_cmd = "SELECT query_id, total_count FROM github"
    sql_cmd = """SELECT responses.id, github.total_count, responses.MI_label FROM github LEFT JOIN responses ON responses.id=github.query_id"""
    cur.execute(sql_cmd)
    gh_results = []
    for row in cur:
        gh_results.append((row[0], row[1], row[2]))
    con.close()
    return gh_results


if __name__ == "__main__":
    # pass
    qs = load_queries_from_db(db_file="databases/Jan-31-2023.db")
