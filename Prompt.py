import re
import random
import json
import pprint

from numpy import clip as np_clip
from collections import defaultdict, Counter
from itertools import product
from typing import List, Tuple

from config import sample_config, openai_params_default, statistics_json
from resources.templates import raw_templates, raw_context, raw_prompts
from resources.templates import categories, CT, VT, IT, S, P


class Variation:
    variables = [
        "CoC",  # Command or Code
        "PL",  # Programming language
        "Language",  # English Chinese
        "Context",  # general or specific
        "Prefix",  # prefix
        # ====================================#
        "Indent",  # [Deprecated] programming style: indent.
        "CodePosition",  # [Deprecated] beginning or middle
        "Others"
    ]
    match_patterns = [
        ('coc', 'code'),
        ('coc', 'command'),
        ('pl', 'python'),
        ('pl', 'json'),
        ('pl', 'sql'),
        ('language', 'english'),
        ('language', 'chinese'),
        ('context', 'generic'),
        ('context', 'specific'),
        # ('prefix', 'prefix'),
        ('indent', '4spaces'),
        ('indent', '2spaces'),
        ('indent', '0space'),
        # ('indent', 'noindent'),
        ('codepos', 'beginning'),
        ('codepos', 'middle'),
    ]
    tag2cat_map = {tag: cat for (cat, tag) in match_patterns}
    default_var = {
        'coc': 'code',
        'pl': 'python',
        'language': 'english',
        'context': 'generic',
        'prefix': '',
        'indent': '4spaces',
        'codepos': 'middle',
        'others': '',
    }

    def __init__(self, params: str):
        assert type(params) is str
        self.note = params
        params = Variation._parse_str(params)
        self.coc = params["coc"]
        self.pl = params["pl"]
        self.language = params["language"]
        self.context = params["context"]
        self.prefix = params["prefix"]
        self.indent = params["indent"]
        self.codepos = params["codepos"]
        self.others = params["others"]

    @staticmethod
    def _parse_str(params: str):
        var_dict = Variation._get_default_variation_dict()
        params = params.lower()
        if 'default' in params:
            return var_dict
        if (idx := params.find('others:')) >= 0:
            var_dict['others'], params = params[idx + 7:], params[:idx]
        params_set = set(params.split(' '))
        for tag in params_set:
            if tag.startswith("prefix"):
                var_dict['prefix'] += tag + ' '
            elif tag in Variation.tag2cat_map:
                var_dict[Variation.tag2cat_map[tag]] = tag
            else:
                var_dict['others'] += ' ' + tag
        return var_dict

    @staticmethod
    def _get_default_variation_dict():
        return Variation.default_var.copy()

    @property
    def var_dict(self):
        return {
            "coc": self.coc,
            "pl": self.pl,
            "language": self.language,
            "context": self.context,
            "prefix": self.prefix,
            "indent": self.indent,
            "codepos": self.codepos,
            "others": self.others,
        }

    def __repr__(self):
        return f"Variation({self.note})"

    # def __str__(self):
    #     return f"Variation({self.note}): {self.var_dict}"

    def __str__(self):
        s = ""
        for v in self.var_dict:
            if self.var_dict[v]:
                s += self.var_dict[v] + ' '
        return s.strip()


class Context:
    def __init__(self, raw_context):
        self.raw_context = raw_context

    @staticmethod
    def parse_context(raw_context):
        pass

    def sample(self, var: str, lang=None):
        """Sample values for a certain variable"""
        # TODO: filter inconsistent language values
        assert isinstance(var, str)
        assert not var.startswith("{{") and not var.startswith(' ')
        if var.startswith("prefix."):
            return random.sample(self.raw_context[var], sample_config.size_prefix)
        elif var.endswith("people_name"):
            return random.sample(self.raw_context[var], sample_config.size_peoplename)
        elif var.startswith("language."):
            assert lang in ('english', 'chinese')
            return list(filter(lambda vt: vt.tag.startswith(lang), self.raw_context[var]))
        else:
            return self.raw_context[var]

    def get_filler_values(self, variables: Tuple[str]):
        def language_var_exist():
            for var in variables:
                if var.startswith("language"):
                    return True
            return False
        if language_var_exist():
            to_get_product = (
                [self.sample(var, "english") for var in variables],
                [self.sample(var, "chinese") for var in variables]
            )
            filler_vals = list(product(*to_get_product[0])) + list(product(*to_get_product[1]))
        else:
            to_get_product = [self.sample(var) for var in variables]
            filler_vals = list(product(*to_get_product))
        return filler_vals


# singleton instance of context
context4template = Context(raw_context)


class PromptTemplate:
    def __init__(self, template_str: str, info: str):
        self.template = template_str
        info_split = info.split(',')
        self.category = info_split[0]
        self.info = info_split[1]
        self.variables = self._parse_template()
        self.filler_vals = self._get_filler_values()

    def _parse_template(self):
        pattern = r"\{\{(.*?)\}\}"
        prog = re.compile(pattern)
        return tuple(set(prog.findall(self.template)))

    def _get_filler_values(self):
        return context4template.get_filler_values(self.variables)

    def render(self, values: Tuple[VT]):
        result = self.template
        tags = []
        assert len(self.variables) == len(values)
        for k, vt in zip(self.variables, values):
            result = result.replace("{{" + k + "}}", vt.val)
            tags.append(vt.tag)
        info = f"{self.category}, {' '.join(tags)} {self.info}"
        return result, info

    def render_all(self):
        assert self.filler_vals is not None
        results = []
        for filler in self.filler_vals:
            prompt, info = self.render(filler)
            results.append((prompt, info))
        return results


class Prompt:
    def __init__(self, info: str, text: str, template: str = ""):
        self.template = template
        self.info = info
        self.text = text
        info_split = self.info.split(',')

        self.categories = info_split[0].split(':')
        self.cate_str_ = ':'.join(self.categories)
        self.note = self.info.split(',')[1] if len(info_split) >= 2 else ""
        self.var = Variation(self.note)

    def __str__(self):
        return f"{self.cate_str_}\n```\n{self.text}\n```\n"

    def __repr__(self):
        return f"Prompt({self.cate_str_}: {repr(self.text)})"


PromptList = List[Prompt]


def get_all_prompts(print_stats = False):
    prompts_all = []
    stat_counter = {c: Counter(from_github=0, from_template=0, hand_crafted=0) for c in S+P}
    # Assemble prompts from templates and from info-template pairs
    assert len(raw_prompts) == len(raw_templates)
    for ct_list, it_list in zip(raw_templates, raw_prompts):
        # For each category,
        # First append template based prompts, from CT pairs
        for ct in ct_list:
            t = PromptTemplate(template_str=ct.tem, info=ct.cat)
            render_results = t.render_all()
            for prompt_txt, info in render_results:
                prompts_all.append(Prompt(text=prompt_txt, info=info, template=t.template))
                stat_counter[prompts_all[-1].cate_str_]['from_template'] += 1

        # Then append those non-template prompts, from IT pairs
        for it in it_list:
            prompts_all.append(Prompt(info=it.info, text=it.text))
            if "from_github" in prompts_all[-1].note:
                stat_counter[prompts_all[-1].cate_str_]['from_github'] += 1
            else:
                stat_counter[prompts_all[-1].cate_str_]['hand_crafted'] += 1

    if print_stats:
        pp = pprint.PrettyPrinter(depth=4)
        pp.pprint(stat_counter)
        with open(statistics_json, "w") as f:
            json.dump(stat_counter, f, indent=4)
        print("Total: ", len(prompts_all))
        # print("Total(from counter): ", sum(map(lambda cnt: sum(cnt.values()), stat_counter.values())))

    return prompts_all


def prompts_group_by_category(prompts: PromptList):
    grouped_prompts = {}
    for p in prompts:
        if p.cate_str_ in grouped_prompts:
            grouped_prompts[p.cate_str_].append(p)
        else:
            grouped_prompts[p.cate_str_] = [p]
    return grouped_prompts


class Query:
    def __init__(self, prompt: Prompt):
        self.prompt = prompt

        self.response_body = None
        self.choices = []
        self.log_probs = []

        self.labels = "unknown"
        self.MI_labels = "unknown"
        self.to_search = ""  # dummy str, because of "not null"
        self.gh_hits = []

        self.params = openai_params_default.copy()
        self.params['prompt'] = self.prompt.text
        self._choose_temperature()

    def __str__(self):
        return f"{self.prompt.cate_str_}\n Tags: **{str(self.prompt.var)}**\n```\n{self.prompt.text}\n```\nParams:{self.params}"

    def __repr__(self):
        return f"Query({self.prompt.cate_str_}: {repr(self.prompt.text)}; temperature:{self.params['temperature']})"

    def _choose_temperature(self):
        def gaussian_sampling(range_start, range_stop):
            mu = (range_start + range_stop) / 2
            sigma = 0.10
            return np_clip(random.gauss(mu, sigma), a_min=range_start, a_max=range_stop)
        if len(self.prompt.var.prefix) > 0:
            self.params['temperature'] = gaussian_sampling(0.1, 0.4)
        elif self.prompt.var.context == 'specific':
            self.params['temperature'] = gaussian_sampling(0.4, 0.7)
        elif self.prompt.var.context == 'generic':
            self.params['temperature'] = gaussian_sampling(0.7, 1.0)
        else:
            self.params['temperature'] = 1.0

    @staticmethod
    def sql_header() -> List[Tuple[str, str]]:
        return [
            ("category", "text not null"),
            ("note", "text not null"),
            ("input", "text not null"),
            ("template", "text not null"),
            # -----------------------------
            ("choice_id", "integer not null"),
            ("choice", "text not null"),
            # -----------------------------
            ("log_probs", "text not null"),
            # -----------------------------
            ("label", "text not null"),
            ("MI_label", "text not null"),
            ("to_search", "text not null"),
            ("params", "text not null"),
        ]

    @property
    def sql_data(self):
        return [(
            self.prompt.cate_str_, self.prompt.note, self.prompt.text, self.prompt.template,
            i, self.choices[i],
            # json.dumps(self.response_body.choices[i].logprobs.token_logprobs),
            json.dumps(self.log_probs[i]),
            self.labels, self.MI_labels, self.to_search, json.dumps(self.params)
        ) for i in range(len(self.choices))]


QueryList = List[Query]


def get_all_queries():
    prompts_all = get_all_prompts()
    return [Query(p) for p in prompts_all]


if __name__ == "__main__":
    prompts_all = get_all_prompts(print_stats=True)
    # queries_all = get_all_queries()
    # utils.export_prompts_to_md(queries_all)
