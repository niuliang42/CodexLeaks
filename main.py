import os
import sys
import time
import datetime
import pprint
import traceback
import sqlite3

import openai
from loguru import logger
from tqdm import tqdm

import utils
from utils import SQLCommandEnum
from config import log_file_md, raw_log_file_md, openai_params_default
from Prompt import Query, get_all_queries

pretty_printer = pprint.PrettyPrinter(indent=2)

log_title = f"General Info {datetime.datetime.today().strftime('%b-%d-%Y')}"

# Adjust default handler
logger.remove()
logger.add(sys.stderr, level="SUCCESS")

class OpenAIQuerier:
    def __init__(self, raw_log_file=None, log_file=None):
        self.raw_log_file = raw_log_file
        self.log_file = log_file
        self.queries = get_all_queries()
        # Load your API key from an environment variable or secret management service
        self.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_key = self.api_key
        if raw_log_file:
            logger.add(self.raw_log_file,
                       format="### {extra[log_title]}\n**Time | Level:** {time:YYYY-MM-DD HH:mm:ss} | {level}\n\n{message}\n",
                       level="DEBUG")
        if log_file:
            logger.add(self.log_file,
                       format="### {extra[log_title]}\n**Time:** {time:YYYY-MM-DD HH:mm:ss}\n\n{message}\n",
                       level="INFO")
        self.logger = logger.bind(log_title=log_title)
        # Interval seconds between 2 queries. Limit: 20 queries / min
        self.interval = 7 * openai_params_default['n']
        self.logger.info(
            f"OpenAI_Queries initialized with params:\n```\n{pretty_printer.pformat(openai_params_default)}\n```")

        self.db_info = None
        self.db_con = None

    def __enter__(self):
        self.db_info = utils.db_info_query
        self.db_con = sqlite3.connect(self.db_info._db_file)
        with self.db_con:
            self.db_con.execute(utils.get_sql_cmd(self.db_info, SQLCommandEnum.CreateTable))
        return self

    def __exit__(self, exception_type, exception_val, trace):
        try:
            self.db_con.close()
            self.db_con = None
        except AttributeError:  # isn't closable
            print("Error closing database.")
            return True  # exception handled successfully

    # Don't try to run query function in parallel!
    # Reasons: 1) prompt_cat_str; 2) API usage courtesy.
    def _query(self, query: Query):
        """Query the prompt and keep records in the log files."""
        try:
            response = openai.Completion.create(**query.params)
        except Exception:
            self.logger = logger.bind(log_title="Exception from OpenAI")
            self.logger.error(traceback.format_exc())
            exit(1)
        else:
            query.response_body = response
            for i, choice in enumerate(response['choices']):
                query.choices.append(choice["text"])
                query.log_probs.append(choice.logprobs.token_logprobs if "logprobs" in query.params else [])

            # Logging
            self.logger = logger.bind(log_title=query.prompt.cate_str_)
            log_info_choices = "".join(
                [f"The {i + 1}th choice:\n```\n" + choice + '\n```\n' for i, choice in enumerate(query.choices)])
            self.logger.info(
                f"**Prompt:**\n```\n{query.prompt.text}\n```\n**Results: Query id: {response['id']}**\n\n{log_info_choices}")
            self.logger.debug(f"**Raw Response:**\n```\n{response}\n```\n")
            return query

    def _insert_to_db(self, query: Query):
        with self.db_con:
            self.db_con.executemany(
                utils.get_sql_cmd(self.db_info, SQLCommandEnum.Insert_Query),
                query.sql_data
            )

    def query_by_filter(self, func_filter=None, to_pickle=False):
        to_query = self.queries if not callable(func_filter) else func_filter(self.queries)
        for query in tqdm(to_query):
            time.sleep(self.interval)
            self._query(query)
            if self.db_con is not None:
                self._insert_to_db(query)

        if to_pickle:
            utils.save_prompts_to_pickle(to_query)

        self.logger.opt(raw=True).info('-' * 80 + '\n')
        return self


def _run_queries(save=True, filter_func=None):
    if save:
        with OpenAIQuerier(raw_log_file=raw_log_file_md, log_file=log_file_md) as Q:
            Q.query_by_filter(to_pickle=False, func_filter=filter_func)
    else:
        Q = OpenAIQuerier(raw_log_file=raw_log_file_md, log_file=log_file_md)
        Q.query_by_filter(func_filter=filter_func, to_pickle=True)


if __name__ == "__main__":
    _run_queries(save=True, filter_func=None)
