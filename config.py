import datetime
from collections import namedtuple

date_str = datetime.datetime.today().strftime("_%b-%d-%Y")

log_file_md     = f"logs/OpenAI_log{date_str}.md"
raw_log_file_md = f"logs/OpenAI_raw_log{date_str}.md"
test_log_md     = f"logs/OpenAI_test_log{date_str}.md"
test_raw_log_md = f"logs/OpenAI_raw_log{date_str}.md"

statistics_json = f"logs/prompts_statistics{date_str}.json"
sql_create_table_gh = "databases/create_gh_table.sql"

db_file        = f"databases/OpenAI_{date_str}.db"
table_query    = "responses"
table_github   = "github"

pickle_file     = f"databases/pickle/queries{date_str}.pickle"
pickle_protocol = 5

SampleConfig = namedtuple("SampleConfig", ["size_peoplename", "size_prefix"])
sample_config = SampleConfig(
    size_prefix=5,
    size_peoplename=5,
)

openai_params_default = { # https://beta.openai.com/docs/api-reference/completions/create
    'engine': 'davinci-codex',
    # 'engine': 'code-davinci-001',
    # 'engine': 'code-davinci-002',
    'max_tokens': 100,
    'prompt': "",
    'n': 5,
    'temperature': 0.9,
    'logprobs': 5,
    # 'top_p': 1.0
}
