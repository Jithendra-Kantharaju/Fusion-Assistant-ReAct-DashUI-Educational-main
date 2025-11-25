required python version is 3.11.9

To setup:
1) brew install pyenv (Mac/Linux)
2) pyenv install 3.11.9
3) pyenv global 3.11.9
4) Check using: python --version
5) cd /path/to/your/project
6) python3.11 -m venv <project name>
7) Activate your environment: source <project name>/bin/activate
8) upgrade pip: pip install --upgrade pip
9) Install packages: pip install -r requirements.txt

**Note** The setup step is going to require a variable amount of debugging dependent on your environment. I've done my best to minimize this.

Things to do:
1) Read through all of the code start with either the Dash_ui_ReAct.py or fusion_assistant_ReAct/app.py
2) Navigate to the react_agent file to understand how to register tools/agents.
3) Navigate to the agents folder and understand how to build the necessary agents.
4) Navigate to the vectorstores and retriever files to understand how to build the necesary vectorstores and retrieval methods.
5) Document all of your steps in understanding developign and running.
6) Feel free to use this as inspiration to start from scratch and build you own system :) 