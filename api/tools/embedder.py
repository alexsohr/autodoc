import adalflow as adal
import logging

from api.config import configs

logger = logging.getLogger(__name__)

def get_embedder(is_local_ollama: bool = False) -> adal.Embedder:
    if is_local_ollama:
        embedder_config = configs["embedder_ollama"]
    else:
        embedder_config = configs["embedder"]

    logger.debug(f"=== EMBEDDER DEBUG ===")
    logger.debug(f"Using local ollama: {is_local_ollama}")
    logger.debug(f"Embedder config: {embedder_config}")

    # --- Initialize Embedder ---
    model_client_class = embedder_config["model_client"]
    if "initialize_kwargs" in embedder_config:
        logger.debug(f"Found initialize_kwargs: {embedder_config['initialize_kwargs']}")
        model_client = model_client_class(**embedder_config["initialize_kwargs"])
    else:
        logger.debug("No initialize_kwargs found, using default initialization")
        model_client = model_client_class()
    
    logger.debug(f"Created model client: {model_client}")
    if hasattr(model_client, '_api_key'):
        logger.debug(f"Model client API key set: {bool(model_client._api_key)}")
        if model_client._api_key:
            logger.debug(f"API key starts with sk-: {model_client._api_key.startswith('sk-')}")
    
    embedder = adal.Embedder(
        model_client=model_client,
        model_kwargs=embedder_config["model_kwargs"],
    )
    return embedder
