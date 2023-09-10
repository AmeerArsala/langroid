# Using Langroid with a local LLama2 model

## Background

There are a couple of ways to use LLama2 models:

- Using the HuggingFace `transformers` library, e.g. if you click on "Use In Transformers" 
button on [https://huggingface.co/TheBloke/Llama-2-13B-chat-GGUF](https://huggingface.co/TheBloke/Llama-2-13B-chat-GGUF) you get the following 
instructions:
```python
# Use a pipeline as a high-level helper
from transformers import pipeline
pipe = pipeline("text-generation", model="TheBloke/Llama-2-13B-chat-GGUF")

OR 

# Load model directly
from transformers import AutoModel
model = AutoModel.from_pretrained("TheBloke/Llama-2-13B-chat-GGUF")
```
  In general with this approach you will need GPUs to run the model.

- Using `llama.cpp`: run quantized versions of these models locally on CPU, e.g. on your macbook.

In these notes we explore the `llama.cpp` approach. 

!!! note "Tested on Macbook M1 Pro Max"
        This has been tested only on a Macbook Pro M1 Max with 64GB RAM. 

## Install `llama-cpp-python`
The overall plan will be to spin up a server that presents an OpenAI-like API to 
the local llama model, and then use Langroid to interact with this server.

!!! warning "Keep the server, client virtual envs separate" 
        Very important to install `llama-cpp-python` in a separate virtual env 
        from the one where you install Langroid.

Follow the instructions here:
[https://github.com/abetlen/llama-cpp-python](https://github.com/abetlen/llama-cpp-python)

Essentially, you can do `poetry add llama-cpp-python` or `pip install llama-cpp-python`.

As the repo says, you may need to do:

```bash
pip install "llama-cpp-python[server]" --force-reinstall --upgrade --no-cache-dir
```


## Download a model

E.g. go here:
[https://huggingface.co/TheBloke/Llama-2-13B-chat-GGUF/tree/main](https://huggingface.co/TheBloke/Llama-2-13B-chat-GGUF/tree/main)

Pick one of the `gguf` model files, say `llama-2-13b-chat.Q4_K_M.gguf` and click 
the download button, save the model under your `./models/` dir.

## Directly use the model in Python

```python
from llama_cpp import Llama
llm = Llama(
    model_path="./models/Llama-2-13B-chat-GGUF/llama-2-13b-chat.Q4_K_M.gguf",
    n_ctx=1000, # context window
)
# since we are using a "chat" model, we can directly ask questions
llm("Name the planets in the solar system")
```

## Set up a web-server that presents an OpenAI-like API

This is more interesting for us, since this means we can directly use it with Langroid.

Then you can run the server like this:

```bash
python3 -m llama_cpp.server \
  --model models/Llama-2-13B-chat-GGUF/llama-2-13b-chat.Q4_K_M.gguf \
  --
```
There are various command-line options you can give here, see the full list
by running: 
```bash
python3 -m llama_cpp.server --help
```
We highlight some of the options here:
```bash
--n_ctx N_CTX         The context size. (default: 2048)
--host HOST           Listen address (default: localhost)
--port PORT           Listen port (default: 8000)
```
Then this presents an OpenAPI doc here:

[http://localhost:8000/docs](http://localhost:8000/docs)

As you can all the usual OpenAI end-points are available here.


## Use the local model with the OpenAI library

Awesome that this actually works: You simply use the `openai` library,
pointing it to the local server `http://localhost:8000/v1`, 
give a fake OpenAI API key, and it works!

```python
import os
import openai
# modify host, port if you changed the defaults when running the server
openai.api_base = "http://localhost:8000/v1"

completion = openai.ChatCompletion.create(
  model="mydemo",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of Belgium?"}
  ]
)

print(completion.choices[0].message.content)
```

## Use the locally running Llama2 with Langroid

Once you have the above server running (e.g., in a separate terminal tab),
create another virtual env where you install langroid as usual.
Note that local models are supported from version 0.1.59 onwards. 
There are two ways to setup Langroid to use local Llama2 models:

###  Option 1: Via Environment Variables

Make sure you have set up a `.env` file as described in
the [langroid-examples](https://github.com/langroid/langroid-examples#set-up-environment-variables-api-keys-etc) repo.
Then add these variable to the `.env` file:
```bash
# modify if using non-default host, port when you set up the server above
OPENAI_LOCAL.API_BASE=http://localhost:8000/v1
OPENAI_CHAT_MODEL=local
```
In case you are using the non-default context length (by passing `--n_ctx` to the server),
you would need to set an additional environment variable as well, as in this example:
```bash
OPENAI_LOCAL.CONTEXT_LENGTH=1000
```
Since you are using a local model, of course the value of `OPENAI_API_KEY` is irrelevant.
You can set it to a junk value just to make sure you are not using the OpenAI API.

Now any script or test that uses Langroid will use the local model.

### Option 2: By creating config objects in Python Code

Switching to a local Llama model using environment variables is convenient because
you don't need to change any code. 
However, switching models within our Python code offers more flexibility, 
e.g., to programmatically switch 
between using a local model and the OpenAI API, for different types of tasks, or 
allow different agents to use different models. 
Of course, the two options can be combined, as noted in the comments below.

In your script where you want to use the local model,
first specify an instance of `OpenAIGPTConfig` with the relevant values:

```python
from langroid.language_models.openai_gpt import (
    OpenAIGPTConfig, OpenAIChatModel, LocalModelConfig
)
from dotenv import load_dotenv
load_dotenv() # read in .env file
local_llm_config = OpenAIGPTConfig(
    chat_model=OpenAIChatModel.LOCAL,
    local=LocalModelConfig(
        # If omitted, this is obtained from the OPENAI_LOCAL.API_BASE env variable
        api_base="http://localhost:8000/v1", # modify if using non-default host, port
        # if omitted, this is obtained from the OPENAI_LOCAL.CONTEXT_LENGTH env variable
        context_length=1000, # if using non-default context length
    ),
)
```

Then use this config to define a `ChatAgentConfig`, create an agent, wrap it in a Task, and run it:

```python
from langroid.agent.chat_agent import ChatAgentConfig, ChatAgent
from langroid.agent.task import Task

config = ChatAgentConfig(
        system_message="You are a helpful assistant.",
        llm=local_llm_config,
)
agent = ChatAgent(config=config)
task = Task(agent=agent)
task.run()
```

See a full working example of a simple command-line chatbot that you can use with either
the OpenAI GPT4 model or a local llama model, in the `langroid-examples` repo:
[https://github.com/langroid/langroid-examples/blob/main/examples/basic/chat.py](https://github.com/langroid/langroid-examples/blob/main/examples/basic/chat.py).

!!! warning "Tests May Fail, results may be inferior, apps/examples may fail!"
        Be aware that while the above enables you to use Langroid with local llama2 models,
        the tests or examples may fail, and tools and special agents may not work well, 
        if they work at all. The reason is that a lot of the code in Langroid (and for that 
        matter in any LLM framework) relies on a certain level of competence of the underlying
        LLM model. When we say "competence" we are referring to accuracy of responses, alignment,
        and ability to follow instructions. Since there is still (as of Aug 2023) a huge gap between Llama2 models
        and GPT-4, much of the code in Langroid may not work well with Llama2 models.
        It could well be that with much more explicit prompting and many more few-shot examples,
        the behavior of the agents using llama2 models can be improved. But we leave this to the 
        user to explore. Another point to note is that it is possible that llama2 behavior
        is sufficiently "smart" for certain narrowly defined tasks, but again we leave
        this to users to explore.

        



