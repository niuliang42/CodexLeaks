# CodexLeaks
The code repo for USENIX Security 2023 paper **CodexLeaks: Privacy Leaks from Code Generation Language Models in GitHub Copilot**.

## Please cite us:
```bibtex
@inproceedings{CodexLeaks2023,
  title={{CodexLeaks: Privacy Leaks from Code Generation Language Models in GitHub Copilot}},
  author={Liang Niu, Shujaat Mirza, Zayd Maradni, Christina Pöpper},
  booktitle={32nd USENIX Security Symposium (USENIX Security 23)},
  pages={????--????},
  year={2023}
}
```

## File Organization
| File                         	| Functionality                                                       	|
| ----------------------------- | --------------------------------------------------------------------- |
| main.py                    	| OpenAI Query procedure file.                                        	|
| config.py                    	| Configurations.                                                    	|
| Prompt.py                    	| Prompts and Query relates classes definitions.                        |
| utils.py                    	| Utility functions.                                                    |
| /resources/templates.py       | Prompts and templates.                                                |
| /Blind_MI/                    | Blind MI attack related code.                                        	|
| /annotator/                   | The web application for annotating the responses from Codex.         	|

## Note
Codex is shutdown by OpenAI, so the code is no longer runnable.
