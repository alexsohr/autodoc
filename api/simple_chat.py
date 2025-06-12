import logging
import os
from typing import List, Optional
from urllib.parse import unquote

from adalflow import GoogleGenAIClient
from adalflow.components.model_client.ollama_client import OllamaClient
from adalflow.core.types import ModelType
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from api.config import get_model_config, configs
from api.data_pipeline import count_tokens, get_file_content
from api.openai_client import OpenAIClient
from api.openrouter_client import OpenRouterClient
from api.bedrock_client import BedrockClient
from api.rag import RAG

# Unified logging setup
from api.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Simple Chat API",
    description="API for streaming and non-streaming chat completions"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Models for the API
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatCompletionRequest(BaseModel):
    """
    Model for requesting a chat completion.
    """
    repo_url: str = Field(..., description="URL of the repository to query")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    filePath: Optional[str] = Field(None, description="Optional path to a file in the repository to include in the prompt")
    token: Optional[str] = Field(None, description="Personal access token for private repositories")
    type: Optional[str] = Field("github", description="Type of repository (e.g., 'github', 'gitlab', 'bitbucket')")

    # model parameters
    provider: str = Field("google", description="Model provider (google, openai, openrouter, ollama, bedrock)")
    model: Optional[str] = Field(None, description="Model name for the specified provider")

    language: Optional[str] = Field("en", description="Language for content generation (e.g., 'en')")
    excluded_dirs: Optional[str] = Field(None, description="Comma-separated list of directories to exclude from processing")
    excluded_files: Optional[str] = Field(None, description="Comma-separated list of file patterns to exclude from processing")
    included_dirs: Optional[str] = Field(None, description="Comma-separated list of directories to include exclusively")
    included_files: Optional[str] = Field(None, description="Comma-separated list of file patterns to include exclusively")

async def _process_chat_request(request: ChatCompletionRequest):
    """
    Helper function to process a chat request (streaming or non-streaming).
    This function contains the common logic for both endpoints.
    """
    try:
        request_rag = RAG(provider=request.provider, model=request.model)

        excluded_dirs = [unquote(d) for d in request.excluded_dirs.split('\n') if d.strip()] if request.excluded_dirs else []
        excluded_files = [unquote(f) for f in request.excluded_files.split('\n') if f.strip()] if request.excluded_files else []
        included_dirs = [unquote(d) for d in request.included_dirs.split('\n') if d.strip()] if request.included_dirs else []
        included_files = [unquote(f) for f in request.included_files.split('\n') if f.strip()] if request.included_files else []

        if excluded_dirs: logger.info(f"Using custom excluded directories: {excluded_dirs}")
        if excluded_files: logger.info(f"Using custom excluded files: {excluded_files}")
        if included_dirs: logger.info(f"Using custom included directories: {included_dirs}")
        if included_files: logger.info(f"Using custom included files: {included_files}")

        request_rag.prepare_retriever(
            request.repo_url, 
            request.type or "github", 
            request.token or "", 
            excluded_dirs, 
            excluded_files, 
            included_dirs, 
            included_files
        )
        logger.info(f"Retriever prepared for {request.repo_url}")
    except Exception as e:
        logger.error(f"Error preparing retriever: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error preparing retriever: {str(e)}")

    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    if request.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user")

    for i in range(0, len(request.messages) - 1, 2):
        if i + 1 < len(request.messages):
            user_msg, assistant_msg = request.messages[i], request.messages[i+1]
            if user_msg.role == "user" and assistant_msg.role == "assistant":
                request_rag.memory.add_dialog_turn(user_query=user_msg.content, assistant_response=assistant_msg.content)

    query = request.messages[-1].content
    context_text = ""
    try:
        rag_query = f"Contexts related to {request.filePath}" if request.filePath else query
        retrieved_documents = request_rag(rag_query, language=request.language)
        
        if retrieved_documents and retrieved_documents[0].documents:
            docs_by_file = {}
            for doc in retrieved_documents[0].documents:
                file_path = doc.meta_data.get('file_path', 'unknown')
                docs_by_file.setdefault(file_path, []).append(doc)
            
            context_parts = [f"## File Path: {fp}\n\n" + "\n\n".join([d.text for d in docs]) for fp, docs in docs_by_file.items()]
            context_text = "\n\n" + "-" * 10 + "\n\n".join(context_parts)
        else:
            logger.warning("No documents retrieved from RAG")
    except Exception as e:
        logger.error(f"Error in RAG retrieval: {str(e)}", exc_info=True)

    repo_name = request.repo_url.split("/")[-1]
    system_prompt_template = configs.get('lang_config', {}).get('languages', {}).get(request.language, {}).get('system_prompt', "{repo_name} - {repo_url}\n\n{context_text}\n\nFile: {file_path}")
    system_prompt = system_prompt_template.format(
        repo_name=repo_name,
        repo_url=request.repo_url,
        context_text=context_text,
        file_path=request.filePath or "the repository"
    )
    
    model_messages = []
    if system_prompt and request.provider != "google":
        model_messages.append({"role": "system", "content": system_prompt})

    for message in request.messages:
        # Use provider-specific role mapping
        if request.provider == "google":
            role = "model" if message.role == "assistant" else "user"
        else:
            # For OpenAI, OpenRouter, Ollama, Bedrock - use standard roles
            role = message.role  # Keep original role (assistant/user)
        model_messages.append({"role": role, "content": message.content})
        
    return model_messages, system_prompt


@app.post("/chat/completions/stream")
async def chat_completions_stream(request: ChatCompletionRequest):
    """Stream a chat completion response."""
    try:
        model_messages, system_prompt = await _process_chat_request(request)
        model_config = get_model_config(request.provider, request.model)
        if not model_config:
            raise HTTPException(status_code=404, detail=f"Model config not found for provider {request.provider} and model {request.model}")

        async def response_stream():
            try:
                client_class = {
                    "google": GoogleGenAIClient, "openai": OpenAIClient, "openrouter": OpenRouterClient,
                    "ollama": OllamaClient, "bedrock": BedrockClient
                }.get(request.provider)
                
                if not client_class:
                    raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")

                client = client_class()
                api_kwargs = {
                    "model": model_config.get('model_kwargs', {}).get('model'),
                    "messages": model_messages,
                    "stream": True
                }
                stream = await client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                logger.error(f"Error during streaming: {str(e)}", exc_info=True)
                yield f"Error: {str(e)}"

        return StreamingResponse(response_stream(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in stream endpoint: {str(e)}", exc_info=True)
        return StreamingResponse(iter([f"Error: {e.detail if isinstance(e, HTTPException) else 'An unexpected error occurred.'}"]), status_code=e.status_code if isinstance(e, HTTPException) else 500)


@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Provide a non-streaming chat completion response."""
    try:
        model_messages, system_prompt = await _process_chat_request(request)
        model_config = get_model_config(request.provider, request.model)
        if not model_config:
            raise HTTPException(status_code=404, detail=f"Model config not found for provider {request.provider} and model {request.model}")

        client_class = {
            "google": GoogleGenAIClient, "openai": OpenAIClient, "openrouter": OpenRouterClient,
            "ollama": OllamaClient, "bedrock": BedrockClient
        }.get(request.provider)

        if not client_class:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {request.provider}")

        client = client_class()
        api_kwargs = {
            "model": model_config.get('model_kwargs', {}).get('model'),
            "messages": model_messages,
            "stream": False
        }
        response = await client.acall(api_kwargs=api_kwargs, model_type=ModelType.LLM)
        full_response = response.raw_response if response and response.raw_response else ""

        return JSONResponse(content={"role": "assistant", "content": full_response})

    except Exception as e:
        logger.error(f"Error in completion endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=e.status_code if isinstance(e, HTTPException) else 500, detail=e.detail if isinstance(e, HTTPException) else "An unexpected error occurred.")


@app.get("/")
async def root():
    """Root endpoint to check if the API is running"""
    return {"message": "Welcome to the Simple Chat API"} 