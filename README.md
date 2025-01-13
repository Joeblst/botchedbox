# Botchedbox - LLM Security Configuration Benchmark Tool

Botchedbox is a benchmark tool developed as part of a master's thesis. 
It evaluates Large Language Models (LLMs) capabilities in automating IT security measures.
The tool focuses on testing LLMs ability to handle various security-related tasks such as:
- application configuration
- firewall rules generation
- vulnerability mitigation on a system level
- rights management
- phishing detection

## Features

- Automated evaluation of LLM responses
- Support for multiple LLM providers
- Customizable test cases
- Built-in test cases for:
    - Application configuration (Apache, OpenSSH, Samba)
    - Phishing email detection
    - Firewall configuration (IPTables, NFTables)
    - Vulnerability mitigation
    - Rights management
- Visualization of benchmark results
- Manual and automatic validation of LLM outputs
- Docker support

## Requirements

### Running the Tool
- Docker and Docker Compose
- API keys for supported LLM providers

### Development Requirements
- Python 3.8+
- Django
- Additional Python packages listed in requirements.txt

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/Joeblst/botchedbox.git
cd botchedbox
```

2. Set up API keys either through:
    - Environment variables:
      ```bash
      cp .env.example .env
      # Edit .env with your API keys
      ```
    - Docker Compose:
      ```yaml
      # Edit docker-compose.yml
      environment:
        OPENAI_API_KEY: your_key
        ANTHROPIC_API_KEY: your_key
        GOOGLE_API_KEY: your_key
        # Add other required API keys
      ```

3. Start the application using Docker:
```bash
docker compose up -d
```

4. Access the web interface at `http://localhost:8000`

## Adding New Test Cases

New test cases can be added by creating a new directory under `testcases/` with the following structure:

```
testcases/
└── your_test_case/
    ├── benchmark.yaml                          # Test case configuration
    ├── testing_script.py # Validation script
    └── configuration_file                      # Additional test data
```

The benchmark.yaml should follow this format:

```yaml
problem:
  id: 'test-case-id'
  type: "config|firewall|ansible|phishing"
  description: "Test case description"
  verify_method: "script|manual|table"
  verify_script: "testing_script.py"
  file: "configuration_file"

llm:
  default:
    system: |
      System prompt for the LLM
    prompt: |
      User prompt describing the task
```

You can copy the `examples/benchmark.yaml` as a starting point.
Look at other testcases as an example for implementing a testing script.

### Optional:
To load data which was already tested use:
```bash
docker-compose exec botchedbox ./manage.py loaddata benchmark_data.json
```

## Adding New LLMs

To add support for a new LLM provider:

1. Add the provider configuration to `config/llm.yaml`
2. If needed Implement the API client in `services/llm_service.py`
3. Add necessary environment variables to `.env` or the docker compose file

## License

This project is licensed under the MIT License - see the LICENSE file for details.
