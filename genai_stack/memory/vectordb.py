from typing import Optional, Dict
from langchain.memory import VectorStoreRetrieverMemory
from genai_stack.memory.base import BaseMemory, BaseMemoryConfig, BaseMemoryConfigModel
from genai_stack.memory.utils import parse_chat_conversation_history_search_result, extract_text, format_index_name


class VectorDBMemoryConfigModel(BaseMemoryConfigModel):
    """Data Model for the configs"""

    retrieve_parameters:Optional[Dict] = {
        'search_type':'similarity',
        'search_kwargs':{'k':4}
    }
    chromadb:Optional[Dict] = {
        'index_name':'Test_history'
    }
    weaviate:Optional[Dict] = {
        'index_name':'Test_history',
        'text_key':'chat_history'
    }


class VectorDBMemoryConfig(BaseMemoryConfig):
    data_model = VectorDBMemoryConfigModel


class VectorDBMemory(BaseMemory):
    config_class = VectorDBMemoryConfig
    memory = None
    lc_client = None

    def _post_init(self, *args, **kwargs):
        config:VectorDBMemoryConfigModel  = self.config.config_data

        # We have to pass the index name in two places, one is to Vectordb and to VectorStoreRetriever.
        # in case of weaviate, if we pass the index name in lowercase, the weaviate will internally convert it to pascal for schema/collection
        # eg passed index name => chatting, weaviate converted to Chatting,
        # But if VectorStoreRetriever use the lowercased index name, it throws index error, since the weaviate changed to pascal.
        # To handle this we are converting the index name to pascal before intializing the Vectordb and Vectorstoreretriever, and to 
        # maintain the consistency, we are also converting the chromadb index name to pascal, instead of conditionally doing only for weaviate.
        kwarg_map = format_index_name(config)        

        self.lc_client = self.mediator.create_index(kwarg_map)

        retriever = self.lc_client.as_retriever(
            **{k:v for k,v in config.retrieve_parameters.items()}
        )

        cls_name = self.lc_client.__class__.__name__

        # We should also pass the configuration to VectorStoreRetriever. so after creating collection we get langchain vector client. 
        # we match the kwarg_map with the class name of the initialized vector client.
        # and in langchain, class name for chroma client is "Chroma", so to match with the kwarg_map we append DB to Chroma 
        if cls_name == "Chroma":
            cls_name = cls_name+"DB"

        self.memory = VectorStoreRetrieverMemory(
            retriever=retriever,
            memory_key=kwarg_map.get(cls_name)['index_name'],
            return_docs=True
        )

    def add_text(self, user_text: str, model_text: str):
        self.memory.save_context({"input": user_text}, {"output": model_text})

    def get_chat_history(self, query):
        documents = self.memory.load_memory_variables({"prompt": query})[self.memory.memory_key]
        return parse_chat_conversation_history_search_result(search_results=documents)