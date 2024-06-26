import os
import yaml
import streamlit as st
from praisonai import PraisonAI
from openai import OpenAI
from config import AGENTS_DIR

def initialize_env():
    default_values = {
        "OPENAI_MODEL_NAME": "Enter Model Name Here",
        "OPENAI_API_BASE": "Enter API Base Here",
        "OPENAI_API_KEY": "Enter API Key Here",
        "OPENAI_LLM_API_KEY": "Enter API Key Here",
        "OLLAMA_MISTRAL_API_KEY": "NA",
        "FASTCHAT_API_KEY": "NA",
        "LM_STUDIO_API_KEY": "NA",
        "MISTRAL_API_API_KEY": "Enter API Key Here",
        "GROQ_API_KEY": "Enter API Key Here"
    }

    env_path = '.env'
    env_vars = {}

    if os.path.exists(env_path):
        with open(env_path, 'r') as file:
            env_vars = dict(line.strip().split('=', 1) for line in file if '=' in line)

    env_vars.update({key: env_vars.get(key, value) for key, value in default_values.items()})

    with open(env_path, 'w') as file:
        for key, value in env_vars.items():
            file.write(f"{key}={value}\n")

    os.environ.update(env_vars)

def update_env(model_name, api_base, api_key):
    from config import MODEL_SETTINGS
    settings = MODEL_SETTINGS[model_name]

    env_path = '.env'
    env_vars = {}

    if os.path.exists(env_path):
        with open(env_path, 'r') as file:
            env_vars = dict(line.strip().split('=', 1) for line in file if '=' in line)

    env_vars.update({
        "OPENAI_MODEL_NAME": settings["OPENAI_MODEL_NAME"],
        "OPENAI_API_BASE": api_base,
        "OPENAI_API_KEY": api_key
    })

    if model_name == "openai":
        env_vars["OPENAI_LLM_API_KEY"] = api_key
    else:
        env_vars[f"{model_name.upper()}_API_KEY"] = api_key

    with open(env_path, 'w') as file:
        for key, value in env_vars.items():
            file.write(f"{key}={value}\n")

    os.environ.update(env_vars)

    st.session_state.client = OpenAI(api_key=api_key, base_url=api_base)

def get_api_key(model_name):
    if model_name == "openai":
        return os.getenv("OPENAI_LLM_API_KEY", "Enter API Key Here")
    return os.getenv(f"{model_name.upper()}_API_KEY", "NA" if model_name in ["ollama_mistral", "fastchat", "lm_studio"] else "Enter API Key Here")

def get_agents_list():
    agents_dir = 'agents'
    agents_files = ["Auto Generate New Agents"]  # Ensure "Auto Generate New Agents" is the default option

    if os.path.exists(agents_dir):
        agents_files.extend(f for f in os.listdir(agents_dir) if f.endswith('.yaml'))

    return agents_files

def rename_and_move_yaml():
    agents_dir = 'agents'
    if not os.path.exists(agents_dir):
        os.makedirs(agents_dir)
    
    existing_agents = [f for f in os.listdir(agents_dir) if f.startswith('agent_') and f.endswith('.yaml')]
    new_agent_number = len(existing_agents) + 1
    new_agent_filename = f'agent_{new_agent_number}.yaml'

    # Ensure 'test.yaml' exists before attempting to rename
    if os.path.exists('test.yaml'):
        os.rename('test.yaml', os.path.join(agents_dir, new_agent_filename))
        return new_agent_filename
    else:
        raise FileNotFoundError("The file 'test.yaml' does not exist.")

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def save_yaml(data, file_path):
    with open(file_path, 'w') as file:
        yaml.safe_dump(data, file, sort_keys=False)

def initialize_session_state():
    st.session_state.setdefault('llm_model', 'OpenAi')
    st.session_state.setdefault('client', OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE")))
    if 'api_key' not in st.session_state:
        st.session_state.api_key = get_api_key(st.session_state.llm_model)
    st.session_state.setdefault('show_edit_container', False)
    if "messages" not in st.session_state:
        st.session_state.messages = []

def run_praison(framework, prompt, agent):
    praison_ai_args = {
        "framework": framework,
        "auto": prompt if agent == "Auto Generate New Agents" else None,
        "agent_file": f"{AGENTS_DIR}/{agent}" if agent != "Auto Generate New Agents" else None
    }
    praison_ai = PraisonAI(**{k: v for k, v in praison_ai_args.items() if v is not None})
    return praison_ai.main()
