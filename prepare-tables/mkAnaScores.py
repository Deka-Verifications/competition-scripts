#!/usr/bin/env python3

"""
BenchExec is a framework for reliable benchmarking.
This file is part of BenchExec.

Copyright (C) 2007-2019  Dirk Beyer
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import itertools
import os
from pathlib import Path
import sys
import re
from typing import Optional, List, Tuple
from multiprocessing import Pool
from functools import partial
from decimal import Decimal
import benchexec.tablegenerator as tablegenerator
import benchexec.result as result
import yaml
import _logging as logging

Util = tablegenerator.util

SV_COMP = "SV-COMP"
TEST_COMP = "Test-Comp"

STATS_INDEX_TOTAL = 0
STATS_INDEX_CORRECT = 1
STATS_INDEX_CORRECT_TRUE = 2
STATS_INDEX_CORRECT_FALSE = 3
STATS_INDEX_CORRECT_UNCONFIRMED = 4
STATS_INDEX_CORRECT_UNCONFIRMED_TRUE = 5
STATS_INDEX_CORRECT_UNCONFIRMED_FALSE = 6
STATS_INDEX_INCORRECT = 7
STATS_INDEX_INCORRECT_TRUE = 8
STATS_INDEX_INCORRECT_FALSE = 9
STATS_INDEX_SCORE = 10

SCORE_COLUMN_NAME = "score"
""""Name (title) of the score column in run result XMLs."""

SCORE_CORRECT_FALSE = 1
SCORE_INCORRECT_FALSE = -16


FALSIFIER_PREFIX = "Falsification"

# global variables used to exchange info between methods
TABLENAME = None
HTMLSCORES = None
TABSCORES = None
RSFSCORES = None
TABLESETUP = None
TEXRANKING = None
TEXRESULTS = None
QPLOT_PATH = None


def msg_to_output(msg):
    print(msg)


def err_to_output(err):
    print(err)


DATE = "????-??-??_??-??-??"


def rename_to_old_if_exists(path):
    if path.exists():
        path_old = Path(str(path) + ".old")
        msg_to_output(
            str(path) + " already exists. Moving it to " + str(path_old) + "."
        )
        msg_to_output("This may overwrite such an existing file!")
        path.rename(path_old)


class CategoryData:
    """
    Single data measurement in category.
    """

    def __init__(
        self,
        data_total,
        data_success,
        data_success_false,
        data_unconfirmed,
        data_unconfirmed_false,
        sequence=None,
    ):
        self.total = data_total
        """ Measurement over all tasks. """

        self.success = data_success
        """ Measurement over all tasks that were solved successfully (correct + confirmed). """

        self.success_false = data_success_false
        """
            Measurement over all tasks that were solved successfully (correct + confirmed)
            and that have verdict 'false'.
        """

        self.success_true = self.success - self.success_false
        """
            Measurement over all tasks that were solved successfully (correct + confirmed)
            and that have verdict 'true'.
        """

        self.unconfirmed = data_unconfirmed
        """
            Measurement over all tasks that were solved correctly, but that were not confirmed.
        """

        self.unconfirmed_false = data_unconfirmed_false
        """
            Measurement over all tasks that were solved correctly, but that were not confirmed,
            and that have verdict 'false'.
        """

        self.unconfirmed_true = self.unconfirmed - self.unconfirmed_false
        """
            Measurement over all tasks that were solved correctly, but that were not confirmed,
            and that have verdict 'true'.
        """

        self.sequence = sequence
        """ Sequence of individual measurements. """


class CategoryResult:
    """
    Category result storing achieved score,
    number of true positives, true negatives, false positives and false negatives,
    as well as additional statistics.
    """

    def __init__(
        self,
        score: Decimal,
        score_false: Decimal,
        cputime: CategoryData,
        cpuenergy: CategoryData,
        correct_false: int,
        correct_true: int,
        correct_unconfirmed_false: int,
        correct_unconfirmed_true: int,
        incorrect_false: int,
        incorrect_true: int,
        qplot_cputime: list,
        qplot_cpuenergy: list,
        results_file: str,
    ):

        self.score = score
        self.score_false = score_false
        self.cputime = cputime
        self.cpuenergy = cpuenergy
        self.correct_false = correct_false
        self.correct_true = correct_true
        self.correct_unconfirmed_false = correct_unconfirmed_false
        self.correct_unconfirmed_true = correct_unconfirmed_true
        self.incorrect_false = incorrect_false
        self.incorrect_true = incorrect_true
        self.qplot_cputime = qplot_cputime
        self.qplot_cpuenergy = qplot_cpuenergy
        self.results_file = results_file


class Category:
    """
    Category object storing the name of the category, the number of tasks,
    the max possible score in the category and verifiers' scores in the same.
    """

    def __init__(
        self, name, tasks=None, possible_score=None, possible_score_false=None
    ):
        self._name = name
        self._tasks = tasks
        self._possible_score = possible_score
        self._possible_score_false = possible_score_false
        self.results = {}  # Participant name -> CategoryResult object

    @property
    def name(self):
        return self._name

    @property
    def tasks(self):
        return self._tasks

    @property
    def possible_score(self):
        return self._possible_score

    @property
    def possible_score_false(self):
        return self._possible_score_false

    @tasks.setter
    def tasks(self, tasks):
        self._tasks = tasks

    @possible_score.setter
    def possible_score(self, possible_score):
        self._possible_score = possible_score


####################################
##########################################################
###### Real code begins here #######
##########################################################
####################################


def write_text(path, text):
    # Only compatible to python > 3.5
    # path.write_text(text)
    with open(str(path), "a") as f:
        f.write(text + "\n")


def read_text(path):
    # Only compatible to python > 3.5
    # return path.read_text()
    with open(str(path), "r") as f:
        return f.read()


def write_to_rfs(category, verifier, rows: Tuple[str, str]):
    string = "\n".join(["\t".join([category, verifier, r[0], r[1]]) for r in rows])
    write_text(RSFSCORES, string)


def get_results_XML_file(category, verifier, results_path, category_info):
    # Get xml results file for each verifier and category
    # - if a merged.xml file exists, we take it.
    # Otherwise, we take the default xml file.
    # If none exists, we assume the verifier didn't take part in the category.
    results_file_no_merged_string = (
        str(verifier)
        + "."
        + DATE
        + ".results."
        + get_competition_with_year(category_info)
        + "_"
        + category
        + ".xml.bz2"
    )
    results_file_merged_string = results_file_no_merged_string + ".merged.xml.bz2"
    try:
        xml_files = list(results_path.glob(results_file_merged_string))
        if not xml_files:
            logging.debug(
                "No results file '*.merged.*' with validator info for tool %s and category %s. Trying to use original results XML.",
                verifier,
                category,
            )
            xml_files = list(results_path.glob(results_file_no_merged_string))
        if len(xml_files) > 1:
            xml_files = sorted(
                xml_files, reverse=True
            )  # sorts by date due to file name structure
        if not xml_files:
            logging.debug(
                "No results file for verifier %s and category %s. Used string: %s",
                verifier,
                category,
                results_file_merged_string,
            )
            return None
        return str(xml_files[0])
    except Exception as e:
        logging.exception("Exception for %s: %s", results_file_merged_string, e)
        return None


def is_false(status):
    return status.startswith("false")


def accumulate_data(data: List[CategoryData]) -> CategoryData:
    total = _sum([v.total or Decimal(0) for v in data])
    success = _sum([v.success or Decimal(0) for v in data])
    success_false = _sum([v.success_false or Decimal(0) for v in data])
    unconfirmed = _sum([v.unconfirmed or Decimal(0) for v in data])
    unconfirmed_false = _sum([v.unconfirmed_false or Decimal(0) for v in data])
    return CategoryData(total, success, success_false, unconfirmed, unconfirmed_false)


def combine_qplots(qplots: List[list], category_amount) -> list:
    qplot_data = itertools.chain.from_iterable(qplots)
    return [
        ((float(score) / category_amount), value, status)
        for score, value, status in qplot_data
    ]


def handle_meta_category(meta_category, category_info, processed_categories):
    categories = get_categories(category_info)
    try:
        demo_categories = get_demo_categories(category_info)
    except KeyError:
        demo_categories = list()
    subverifiers = categories[meta_category]["verifiers"]

    subcategories = {
        sub: processed_categories[sub]
        for sub in categories[meta_category]["categories"]
        if sub not in demo_categories
    }
    subcategories_info = list(subcategories.values())
    category_amount = len(subcategories)
    tasks = sum([c.tasks for c in subcategories_info])

    def normalize_score(score):
        return score / category_amount * tasks

    # Comment this assert if you want to allow empty categories
    assert not [
        n for n, c in subcategories.items() if c.tasks == 0
    ], "Empty categories for meta category %s: %s" % (
        meta_category,
        [n for n, c in subcategories.items() if c.tasks == 0],
    )

    # Sum of each category's normalized score, normalized according to the number of tasks of that individual category
    possible_score = sum(
        [
            Decimal(c.possible_score) / c.tasks
            for c in subcategories_info
            if c.tasks != 0
        ]
    )
    possible_score = normalize_score(possible_score)  # 3.05 * 100 / 2
    possible_score_false = sum(
        [
            Decimal(c.possible_score_false) / c.tasks
            for c in subcategories_info
            if c.tasks != 0
        ]
    )
    possible_score_false = normalize_score(possible_score_false)

    cat_info = Category(meta_category, tasks, possible_score, possible_score_false)

    for verifier in subverifiers:
        subcategories_available = [
            c for c in subcategories_info if verifier in c.results
        ]
        if len(subcategories_available) < len(subcategories):
            logging.info(
                "Not considering verifier %s for category %s because of missing sub-categories. Available sub-categories: %s",
                verifier,
                meta_category,
                [c.name for c in subcategories_available],
            )
            continue
        relevant_results = [c.results[verifier] for c in subcategories_available]

        # can't use relevant_results here because we need the number of total tasks per category
        sum_of_avg_scores = sum(
            [
                Decimal(c.results[verifier].score) / c.tasks
                for c in subcategories_info
                if verifier in c.results.keys() and c.tasks != 0
            ]
        )
        score = normalize_score(sum_of_avg_scores)
        sum_of_avg_scores_false = sum(
            [
                Decimal(c.results[verifier].score_false) / c.tasks
                for c in subcategories_info
                if verifier in c.results.keys() and c.tasks != 0
            ]
        )
        score_false = normalize_score(sum_of_avg_scores_false)

        cputime_data = accumulate_data([r.cputime for r in relevant_results])
        cpuenergy_data = accumulate_data([r.cpuenergy for r in relevant_results])

        correct_false = sum(
            [
                c.results[verifier].correct_false or 0
                for c in subcategories_info
                if verifier in c.results.keys()
            ]
        )
        correct_true = sum(
            [
                c.results[verifier].correct_true or 0
                for c in subcategories_info
                if verifier in c.results.keys()
            ]
        )
        correct_unconfirmed_false = sum(
            [
                c.results[verifier].correct_unconfirmed_false or 0
                for c in subcategories_info
                if verifier in c.results.keys()
            ]
        )
        correct_unconfirmed_true = sum(
            [
                c.results[verifier].correct_unconfirmed_true or 0
                for c in subcategories_info
                if verifier in c.results.keys()
            ]
        )
        incorrect_false = sum(
            [
                c.results[verifier].incorrect_false or 0
                for c in subcategories_info
                if verifier in c.results.keys()
            ]
        )
        incorrect_true = sum(
            [
                c.results[verifier].incorrect_true or 0
                for c in subcategories_info
                if verifier in c.results.keys()
            ]
        )

        qplot_cputime = combine_qplots(
            [
                c.results[verifier].qplot_cputime
                for c in subcategories_info
                if verifier in c.results.keys()
            ],
            category_amount,
        )
        qplot_cpuenergy = combine_qplots(
            [
                c.results[verifier].qplot_cpuenergy
                for c in subcategories_info
                if verifier in c.results.keys()
            ],
            category_amount,
        )

        cat_info.results[verifier] = CategoryResult(
            score,
            score_false,
            cputime_data,
            cpuenergy_data,
            correct_false,
            correct_true,
            correct_unconfirmed_false,
            correct_unconfirmed_true,
            incorrect_false,
            incorrect_true,
            qplot_cputime,
            qplot_cpuenergy,
            None,
        )

    return cat_info


def _get_column_index(column_name: str, run_set_result) -> Optional[int]:
    """Get the index of the column with the given name in the given RunSetResult or RunResult."""
    columns = run_set_result.columns
    return next((columns.index(c) for c in columns if c.title == column_name), None)


def _get_column_values(
    column_name: str, run_set_result: tablegenerator.RunSetResult
) -> List[Decimal]:

    column_index = _get_column_index(column_name, run_set_result)
    if column_index is None:
        return list()

    return [Util.to_decimal(r.values[column_index]) for r in run_set_result.results]


def _sum(vs):
    return Decimal(sum(vs))


def _create_category_data(
    column_name: str, run_set_result: tablegenerator.RunSetResult
) -> CategoryData:
    correct_mask = [
        r.category == result.CATEGORY_CORRECT for r in run_set_result.results
    ]
    unconfirmed_mask = [
        r.category == result.CATEGORY_CORRECT_UNCONFIRMED
        for r in run_set_result.results
    ]
    false_results = [is_false(r.status) for r in run_set_result.results]
    correct_false_mask = [c and f for c, f in zip(correct_mask, false_results)]
    unconfirmed_false_mask = [c and f for c, f in zip(unconfirmed_mask, false_results)]

    data_sequence = _get_column_values(column_name, run_set_result)
    assert all((d is None or isinstance(d, Decimal) for d in data_sequence))

    total = _sum(v or 0 for v in data_sequence)
    success = _sum(v or 0 for v in itertools.compress(data_sequence, correct_mask))
    success_false = _sum(
        v or 0 for v in itertools.compress(data_sequence, correct_false_mask)
    )
    unconfirmed = _sum(
        v or 0 for v in itertools.compress(data_sequence, unconfirmed_mask)
    )
    unconfirmed_false = _sum(
        v or 0 for v in itertools.compress(data_sequence, unconfirmed_false_mask)
    )

    return CategoryData(
        total, success, success_false, unconfirmed, unconfirmed_false, data_sequence
    )


def get_score(run_result: tablegenerator.RunResult, competition) -> Optional[Decimal]:
    score_column_index = _get_column_index(SCORE_COLUMN_NAME, run_result)

    score = run_result.score
    if score_column_index is not None:
        # Always use explicitly given score instead of score computed by table generator,
        # if available
        listed_score = run_result.values[score_column_index]
        score = None
        if listed_score is not None:
            try:
                score = Decimal(listed_score)
            except TypeError as e:
                logging.debug(
                    "Type error while creating score for %s",
                    run_result.task_id,
                    exc_info=e,
                )
    if score is None:
        if SV_COMP in competition:
            return None
        else:
            score = Decimal(0.0)

    return score


def _get_scores_data(
    run_set_result: tablegenerator.RunSetResult,
    category: str,
    verifier: str,
    competition: str,
) -> List[Decimal]:
    score, score_false = 0, 0
    correct_true, correct_false = 0, 0
    correct_unconfirmed_true, correct_unconfirmed_false = 0, 0
    incorrect_true, incorrect_false = 0, 0

    for run_result in run_set_result.results:
        run_result.score = get_score(run_result, competition)

        if run_result.score is None:
            logging.warning(
                'Score missing for task "{0}" (category "{1}", verifier "{2}"), cannot produce score-based quantile data.'.format(
                    run_result.task_id[0], category, verifier
                )
            )
            continue

        score += run_result.score
        if is_false(run_result.status):
            score_false += run_result.score
        if run_result.category == result.CATEGORY_CORRECT:
            if is_false(run_result.status):
                correct_false += 1
            else:
                correct_true += 1
        elif run_result.category == result.CATEGORY_CORRECT_UNCONFIRMED:
            if is_false(run_result.status):
                correct_unconfirmed_false += 1
            else:
                correct_unconfirmed_true += 1
        elif run_result.category == result.CATEGORY_WRONG:
            if is_false(run_result.status):
                incorrect_false += 1
            else:
                incorrect_true += 1

    expected_score = (
        correct_false * 1
        + correct_true * 2
        + correct_unconfirmed_true * 0
        + correct_unconfirmed_false * 0
        + incorrect_false * -16
        + incorrect_true * -32
    )
    assert not SV_COMP in competition or score == expected_score
    expected_score = (
        correct_false * 1 + correct_unconfirmed_false * 0 + incorrect_false * -16
    )
    assert not SV_COMP in competition or score_false == expected_score

    return {
        "score": score,
        "score_false": score_false,
        "correct_true": correct_true,
        "correct_false": correct_false,
        "correct_unconfirmed_true": correct_unconfirmed_true,
        "correct_unconfirmed_false": correct_unconfirmed_false,
        "incorrect_true": incorrect_true,
        "incorrect_false": incorrect_false,
    }


def get_category_info(run_set_result, category: str) -> Optional[Category]:
    rows = tablegenerator.get_rows([run_set_result])
    score_column_index = _get_column_index(SCORE_COLUMN_NAME, run_set_result)
    tasks_total = len(rows)
    if score_column_index is None:
        logging.debug("Computing our own score for %s", category)
        # No explicit score column given => use scores computed by table generator
        max_score, count_true, count_false = tablegenerator.htmltable._get_task_counts(
            rows
        )
        possible_score = max_score or Decimal(0)
        possible_score_false = count_false * SCORE_CORRECT_FALSE
    else:
        possible_score = 0  # We use 0 instead of None because this avoid many special cases for algorithmic computations later on
        possible_score_false = 0
    if tasks_total == 0:
        logging.debug("No tasks for category %s, returning no category info", category)
        return None
    return Category(category, tasks_total, possible_score, possible_score_false)


def _get_qplot_data(
    run_set_result: tablegenerator.RunSetResult,
    values: List[Decimal],
    tasks_total: int,
    category: str,
    verifier: str,
    competition: str,
) -> List[Tuple[float, float, str]]:
    """
    Return list of tuples (normalized_score, value, status).
    Each tuple represents one run result with its score, the
    corresponding value from the given value list, and the run's status.
    """
    # TODO: Replace returned tuple by dict with speaking names as keys

    qplot_data = []
    for run_result, curr_value in zip(run_set_result.results, values):
        if (
            run_result.category == result.CATEGORY_WRONG
            or run_result.category == result.CATEGORY_CORRECT
            or run_result.category == result.CATEGORY_CORRECT_UNCONFIRMED
            or not SV_COMP in competition
        ):
            qplot_data.append(
                (float(run_result.score) / tasks_total, curr_value, run_result.status)
            )
        elif run_result.category == result.CATEGORY_MISSING:
            print(
                'Property missing for task "{0}" (category "{1}", verifier "{2}"), cannot produce score-based quantile data.'.format(
                    run_result.task_id[0], category, verifier
                )
            )
            continue
        else:
            assert run_result.category in {
                result.CATEGORY_ERROR,
                result.CATEGORY_UNKNOWN,
            }
    return qplot_data


def get_verifiers(category_info):
    return category_info["verifiers"]


def get_verifier_info(category_info, verifier):
    return get_verifiers(category_info)[verifier]


def get_representative_info(category_info, verifier):
    return get_verifier_info(category_info, verifier)["jury-member"]


def get_categories(category_info):
    """Returns the defined meta-categories of the given category info"""
    return category_info["categories"]


def get_demo_categories(category_info):
    try:
        return category_info["demo_categories"]
    except KeyError:
        # no demo categories in category info
        return list()


def get_hors_concours(category_info):
    try:
        return category_info["hors_concours"]
    except KeyError:
        # no hors concours in category info
        return list()


def get_all_categories_table_order(category_info):
    return category_info["categories_table_order"]


def get_all_categories_process_order(category_info):
    return category_info["categories_process_order"]


def get_competition_with_year(category_info) -> str:
    year = str(category_info["year"])[-2:]
    competition = category_info["competition"]
    return competition + year


def handle_base_category(category, results_path, category_info):
    cat_info = None
    competition = category_info["competition"]
    for verifier in get_verifiers(category_info):
        results_file = get_results_XML_file(
            category, verifier, results_path, category_info
        )
        if results_file is None:
            continue
        # print(verifier)
        # load results
        run_set_result = tablegenerator.RunSetResult.create_from_xml(
            results_file, tablegenerator.parse_results_file(results_file)
        )
        run_set_result.collect_data(False)

        if cat_info is None:
            cat_info = get_category_info(run_set_result, category)
            if cat_info is None:
                logging.debug("No tasks in category %s for %s", category, verifier)
                continue

        # Collect data points (score, cputime, status) for generating quantile plots.
        score_data = _get_scores_data(run_set_result, category, verifier, competition)
        cputime = _create_category_data("cputime", run_set_result)
        cpuenergy = _create_category_data("cpuenergy", run_set_result)

        if not cputime.sequence:
            logging.debug("CPU time missing for {0}, {1}".format(verifier, category))
        if not cpuenergy.sequence:
            logging.debug("CPU energy missing for {0}, {1}".format(verifier, category))

        get_qplot = partial(
            _get_qplot_data,
            run_set_result=run_set_result,
            tasks_total=cat_info.tasks,
            category=category,
            verifier=verifier,
            competition=competition,
        )

        qplot_data_cputime = get_qplot(values=cputime.sequence)
        qplot_data_cpuenergy = get_qplot(values=cpuenergy.sequence)

        cat_info.results[verifier] = CategoryResult(
            cputime=cputime,
            qplot_cputime=qplot_data_cputime,
            cpuenergy=cpuenergy,
            qplot_cpuenergy=qplot_data_cpuenergy,
            results_file=results_file,
            **score_data,
        )  # expands to the individual score parameters
    return cat_info


def get_best(category, category_info, isFalsification=False):
    hors_concours = get_hors_concours(category_info)
    competitors = [
        (v, r)
        for v, r in category.results.items()
        if v not in hors_concours
        and not is_opt_out(category.name, verifier=v, category_info=category_info)
    ]
    if isFalsification:
        result = [
            name
            for name, result in sorted(
                competitors,
                key=lambda x: (
                    x[1].score_false,
                    (1 / Decimal(x[1].cputime.success_false))
                    if x[1].cputime.success_false
                    else 0,
                ),
                reverse=True,
            )[0:3]
        ]
    else:
        result = [
            name
            for name, result in sorted(
                competitors,
                key=lambda x: (
                    x[1].score,
                    (1 / Decimal(x[1].cputime.success)) if x[1].cputime.success else 0,
                ),
                reverse=True,
            )[0:3]
        ]
    if len(result) < 3 and category.name not in get_demo_categories(category_info):
        logging.warning(
            "Less than three verifiers in category %s. Verifiers: %s",
            category.name,
            [r for r in category.results],
        )
    while len(result) < 3:
        result.append(None)
    return result


def get_name(category_info, verifier):
    try:
        return get_verifier_info(category_info, verifier)["name"]
    except KeyError:
        logging.error("Participant not in category structure: %s", verifier)
        sys.exit(1)


def to_http(url):
    if url:
        if not url.startswith("http"):
            logging.warning("URL is not a valid http URL: %s", url)
            logging.info("Adding missing https:// to invalid URL %s", url)
            return f"https://{url}"
    return url


def get_project_url(category_info, verifier):
    info = get_verifier_info(category_info, verifier)
    try:
        url = info["url"]
    except KeyError:
        logging.warning("No project url for %s", verifier)
        return ""
    return to_http(url)


def get_link(category_info, verifier):
    url = get_project_url(category_info, verifier)
    return f"<a href='{url}'>{get_name(category_info, verifier)}</a>"


def get_link_alltab(verifier, category_info):
    return (
        "<a href='"
        + verifier
        + ".results."
        + get_competition_with_year(category_info)
        + ".All.table.html'>"
        + get_name(category_info, verifier)
        + "</a>"
    )


def get_member_lines(category_info):
    result_members = "\t<tr>\n\t\t<td>Representing Jury Member</td><td></td>"
    result_affil = "\t<tr>\n\t\t<td>Affiliation</td><td></td>"
    for verifier in get_verifiers(category_info):
        member_info = get_representative_info(category_info, verifier)
        try:
            member_name = member_info["name"]
            member_affiliation = (
                f"{member_info['institution']}, {member_info['country']}"
            )
        except KeyError as e:
            logging.warning("Failed to get info for %s, ignoring: %s", verifier, e)
            continue
        try:
            member_homepage = to_http(member_info["url"])
            result_members += (
                "<td><a href='" + member_homepage + "'>" + member_name + "</a></td>"
            )
        except KeyError:
            result_members += "<td>" + member_name + "</td>"

        result_affil += "<td>" + member_affiliation + "</td>"
    result_members += "\n\t</tr>\n"
    result_affil += "\n\t</tr>\n"
    return result_members + result_affil


def get_verifier_html_and_tab(category_info):
    verifier_html = (
        "\t\t<th><a href='../../systems.php'>Participants</a></th><th>Plots</th>"
    )
    verifier_tab = "Participants\t\t"

    for verifier in get_verifiers(category_info):
        logging.info(verifier)
        verifier_html += "<th>" + get_link_alltab(verifier, category_info) + "</th>"
        verifier_tab += get_name(category_info, verifier) + "\t"

    return verifier_html, verifier_tab


def is_opt_out(category, verifier, category_info):
    # The OPT_OUT has higher dominance than the OPT_IN (i.e. if a verifier, category is on the OPT_OUT,
    # it doesn't matter whether the same pair is on the OPT_IN - it is not displayed)
    if "opt_out" not in category_info or not category_info["opt_out"]:
        return False  # there are no opt outs at all, so the queried one can't be one
    opt_out = category_info["opt_out"]
    return verifier in opt_out and category in opt_out[verifier]


def prepare_qplot_csv(
    qplot: list, processed_category: Category, competition: str
) -> Optional[List[Tuple]]:
    category_tasks = processed_category.tasks
    if not qplot:
        return None

    x_and_y_list = list()
    if processed_category.name.startswith(FALSIFIER_PREFIX):
        qplot_data = [(s, c, st) for (s, c, st) in qplot if is_false(st)]
    else:
        qplot_data = qplot

    if SV_COMP in competition:
        # Left-most data-point in plot is at the sum of all negative scores
        index = sum(
            [float(score) * category_tasks for score, _, _ in qplot_data if score < 0]
        )
        # Data points for positive scores, sort them by value
        qplot_ordered = [(score, value) for score, value, _ in qplot_data if score > 0]
        qplot_ordered.sort(key=lambda entry: entry[1])
        for score, value in qplot_ordered:
            index += float(score) * category_tasks
            x_and_y_list.append((index, value))
    else:
        # Left-most data-point is zero for Test-Comp
        index = 0.0
        score_accum = 0.0
        # Data points for score/coverage
        qplot_ordered = [(score, value) for score, value, _ in qplot_data if score >= 0]
        qplot_ordered.sort(key=lambda entry: -entry[0])
        for score, value in qplot_ordered:
            index += 1.0
            score_accum += float(score) * category_tasks
            x_and_y_list.append((score_accum, index))

    return x_and_y_list


def write_csv(
    path: Path, qplot_data: list, processed_category: Category, category_info
) -> None:
    qplot_x_and_y_values = prepare_qplot_csv(
        qplot_data, processed_category, category_info["competition"]
    )
    if qplot_x_and_y_values:
        if path.exists():
            path.unlink()
        if not path.parent.exists():
            os.makedirs(str(path.parent))
        csv = "\n".join([str(x) + "\t" + str(y) for x, y in qplot_x_and_y_values])
        write_text(path, csv)


def _prepare_for_rfs(value: Decimal) -> str:
    return str(round(value, 9) if value else value)


def _get_html_table_cell(content: Optional[str], measure: str, rank_class: str) -> str:
    if content is not None and content != "":
        return (
            "<td class='value"
            + rank_class
            + "'>"
            + content
            + "&nbsp;"
            + measure
            + "</td>"
        )
    else:
        return "<td></td>"


def dump_output_files(processed_categories, category_info):
    verifier_html, verifier_tab = get_verifier_html_and_tab(category_info)
    html_string = (
        """
<hr/>
<h2>Table of All Results</h2>

<p>
In every table cell for competition results,
we list the points in the first row and the CPU time (rounded to two significant digits) for successful runs in the second row.
</p>

<p>
The entry 'Hors Concours' in the row for 'Representing Jury Member' means
that the tool was added at the organizer's disposition and
does not participate in the rankings or prize allocation.<br/>
The entry '&ndash;' means that the competition candidate opted-out in the category.<br/>
The definition of the <a href="../../rules.php#scores">scoring schema</a>
and the <a href="../../benchmarks.php">categories</a> is given on the respective SV-COMP web pages.
</p>

<p>
<input type='checkbox' id='hide-base-categories' onclick="$('.sub').toggle()"><label id='hide-base-categories-label' for='hide-base-categories'>Hide base categories</label>
</p>
"""
        + "<table id='scoretable'>\n"
        + "<thead>\n"
        + "\t<tr class='head'>\n"
        + verifier_html
        + "\n\t</tr>\n"
        + "</thead>\n<tbody>"
        + get_member_lines(category_info)
    )
    html_ranking_string = """
<hr />
<h2><a id="plots">Ranking by Category (with Score-Based Quantile Plots)</a></h2>

<table id='ranktable'>
<tr>
"""
    tab_string = ""
    tex_ranking_string = "\\\\[-\\normalbaselineskip]" + "\n"

    meta_categories = get_categories(category_info)
    demo_categories = get_demo_categories(category_info)
    categories_table_order = get_all_categories_table_order(category_info)
    verifiers = get_verifiers(category_info)

    for category in categories_table_order:
        if category in demo_categories:
            continue
        tasks_total = processed_categories[category].tasks
        if category.startswith(FALSIFIER_PREFIX):
            possible_score = round(processed_categories[category].possible_score_false)
            best_verifiers = get_best(
                processed_categories[category], category_info, isFalsification=True
            )
        else:
            possible_score = round(processed_categories[category].possible_score)
            best_verifiers = get_best(processed_categories[category], category_info)
        score_tab = category + "\t" + str(tasks_total) + "\t"
        cputime_success_tab = "CPU Time\t\t"
        cputime_success_true_tab = "CPU Time (true-tasks)\t\t"
        cputime_success_false_tab = "CPU Time (false-tasks)\t\t"
        cpuenergy_success_tab = "CPU Energy\t\t"
        correct_true_tab = "correct true\t\t"
        correct_false_tab = "correct false\t\t"
        unconfirmed_true_tab = "unconfirmed true\t\t"
        unconfirmed_false_tab = "unconfirmed false\t\t"
        incorrect_true_tab = "incorrect true\t\t"
        incorrect_false_tab = "incorrect false\t\t"

        if category in meta_categories:
            prefix = "META_"
        else:
            prefix = ""
        filename = prefix + category
        categoryname = category

        score_html = (
            "\t<td class='category-name'><a href='"
            + filename
            + ".table.html'>"
            + categoryname
            + "</a><br />"
            + "<span class='stats'>"
            + str(tasks_total)
            + " tasks"
        )
        if possible_score:
            score_html += ", max. score: " + str(possible_score)
        score_html += (
            "</span></td>\n"
            + "<td class='tinyplot'><a href='quantilePlot-"
            + categoryname.replace(".", "-")
            + ".svg'><img class='tinyplot' src='quantilePlot-"
            + categoryname.replace(".", "-")
            + ".svg' alt='Quantile-Plot' /></a></td>\n"
        )
        cputime_success_html = "\t<td>CPU time</td><td></td>"
        cpuenergy_success_html = "\t<td>CPU energy</td><td></td>"

        write_text(
            RSFSCORES,
            categoryname
            + "\tTASKSTOTAL\t"
            + str(processed_categories[category].tasks)
            + "\n"
            + categoryname
            + "\tMAXSCORE\t"
            + str(possible_score),
        )

        results = processed_categories[category].results
        for verifier in verifiers:
            if verifier not in results.keys() or is_opt_out(
                category, verifier, category_info
            ):
                score = ""
                cputime_success = ""
                cputime_success_true = ""
                cputime_success_false = ""
                cpuenergy_success = ""
                correct_true = ""
                correct_false = ""
                unconfirmed_true = ""
                unconfirmed_false = ""
                incorrect_true = ""
                incorrect_false = ""
            else:
                if category.startswith(FALSIFIER_PREFIX):
                    # Compute score taking into account only correct and incorrect false
                    score = results[verifier].score_false
                    # assert round(score) == round(results[verifier].correct_false * 1 + results[verifier].incorrect_false * -16)
                    cputime_success = results[verifier].cputime.success_false
                    cputime_success_true = None
                    cputime_success_false = cputime_success
                    cpuenergy_success = results[verifier].cpuenergy.success_false
                else:
                    score = results[verifier].score
                    # assert round(score) == round(results[verifier].correct_false * 1 + results[verifier].correct_true * 2 \
                    #                             + results[verifier].incorrect_false * -16 + results[verifier].incorrect_true * -32)
                    cputime_success = results[verifier].cputime.success
                    cputime_success_true = results[verifier].cputime.success_true
                    cputime_success_false = results[verifier].cputime.success_false
                    cpuenergy_success = results[verifier].cpuenergy.success

                rfs_rows = [
                    ("SCORE", _prepare_for_rfs(score)),
                    ("CPUTIMESUCCESS", _prepare_for_rfs(cputime_success)),
                    ("CPUTIMESUCCESSTRUE", _prepare_for_rfs(cputime_success_true)),
                    ("CPUTIMESUCCESSFALSE", _prepare_for_rfs(cputime_success_false)),
                    ("CPUENERGYSUCCESS", _prepare_for_rfs(cpuenergy_success)),
                ]
                write_to_rfs(categoryname, verifier, rfs_rows)

                score = round(score)
                if score is None:
                    score = ""

                correct_true = results[verifier].correct_true
                correct_false = results[verifier].correct_false
                unconfirmed_true = results[verifier].correct_unconfirmed_true
                unconfirmed_false = results[verifier].correct_unconfirmed_false
                incorrect_true = results[verifier].incorrect_true
                incorrect_false = results[verifier].incorrect_false

            rank_class = ""
            if category in meta_categories["Overall"][
                "categories"
            ] or category.endswith("Overall"):
                if verifier == best_verifiers[0]:
                    rank_class = " gold"
                elif verifier == best_verifiers[1]:
                    rank_class = " silver"
                elif verifier == best_verifiers[2]:
                    rank_class = " bronze"

            correct_true_tab += str(correct_true) + "\t"
            correct_false_tab += str(correct_false) + "\t"
            unconfirmed_true_tab += str(unconfirmed_true) + "\t"
            unconfirmed_false_tab += str(unconfirmed_false) + "\t"
            incorrect_true_tab += str(incorrect_true) + "\t"
            incorrect_false_tab += str(incorrect_false) + "\t"

            score_tab += str(score) + "\t"
            cputime_success_tab += str(cputime_success) + "\t"
            cputime_success_true_tab += str(cputime_success_true) + "\t"
            cputime_success_false_tab += str(cputime_success_false) + "\t"
            cpuenergy_success_tab += str(cpuenergy_success) + "\t"

            def round_time(value):
                time_column = tablegenerator.Column(
                    "Time", "", 2, "", tablegenerator.columns.ColumnMeasureType(2)
                )
                if value == "" or value is None:
                    return ""
                return time_column.format_value(value, format_target="csv").strip()

            def round_energy(value):
                energy_column = tablegenerator.Column(
                    "Energy", "", 2, "", tablegenerator.columns.ColumnMeasureType(2)
                )
                if value == "" or value is None:
                    return ""
                return energy_column.format_value(value, format_target="csv").strip()

            cputime_success = round_time(cputime_success)
            cputime_success_true = round_time(cputime_success_true)
            cputime_success_false = round_time(cputime_success_false)
            cpuenergy_success = round_energy(cpuenergy_success)

            score_link = str(score)
            if score is not None and score != "":
                results_file = results[verifier].results_file
                if results_file:
                    score_link = (
                        "<a href='"
                        + os.path.basename(results_file)
                        + ".table.html'>"
                        + score_link
                        + "</a>"
                    )
                else:
                    score_link = (
                        "<a href='"
                        + filename
                        + "_"
                        + verifier
                        + ".table.html'>"
                        + score_link
                        + "</a>"
                    )
            score_html += (
                "<td class='value"
                + rank_class
                + ("" if score != "" else " empty")
                + "'>"
                + score_link
                + "</td>"
            )
            cputime_success_html += _get_html_table_cell(
                cputime_success, "s", rank_class
            )
            cpuenergy_success_html += _get_html_table_cell(
                cpuenergy_success, "J", rank_class
            )

            # CSV file for Quantile Plot
            if score is not None and score != "":
                cputime_path = QPLOT_PATH / Path(
                    "QPLOT."
                    + categoryname.replace(".", "-")
                    + "."
                    + get_name(category_info, verifier)
                    .replace("/", "-")
                    .replace(" ", "-")
                    .replace(".", "-")
                    + "."
                    + "quantile-plot.csv"
                )

                write_csv(
                    cputime_path,
                    results[verifier].qplot_cputime,
                    processed_categories[category],
                    category_info,
                )
                cpuenergy_path = QPLOT_PATH / Path(
                    "QPLOT."
                    + categoryname.replace(".", "-")
                    + "."
                    + get_name(category_info, verifier)
                    .replace("/", "-")
                    .replace(" ", "-")
                    .replace(".", "-")
                    + "."
                    + "quantile-plot-cpuenergy.csv"
                )

                write_csv(
                    cpuenergy_path,
                    results[verifier].qplot_cpuenergy,
                    processed_categories[category],
                    category_info,
                )

        # end for verifier

        tab_string += (
            "\n".join(
                [
                    score_tab,
                    cputime_success_tab,
                    cputime_success_true_tab,
                    cputime_success_false_tab,
                    cpuenergy_success_tab,
                    correct_true_tab,
                    correct_false_tab,
                    unconfirmed_true_tab,
                    unconfirmed_false_tab,
                    incorrect_true_tab,
                    incorrect_false_tab,
                ]
            )
            + "\n"
        )

        if category in meta_categories["Overall"]["categories"] or category.endswith(
            "Overall"
        ):
            trprefix = "main"
        else:
            trprefix = "sub"
        html_string += (
            "\n".join(
                [
                    "\t<tr class='" + trprefix + " score' id='" + category + "'>",
                    score_html,
                    "\t</tr>",
                    "\t<tr class='" + trprefix + " cputime'>",
                    cputime_success_html,
                    "\t</tr>",
                ]
            )
            + "\n"
        )
        sizeclass = ""
        if category == "Overall":
            sizeclass = " colspan='2'"
        if trprefix == "main":
            html_ranking_string += (
                "    <td class='rank'"
                + sizeclass
                + ">\n"
                + "      <span class='title'><a href="
                + filename
                + ".table.html>"
                + categoryname
                + "</a></span><br />\n"
                + "        <span class='rank gold'  >1. "
                + get_link(category_info, best_verifiers[0])
                + "</span> <br />\n"
                + "        <span class='rank silver'>2. "
                + get_link(category_info, best_verifiers[1])
                + "</span> <br />\n"
                + "        <span class='rank bronze'>3. "
                + get_link(category_info, best_verifiers[2])
                + "</span> <br />\n"
                + "        <a href='quantilePlot-"
                + categoryname.replace(".", "-")
                + ".svg'><img class='plot' src='quantilePlot-"
                + categoryname.replace(".", "-")
                + ".svg' alt='Quantile-Plot' /></a>\n"
                + "    </td>\n"
            )
            if categoryname in ["ConcurrencySafety", "SoftwareSystems", "Overall"]:
                html_ranking_string += "  </tr>\n" + "  <tr>\n"
        # Dump ranking table
        if category in meta_categories["Overall"]["categories"] or category.endswith(
            "Overall"
        ):
            tex_ranking_string += (
                "\\hline"
                + "\n"
                + "\\rankcategory{"
                + category
                + "}&&&&&&& \\placeholderrank{}\\\\"
                + "\n"
            )
            for rank in range(0, 3):
                verifier = best_verifiers[rank]
                result = results[verifier]
                score_tex = str(round(result.score))
                cputime = result.cputime.success
                cpuenergy = result.cpuenergy.success
                count_correct = result.correct_true + result.correct_false
                count_unconfirmed = (
                    result.correct_unconfirmed_true + result.correct_unconfirmed_false
                )
                count_incorrect_false = result.incorrect_false
                count_incorrect_true = result.incorrect_true
                if category.startswith(FALSIFIER_PREFIX):
                    score_tex = str(round(result.score_false))
                    cputime = result.cputime.success_false
                    cpuenergy = result.cpuenergy.success_false
                    count_correct = result.correct_false
                    count_unconfirmed = result.correct_unconfirmed_false
                    count_incorrect_false = result.incorrect_false
                    count_incorrect_true = ""

                verifier_tex = "\\ranktool{\\" + re.sub("[-0-9]", "", verifier) + "}"
                if rank == 0:
                    score_tex = "\\bfseries " + score_tex + ""
                    verifier_tex = "\win{" + verifier_tex + "}"
                tex_ranking_string += (
                    ""
                    + str(rank + 1)
                    + " & "
                    + verifier_tex
                    + " & "
                    + score_tex
                    + " & "
                    + str(round_time(cputime / 3600))
                    + " & "
                    + str(round_energy(cpuenergy / 3600000))
                    + " & "
                    + str(count_correct)
                    + " & "
                    + str(count_unconfirmed)
                    + " & "
                    + str(count_incorrect_false if count_incorrect_false != 0 else "")
                    + " & {\\bfseries "
                    + str(count_incorrect_true if count_incorrect_true != 0 else "")
                    + "} "
                    + "\\\\"
                    + "\n"
                )

    # end for category
    tab_string += verifier_tab + "\n"
    html_string += (
        "\t<tr class='head'>\n" + verifier_html + "\n\t</tr>\n" + "</tbody></table>\n"
    )
    html_ranking_string += """
  </tr>
</table>
"""

    # Result table in TeX
    tex_results_header_string = (
        "\\\\[-\\normalbaselineskip]"
        + """
  \\begin{minipage}[b]{25mm}
  {\\normalsize\\bfseries Participant}\\\\
  {}
  \end{minipage}
  \colspace{}
"""
    )
    write_text(TEXRESULTS, tex_results_header_string)
    # Header for results table
    for category in categories_table_order:
        if not category in meta_categories["Overall"][
            "categories"
        ] and not category.endswith("Overall"):
            continue
        tasks_total = processed_categories[category].tasks
        if category.startswith(FALSIFIER_PREFIX):
            possible_score = round(processed_categories[category].possible_score_false)
            best_verifiers = get_best(
                processed_categories[category], category_info, isFalsification=True
            )
        else:
            possible_score = round(processed_categories[category].possible_score)
            best_verifiers = get_best(processed_categories[category], category_info)
        tex_results_header_string = (
            "& \colspace{}"
            + "\\up{\\bfseries "
            + str(category)
            + "} "
            + "\\up{"
            + str(possible_score)
            + " points}"
            + "\\up{"
            + str(tasks_total)
            + " tasks}"
            + "\\colspace{}"
        )
        write_text(TEXRESULTS, tex_results_header_string)
    write_text(TEXRESULTS, "\\\\")

    # Body rows for results table
    for verifier in verifiers:
        tex_results_stringscore = (
            "\hlineresults"
            + "\n"
            + "{\\bfseries\scshape \\"
            + re.sub("[-0-9]", "", verifier)
            + "} \spaceholder"
        )
        for category in categories_table_order:
            if category.startswith(FALSIFIER_PREFIX):
                best_verifiers = get_best(
                    processed_categories[category], category_info, isFalsification=True
                )
            else:
                best_verifiers = get_best(processed_categories[category], category_info)
            if not category in meta_categories["Overall"][
                "categories"
            ] and not category.endswith("Overall"):
                continue
            results = processed_categories[category].results
            if verifier not in results.keys() or is_opt_out(
                category, verifier, category_info
            ):
                score = "\\none"
            else:
                if category.startswith(FALSIFIER_PREFIX):
                    score = results[verifier].score_false
                else:
                    score = results[verifier].score
                score = str(round(score))
                if verifier == best_verifiers[0]:
                    score = "\\gold{" + score + "}"
                elif verifier == best_verifiers[1]:
                    score = "\\silver{" + score + "}"
                elif verifier == best_verifiers[2]:
                    score = "\\bronze{" + score + "}"
            tex_results_stringscore += " & " + score
        tex_results_stringscore += "\\\\[-0.2ex]"
        write_text(TEXRESULTS, tex_results_stringscore)

    write_text(TABSCORES, tab_string)
    write_text(HTMLSCORES, html_ranking_string)
    write_text(HTMLSCORES, html_string)
    write_text(TEXRANKING, tex_ranking_string)


def handle_category(category, results_path, category_info, processed_categories=None):
    msg_to_output("Processing category " + str(category) + ".")
    if category in get_categories(category_info):
        info = handle_meta_category(category, category_info, processed_categories)
    else:
        info = handle_base_category(category, results_path, category_info)
    assert info is not None, "No info for %s" % category
    print("Category " + category + " done.")
    return category, info


def concatenate_dict(dict1, dict2):
    return dict(list(dict1.items()) + list(dict2.items()))


def handle_categories_parallel(
    category_names, results_path, category_info, processed_categories=None
):
    # Use enough processes such that all categories can be processed in parallel
    with Pool(len(category_names)) as parallel:
        # with Pool(1) as parallel:
        handle_category_with_info_set = partial(
            handle_category,
            results_path=results_path,
            category_info=category_info,
            processed_categories=processed_categories,
        )
        result_categories = parallel.map(handle_category_with_info_set, category_names)
        return dict(result_categories)


def parse(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--category",
        required=False,
        default="benchmark-defs/category-structure.yml",
        help="path to categories.yml",
    )
    parser.add_argument(
        "--results_path",
        required=False,
        default="./results-verified",
        help="path to verification-run results",
    )
    parser.add_argument(
        "--verbose",
        required=False,
        default=False,
        action="store_true",
        help="verbose output",
    )
    args = parser.parse_args(argv)

    args.category = Path(args.category)
    args.results_path = Path(args.results_path)

    if not args.category.exists:
        raise FileNotFoundError(f"Category file {args.category} does not exist")
    if not args.results_path.exists or not args.results_path.is_dir():
        raise FileNotFoundError(f"Results directory {args.results_path} does not exist")
    return args


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse(argv)
    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.init(log_level, name="mkAnaScores")

    results_path = args.results_path
    categories_yml = args.category

    global TABLENAME, HTMLSCORES, TABSCORES, RSFSCORES, TABLESETUP, TEXRANKING, TEXRESULTS, QPLOT_PATH
    TABLENAME = "scoretable"
    # TABLENAME  = "AhT8IeQuoo"
    HTMLSCORES = results_path / Path(TABLENAME + ".html")
    TABSCORES = results_path / Path(TABLENAME + ".tsv")
    RSFSCORES = results_path / Path(TABLENAME + ".rsf")
    TABLESETUP = Path("scripts/prepare-tables") / "mkAnaAllTables-Config.sh"
    TEXRANKING = results_path / "scoreranking.tex"
    TEXRESULTS = results_path / "scoreresults.tex"
    QPLOT_PATH = Path("./results-qplots")

    rename_to_old_if_exists(RSFSCORES)
    rename_to_old_if_exists(TABSCORES)
    rename_to_old_if_exists(HTMLSCORES)
    rename_to_old_if_exists(TEXRANKING)
    rename_to_old_if_exists(TEXRESULTS)
    rename_to_old_if_exists(TABLESETUP)

    with open(categories_yml) as inp:
        try:
            ctgry_info = yaml.load(inp, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            print(e)
            sys.exit(1)

    meta_categories = get_categories(ctgry_info)
    demo_categories = get_demo_categories(ctgry_info)
    categories_process_order = get_all_categories_process_order(ctgry_info)

    base_categories = [
        category
        for category in categories_process_order
        if category not in meta_categories
    ]
    base_categories_for_metas = [
        base_cat for base_cat in base_categories if base_cat not in demo_categories
    ]

    # For mkAnaAllTables.sh
    table_setup_string = 'VERIFIERS="'
    for verifier in ctgry_info["verifiers"]:
        table_setup_string += verifier + " "
    table_setup_string += '";\n\n'

    table_setup_string += 'CATEGORIES="'
    for base_cat in base_categories:
        table_setup_string += base_cat + " "
    table_setup_string += '";\n\n'

    table_setup_string += "VERIFIERSLIST=(\n"
    for (meta_cat, dictionary) in meta_categories.items():
        table_setup_string += '"' + meta_cat + ": "
        for verifier in dictionary["verifiers"]:
            table_setup_string += verifier + " "
        table_setup_string += '"\n'
    table_setup_string += ")\n\n"

    table_setup_string += "CATEGORIESLIST=(\n"
    for (meta_cat, dictionary) in meta_categories.items():
        if meta_cat not in ("Overall", "FalsificationOverall"):
            table_setup_string += '"' + meta_cat + ": "
            for cat in [
                c for c in base_categories_for_metas if c in dictionary["categories"]
            ]:
                table_setup_string += cat + " "
            table_setup_string += '"\n'
    table_setup_string += '"FalsificationOverall: '
    for base_cat in base_categories_for_metas:
        table_setup_string += base_cat + " "
    table_setup_string += '"\n'
    table_setup_string += '"Overall: '
    for base_cat in base_categories_for_metas:
        table_setup_string += base_cat + " "
    table_setup_string += '"\n'
    table_setup_string += ")\n\n"
    write_text(TABLESETUP, table_setup_string)

    meta_categories = [
        category
        for category in categories_process_order
        if category in meta_categories and not category.endswith("Overall")
    ]

    # First handle base categories (on the results of which the meta categories depend)
    processed_categories = handle_categories_parallel(
        base_categories, results_path, ctgry_info
    )
    msg_to_output("Base categories done.")

    # Second meta categories
    for category in meta_categories:
        processed_categories = concatenate_dict(
            processed_categories,
            dict(
                [
                    handle_category(
                        category, results_path, ctgry_info, processed_categories
                    )
                ]
            ),
        )
    msg_to_output("Meta categories done.")
    # Third 'Overall' categories consisting of some meta- and some base categories
    # Since 'Overall' is a meta category, it is already very fast and no parallelization is needed.
    processed_categories = concatenate_dict(
        processed_categories,
        dict(
            [handle_category("Overall", results_path, ctgry_info, processed_categories)]
        ),
    )
    msg_to_output("Overall done.")
    competition = ctgry_info["competition"]
    if SV_COMP in competition:
        processed_categories = concatenate_dict(
            processed_categories,
            dict(
                [
                    handle_category(
                        "FalsificationOverall",
                        results_path,
                        ctgry_info,
                        processed_categories,
                    )
                ]
            ),
        )
        msg_to_output("FalsifierOverall done.")
        processed_categories = concatenate_dict(
            processed_categories,
            dict(
                [
                    handle_category(
                        "JavaOverall", results_path, ctgry_info, processed_categories
                    )
                ]
            ),
        )
        msg_to_output("JavaOverall done.")

    msg_to_output("Dumping TSV and HTML.")
    dump_output_files(processed_categories, ctgry_info)
    msg_to_output("Finished.")

    """
  # Print CPU times total
  cputime_competition = 0
  for category in processed_categories.keys():
      cputime_category = 0
      for verifier in get_verifiers(category_info):
          results = processed_categories[category].results
          if verifier not in results.keys():
              continue
          cputime_category    += results[verifier].cputime.total
          print(category, verifier, round(results[verifier].cputime.total/3600))
      print(category, round(cputime_category/3600))
  """


if __name__ == "__main__":
    sys.exit(main())
