import os
from operator import itemgetter
from typing import Optional

from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI  
from langchain.prompts import PromptTemplate
import tiktoken

from .model import ModelProvider


class OpenAI(ModelProvider):
    """
    A wrapper class for interacting with OpenAI's API, providing methods to encode text, generate prompts,
    evaluate models, and create LangChain runnables for language model interactions.

    Attributes:
        model_name (str): The name of the OpenAI model to use for evaluations and interactions.
        api_key (str): The API key for accessing OpenAI services.
        model (AsyncOpenAI): An instance of the AsyncOpenAI client for asynchronous API calls.
        enc (Encoder): An encoder instance for encoding and decoding text to and from token representations.
    """
        
    def __init__(self, model_name: str = "gpt-3.5-turbo-0125", api_key: str = None):
        """
        Initializes the OpenAI model provider with a specific model and API key.

        Args:
            model_name (str): The name of the OpenAI model to use. Defaults to 'gpt-3.5-turbo-0125'.
            api_key (str, optional): The API key for OpenAI. If not provided, attempts to use OPENAI_API_KEY from environment variables.
        
        Raises:
            ValueError: If neither api_key is provided nor OPENAI_API_KEY is found in the environment.
        """
        
        if (api_key is None) and (not os.getenv('OPENAI_API_KEY')):
            raise ValueError("Either api_key must be supplied with init, or OPENAI_API_KEY must be in env. Used for evaluation model")

        self.model_name = model_name
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = AsyncOpenAI(api_key=self.api_key)
        self.tokenizer = tiktoken.encoding_for_model(self.model_name)
    
    async def evaluate_model(self, prompt: str) -> str:
        """
        Evaluates a given prompt using the OpenAI model and retrieves the model's response.

        Args:
            prompt (str): The prompt to send to the model.

        Returns:
            str: The content of the model's response to the prompt.
        """
        response = await self.model.chat.completions.create(
                model=self.model_name,
                messages=prompt,
                max_tokens=300,
                temperature=0
            )
        return response.choices[0].message.content
    
    def generate_prompt(self, context: str, retrieval_question: str) -> str | list[dict[str, str]]:
        """
        Generates a structured prompt for querying the model, based on a given context and retrieval question.

        Args:
            context (str): The context or background information relevant to the question.
            retrieval_question (str): The specific question to be answered by the model.

        Returns:
            list[dict[str, str]]: A list of dictionaries representing the structured prompt, including roles and content for system and user messages.
        """
        return [{
                "role": "system",
                "content": "You are a helpful AI bot that answers questions for a user. Keep your response short and direct"
            },
            {
                "role": "user",
                "content": context
            },
            {
                "role": "user",
                "content": f"{retrieval_question} Don't give information outside the document or repeat your findings"
            }]
    
    def encode_text_to_tokens(self, text: str) -> list[int]:
        """
        Encodes a given text string to a sequence of tokens using the model's tokenizer.

        Args:
            text (str): The text to encode.

        Returns:
            list[int]: A list of token IDs representing the encoded text.
        """
        return self.tokenizer.encode(text)
    
    def decode_tokens(self, tokens: list[int], context_length: Optional[int] = None) -> str:
        """
        Decodes a sequence of tokens back into a text string using the model's tokenizer.

        Args:
            tokens (list[int]): The sequence of token IDs to decode.
            context_length (Optional[int], optional): An optional length specifying the number of tokens to decode. If not provided, decodes all tokens.

        Returns:
            str: The decoded text string.
        """
        return self.tokenizer.decode(tokens[:context_length])
    
    def get_langchain_runnable(self, context: str) -> str:
        """
        Creates a LangChain runnable that constructs a prompt based on a given context and a question, 
        queries the OpenAI model, and returns the model's response. This method leverages the LangChain 
        library to build a sequence of operations: extracting input variables, generating a prompt, 
        querying the model, and processing the response.

        Args:
            context (str): The context or background information relevant to the user's question. 
            This context is provided to the model to aid in generating relevant and accurate responses.

        Returns:
            str: A LangChain runnable object that can be executed to obtain the model's response to a 
            dynamically provided question. The runnable encapsulates the entire process from prompt 
            generation to response retrieval.

        Example:
            To use the runnable:
                - Define the context and question.
                - Execute the runnable with these parameters to get the model's response.
        """

        template = """You are a helpful AI bot that answers questions for a user given the context provided.\n 
        Keep your response short and direct. Don't give information outside the document or repeat your findings. Here is your context: 
        \n ------- \n {context} \n ------- \n
        Here is the user question: \n --- --- --- \n {question}"""
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"],
        )
        # Create a LangChain runnable
        model = ChatOpenAI(temperature=0, model=self.model_name)
        chain = ( {"context": lambda x: context,
                  "question": itemgetter("question")} 
                | prompt 
                | model 
                )
        return chain
    

