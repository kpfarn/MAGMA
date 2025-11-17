"""
Cloud storage configuration for MAGMA to reduce local disk usage
"""

import os
from typing import Optional

class CloudStorageConfig:
    """Configuration for using cloud storage to reduce local disk usage"""
    
    def __init__(self):
        # Use environment variables for cloud storage
        self.use_cloud_cache = os.getenv('MAGMA_USE_CLOUD_CACHE', 'false').lower() == 'true'
        self.cloud_cache_url = os.getenv('MAGMA_CLOUD_CACHE_URL', '')
        
    def get_model_cache_dir(self) -> Optional[str]:
        """Return cloud cache directory if configured, otherwise None"""
        if self.use_cloud_cache and self.cloud_cache_url:
            return self.cloud_cache_url
        return None
    
    def should_offload_models(self) -> bool:
        """Whether to offload models to cloud storage"""
        return self.use_cloud_cache

# Example usage in your LLM interface:
# from cloud_storage_config import CloudStorageConfig
# 
# cloud_config = CloudStorageConfig()
# if cloud_config.should_offload_models():
#     # Use model offloading
#     model = AutoModelForCausalLM.from_pretrained(
#         model_id,
#         cache_dir=cloud_config.get_model_cache_dir(),
#         torch_dtype=torch.float16  # Use half precision
#     )

