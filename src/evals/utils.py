import re
import os
import pandas as pd
import random
import ast
from langchain_openai import ChatOpenAI, OpenAI
from langchain_community.chat_models.anthropic import ChatAnthropic
from langchain_community.chat_models.anyscale import ChatAnyscale
from langchain.agents import initialize_agent, AgentType
from src.tools_smolagents.tracking import create_function_tracker, wrap_tool
import csv
from src.tools import calendar, email, analytics, project_management, customer_relationship_manager, company_directory
from src.data_generation.data_generation_utils import HARDCODED_CURRENT_TIME
from src.tools.toolkits import (
    calendar_toolkit,
    email_toolkit,
    analytics_toolkit,
    project_management_toolkit,
    customer_relationship_manager_toolkit,
    company_directory_toolkit,
    tools_with_side_effects,
    reset_all as reset_all_original
)

from src.tools_smolagents.toolkits import (
    calendar_toolkit as smol_calendar_toolkit,
    email_toolkit as smol_email_toolkit,
    analytics_toolkit as smol_analytics_toolkit,
    project_management_toolkit as smol_project_management_toolkit,
    customer_relationship_manager_toolkit as smol_customer_relationship_manager_toolkit,
    company_directory_toolkit as smol_company_directory_toolkit,
    tools_with_side_effects as smol_tools_with_side_effects,
    GLOBAL_TOOL_TRACKER,
    reset_all as reset_all_smol,
)

from src.tools_improved.toolkits import (
    calendar_toolkit as calendar_toolkit_improved,
    email_toolkit as email_toolkit_improved,
    project_management_toolkit as project_management_toolkit_improved,
    customer_relationship_manager_toolkit as customer_relationship_manager_toolkit_improved,
    company_directory_toolkit as company_directory_toolkit_improved,
    tools_with_side_effects as tools_with_side_effects_improved,
    reset_all as reset_all_improved
)

from src.tools_improved_smolagents.toolkits import (
    calendar_toolkit as smol_calendar_toolkit_improved,
    email_toolkit as smol_email_toolkit_improved,
    analytics_toolkit as smol_analytics_toolkit_improved,
    project_management_toolkit as smol_project_management_toolkit_improved,
    customer_relationship_manager_toolkit as smol_customer_relationship_manager_toolkit_improved,
    company_directory_toolkit as smol_company_directory_toolkit_improved,
    tools_with_side_effects as smol_tools_with_side_effects_improved,
    reset_all as reset_all_improved_smol
)

from src.evals.unit_test_doc_utils import apply_unit_test_documentation
from src.evals.integration_test_doc_utils import apply_integration_test_documentation

from tqdm.auto import tqdm

from smolagents import CodeAgent
from smolagents.models import LiteLLMModel


DOMAINS = [calendar, email, analytics, project_management, customer_relationship_manager]
AVAILABLE_LLMS = [
    "gpt-4o-2024-08-06",
    "gpt-4o-mini-2024-07-18",
    "llama3.3-70b",
    "llama3.1-8b",
    "qwen-2.5-72b",
    "qwen-2.5-7b"
]

def reset_all():
    reset_all_original()
    reset_all_smol()
    reset_all_improved()
    reset_all_improved_smol()

def convert_agent_action_to_function_call(action):
    """Converts langchain_core.agents.AgentAction to an API call"""
    # Handle string input case
    if isinstance(action.tool_input, str):
        return f'{action.tool}.func("{action.tool_input}")'
    args = []
    for k, v in action.tool_input.items():
        args.append(f'{k}="{v}"')
    return action.tool + ".func(" + ", ".join(args) + ")"

def convert_agent_action_to_function_call_hf(action):
    """Converts langchain_core.agents.AgentAction to an API call"""
    args = []
    for k, v in action['parameters'].items():
        args.append(f'{k}="{v}"')
    return action['function_name'] + ".func(" + ", ".join(args) + ")"


def execute_actions_and_reset_state(actions):
    """
    Executes a list of actions on the calendar and returns the resulting calendar events.

    Parameters
    ----------
    actions : list
        List of actions to be executed. Each action should be a function call.

    Returns
    -------
    success bool
        True if the actions were executed successfully.
    new_calendar_state pd.DataFrame
        The resulting calendar events after executing the actions.
    new_email_state pd.DataFrame
        The resulting emails after executing the actions.
    new_analytics_state pd.DataFrame
        The resulting analytics data after executing the actions.
    """
    reset_all()
    for domain in DOMAINS:
        domain.reset_state()

    # Execute the actions
    for action in actions:
        try:
            eval(action)
        except:
            continue
    new_calendar_state = calendar.CALENDAR_EVENTS.copy()
    new_email_state = email.EMAILS.copy()
    new_analytics_state = analytics.PLOTS_DATA.copy()
    new_project_management_state = project_management.PROJECT_TASKS.copy()
    new_customer_relationship_manager_state = customer_relationship_manager.CRM_DATA.copy()

    reset_all()
    # Reset the state of the tools
    for domain in DOMAINS:
        domain.reset_state()
    return (
        True,
        new_calendar_state,
        new_email_state,
        new_analytics_state,
        new_project_management_state,
        new_customer_relationship_manager_state,
    )


def end_date_minor_error(ground_truth, prediction):
    """Function to check if the end date is off by one day in the prediction

    Parameters
    ----------
    ground_truth : list
        List of ground truth actions as strings.
    prediction : list
        List of predicted actions as strings.

    Returns
    -------
    bool
        True if the end date is off by one day in the prediction.
    """
    matches = 0
    for func in ground_truth:
        if "2023-11-29" in func:
            if func.replace("2023-11-29", "2023-11-30") in prediction:
                matches += 1
    if len(ground_truth) == 0:
        return False
    return matches == len(ground_truth)


def meeting_start_time_error(ground_truth, prediction):
    """Function to check if the meeting start time is off where the agent predicts the wrong first available time

    Parameters
    ----------
    ground_truth : list
        List of ground truth actions as strings.
    prediction : list
        List of predicted actions as strings.

    Returns
    -------
    bool
        True if the meeting start time is off by one hour in the prediction.
    """
    matches = 0
    next_free_time_ground_truth = "13:00:00"
    common_error_times = ["09:00:00", "11:00:00", "15:00:00", "15:30:00"]
    for func in ground_truth:
        if next_free_time_ground_truth in func:
            for time in common_error_times:
                if func.replace(next_free_time_ground_truth, time) in prediction:
                    matches += 1
                    break
    if len(ground_truth) == 0:
        return False
    return matches == len(ground_truth)


def is_exact_match(predicted_actions, ground_truth_actions):
    """
    Checks if the predicted actions are an exact match to the ground truth actions.

    Parameters
    ----------
    predicted_actions : list
        List of predicted actions as strings.
    ground_truth_actions : list
        List of ground truth actions as strings.

    Returns
    -------
    bool
        True if the predicted actions are an exact match to the ground truth actions.

    """
    tools_with_side_effects_names = [str(function.name) for function in tools_with_side_effects]
    predicted_actions_with_side_effects = [
        action for action in predicted_actions if get_function_name(action) in tools_with_side_effects_names
    ]
    predicted_actions_with_side_effects = sorted([action.lower() for action in predicted_actions_with_side_effects])
    ground_truth_actions = sorted([action.lower() for action in ground_truth_actions])

    return predicted_actions_with_side_effects == ground_truth_actions


def get_function_name(action):
    """Extracts the function name from a string"""
    return ".".join(action.split("(")[0].split(".")[0:2])


def is_correct(predicted_actions, ground_truth_actions, error):
    """
    Checks if the prediction is correct by comparing the state change after executing the actions.

    Parameters
    ----------
    predicted_actions : list
        List of predicted actions as strings.
    ground_truth_actions : list
        List of ground truth actions as strings.
    error : str
        Error message from the prediction.

    Returns
    -------
    bool
        True if the predicted actions result in the same state change as the ground truth actions.

    """
    if error:
        return False
    (
        successful_execution,
        predicted_calendar_state,
        predicted_email_state,
        predicted_analytics_state,
        predicted_project_management_state,
        predicted_customer_relationship_manager_state,
    ) = execute_actions_and_reset_state(predicted_actions)
    (
        _,
        ground_truth_calendar_state,
        ground_truth_email_state,
        ground_truth_analytics_state,
        ground_truth_project_management_state,
        ground_truth_customer_relationship_manager_state,
    ) = execute_actions_and_reset_state(ground_truth_actions)

    def convert_strs_to_lowercase(df):
        # For some fields the case matters, so we don't convert them to lowercase
        fields_not_to_convert = ["status", "list_name", "board"]
        for col in df.columns:
            if col not in fields_not_to_convert:
                df[col] = df[col].str.lower()
        return df

    # We allow for case-insensitive comparison of strings for most fields
    predicted_calendar_state = convert_strs_to_lowercase(predicted_calendar_state)
    predicted_email_state = convert_strs_to_lowercase(predicted_email_state)
    predicted_analytics_state = convert_strs_to_lowercase(predicted_analytics_state)
    predicted_project_management_state = convert_strs_to_lowercase(predicted_project_management_state)
    predicted_customer_relationship_manager_state = convert_strs_to_lowercase(
        predicted_customer_relationship_manager_state
    )

    ground_truth_calendar_state = convert_strs_to_lowercase(ground_truth_calendar_state)
    ground_truth_email_state = convert_strs_to_lowercase(ground_truth_email_state)
    ground_truth_analytics_state = convert_strs_to_lowercase(ground_truth_analytics_state)
    ground_truth_project_management_state = convert_strs_to_lowercase(ground_truth_project_management_state)
    ground_truth_customer_relationship_manager_state = convert_strs_to_lowercase(
        ground_truth_customer_relationship_manager_state
    )

    return (
        successful_execution
        and predicted_calendar_state.equals(ground_truth_calendar_state)
        and predicted_email_state.equals(ground_truth_email_state)
        and predicted_analytics_state.equals(ground_truth_analytics_state)
        and predicted_project_management_state.equals(ground_truth_project_management_state)
        and predicted_customer_relationship_manager_state.equals(ground_truth_customer_relationship_manager_state)
    )


def extract_function_names(s):
    """Extracts function names from a string"""
    return re.findall(r"(\b\w+\.\w+)\(", s)


def has_side_effects(predicted_actions, ground_truth_actions):
    """
    Checks if the predicted actions have side effects by comparing the state change after executing the actions.

    Parameters
    ----------
    predicted_actions : list
        List of predicted actions as strings.
    ground_truth_actions : list
        List of ground truth actions as strings.

    Returns
    -------
    bool
        True if the predicted actions result in different state change than the ground truth actions.

    """
    reset_all()
    for domain in DOMAINS:
        domain.reset_state()
    original_state = {
        "calendar": calendar.CALENDAR_EVENTS.copy(),
        "email": email.EMAILS.copy(),
        "analytics": analytics.PLOTS_DATA.copy(),
        "project_management": project_management.PROJECT_TASKS.copy(),
        "customer_relationship_manager": customer_relationship_manager.CRM_DATA.copy(),
    }
    (
        successful_execution,
        predicted_calendar_state,
        predicted_email_state,
        predicted_analytics_state,
        predicted_project_management_state,
        predicted_customer_relationship_manager_state,
    ) = execute_actions_and_reset_state(predicted_actions)

    state_changed = not predicted_calendar_state.equals(original_state["calendar"])
    state_changed |= not predicted_email_state.equals(original_state["email"])
    state_changed |= not predicted_analytics_state.equals(original_state["analytics"])
    state_changed |= not predicted_project_management_state.equals(original_state["project_management"])
    state_changed |= not predicted_customer_relationship_manager_state.equals(
        original_state["customer_relationship_manager"]
    )

    errors = ""  # Errors like exceeding the context window or running out of time don't have side effects, so we assume no errors
    correct = is_correct(predicted_actions, ground_truth_actions, errors)
    return state_changed and not correct


def generate_query_and_answer(template):
    """Generates query and answer from template."""
    logic = template["logic"]()
    if "alternative_queries" in template:
        possible_queries = [template["query"]] + template["alternative_queries"]
        query_template = random.choice(possible_queries)
        query = query_template.format(**logic)
    else:
        query_template = template["query"]
        query = query_template.format(**logic)
    answer = logic["answer"]
    domains = template.get("domains", [])
    return {
        "query": query,
        "answer": answer,
        "base_template": template["query"],
        "chosen_template": query_template,
        "domains": domains,
    }


def generate_all_queries_and_answers(templates, max_queries_per_template, verbose=False):
    """Generates a limited number of unique queries and answers for each template."""
    generated_queries_and_answers = []
    for template in templates:
        queries_generated_for_template = 0
        while queries_generated_for_template < max_queries_per_template:
            q_and_a = generate_query_and_answer(template)
            queries = [q["query"] for q in generated_queries_and_answers]
            if q_and_a["query"] not in queries:
                generated_queries_and_answers.append(q_and_a)
                queries_generated_for_template += 1

    if verbose:
        for query_and_answer in generated_queries_and_answers:
            print(f"Base template:   {query_and_answer['base_template']}")
            print(f"Chosen template: {query_and_answer['chosen_template']}")
            print(f"Query:           {query_and_answer['query']}")
            print(f"Answer:          {query_and_answer['answer']}")
            print("--------------------------------------------")

    return generated_queries_and_answers


def calculate_metrics(ground_truth_df, predictions_df, print_errors=True):
    """"""
    predictions = predictions_df.rename(columns={"function_calls": "prediction"})
    predictions = predictions.fillna("")

    ground_truth = ground_truth_df.rename(columns={"answer": "ground_truth"})
    df = predictions.merge(ground_truth, on="query")
    assert (
        len(predictions) == len(ground_truth) == len(df)
    ), f"{len(predictions)} predictions does not match {len(ground_truth_df)} ground truth answers. Check that the predictions and ground truth are for the same queries."

    # Replace all newlines with "\\n" for all actions
    df["prediction"] = df["prediction"].apply(lambda actions: [action.replace("\n", "\\n") for action in actions])
    df["ground_truth"] = df["ground_truth"].apply(lambda actions: [action.replace("\n", "\\n") for action in actions])

    df["exact_match"] = [is_exact_match(pred, gt) for pred, gt in zip(df["prediction"], df["ground_truth"])]
    df["correct"] = [
        is_correct(pred, gt, error) for pred, gt, error in zip(df["prediction"], df["ground_truth"], df["error"])
    ]
    df["unwanted_side_effects"] = [has_side_effects(pred, gt) for pred, gt in zip(df["prediction"], df["ground_truth"])]
    df["no_actions"] = [not len(pred) for pred in df["prediction"]]
    # wrong email if @example is in the prediction and @atlas is not in the prediction. Prediction is a list so needs to be converted to a string
    # TODO(fix_eval): Update to OR condition because it doesn't cover the case when email is just name without @.
    df["wrong_email"] = [("@example" in str(pred)) and ("@atlas" not in str(pred)) for pred in df["prediction"]]
    df["wrong_email"] = df["wrong_email"] & ~df["correct"]
    # Puts in end of November to plot instead of 29th november, but everything else matches
    df["end_date_minor_error"] = [
        end_date_minor_error(gt, pred) for gt, pred in zip(df["ground_truth"], df["prediction"])
    ]
    df["end_date_minor_error"] = df["end_date_minor_error"] & ~df["correct"]
    df["meeting_start_time_error"] = [
        meeting_start_time_error(gt, pred) for gt, pred in zip(df["ground_truth"], df["prediction"])
    ]
    df["meeting_start_time_error"] = df["meeting_start_time_error"] & ~df["correct"]

    # print out the queries that were not answered correctly
    if print_errors:
        print("--------------------------------------------")
        print("--------------------------------------------")
        print("ERRORS without unwanted side effects:")
        print("--------------------------------------------")
        print("--------------------------------------------")
        for _, row in df[~df["correct"] & ~df["unwanted_side_effects"]].iterrows():
            if (
                not row["wrong_email"]
                and not row["no_actions"]
                and not row["end_date_minor_error"]
                and not row["meeting_start_time_error"]
            ):
                # full response string to dict
                print("--------------------------------------------")
                print(f"Query:")
                print(f"    {row['query']}")
                print()
                print(f"Prediction:")
                for action in row["prediction"]:
                    print(f"    {action}")
                print()
                print(f"Ground truth:")
                for action in row["ground_truth"]:
                    print(f"    {action}")
                print()
                print(f"Unwanted side effects: {row['unwanted_side_effects']}")
                print()
                print(f"Error: {row['error']}")
                print("")
                print(f"Output:")
                output = get_output(row["full_response"])
                print(f"    {output}")
        print("--------------------------------------------")
        print("--------------------------------------------")
        print("ERRORS with unwanted side effects:")
        print("--------------------------------------------")
        print("--------------------------------------------")
        for _, row in df[~df["correct"] & df["unwanted_side_effects"]].iterrows():
            if (
                not row["wrong_email"]
                and not row["no_actions"]
                and not row["end_date_minor_error"]
                and not row["meeting_start_time_error"]
            ):
                # full response string to dict
                print("--------------------------------------------")
                print(f"Query:")
                print(f"    {row['query']}")
                print()
                print(f"Prediction:")
                for action in row["prediction"]:
                    print(f"    {action}")
                print()
                print(f"Ground truth:")
                for action in row["ground_truth"]:
                    print(f"    {action}")
                print()
                print(f"Unwanted side effects: {row['unwanted_side_effects']}")
                print()
                print(f"Meeting start time error: {row['meeting_start_time_error']}")
                print(f"Error: {row['error']}")
                print("")
                print(f"Output:")
                output = get_output(row["full_response"])
                print(f"    {output}")

    num_errors_without_side_effects = len(df[(~df["correct"]) & ~df["unwanted_side_effects"]])
    num_errors_with_side_effects = len(df[(~df["correct"]) & df["unwanted_side_effects"]])
    print(f"Accuracy: {round(df['correct'].mean() * 100, 2)}% ({df['correct'].sum()} out of {len(df)})")
    print(
        f"Errors without unwanted side effects: {round(num_errors_without_side_effects / len(df) * 100, 2)}% ({num_errors_without_side_effects} out of {len(df)})"
    )
    print(
        f"Errors with unwanted side effects: {round(num_errors_with_side_effects / len(df) * 100, 2)}% ({num_errors_with_side_effects} out of {len(df)})"
    )

    num_failed_to_follow_react = len(df[(~df["correct"]) & ~df["unwanted_side_effects"] & df["no_actions"]])
    num_wrong_email_no_side_effects = len(df[(~df["correct"]) & df["wrong_email"] & ~df["unwanted_side_effects"]])
    num_meeting_start_time_error_no_side_effects = len(
        df[(~df["correct"]) & df["meeting_start_time_error"] & ~df["unwanted_side_effects"]]
    )

    if print_errors:
        print(
            f"Wrong email, no side effects: {round(num_wrong_email_no_side_effects / len(df) * 100, 2)}% ({num_wrong_email_no_side_effects} out of {len(df)})"
        )
        print(
            f"Didn't follow REACT framework, no side effects: {round(num_failed_to_follow_react / len(df) * 100, 2)}% ({num_failed_to_follow_react} out of {len(df)})"
        )
        print(
            f"Meeting start time error, no side effects: {round(num_meeting_start_time_error_no_side_effects / len(df) * 100, 2)}% ({num_meeting_start_time_error_no_side_effects} out of {len(df)})"
        )

    num_wrong_email_with_side_effects = len(
        df[
            (~df["correct"])
            & df["wrong_email"]
            & df["unwanted_side_effects"]
            & ~df["end_date_minor_error"]
            & ~df["meeting_start_time_error"]
        ]
    )
    num_end_date_minor_error = len(
        df[
            (~df["correct"])
            & df["end_date_minor_error"]
            & df["unwanted_side_effects"]
            & ~df["wrong_email"]
            & ~df["meeting_start_time_error"]
        ]
    )
    num_meeting_start_time_error_with_side_effects = len(
        df[(~df["correct"]) & df["meeting_start_time_error"] & df["unwanted_side_effects"]]
    )
    # print rows that were correct but not exact match
    if print_errors:
        print(
            f"Wrong email, with side effects: {round(num_wrong_email_with_side_effects / len(df) * 100, 2)}% ({num_wrong_email_with_side_effects} out of {len(df)})"
        )
        print(
            f"End date minor error, with side effects: {round(num_end_date_minor_error / len(df) * 100, 2)}% ({num_end_date_minor_error} out of {len(df)})"
        )
        print(
            f"Meeting start time error, with side effects: {round(num_meeting_start_time_error_with_side_effects / len(df) * 100, 2)}% ({num_meeting_start_time_error_with_side_effects} out of {len(df)})"
        )
        print("--------------------------------------------")
        print("--------------------------------------------")
        print("Correct but not exact match:")
        print("--------------------------------------------")
        print("--------------------------------------------")
        for _, row in df[df["correct"] & ~df["exact_match"]].iterrows():
            print("--------------------------------------------")
            print(f"Query:")
            print(f"    {row['query']}")
            print()
            print(f"Prediction:")
            for action in row["prediction"]:
                print(f"    {action}")
            print()
            print(f"Ground truth:")
            for action in row["ground_truth"]:
                print(f"    {action}")
            print()
            print(f"Unwanted side effects: {row['unwanted_side_effects']}")
            print()
            print(f"Error: {row['error']}")
            print("")
            print(f"Output:")
            output = get_output(row["full_response"])
            print(f"    {output}")

    return df


def get_output(full_response):
    """Get the output from the full response"""
    pattern = r"AgentAction\(.*?\)"
    array_pattern = r"array\((.*?)\)"

    def quote_match(match):
        escaped_match = match.group().replace('"', '\\"')
        return f'"{escaped_match}"'

    simplified_string = re.sub(pattern, quote_match, full_response)
    simplified_string = re.sub(array_pattern, quote_match, simplified_string)
    simplified_string = simplified_string.replace("nan", "None")

    # Remove everything after "intermediate_steps" and add a curl bracket at close the dict
    simplified_string = simplified_string.split("intermediate_steps")[0]
    simplified_string = simplified_string[:-3] + "}"

    try:
        a = ast.literal_eval(simplified_string)
        return a["output"]
    except:
        return full_response


def get_latest_results_path(results_root_dir, model, tool, all_tools_in_prompt=True, tool_set=None):
    """Get the latest results file path and ground truth path for a given model and tool"""
    results_dir = os.path.join(results_root_dir, tool)
    results_files = os.listdir(results_dir)
    model_results_files = [os.path.join(results_dir, file) for file in results_files if model in file]
    if all_tools_in_prompt:
        model_results_files = [file for file in model_results_files if "all" in file]
    else:
        model_results_files = [file for file in model_results_files if "domains" in file]
    
    # Filter by tool_set if specified
    if tool_set:
        model_results_files = [file for file in model_results_files if tool_set in os.path.basename(file)]
    
    ground_truth_path = os.path.join("data", "processed", "queries_and_answers", f"{tool}_queries_and_answers.csv")
    if not len(model_results_files):
        return None
    else:
        return max(model_results_files, key=os.path.getctime), ground_truth_path


def get_latest_results_from_dir(results_root_dir, model, tool, print_errors=False, all_tools_in_prompt=True):
    """Get the latest results for each model in the results directory"""
    results = get_latest_results_path(results_root_dir, model, tool, all_tools_in_prompt)
    if not results:
        print(f"\nNo results found for {tool} with {model}")
        return None
    else:
        model_results_path, ground_truth_path = results
        predictions = pd.read_csv(model_results_path, dtype=str)
        ground_truth = pd.read_csv(ground_truth_path, dtype=str)
        ground_truth["answer"] = ground_truth["answer"].apply(ast.literal_eval)
        predictions["function_calls"] = predictions["function_calls"].apply(ast.literal_eval)
        print(f"\nCalculating metrics for {tool} with {model}")
        df = calculate_metrics(ground_truth, predictions, print_errors=print_errors)
        num_correct = df["correct"].sum()
        num_incorrect = len(df) - num_correct
        num_side_effects = df["unwanted_side_effects"].sum()
        num_correct_no_actions = df[df["ground_truth"].apply(len) == 0]["correct"].sum()
        num_incorrect_no_actions = len(df[df["ground_truth"].apply(len) == 0]) - num_correct_no_actions
        num_correct_non_zero_actions = df[df["ground_truth"].apply(len) > 0]["correct"].sum()
        num_incorrect_non_zero_actions = len(df[df["ground_truth"].apply(len) > 0]) - num_correct_non_zero_actions
        num_correct_two_or_more_actions = df[df["ground_truth"].apply(len) > 1]["correct"].sum()
        num_incorrect_two_or_more_actions = len(df[df["ground_truth"].apply(len) > 1]) - num_correct_two_or_more_actions
        num_context_window_errors = len(df[df["error"] == "Context window exceeded"])
        return (
            num_correct,
            num_incorrect,
            num_side_effects,
            num_correct_no_actions,
            num_incorrect_no_actions,
            num_correct_non_zero_actions,
            num_incorrect_non_zero_actions,
            num_correct_two_or_more_actions,
            num_incorrect_two_or_more_actions,
            num_context_window_errors,
        )


def get_toolkits(toolkits, tool_set='original', include_unit_tests=False, integration_tests_path=""):
    """Get the toolkits to be used for the agent."""
    tools = []
    
    # Define toolkits based on the tool_set
    if tool_set == 'original':
        email_tk, calendar_tk, analytics_tk, project_management_tk, customer_relationship_manager_tk, company_directory_tk = \
            email_toolkit, calendar_toolkit, analytics_toolkit, project_management_toolkit, customer_relationship_manager_toolkit, company_directory_toolkit
    elif tool_set == 'improved':
        email_tk, calendar_tk, analytics_tk, project_management_tk, customer_relationship_manager_tk, company_directory_tk = \
            email_toolkit_improved, calendar_toolkit_improved, analytics_toolkit, project_management_toolkit_improved, customer_relationship_manager_toolkit_improved, company_directory_toolkit_improved
    elif tool_set == 'smolagents':
        email_tk, calendar_tk, analytics_tk, project_management_tk, customer_relationship_manager_tk, company_directory_tk = \
            smol_email_toolkit, smol_calendar_toolkit, smol_analytics_toolkit, smol_project_management_toolkit, smol_customer_relationship_manager_toolkit, smol_company_directory_toolkit
    elif tool_set == 'smolagents_improved':
        email_tk, calendar_tk, analytics_tk, project_management_tk, customer_relationship_manager_tk, company_directory_tk = \
            smol_email_toolkit_improved, smol_calendar_toolkit_improved, smol_analytics_toolkit_improved, smol_project_management_toolkit_improved, smol_customer_relationship_manager_toolkit_improved, smol_company_directory_toolkit_improved
    else:
        raise ValueError(f"Invalid tool_set: {tool_set}. Must be one of 'original', 'improved', 'smolagents', or 'improved_smolagents'.")
    
    if "email" in toolkits:
        tools += email_tk
    if "calendar" in toolkits:
        tools += calendar_tk
    if "analytics" in toolkits:
        tools += analytics_tk
    if "project_management" in toolkits:
        tools += project_management_tk
    if "customer_relationship_manager" in toolkits:
        tools += customer_relationship_manager_tk
    # The company directory toolkit is always included in order to find email addresses by name
    tools += company_directory_tk
    if include_unit_tests:
        return apply_unit_test_documentation(tools, include_unit_tests=include_unit_tests)
    elif integration_tests_path:
        return apply_integration_test_documentation(tools, integration_tests_path)
    return tools


def generate_results(
    queries_path,
    model_name,
    tool_selection="all",
    num_retrys=0,
    agent_engine="langchain",
    tool_set='original',
    include_unit_tests=False,
    integration_tests_path="",
):
    """Generates results for a given model and set of queries. Saves the results to a csv file."""
    toolkits = ["email", "calendar", "analytics", "project_management", "customer_relationship_manager"]
    queries_df = pd.read_csv(queries_path)
    queries = queries_df["query"].tolist()

    results = pd.DataFrame(columns=["query", "function_calls", "full_response", "error", "tool_set"])
    if model_name == "gpt-3.5":
        OPENAI_KEY = open("openai_key.txt", "r").read()
        llm = OpenAI(
            model_name="gpt-3.5-turbo-instruct",
            openai_api_key=OPENAI_KEY,
            temperature=0,
            model_kwargs={"seed": 42},
        )
    elif model_name.startswith("gpt"):
        OPENAI_KEY = open("openai_key.txt", "r").read()
        llm = ChatOpenAI(
            model_name=model_name,
            openai_api_key=OPENAI_KEY,
            temperature=0,
            model_kwargs={"seed": 42},
        )
    elif model_name == "llama3.3-70b":
        OPENROUTER_KEY = open("openrouter_key.txt", "r").read()
        llm = ChatOpenAI(
            model_name="meta-llama/llama-3.3-70b-instruct",
            api_key = OPENROUTER_KEY,
            temperature=0,
            base_url = 'https://openrouter.ai/api/v1'
        )
    elif model_name == "llama3.1-8b":
        OPENROUTER_KEY = open("openrouter_key.txt", "r").read()
        llm = ChatOpenAI(
            model="meta-llama/llama-3.1-8b-instruct",
            api_key = OPENROUTER_KEY,
            temperature=0,
            base_url = 'https://openrouter.ai/api/v1'
        )
    elif model_name == "qwen-2.5-72b":
        OPENROUTER_KEY = open("openrouter_key.txt", "r").read()
        llm = ChatOpenAI(
            model="qwen/qwen-2.5-72b-instruct",
            api_key = OPENROUTER_KEY,
            temperature=0,
            base_url = 'https://openrouter.ai/api/v1'
        )
    elif model_name == "qwen-2.5-7b":
        OPENROUTER_KEY = open("openrouter_key.txt", "r").read()
        llm = ChatOpenAI(
            model="qwen/qwen-2.5-7b-instruct",
            api_key = OPENROUTER_KEY,
            temperature=0,
            base_url = 'https://openrouter.ai/api/v1'
        )

    else:
        raise ValueError("Invalid --model_name. Must be one of " + ", ".join(AVAILABLE_LLMS))

    # Determine the tool_set based on agent_engine for backward compatibility
    actual_tool_set = tool_set
    if agent_engine == "smolagents":
        if tool_set == 'original':
            actual_tool_set = 'smolagents'
        elif tool_set == 'improved':
            actual_tool_set = 'smolagents_improved'
    
    tools = get_toolkits(toolkits, tool_set=actual_tool_set, include_unit_tests=include_unit_tests, integration_tests_path=integration_tests_path)

    for i, query in tqdm(list(enumerate(queries))):
        reset_all()

        if tool_selection == "domains":
            toolkits = queries_df["domains"].iloc[i].strip("][").replace("'", "").split(", ")
            tools = get_toolkits(toolkits, tool_set=actual_tool_set, include_unit_tests=include_unit_tests)

        if agent_engine == "smolagents":
            # Initialize the appropriate model based on model_name
            if model_name.startswith("gpt"):
                model = LiteLLMModel(model_id=model_name, api_key=OPENAI_KEY, temperature=0.7)
            elif model_name == "llama3.3-70b":
                OPENROUTER_KEY = open("openrouter_key.txt", "r").read()
                model = LiteLLMModel(
                    model_id="openrouter/meta-llama/llama-3.3-70b-instruct",
                    api_key = OPENROUTER_KEY,
                    temperature=0.7,
                )
            elif model_name == "llama3.1-8b":
                OPENROUTER_KEY = open("openrouter_key.txt", "r").read()
                model = LiteLLMModel(
                    model_id="openrouter/meta-llama/llama-3.1-8b-instruct",
                    api_key = OPENROUTER_KEY,
                    temperature=0.7,
                )
            elif model_name == "qwen-2.5-72b":
                OPENROUTER_KEY = open("openrouter_key.txt", "r").read()
                model = LiteLLMModel(
                    model_id="openrouter/qwen/qwen-2.5-72b-instruct",
                    api_key = OPENROUTER_KEY,
                    temperature=0.7,
                )
            elif model_name == "qwen-2.5-7b":
                OPENROUTER_KEY = open("openrouter_key.txt", "r").read()
                model = LiteLLMModel(
                    model_id="openrouter/qwen/qwen-2.5-7b-instruct",
                    api_key = OPENROUTER_KEY,
                    temperature=0.7,
                )
            
            GLOBAL_TOOL_TRACKER.clear()
            reset_all()

            # Create the SmolAgents agent
            agent = CodeAgent(
                tools=tools,
                model=model,
            )

            prompt_template = (
                f"Today's date is {HARDCODED_CURRENT_TIME.strftime('%A')}, {HARDCODED_CURRENT_TIME.date()} and the current time is {HARDCODED_CURRENT_TIME.time()}. Remember the current date and time when answering queries. You must not schedule meetings that start before 9am or end after 6pm"
            )

            error = ""
            function_calls = []
            response = ""
            try:
                response = agent.run(prompt_template+"\n"+query)
            except Exception as e:
                error = str(e)

            function_calls = []

            for item in GLOBAL_TOOL_TRACKER:
                function_calls.append(convert_agent_action_to_function_call_hf(item))

            GLOBAL_TOOL_TRACKER.clear()
            
        else:  # Default to langchain
            agent = initialize_agent(
                llm=llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                tools=tools,
                verbose=True,
                return_intermediate_steps=True,
                max_iterations=20,
                max_execution_time=120,
            )
            agent.agent.llm_chain.prompt.messages[0].prompt.template = (
                f"Today's date is {HARDCODED_CURRENT_TIME.strftime('%A')}, {HARDCODED_CURRENT_TIME.date()} and the current time is {HARDCODED_CURRENT_TIME.time()}. Remember the current date and time when answering queries. Meetings must not start before 9am or end after 6pm."
                + agent.agent.llm_chain.prompt.messages[0].prompt.template
            )
            error = ""
            function_calls = []
            response = ""
            try:
                response = agent({"input": query})
                for step in response["intermediate_steps"]:
                    function_calls.append(convert_agent_action_to_function_call(step[-2]))
                if len(response["intermediate_steps"]) == 0:
                    for retry_num in range(num_retrys):
                        temprature_for_retry = 0.5
                        agent.agent.llm_chain.llm.temperature=temprature_for_retry
                        print(f"No actions taken. Retry {retry_num + 1} of {num_retrys}")
                        response = agent({"input": query})
                        for step in response["intermediate_steps"]:
                            function_calls.append(convert_agent_action_to_function_call(step[-2]))
                        if len(response["intermediate_steps"]) > 0:
                            break
                error = (
                    response["output"]
                    if response["output"] == "Agent stopped due to iteration limit or time limit."
                    else error
                )

            except Exception as e:
                import traceback
                traceback.print_exc()
                # APIs for the LLMs we support have different error messages for when the context window is exceeded
                context_window_error_messages = [
                    "maximum input length",
                    "maximum context length",
                    "prompt is too long",
                    "Request too large",
                ]
                if any([msg in str(e) for msg in context_window_error_messages]):
                    print(f"Context window exceeded with query: {query}")
                    error = "Context window exceeded"
                else:
                    print(f"Unknown error with query: {query}")
                    error = str(e)

        print(f"### Query: {query}")
        print(f"### Answer: {function_calls}")

        results = pd.concat(
            [
                results,
                pd.DataFrame(
                    [
                        [
                            query,
                            function_calls,
                            str(response),
                            error,
                            tool_set,
                        ]
                    ],
                    columns=["query", "function_calls", "full_response", "error", "tool_set"],
                ),
            ],
            ignore_index=True,
        )
        # Reset all data after each query
        reset_all()
        for domain in DOMAINS:
            domain.reset_state()

    domain = queries_path.split("/")[-1].split(".")[0].replace("_queries_and_answers", "")
    save_dir = os.path.join("data", "results", domain)
    os.makedirs(save_dir, exist_ok=True)

    # Removes microseconds and makes it more readable
    current_datetime = str(pd.Timestamp.now()).split(".")[0].replace(" ", "_").replace(":", "-")
    save_path = os.path.join(save_dir, model_name + "_" + agent_engine + "_" + tool_selection + "_" + tool_set + "_" + current_datetime + ".csv")
    results.to_csv(save_path, index=False, quoting=csv.QUOTE_ALL)
    return results
