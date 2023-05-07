from llmagent.utils.logging import setup_colored_logging
from llmagent.utils import configuration
import typer
from llmagent.language_models.base import LLMMessage, Role
from llmagent.agent.base import AgentConfig
from llmagent.agent.chat_agent import ChatAgent
from llmagent.vector_store.qdrantdb import QdrantDBConfig
from llmagent.embedding_models.models import OpenAIEmbeddingsConfig
from llmagent.vector_store.base import VectorStoreConfig
from llmagent.language_models.base import LLMConfig
from llmagent.parsing.parser import ParsingConfig
from llmagent.prompts.prompts_config import PromptsConfig
from rich import print

app = typer.Typer()

setup_colored_logging()


class DockerChatAgentConfig(AgentConfig):
    debug: bool = False
    stream: bool = True
    max_tokens: int = 200
    vecdb: VectorStoreConfig = QdrantDBConfig(
        type="qdrant",
        collection_name="test",
        storage_path=".qdrant/test/",
        embedding=OpenAIEmbeddingsConfig(
            model_type="openai",
            model_name="text-embedding-ada-002",
            dims=1536,
        ),
    )
    llm: LLMConfig = LLMConfig(type="openai")
    parsing: ParsingConfig = ParsingConfig(
        chunk_size=100,
        chunk_overlap=10,
    )

    prompts: PromptsConfig = PromptsConfig(
        max_tokens=200,
    )


def chat(config: DockerChatAgentConfig) -> None:
    configuration.update_global_settings(config, keys=["debug", "stream"])

    print("[blue]Hello I am here to make your dockerfile!")
    print("[cyan]Enter x or q to quit")
    task = [
        LLMMessage(
            role=Role.SYSTEM,
            content="""You are a devops engineer. For a given repo URL, you have to 
            write a dockerfile to containerize it. Come up with a plan to do this,
            breaking it down into small steps. At each step, show what you are 
            THINKING, and ask me what you need to know in order to complete your task. 
            When I answer it, think about your next step, show me your THINKING, 
            ASK me another question, and so on, until you say you are DONE, and show 
            me the completed dockerfile.""",
        ),
        LLMMessage(
            role=Role.SYSTEM,
            name="example_assistant",
            content="""
            THINKING: I first need to know which repo to containerize, 
            so I need to know the URL.
            QUESTION: What is the URL of the repo?
            """.strip(),
        ),
        LLMMessage(
            role=Role.SYSTEM,
            name="example_user",
            content="The URL is https://github.com/blah/bar",
        ),
        LLMMessage(
            role=Role.SYSTEM,
            name="example_assistant",
            content="""
            THINKING: thank you. The dockerfile setup depends on the 
            language.
            QUESTION: What language is the repo written in?
            """.strip(),
        ),
        LLMMessage(role=Role.SYSTEM, name="example_user", content="Python"),
        LLMMessage(
            role=Role.SYSTEM,
            name="example_assistant",
            content="""
            THINKING: thank you. The python version can make a big difference to the 
            docker file structure and dependencies.
            QUESTION: What version of python is the repo written in?
            """.strip(),
        ),
        LLMMessage(role=Role.SYSTEM, name="example_user", content="3.8"),
        LLMMessage(
            role=Role.USER,
            content="""You are a sophisticated devops engineer, and you 
                           need to write a dockerfile for a repo. IGNORE ALL DETAILS 
                           in the above conversation, which was only an example.
                           Keep in mind your task and start FRESH.
                           Please think in small steps, and do this gradually, and focus on what 
                           information you need to know to accomplish your task.
                           Please send me your first THINKING, and QUESTION.
                           For each question, whenever possile, give me a numbered 
                           list of choices so I can easily select one or a few.
                           VERY IMPORTANT: 
                           (a) Make sure you have everything you need 
                               before you start generating a dockerfile.
                           (b) Be EXHAUSTIVE: ask me about ALL the INFO you may 
                           possibly need to generate the docker file!!
                           """,
        ),
    ]

    agent = ChatAgent(config, task)
    agent.run()


@app.command()
def main(debug: bool = typer.Option(False, "--debug", "-d", help="debug mode")) -> None:
    config = DockerChatAgentConfig(debug=debug)
    chat(config)


if __name__ == "__main__":
    app()
