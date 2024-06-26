from praisonai import PraisonAI
import streamlit as st
import requests
from utils import update_env, get_agents_list, get_api_key, initialize_env, rename_and_move_yaml, load_yaml, save_yaml, initialize_session_state
from config import MODEL_SETTINGS, FRAMEWORK_OPTIONS, DEFAULT_FRAMEWORK, AGENTS_DIR, AVAILABLE_TOOLS

# Set Streamlit to wide mode
st.set_page_config(layout="wide")

# Initialize the .env file with default values if not present
initialize_env()
initialize_session_state()

def update_model():
    st.session_state.api_key = get_api_key(st.session_state.llm_model)
    update_env(st.session_state.llm_model, st.session_state.api_base, st.session_state.api_key)

def get_ollama_models(api_base):
    try:
        
        url = f"{api_base[:-3]}/api/tags"
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception if the request was unsuccessful
        models = [model['name'] for model in response.json()['models']]
        return models
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to the Ollama server: {e}")
        return []

def generate_response(framework_name):
    if st.session_state.llm_model == "Ollama":
        # Use the Ollama provider to generate the response
        # You'll need to implement the logic for using the Ollama provider here
        pass
    else:
        praison_ai_args = {
            "framework": framework_name,
            "auto": prompt if agent == "Auto Generate New Agents" else None,
            "agent_file": f"{AGENTS_DIR}/{agent}" if agent != "Auto Generate New Agents" else None
        }
        praison_ai = PraisonAI(**{k: v for k, v in praison_ai_args.items() if v is not None})
        return praison_ai.main()

@st.experimental_dialog("Edit Agents", width="large")
def edit_agent_dialog():
    yaml_data = load_yaml(f"{AGENTS_DIR}/{agent}")
    roles = yaml_data.get("roles", {})
    updated_roles = {}
    
    topic = st.text_area("Topic", value=yaml_data.get("topic", ""), height=150)

    col1, col2 = st.columns(2)
    col_idx = 0

    for role_name, role_data in roles.items():
        col = [col1, col2][col_idx % 2]
        col_idx += 1
        with col.container(border=True):
            st.subheader(f"{role_data.get('role', '')}")
            default_tools = [tool for tool in role_data.get("tools", []) if tool in AVAILABLE_TOOLS]
            tools = st.multiselect("Tools", options=AVAILABLE_TOOLS, default=default_tools, key=f"tools_{role_name}")
            role = st.text_input("Role", value=role_data.get("role", ""), key=f"role_{role_name}")
            backstory = st.text_area("Backstory", value=role_data.get("backstory", ""), key=f"backstory_{role_name}")
            goal = st.text_area("Goal", value=role_data.get("goal", ""), key=f"goal_{role_name}")

            updated_tasks = {
                task_name: {
                    "description": st.text_area(f"Description: {task_name.replace('_', ' ').title()}", value=task_data.get("description", ""), key=f"description_{role_name}_{task_name}"),
                    "expected_output": st.text_area(f"Expected Output: {task_name.replace('_', ' ').title()}", value=task_data.get("expected_output", ""), key=f"expected_output_{role_name}_{task_name}")
                } for task_name, task_data in role_data.get("tasks", {}).items()
            }

            updated_roles[role_name] = {
                "role": role,
                "backstory": backstory,
                "goal": goal,
                "tasks": updated_tasks,
                "tools": tools
            }

    if st.button("Update"):
        yaml_data["topic"] = topic
        yaml_data["roles"] = updated_roles
        save_yaml(yaml_data, f"{AGENTS_DIR}/{agent}")
        st.toast(f"{agent} has been updated.")
        st.session_state.show_edit_container = False
        st.rerun()

    if st.button("Cancel"):
        st.session_state.show_edit_container = False
        st.rerun()

with st.sidebar:
    st.title("PraisonAI Chatbot")
    with st.expander("LLM Settings", expanded=True):
        st.selectbox("Select LLM Provider", options=sorted(MODEL_SETTINGS.keys()), key='llm_model', on_change=update_model)
        st.text_input("API Base", value=MODEL_SETTINGS[st.session_state.llm_model]["OPENAI_API_BASE"], key='api_base')
        
        if st.session_state.llm_model == "Ollama":
            models = get_ollama_models(st.session_state.api_base)
            st.selectbox("Model", models, key='model_name')
        else:
            st.text_input("Model", value=MODEL_SETTINGS[st.session_state.llm_model]["OPENAI_MODEL_NAME"], key='model_name')
        st.text_input("API Key", value=st.session_state.api_key, key='api_key', type="password")
    
    with st.expander("Agent Settings", expanded=True):
        framework = st.selectbox("Agentic Framework", options=FRAMEWORK_OPTIONS, index=FRAMEWORK_OPTIONS.index(DEFAULT_FRAMEWORK))
        agents_list = get_agents_list()
        agent = st.selectbox("Select Existing Agents", options=sorted(agents_list), index=agents_list.index("Auto Generate New Agents") if "Auto Generate New Agents" in agents_list else 0)

        edit_button_placeholder = st.empty()
        if agent != "Auto Generate New Agents" and not st.session_state.show_edit_container:
            with edit_button_placeholder:
                if st.button("Edit Agent"):
                    st.session_state.show_edit_container = True
                    edit_button_placeholder.empty()
                    edit_agent_dialog()

update_env(st.session_state.llm_model, st.session_state.api_base, st.session_state.api_key)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Type your message here..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        if framework.lower() == "none":
            stream = st.session_state.client.chat.completions.create(
                model=st.session_state["model_name"],
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                stream=True,
            )
            response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})

        elif framework.lower() == "battle":
            col1, col2 = st.columns(2)

            with st.spinner("Generating CrewAi Response..."):
                with col1.container(border=True):
                    response_crewai = generate_response("crewai")
                    st.subheader("CrewAi Response:")
                    st.markdown(response_crewai, unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": response_crewai})

            with st.spinner("Generating AutoGen Response..."):
                with col2.container(border=True):
                    response_autogen = generate_response("autogen")
                    st.subheader("AutoGen Response:")
                    st.markdown(response_autogen, unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": response_autogen})

            if agent == "Auto Generate New Agents":
                try:
                    new_agent_filename = rename_and_move_yaml()
                    st.toast(f"Generated agent file: {new_agent_filename}")
                except FileNotFoundError as e:
                    st.error(str(e))

        else:
            with st.spinner("Generating response..."):
                response = generate_response(framework.lower())
                st.markdown(response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": response})

                if agent == "Auto Generate New Agents":
                    try:
                        new_agent_filename = rename_and_move_yaml()
                        st.toast(f"Generated agent file: {new_agent_filename}")
                    except FileNotFoundError as e:
                        st.error(str(e))
